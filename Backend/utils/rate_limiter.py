"""
Rate Limiting — in-memory (dev) or Redis-backed (production).
Applied per IP on public endpoints and per user on API endpoints.
"""
import time
import logging
from collections import defaultdict
from threading import Lock
from typing import Optional
from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)

# ── In-memory store (dev/single-node) ────────────────────────────────────────

class _InMemoryStore:
    def __init__(self):
        self._data: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        now = time.time()
        with self._lock:
            timestamps = self._data[key]
            # Remove old entries outside window
            self._data[key] = [t for t in timestamps if now - t < window]
            count = len(self._data[key])
            if count >= limit:
                oldest = self._data[key][0]
                retry_after = int(window - (now - oldest)) + 1
                return False, retry_after
            self._data[key].append(now)
            return True, 0

    def reset(self, key: str):
        with self._lock:
            self._data.pop(key, None)


# ── Redis store (production) ──────────────────────────────────────────────────

class _RedisStore:
    def __init__(self, redis_url: str):
        import redis
        self._r = redis.from_url(redis_url, decode_responses=True)

    def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        import time
        pipe = self._r.pipeline()
        now = time.time()
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window)
        results = pipe.execute()
        count = results[1]
        if count >= limit:
            oldest_score = self._r.zrange(key, 0, 0, withscores=True)
            retry_after = int(window - (now - oldest_score[0][1])) + 1 if oldest_score else window
            # Remove the one we just added
            self._r.zremrangebyscore(key, now, now)
            return False, retry_after
        return True, 0

    def reset(self, key: str):
        self._r.delete(key)


# ── Factory ───────────────────────────────────────────────────────────────────

def _make_store():
    try:
        from core.config import get_settings
        s = get_settings()
        if s.REDIS_URL and s.REDIS_URL.strip():
            store = _RedisStore(s.REDIS_URL)
            logger.info("Rate limiter: Redis backend")
            return store
    except Exception as e:
        logger.warning(f"Redis connection failed, falling back to in-memory: {e}")
    logger.info("Rate limiter: in-memory backend")
    return _InMemoryStore()


_store = _make_store()


# ── Limiter decorator / dependency ────────────────────────────────────────────

class RateLimiter:
    """
    FastAPI dependency for rate limiting.
    Usage:
        @router.post("/apply/{token}")
        async def apply(request: Request, _=Depends(RateLimiter(10, 60))):
            ...
    """
    def __init__(self, limit: int, window: int, key_func=None):
        self.limit = limit
        self.window = window
        self.key_func = key_func or self._default_key

    def _default_key(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        ip = forwarded.split(",")[0].strip() if forwarded else (
            request.client.host if request.client else "unknown"
        )
        return f"rl:{request.url.path}:{ip}"

    async def __call__(self, request: Request):
        key = self.key_func(request)
        allowed, retry_after = _store.is_allowed(key, self.limit, self.window)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )


# ── Pre-built limiters ────────────────────────────────────────────────────────

# Public apply endpoint — 20 per IP per minute (increased for production)
apply_limiter = RateLimiter(limit=20, window=60)

# Login — 10 attempts per IP per minute (increased for production)
login_limiter = RateLimiter(limit=10, window=60)

# General API — 500 per IP per minute (increased for production)
api_limiter = RateLimiter(limit=500, window=60)

# Bulk upload — 10 per user per minute (increased for production)
bulk_limiter = RateLimiter(limit=10, window=60)

# Chat — 60 per user per minute (increased for production)
chat_limiter = RateLimiter(limit=60, window=60)
