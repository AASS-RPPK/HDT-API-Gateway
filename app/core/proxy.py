from __future__ import annotations

import httpx
from fastapi import Request, Response

from app.core.config import settings

_client: httpx.AsyncClient | None = None


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=settings.PROXY_TIMEOUT)
    return _client


async def close_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
        _client = None


async def proxy_request(request: Request, upstream_base: str) -> Response:
    """Forward an incoming request to the upstream service and return its response."""
    client = await get_client()

    # Build the upstream URL preserving path and query string.
    url = f"{upstream_base.rstrip('/')}{request.url.path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"

    # Forward headers, excluding hop-by-hop headers.
    excluded = {"host", "connection", "keep-alive", "transfer-encoding"}
    headers = {
        k: v for k, v in request.headers.items() if k.lower() not in excluded
    }

    body = await request.body()

    upstream_response = await client.request(
        method=request.method,
        url=url,
        headers=headers,
        content=body,
    )

    # Build response, forwarding status and headers from upstream.
    response_excluded = {"transfer-encoding", "connection", "keep-alive"}
    response_headers = {
        k: v
        for k, v in upstream_response.headers.items()
        if k.lower() not in response_excluded
    }

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
    )
