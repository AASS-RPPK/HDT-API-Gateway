from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PORT: int = Field(default=8000, ge=1, le=65535)

    # Upstream service URLs
    IMAGE_PROCESSING_URL: str = "http://image-processing:8001"
    AI_PREDICTION_URL: str = "http://ai-prediction:8002"
    AI_AGENT_URL: str = "http://ai-agent:8003"
    BEHAVIORAL_MONITORING_URL: str = "http://behavioral-monitoring:8004"
    IDENTITY_PROVIDER_URL: str = "http://identity-provider:8005"
    ACTIVE_LEARNING_URL: str = "http://active-learning:8006"

    # Request timeout for proxied calls (seconds).
    PROXY_TIMEOUT: float = 60.0

    # Comma-separated allowed origins for CORS.
    CORS_ORIGINS: str = ""

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _normalize_cors_origins(cls, v: object) -> str:
        if v is None:
            return ""
        return str(v)

    def cors_origins_list(self) -> list[str]:
        raw = self.CORS_ORIGINS.strip()
        if not raw:
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]


settings = Settings()

# ---------------------------------------------------------------------------
# Service registry: maps a path prefix to the upstream base URL.
#
# The gateway strips nothing -- it forwards the full path as-is so that
# each microservice receives the routes it expects.
# ---------------------------------------------------------------------------
SERVICE_ROUTES: list[tuple[str, str]] = [
    # HDT-Identity-Provider (public auth endpoints)
    ("/auth", settings.IDENTITY_PROVIDER_URL),

    # HDT-Image-Processing
    ("/api/upload", settings.IMAGE_PROCESSING_URL),
    ("/api/conversion", settings.IMAGE_PROCESSING_URL),
    ("/conversion", settings.IMAGE_PROCESSING_URL),
    ("/dzi", settings.IMAGE_PROCESSING_URL),

    # HDT-Active-Learning — more specific annotation sub-paths must come before
    # the generic /models/annotation prefix so they are matched first.
    ("/feedback", settings.ACTIVE_LEARNING_URL),
    ("/models/annotation/train", settings.ACTIVE_LEARNING_URL),
    ("/models/annotation/deploy", settings.ACTIVE_LEARNING_URL),

    # HDT-AI-Prediction (annotation prediction + legacy path)
    ("/models/annotation", settings.AI_PREDICTION_URL),
    ("/model/annotations", settings.AI_PREDICTION_URL),

    # HDT-AI-Agent
    ("/models/chatbot", settings.AI_AGENT_URL),

    # HDT-Behavioral-Monitoring
    ("/users", settings.BEHAVIORAL_MONITORING_URL),
]

# ---------------------------------------------------------------------------
# Paths that do NOT require a valid Bearer token.
# Auth endpoints must be public so users can register / login.
# ---------------------------------------------------------------------------
PUBLIC_PATHS: list[str] = [
    "/health",
    "/health/services",
    # Allow local FE upload + polling without requiring the identity provider.
    # The downstream Image Processing service still enforces its own Bearer-token allowlist.
    "/api/upload",
    "/api/conversion",
    "/dzi",
    "/auth/register",
    "/auth/login",
    "/auth/refresh",
    "/docs",
    "/openapi.json",
    # Allow `hipa-converter` pooling worker to call conversion endpoints using Basic Auth
    # (it does not have a Bearer token / Identity Provider).
    "/conversion",
]
