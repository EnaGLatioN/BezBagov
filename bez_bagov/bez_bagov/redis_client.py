import json
import time
import uuid

import redis
from django.conf import settings

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD or None,
    decode_responses=True,
    socket_timeout=2,
    socket_connect_timeout=2,
    health_check_interval=30,
)

SESSION_TTL = 60 * 30                # 30 минут
MAX_MESSAGES = 100
MAX_MESSAGE_LEN = 2000

_PUSH_SCRIPT = """
redis.call('LPUSH', KEYS[1], ARGV[1])
redis.call('LTRIM', KEYS[1], 0, ARGV[2])
redis.call('EXPIRE', KEYS[1], ARGV[3])
redis.call('HSET', KEYS[2], 'last_seen', ARGV[4])
redis.call('EXPIRE', KEYS[2], ARGV[3])
return 1
"""
_push = redis_client.register_script(_PUSH_SCRIPT)


def _keys(session_id: str) -> tuple[str, str]:
    return f"chat:messages:{session_id}", f"chat:session:{session_id}"


def create_session(user_agent: str = "", ip_hash: str = "") -> str:
    session_id = uuid.uuid4().hex
    meta_key = f"chat:session:{session_id}"
    redis_client.hset(
        meta_key,
        mapping={
            "created_at": int(time.time()),
            "last_seen": int(time.time()),
            "user_agent": user_agent[:300],
            "ip_hash": ip_hash,
        },
    )
    redis_client.expire(meta_key, SESSION_TTL)
    redis_client.zadd("chat:index:active", {session_id: time.time()})
    redis_client.expire("chat:index:active", SESSION_TTL * 2)  # подстраховка
    return session_id


def push_message(session_id: str, role: str, text: str) -> dict:
    text = (text or "").strip()
    if not text:
        raise ValueError("empty message")
    if len(text) > MAX_MESSAGE_LEN:
        text = text[:MAX_MESSAGE_LEN]

    msg = {
        "id": uuid.uuid4().hex[:12],
        "ts": int(time.time()),
        "role": role,
        "text": text,
    }
    msg_key, meta_key = _keys(session_id)
    _push(
        keys=[msg_key, meta_key],
        args=[
            json.dumps(msg, ensure_ascii=False),
            MAX_MESSAGES - 1,
            SESSION_TTL,
            int(time.time()),
        ],
    )
    redis_client.zadd("chat:index:active", {session_id: time.time()})
    return msg


def get_messages(session_id: str, limit: int = 50) -> list[dict]:
    msg_key, meta_key = _keys(session_id)
    raw = redis_client.lrange(msg_key, 0, limit - 1)
    redis_client.hset(meta_key, "last_seen", int(time.time()))
    redis_client.expire(meta_key, SESSION_TTL)
    return [json.loads(item) for item in reversed(raw)]


def session_exists(session_id: str) -> bool:
    return bool(redis_client.exists(f"chat:session:{session_id}"))


def touch(session_id: str) -> None:
    meta_key = f"chat:session:{session_id}"
    redis_client.hset(meta_key, "last_seen", int(time.time()))
    redis_client.expire(meta_key, SESSION_TTL)
    redis_client.zadd("chat:index:active", {session_id: time.time()})


def rate_ok(session_id: str, limit: int = 20, window: int = 60) -> bool:
    key = f"chat:rate:{session_id}"
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, window, nx=True)
    count, _ = pipe.execute()
    return int(count) <= limit