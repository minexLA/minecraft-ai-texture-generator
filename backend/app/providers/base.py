"""Abstract base class for pluggable AI texture generation providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from PIL import Image

from app.schemas import ProviderId, ProviderInfo, TextureMode


class BaseImageProvider(ABC):
    """Unified interface for cloud and local AI image generation backends."""

    provider_id: ProviderId
    name: str
    description: str
    supports_img2img: bool = True

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if the required credentials or endpoint URL are configured."""

    @abstractmethod
    async def generate(
        self,
        wrapped_prompt: str,
        mode: TextureMode,
        reference_image: Image.Image | None = None,
        strength: float = 0.75,
    ) -> Image.Image:
        """Generate a high-resolution image from the wrapped prompt and optional reference."""

    def get_info(self, is_default: bool = False) -> ProviderInfo:
        """Build serializable ProviderInfo metadata."""
        return ProviderInfo(
            id=self.provider_id,
            name=self.name,
            description=self.description,
            configured=self.is_configured(),
            supports_img2img=self.supports_img2img,
            is_default=is_default,
        )

