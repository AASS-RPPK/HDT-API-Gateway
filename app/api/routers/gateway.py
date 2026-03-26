from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.core.config import SERVICE_ROUTES
from app.core.proxy import proxy_request

router = APIRouter()


def _resolve_upstream(path: str) -> str | None:
    """Return the upstream base URL for a given request path."""
    for prefix, upstream in SERVICE_ROUTES:
        if path == prefix or path.startswith(prefix + "/"):
            return upstream
    return None


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def catch_all(request: Request, path: str) -> Response:
    """Forward every matched request to the appropriate upstream microservice."""
    upstream = _resolve_upstream(request.url.path)
    if upstream is None:
        return JSONResponse(
            status_code=404,
            content={"detail": f"No service registered for path: {request.url.path}"},
        )

    try:
        return await proxy_request(request, upstream)
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"detail": f"Upstream service error: {exc}"},
        )
