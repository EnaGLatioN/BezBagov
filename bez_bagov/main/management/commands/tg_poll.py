import json
import re
import time

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand

from bez_bagov import redis_client as rc

# ловит [chat:<sid>] где sid — 8..64 символа hex/uuid
SID_RE = re.compile(r"\[chat:([0-9a-fA-F-]{8,64})\]")


class Command(BaseCommand):
    help = "Long-polling Telegram -> Redis (ответы оператора в чат на сайте)"

    def handle(self, *args, **opts):
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        if not token:
            self.stderr.write("TELEGRAM_BOT_TOKEN не задан")
            return

        self._token = token
        offset = 0
        self.stdout.write("polling started")

        while True:
            try:
                r = self._get_updates(token, offset)
                data = r.json()
                if not data.get("ok"):
                    self.stderr.write(f"telegram error: {data}")
                    time.sleep(1)
                    continue

                for upd in data.get("result", []):
                    offset = upd["update_id"] + 1
                    self._handle_update(upd)

            except httpx.HTTPError as e:
                self.stderr.write(f"poll error: {e!r}")
                time.sleep(1)
            except Exception as e:
                self.stderr.write(f"unexpected error: {e!r}")
                time.sleep(1)

    def _get_updates(self, token: str, offset: int) -> httpx.Response:
        # 10 попыток — переживаем "моргание" сети
        last_err = None
        for attempt in range(10):
            try:
                return httpx.get(
                    f"https://api.telegram.org/bot{token}/getUpdates",
                    params={"offset": offset, "timeout": 30},
                    timeout=40,
                )
            except httpx.HTTPError as e:
                last_err = e
                if attempt < 9:
                    time.sleep(1)
                    continue
                raise
        raise last_err

    def _handle_update(self, upd: dict):
        msg = upd.get("message") or upd.get("edited_message") or {}
        if not msg:
            return
        if msg.get("from", {}).get("is_bot"):
            return

        text = msg.get("text", "") or ""
        if not text:
            return

        reply_text = (msg.get("reply_to_message") or {}).get("text", "") or ""
        m = SID_RE.search(reply_text) or SID_RE.search(text)
        if not m:
            return

        sid = m.group(1)

        if not rc.session_exists(sid):
            self.stdout.write(f"session {sid} not found/expired")
            return

        clean = SID_RE.sub("", text).strip()
        if not clean:
            return

        # 10 попыток push_message

        rc.push_message(sid, role="assistant", text=clean)


        self.stdout.write(f"-> {sid}: {clean[:80]}")

        # 10 попыток send_reply («ок»)
        self._send_reply(
            token=self._token,
            chat_id=msg["chat"]["id"],
            message_id=msg["message_id"],
            text="ок",
        )

    def _send_reply(self, token: str, chat_id: int, message_id: int, text: str) -> None:
        last_err = None
        for attempt in range(10):
            try:
                resp = httpx.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "reply_to_message_id": message_id,
                        "allow_sending_without_reply": True,
                    },
                    timeout=10,
                )
                data = resp.json()
                if data.get("ok"):
                    return
                last_err = RuntimeError(f"telegram not ok: {data}")
                self.stderr.write(
                    f"send_reply attempt {attempt + 1}/10 failed: {last_err!r}"
                )
            except httpx.HTTPError as e:
                last_err = e
                self.stderr.write(
                    f"send_reply attempt {attempt + 1}/10 failed: {e!r}"
                )
            if attempt < 9:
                time.sleep(1)

        self.stderr.write(f"send_reply failed after 10 attempts: {last_err!r}")