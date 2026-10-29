"""Configuration and environment settings for the Minecraft Texture Generator backend."""

from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def _parse_origins(raw: str) -> list[str]:
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _load_or_generate_secret() -> str:
    env_secret = os.getenv("APP_SECRET_KEY")
    if env_secret:
        return env_secret
    logger.warning(
        "APP_SECRET_KEY not set in environment; generating ephemeral instance-isolated secret."
    )
    return secrets.token_hex(32)


def _clean_env(name: str, default: str | None = None) -> str | None:
    val = os.getenv(name)
    if val is None:
        return default
    cleaned = val.strip().strip('"').strip("'").strip()
    return cleaned if cleaned else default


@dataclass(frozen=True)
class Settings:
    """Immutable application settings loaded from environment variables."""

    app_name: str = "Minecraft Texture Generator API"
    default_provider: str = field(
        default_factory=lambda: (_clean_env("DEFAULT_PROVIDER", "mock") or "mock").lower()
    )
    allowed_origins: list[str] = field(
        default_factory=lambda: _parse_origins(
            _clean_env(
                "CORS_ALLOWED_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
            )
            or ""
        )
    )
    max_upload_bytes: int = field(
        default_factory=lambda: int(_clean_env("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)) or (5 * 1024 * 1024))
    )
    rate_limit_per_minute: int = field(
        default_factory=lambda: int(_clean_env("RATE_LIMIT_PER_MINUTE", "30") or 30)
    )
    secret_key: str = field(default_factory=_load_or_generate_secret)

    # Provider API Keys / Endpoints (never hardcoded, loaded strictly from env)
    openai_api_key: str | None = field(
        default_factory=lambda: _clean_env("OPENAI_API_KEY")
    )
    openai_model: str = field(
        default_factory=lambda: _clean_env("OPENAI_IMAGE_MODEL", "gpt-image-1") or "gpt-image-1"
    )
    gemini_api_key: str | None = field(
        default_factory=lambda: _clean_env("GEMINI_API_KEY")
    )
    gemini_model: str = field(
        default_factory=lambda: _clean_env(
            "GEMINI_IMAGE_MODEL", "imagen-3.0-generate-002"
        )
        or "imagen-3.0-generate-002"
    )
    replicate_api_token: str | None = field(
        default_factory=lambda: _clean_env("REPLICATE_API_TOKEN")
    )
    replicate_model: str = field(
        default_factory=lambda: _clean_env(
            "REPLICATE_MODEL", "black-forest-labs/flux-schnell"
        )
        or "black-forest-labs/flux-schnell"
    )
    fal_api_key: str | None = field(
        default_factory=lambda: _clean_env("FAL_KEY")
    )
    fal_model: str = field(
        default_factory=lambda: _clean_env("FAL_MODEL", "fal-ai/flux/schnell") or "fal-ai/flux/schnell"
    )
    local_sd_url: str | None = field(
        default_factory=lambda: _clean_env("LOCAL_SD_URL")
    )
    hf_token: str | None = field(
        default_factory=lambda: _clean_env("HF_TOKEN")
    )
    hf_model: str = field(
        default_factory=lambda: _clean_env("HF_MODEL", "black-forest-labs/FLUX.1-schnell")
        or "black-forest-labs/FLUX.1-schnell"
    )


def get_settings() -> Settings:
    """Return a current Settings snapshot."""
    return Settings()

