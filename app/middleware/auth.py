from __future__ import annotations

import httpx
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import PUBLIC_PATHS, settings


def _is_public(path: str) -> bool:
    """Return True if the path is in the public (no-auth) list."""
    for public in PUBLIC_PATHS:
        if path == public or path.startswith(public + "/"):
            return True
    return False


class AuthMiddleware(BaseHTTPMiddleware):
    """Validate the Bearer token via the Identity Provider before proxying.

    For every non-public request the middleware:
    1. Extracts the Authorization header.
    2. Calls POST /auth/verify on the Identity Provider.
    3. On success, injects X-User-Id and X-User-Role headers into the
       request so downstream services know who the caller is.
    4. On failure, returns 401 immediately.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method == "OPTIONS" or _is_public(request.url.path):
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing bearer token"})

        token = auth_header.split(" ", 1)[1]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                verify_url = f"{settings.IDENTITY_PROVIDER_URL.rstrip('/')}/auth/verify"
                resp = await client.post(verify_url, json={"token": token})
        except httpx.RequestError:
            return JSONResponse(
                status_code=503,
                content={"detail": "Identity Provider is unreachable"},
            )

        if resp.status_code != 200:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

        payload = resp.json()

        # Inject identity headers so downstream services can use them.
        request.state.user_id = payload.get("sub", "")
        request.state.user_role = payload.get("role", "")

        # Mutate scope headers so the proxy forwards them upstream.
        headers = dict(request.scope["headers"])
        headers[(b"x-user-id")] = payload.get("sub", "").encode()
        headers[(b"x-user-role")] = payload.get("role", "").encode()
        request.scope["headers"] = [
            (k, v) for k, v in request.scope["headers"]
            if k.lower() not in (b"x-user-id", b"x-user-role")
        ] + [
            (b"x-user-id", payload.get("sub", "").encode()),
            (b"x-user-role", payload.get("role", "").encode()),
        ]

        return await call_next(request)
