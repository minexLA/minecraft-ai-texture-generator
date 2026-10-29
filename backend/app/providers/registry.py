"""Provider Registry for runtime switching across AI generation backends."""

from __future__ import annotations

from app.config import get_settings
from app.providers.base import BaseImageProvider
from app.providers.fal_provider import FalProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.huggingface_provider import HuggingFaceProvider
from app.providers.local_sd_provider import LocalStableDiffusionProvider
from app.providers.mock_provider import MockProceduralProvider
from app.providers.openai_provider import OpenAIProvider
from app.providers.pollinations_provider import PollinationsProvider
from app.providers.replicate_provider import ReplicateProvider
from app.providers.upload_provider import UploadOnlyProvider
from app.schemas import ProviderId, ProviderInfo, ProvidersResponse

_PROVIDERS: dict[ProviderId, BaseImageProvider] = {
    "upload_only": UploadOnlyProvider(),
    "pollinations": PollinationsProvider(),
    "mock": MockProceduralProvider(),
    "huggingface": HuggingFaceProvider(),
    "openai": OpenAIProvider(),
    "gemini": GeminiProvider(),
    "replicate": ReplicateProvider(),
    "fal": FalProvider(),
    "local_sd": LocalStableDiffusionProvider(),
}


def get_default_provider_id() -> ProviderId:
    """Resolve the active default provider ID, falling back to 'mock' if unconfigured."""
    configured_default = get_settings().default_provider
    if configured_default in _PROVIDERS:
        pid = configured_default  # type: ignore[assignment]
        if _PROVIDERS[pid].is_configured():
            return pid
    return "mock"


def get_provider(provider_id: ProviderId | str | None = None) -> BaseImageProvider:
    """Retrieve a requested provider instance and verify it is configured."""
    resolved_id: ProviderId = (
        provider_id  # type: ignore[assignment]
        if provider_id in _PROVIDERS
        else get_default_provider_id()
    )
    provider = _PROVIDERS[resolved_id]
    if not provider.is_configured():
        raise ValueError(
            f"Provider '{provider.name}' ({resolved_id}) is not configured. "
            "Set its API key/URL in environment variables or switch to the Built-in Procedural provider."
        )
    return provider


def list_providers() -> ProvidersResponse:
    """Return status and capabilities of all registered providers."""
    default_id = get_default_provider_id()
    items: list[ProviderInfo] = [
        provider.get_info(is_default=(pid == default_id))
        for pid, provider in _PROVIDERS.items()
    ]
    return ProvidersResponse(default_provider=default_id, providers=items)

