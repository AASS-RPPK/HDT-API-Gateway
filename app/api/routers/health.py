from __future__ import annotations

import httpx
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])

_SERVICES = {
    "image_processing": settings.IMAGE_PROCESSING_URL,
    "ai_prediction": settings.AI_PREDICTION_URL,
    "ai_agent": settings.AI_AGENT_URL,
    "behavioral_monitoring": settings.BEHAVIORAL_MONITORING_URL,
}


@router.get("/health")
async def gateway_health() -> dict:
    """Gateway liveness check."""
    return {"status": "ok", "service": "api-gateway"}


@router.get("/health/services")
async def services_health() -> dict:
    """Check reachability of every registered upstream service."""
    results: dict[str, str] = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, base_url in _SERVICES.items():
            try:
                resp = await client.get(f"{base_url.rstrip('/')}/docs")
                results[name] = "ok" if resp.status_code < 500 else "degraded"
            except httpx.RequestError:
                results[name] = "unreachable"

    overall = "ok" if all(v == "ok" for v in results.values()) else "degraded"
    return {"status": overall, "services": results}
