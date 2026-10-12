import hashlib
import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from bez_bagov import redis_client as rc
from bez_bagov.telegram_client import send_to_telegram


COOKIE_NAME = "chat_session_id"
COOKIE_MAX_AGE = 60 * 30  # 30 минут


def _get_or_create_session(request):
    sid = request.COOKIES.get(COOKIE_NAME)
    if sid and rc.session_exists(sid):
        rc.touch(sid)
        return sid

    ip = request.META.get("REMOTE_ADDR", "")
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16] if ip else ""
    return rc.create_session(
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        ip_hash=ip_hash,
    )


@csrf_exempt
@require_POST
def send_message(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)

    text = payload.get("text", "")
    sid = _get_or_create_session(request)

    if not rc.rate_ok(sid):
        return JsonResponse({"error": "too many requests"}, status=429)

    try:
        rc.push_message(sid, role="user", text=text)
    except ValueError:
        return JsonResponse({"error": "empty message"}, status=400)

    delivered = send_to_telegram(text, session_id=sid)

    resp = JsonResponse({"session_id": sid, "delivered": delivered})
    resp.set_cookie(
        COOKIE_NAME,
        sid,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
        secure=not settings.DEBUG,
    )
    return resp


@require_GET
def history(request):
    sid = request.COOKIES.get(COOKIE_NAME)
    if not sid or not rc.session_exists(sid):
        return JsonResponse({"messages": []})
    limit = min(int(request.GET.get("limit", 50)), rc.MAX_MESSAGES)
    return JsonResponse({"messages": rc.get_messages(sid, limit=limit)})


@require_POST
def ping(request):
    sid = request.COOKIES.get(COOKIE_NAME)
    if sid and rc.session_exists(sid):
        rc.touch(sid)
        return JsonResponse({"ok": True})
    return JsonResponse({"ok": False})