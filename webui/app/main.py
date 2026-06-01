from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.datastructures import Headers, UploadFile as StarletteUploadFile

from .config import get_settings
from .models import ServiceResponse, VkInboundPayload
from .repository import InMemoryRepository
from .services.auth import HttpAuthService, ServiceEndpoints
from .services.chat import MockChatService
from .services.vk_bot import DEFAULT_VK_PROMPT
from .services.vk_bridge import VkBridgeService


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
    web_ui=settings.web_ui_base_url,
)
auth_service = HttpAuthService(service_endpoints, settings.access_token_minutes)
chat_service = MockChatService(repository, service_endpoints)
vk_bridge = VkBridgeService(settings)

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
        "service_endpoints": {
            "auth": settings.auth_service_base_url,
            "service_a": settings.service_a_base_url,
            "web_ui": settings.web_ui_base_url,
        },
        **extra,
    }


def page_response(template_name: str, request: Request, session=None, **extra):
    response = templates.TemplateResponse(
        request,
        template_name,
        page_context(request, session=session, **extra),
    )
    if session is not None and getattr(session, "refreshed", False):
        _set_session_cookies(response, session)
    return response


def _build_vk_upload_file(payload: VkInboundPayload) -> StarletteUploadFile:
    attachment = payload.text_attachment
    if attachment is None:
        raise HTTPException(
            status_code=400,
            detail="Для интеграции VK сейчас требуется текстовое вложение.",
        )

    content = attachment.content.encode("utf-8")
    headers = Headers({"content-type": "text/plain; charset=utf-8"})
    return StarletteUploadFile(
        file=BytesIO(content),
        filename=attachment.name,
        size=len(content),
        headers=headers,
    )


def _build_vk_result_message(payload: ServiceResponse) -> str:
    if payload.success:
        parts = ["Lakmus подготовил ответ."]
        if payload.explanation.strip():
            parts.append(payload.explanation.strip())
        else:
            parts.append("Ответ получен.")
        if payload.diagram.strip():
            parts.append("Диаграмма:")
            parts.append(payload.diagram.strip()[:1200])
        return "\n\n".join(parts)

    error_text = payload.error.strip() or "Сервис вернул ошибку без подробностей."
    return "\n\n".join(
        [
            "Lakmus не смог завершить обработку.",
            error_text[:1500],
        ]
    )


async def _notify_vk_if_needed(request_meta: dict, payload: ServiceResponse) -> dict:
    if request_meta.get("source") != "vk":
        return {"channel": "web"}

    peer_id = request_meta.get("vk_peer_id")
    if not isinstance(peer_id, int):
        return {"channel": "vk", "ok": False, "reason": "missing_peer_id"}
    if not vk_bridge.is_configured():
        return {"channel": "vk", "ok": False, "reason": "vk_not_configured"}

    text = _build_vk_result_message(payload)
    try:
        await vk_bridge.send_message(peer_id=peer_id, text=text)
        return {"channel": "vk", "ok": True}
    except Exception as exc:
        return {"channel": "vk", "ok": False, "reason": str(exc)}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    session = await _restore_session(request)
    return page_response("landing.html", request, session=session)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", page_context(request))


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
    username = payload.get("email", payload.get("username", ""))
    password = payload.get("password", "")
    session = await auth_service.login(username, password)
    if session is None:
        raise HTTPException(status_code=400, detail="Введите email и password")

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


@app.delete("/api/chats/{chat_id}")
async def delete_chat_api(chat_id: str, session=Depends(require_session)):
    removed = await chat_service.delete_chat(session.user.id, chat_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Chat not found")

    chats = await chat_service.list_chats(session.user.id)
    return {
        "ok": True,
        "remaining": [
            {
                "id": chat.id,
                "title": chat.title,
                "updated_at": chat.updated_at.isoformat(),
                "message_count": len(chat.messages),
            }
            for chat in chats
        ],
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
    if file is None or not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Сейчас для отправки в сервис А нужно прикрепить файл.",
        )

    try:
        pending = await chat_service.submit(session.user.id, chat_id, prompt, file)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    fresh_chat = await chat_service.get_chat(session.user.id, chat_id)
    return {
        "request": pending.model_dump(mode="json"),
        "chat": fresh_chat.model_dump(mode="json"),
    }


@app.post("/api/integrations/vk/inbound")
async def vk_inbound_api(payload: VkInboundPayload):
    upload_file = _build_vk_upload_file(payload)
    prompt = payload.text.strip() or DEFAULT_VK_PROMPT

    user = repository.get_or_create_user(f"vk_{payload.user_id}")
    created_at = datetime.now().strftime("%d.%m %H:%M")
    chat = await chat_service.create_chat(
        user.id,
        title=f"VK · {created_at}",
        assistant_message=None,
    )

    request_meta = {
        "source": "vk",
        "vk_peer_id": payload.peer_id,
        "vk_user_id": payload.user_id,
        "vk_message_id": payload.message_id,
        "vk_conversation_message_id": payload.conversation_message_id,
        "vk_received_at": payload.received_at.isoformat() if payload.received_at else None,
    }

    try:
        pending = await chat_service.submit(
            user.id,
            chat.id,
            prompt,
            upload_file,
            request_meta=request_meta,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "ok": True,
        "user_id": user.id,
        "chat_id": chat.id,
        "request_id": pending.id,
    }


@app.post("/user/{user_id}/chat/{chat_id}/response")
async def service_b_response_api(user_id: str, chat_id: str, payload: ServiceResponse):
    if payload.user_id != user_id or payload.chat_id != chat_id:
        raise HTTPException(
            status_code=400,
            detail="user_id или chat_id в path не совпадают с body",
        )

    pending = await chat_service.accept_response(payload)
    if pending is None:
        raise HTTPException(status_code=404, detail="Active request for user/chat not found")

    delivery = await _notify_vk_if_needed(pending.meta, payload)
    return {
        "ok": True,
        "request": pending.model_dump(mode="json"),
        "response": payload.model_dump(mode="json"),
        "delivery": delivery,
    }
