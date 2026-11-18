"""Rate limiting en memoria (por IP y grupo de ruta).

Limites: 100 req/min general, 10/min login/register, 5/min depositos y retiros.
El store es deliberadamente simple y reseteable (tests).
"""
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

GENERAL_LIMIT = 100
AUTH_LIMIT = 10
FINANCIAL_LIMIT = 5
WINDOW_SECONDS = 60

# ip -> deque[timestamps]
_store: dict[str, deque] = defaultdict(deque)


def _key(request: Request, group: str) -> str:
    ip = request.client.host if request.client else "unknown"
    return f"{group}:{ip}"


def _check(key: str, limit: int) -> bool:
    now = time.time()
    dq = _store[key]
    while dq and dq[0] <= now - WINDOW_SECONDS:
        dq.popleft()
    if len(dq) >= limit:
        return False
    dq.append(now)
    return True


def reset_store() -> None:
    _store.clear()


async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    method = request.method
    if path in ("/api/auth/login", "/api/auth/register") and method == "POST":
        group, limit = "auth", AUTH_LIMIT
    elif path in ("/api/wallet/deposits", "/api/withdrawals") and method == "POST":
        group, limit = "financial", FINANCIAL_LIMIT
    elif path.startswith("/api/"):
        group, limit = "general", GENERAL_LIMIT
    else:
        return await call_next(request)
    if not _check(_key(request, group), limit):
        return JSONResponse(status_code=429, content={"detail": "Too many requests"})
    return await call_next(request)
