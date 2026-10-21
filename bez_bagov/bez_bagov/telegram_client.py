import json
import logging
import time
import urllib.error
import urllib.request

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
    payload = json.dumps({
        "chat_id": chat_id,
        "text": f"{prefix}{text}",
        "disable_web_page_preview": True,
    }).encode("utf-8")

    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    headers = {"Content-Type": "application/json"}

    last_err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = resp.read()
            data = json.loads(body or b"{}")
            if not data.get("ok"):
                logger.error("Telegram API error: %s", data)
                return False
            return True
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as e:
            last_err = e
            if attempt < 2:
                time.sleep(1)
                continue

    logger.exception("Telegram send failed after retries: %s", last_err)
    return False