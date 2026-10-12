import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


def send_to_telegram(text: str, session_id: str = "") -> bool:
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        logger.warning("Telegram не настроен: нет TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
        return False

    prefix = f"[chat:{session_id[:8]}] " if session_id else ""
    payload = {
        "chat_id": chat_id,
        "text": f"{prefix}{text}",
        "disable_web_page_preview": True,
    }
    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    try:
        r = httpx.post(url, json=payload, timeout=5)
        r.raise_for_status()
        return True
    except httpx.HTTPError as e:
        logger.exception("Telegram send failed: %s", e)
        return False