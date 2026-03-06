from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.websockets import WebSocket, WebSocketDisconnect

from .config import get_settings
from .repository import InMemoryRepository
from .services.auth import MockAuthService, ServiceEndpoints
from .services.chat import MockChatService


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
settings = get_settings()
repository = InMemoryRepository(
    access_minutes=settings.access_token_minutes,
    refresh_days=settings.refresh_token_days,
)
service_endpoints = ServiceEndpoints(
    auth=settings.auth_service_base_url,
    service_a=settings.service_a_base_url,
    service_b=settings.service_b_base_url,
)
auth_service = MockAuthService(repository, service_endpoints)
chat_service = MockChatService(repository, service_endpoints)

app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def _set_session_cookies(response, session) -> None:
    response.set_cookie(
        key=settings.access_cookie_name,
        value=session.access_token,
        httponly=True,
        samesite="lax",
        max_age=settings.access_token_minutes * 60,
    )
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=session.refresh_token,
        httponly=True,
        samesite="lax",
        max_age=settings.refresh_token_days * 24 * 60 * 60,
    )


def _clear_session_cookies(response: JSONResponse) -> None:
    response.delete_cookie(settings.access_cookie_name)
    response.delete_cookie(settings.refresh_cookie_name)


async def _restore_session(request: Request):
    access_token = request.cookies.get(settings.access_cookie_name)
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    return await auth_service.validate_or_refresh(access_token, refresh_token)


async def require_session(request: Request):
    session = await _restore_session(request)
    if session is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return session


def page_context(request: Request, **extra):
    return {
        "request": request,
        "app_name": settings.app_name,
        "service_endpoints": service_endpoints,
        **extra,
    }


def page_response(template_name: str, request: Request, session=None, **extra):
    response = templates.TemplateResponse(
        template_name,
        page_context(request, session=session, **extra),
    )
    if session is not None and getattr(session, "refreshed", False):
        _set_session_cookies(response, session)
    return response


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    session = await _restore_session(request)
    return page_response("landing.html", request, session=session)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", page_context(request))


@app.get("/workspace", response_class=HTMLResponse)
async def workspace_page(request: Request):
    session = await _restore_session(request)
    if session is None:
        return RedirectResponse(url="/login", status_code=303)
    active_chat = await chat_service.get_or_create_default_chat(session.user.id)
    return page_response(
        "workspace.html",
        request,
        session=session,
        initial_chat_id=active_chat.id,
    )


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    session = await _restore_session(request)
    if session is None:
        return RedirectResponse(url="/login", status_code=303)
    chats = await chat_service.list_chats(session.user.id)
    return page_response(
        "history.html",
        request,
        session=session,
        chats=chats,
    )


@app.get("/api/auth/status")
async def auth_status(request: Request):
    session = await _restore_session(request)
    if session is None:
        response = JSONResponse({"authenticated": False}, status_code=401)
        _clear_session_cookies(response)
        return response
    response = JSONResponse(
        {
            "authenticated": True,
            "user": session.user.model_dump(),
            "refreshed": session.refreshed,
        }
    )
    if session.refreshed:
        _set_session_cookies(response, session)
    return response


@app.post("/api/auth/login")
async def login_api(request: Request):
    payload = await request.json()
    username = payload.get("username", "")
    password = payload.get("password", "")
    session = await auth_service.login(username, password)
    if session is None:
        raise HTTPException(status_code=400, detail="Введите username и password")
    response = JSONResponse(
        {
            "authenticated": True,
            "user": session.user.model_dump(),
        }
    )
    _set_session_cookies(response, session)
    return response


@app.post("/api/auth/logout")
async def logout_api(request: Request):
    access_token = request.cookies.get(settings.access_cookie_name)
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    await auth_service.logout(access_token, refresh_token)
    response = JSONResponse({"ok": True})
    _clear_session_cookies(response)
    return response


@app.get("/api/chats")
async def list_chats_api(session=Depends(require_session)):
    chats = await chat_service.list_chats(session.user.id)
    return {
        "items": [
            {
                "id": chat.id,
                "title": chat.title,
                "updated_at": chat.updated_at.isoformat(),
                "message_count": len(chat.messages),
            }
            for chat in chats
        ]
    }


@app.post("/api/chats")
async def create_chat_api(session=Depends(require_session)):
    chat = await chat_service.create_chat(session.user.id)
    return {
        "chat": {
            "id": chat.id,
            "title": chat.title,
            "updated_at": chat.updated_at.isoformat(),
            "message_count": len(chat.messages),
        }
    }


@app.get("/api/chats/{chat_id}")
async def get_chat_api(chat_id: str, session=Depends(require_session)):
    chat = await chat_service.get_chat(session.user.id, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"chat": chat.model_dump(mode="json")}


@app.post("/api/chats/{chat_id}/messages")
async def send_message_api(
    chat_id: str,
    prompt: str = Form(...),
    file: Optional[UploadFile] = File(default=None),
    session=Depends(require_session),
):
    chat = await chat_service.get_chat(session.user.id, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    file_name = file.filename if file and file.filename else None
    pending = await chat_service.submit(session.user.id, chat_id, prompt, file_name)
    fresh_chat = await chat_service.get_chat(session.user.id, chat_id)
    return {
        "request": pending.model_dump(mode="json"),
        "chat": fresh_chat.model_dump(mode="json"),
    }


@app.get("/api/requests/{request_id}")
async def request_status_api(request_id: str, session=Depends(require_session)):
    pending = await chat_service.get_request(request_id)
    if pending is None or pending.user_id != session.user.id:
        raise HTTPException(status_code=404, detail="Request not found")
    return {"request": pending.model_dump(mode="json")}


@app.websocket("/ws/requests/{request_id}")
async def request_status_ws(websocket: WebSocket, request_id: str):
    access_token = websocket.cookies.get(settings.access_cookie_name)
    refresh_token = websocket.cookies.get(settings.refresh_cookie_name)
    session = await auth_service.validate_or_refresh(access_token, refresh_token)
    if session is None:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    try:
        while True:
            request_state = await chat_service.get_request(request_id)
            if request_state is None or request_state.user_id != session.user.id:
                await websocket.send_json({"status": "not_found"})
                await websocket.close(code=4404)
                return
            await websocket.send_json(request_state.model_dump(mode="json"))
            if request_state.status in {"completed", "failed"}:
                await websocket.close(code=1000)
                return
            await websocket.receive_text()
    except WebSocketDisconnect:
        return




