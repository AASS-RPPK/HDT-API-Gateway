from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.gateway import router as gateway_router
from app.api.routers.health import router as health_router
from app.core.config import settings
from app.core.proxy import close_client

app = FastAPI(title="HDT API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoints are registered first (exact routes take priority).
app.include_router(health_router)
# Catch-all proxy router must be last.
app.include_router(gateway_router)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await close_client()
