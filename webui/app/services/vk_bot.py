from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..config import Settings


logger = logging.getLogger(__name__)

VK_API_BASE = "https://api.vk.com/method/"
TEXT_FILE_EXTENSIONS = {"txt", "md", "csv", "tsv", "json", "log"}
START_COMMANDS = {"start", "/start", "начать", "/начать", "привет", "hello"}
HELP_COMMANDS = {"help", "/help", "помощь", "/помощь"}
STATUS_COMMANDS = {"status", "/status", "статус", "/статус"}
DEFAULT_VK_PROMPT = "Проанализируй содержимое текстового файла и кратко верни результат."


class VkApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class VkBotSettings:
    group_id: int
    access_token: str
    api_version: str
    long_poll_wait: int
    forward_url: str
    payload_log_path: str
    max_text_file_bytes: int

    @classmethod
    def from_app_settings(cls, settings: Settings) -> "VkBotSettings":
        return cls(
            group_id=settings.vk_group_id,
            access_token=settings.vk_access_token,
            api_version=settings.vk_api_version,
            long_poll_wait=settings.vk_long_poll_wait,
            forward_url=settings.vk_forward_url,
            payload_log_path=settings.vk_payload_log_path,
            max_text_file_bytes=settings.vk_max_text_file_bytes,
        )

    def validate(self) -> None:
        missing: list[str] = []
        if self.group_id <= 0:
            missing.append("WEBUI_VK_GROUP_ID")
        if not self.access_token.strip():
            missing.append("WEBUI_VK_ACCESS_TOKEN")
        if missing:
            joined = ", ".join(missing)
            raise ValueError(
                "Не заполнены настройки VK-бота: "
                f"{joined}. Укажи их в переменных окружения или в Run Configuration."
            )


@dataclass
class LongPollSession:
    server: str
    key: str
    ts: str


class VkApiClient:
    def __init__(self, settings: VkBotSettings) -> None:
        self.settings = settings

    def call_method(self, method: str, **params: Any) -> Any:
        payload = {
            **params,
            "access_token": self.settings.access_token,
            "v": self.settings.api_version,
        }
        encoded = urlencode(payload, doseq=True).encode("utf-8")
        request = Request(
            f"{VK_API_BASE}{method}",
            data=encoded,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise VkApiError(f"HTTP {exc.code} while calling {method}: {body}") from exc
        except URLError as exc:
            raise VkApiError(f"Network error while calling {method}: {exc}") from exc

        data = json.loads(raw)
        if "error" in data:
            error = data["error"]
            raise VkApiError(
                f"VK API error {error.get('error_code')}: {error.get('error_msg')}"
            )
        return data["response"]

    def get_long_poll_session(self) -> LongPollSession:
        response = self.call_method(
            "groups.getLongPollServer",
            group_id=self.settings.group_id,
        )
        return LongPollSession(
            server=response["server"],
            key=response["key"],
            ts=response["ts"],
        )

    def enable_message_new_events(self) -> None:
        self.call_method(
            "groups.setLongPollSettings",
            group_id=self.settings.group_id,
            enabled=1,
            api_version=self.settings.api_version,
            message_new=1,
        )

    def send_message(self, peer_id: int, text: str) -> None:
        self.call_method(
            "messages.send",
            peer_id=peer_id,
            random_id=random.randint(1, 2_147_483_647),
            message=text,
        )

    def poll(self, session: LongPollSession) -> dict[str, Any]:
        query = urlencode(
            {
                "act": "a_check",
                "key": session.key,
                "ts": session.ts,
                "wait": self.settings.long_poll_wait,
            }
        )
        request = Request(
            f"{session.server}?{query}",
            headers={"User-Agent": "LakmusVkBot/1.0"},
        )
        try:
            with urlopen(request, timeout=self.settings.long_poll_wait + 10) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise VkApiError(f"Long Poll HTTP {exc.code}: {body}") from exc
        except URLError as exc:
            raise VkApiError(f"Long Poll network error: {exc}") from exc
        return json.loads(raw)

    def download_text_file(self, url: str) -> str:
        request = Request(url, headers={"User-Agent": "LakmusVkBot/1.0"})
        with urlopen(request, timeout=30) as response:
            raw = response.read(self.settings.max_text_file_bytes + 1)
        if len(raw) > self.settings.max_text_file_bytes:
            raise ValueError(
                "Файл слишком большой для шаблонного VK-бота. "
                "Сейчас поддерживается только небольшое текстовое вложение."
            )
        for encoding in ("utf-8", "cp1251", "utf-16"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")


class VkMessageHandler:
    def __init__(self, settings: VkBotSettings, api_client: VkApiClient) -> None:
        self.settings = settings
        self.api_client = api_client

    def handle_update(self, update: dict[str, Any]) -> None:
        if update.get("type") != "message_new":
            return

        message = self._extract_message(update)
        if not message:
            return
        if int(message.get("out", 0)) == 1:
            return

        peer_id = int(message.get("peer_id") or 0)
        from_id = int(message.get("from_id") or message.get("user_id") or 0)
        if peer_id <= 0 or from_id <= 0:
            return

        normalized = self._normalize_payload(update, message)
        self._append_payload_log(normalized)

        forwarded = False
        if self._should_forward_payload(normalized):
            forwarded = self._forward_payload(normalized)

        reply = self._build_reply(normalized, forwarded=forwarded)
        self.api_client.send_message(peer_id=peer_id, text=reply)

    def _extract_message(self, update: dict[str, Any]) -> dict[str, Any]:
        obj = update.get("object") or {}
        if isinstance(obj, dict) and "message" in obj and isinstance(obj["message"], dict):
            return obj["message"]
        if isinstance(obj, dict):
            return obj
        return {}

    def _normalize_payload(
        self,
        update: dict[str, Any],
        message: dict[str, Any],
    ) -> dict[str, Any]:
        text = (message.get("text") or message.get("message") or "").strip()
        attachment = self._extract_first_text_attachment(message.get("attachments") or [])
        return {
            "platform": "vk",
            "event_type": update.get("type"),
            "group_id": update.get("group_id"),
            "user_id": str(message.get("from_id") or message.get("user_id") or ""),
            "peer_id": message.get("peer_id"),
            "message_id": message.get("id"),
            "conversation_message_id": message.get("conversation_message_id"),
            "text": text,
            "text_attachment": attachment,
            "received_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    def _extract_first_text_attachment(
        self,
        attachments: list[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        for attachment in attachments:
            if attachment.get("type") != "doc":
                continue
            doc = attachment.get("doc") or {}
            title = doc.get("title") or "document"
            ext = (doc.get("ext") or Path(title).suffix.lstrip(".")).lower()
            url = doc.get("url")
            if ext not in TEXT_FILE_EXTENSIONS or not url:
                continue
            try:
                content = self.api_client.download_text_file(url)
            except Exception as exc:
                logger.warning("Cannot read VK document %s: %s", title, exc)
                content = ""
            return {
                "name": title,
                "ext": ext,
                "size": doc.get("size"),
                "url": url,
                "content": content,
            }
        return None

    def _append_payload_log(self, payload: dict[str, Any]) -> None:
        path = Path(self.settings.payload_log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _should_forward_payload(self, payload: dict[str, Any]) -> bool:
        if not self.settings.forward_url.strip():
            return False
        text = str(payload.get("text") or "").strip().lower()
        if text in START_COMMANDS or text in HELP_COMMANDS or text in STATUS_COMMANDS:
            return False
        return bool(payload.get("text_attachment"))

    def _forward_payload(self, payload: dict[str, Any]) -> bool:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            self.settings.forward_url,
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                return 200 <= response.status < 300
        except Exception as exc:
            logger.warning("Cannot forward VK payload to %s: %s", self.settings.forward_url, exc)
            return False

    def _build_reply(self, payload: dict[str, Any], *, forwarded: bool) -> str:
        text = str(payload.get("text") or "").strip()
        attachment = payload.get("text_attachment")
        command = text.lower()

        if command in START_COMMANDS:
            return (
                "Привет. Я VK-бот Лакмуса.\n\n"
                "Сейчас я умею:\n"
                "1. отвечать на базовые команды;\n"
                "2. принимать одно текстовое сообщение;\n"
                "3. считывать одно текстовое вложение.\n\n"
                "Напиши /help, и я покажу подсказки."
            )

        if command in HELP_COMMANDS:
            return (
                "Доступные команды:\n"
                "/start — приветствие\n"
                "/help — подсказка\n"
                "/status — проверить, что бот активен\n\n"
                "Для обработки через Lakmus сейчас лучше отправлять:\n"
                "- текстовый файл: .txt, .md, .csv, .tsv, .json, .log;\n"
                "- в тексте сообщения короткий промпт к файлу.\n\n"
                "Если промпт не указан, будет использован шаблонный запрос."
            )

        if command in STATUS_COMMANDS:
            mode = "внешний контур подключен" if self.settings.forward_url.strip() else "работаю в шаблонном режиме"
            return f"Бот активен. Long Poll слушает новые сообщения, {mode}."

        if attachment and forwarded:
            prompt_preview = text or DEFAULT_VK_PROMPT
            return (
                "Принял файл и отправил запрос в Lakmus.\n\n"
                f"Промпт: {self._clip(prompt_preview, 220)}\n"
                "Когда сервисы обработают запрос, я пришлю итог в этот же диалог."
            )

        if attachment and self.settings.forward_url.strip():
            return (
                "Файл увидел, но не смог передать его во внутренний контур.\n"
                "Проверь, что web UI запущен и доступен по WEBUI_VK_FORWARD_URL."
            )

        parts: list[str] = ["Сообщение получено."]
        if text:
            parts.append(f"Текст: {self._clip(text, 300)}")
        if attachment:
            parts.append(f"Файл: {attachment['name']}")
            if attachment.get("content"):
                parts.append("Фрагмент файла:")
                parts.append(self._clip(str(attachment["content"]).strip(), 500))
        else:
            parts.append("Чтобы отправить запрос в Lakmus, пришли текстовое вложение и, при желании, промпт в сообщении.")
        parts.append("Команда /help покажет доступные действия.")
        return "\n\n".join(parts)

    def _clip(self, value: str, limit: int) -> str:
        compact = " ".join(value.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 1] + "…"


class VkLongPollBot:
    def __init__(self, settings: VkBotSettings) -> None:
        settings.validate()
        self.settings = settings
        self.api_client = VkApiClient(settings)
        self.handler = VkMessageHandler(settings, self.api_client)

    def setup(self) -> None:
        self.api_client.enable_message_new_events()

    def run_forever(self) -> None:
        session = self.api_client.get_long_poll_session()
        logger.info("VK bot is listening for new messages")

        while True:
            try:
                response = self.api_client.poll(session)
                failed = response.get("failed")
                if failed == 1:
                    session.ts = str(response["ts"])
                    continue
                if failed in {2, 3}:
                    logger.info("Refreshing Long Poll session")
                    session = self.api_client.get_long_poll_session()
                    continue

                session.ts = str(response.get("ts", session.ts))
                for update in response.get("updates", []):
                    self.handler.handle_update(update)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                logger.warning("VK polling error: %s", exc)
                time.sleep(3)
                session = self.api_client.get_long_poll_session()
