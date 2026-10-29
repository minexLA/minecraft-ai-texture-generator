"""Direct image upload provider (runs only the pixel post-processing pipeline)."""

from __future__ import annotations

from PIL import Image

from app.providers.base import BaseImageProvider
from app.schemas import ProviderId, TextureMode


class UploadOnlyProvider(BaseImageProvider):
    """Passes an uploaded image directly to the post-processing pipeline."""

    provider_id: ProviderId = "upload_only"
    name = "Upload Only (No AI)"
    description = "Processes your uploaded or pasted image directly into a texture."
    supports_img2img = True

    def is_configured(self) -> bool:
        return True

    async def generate(
        self,
        wrapped_prompt: str,
        mode: TextureMode,
        reference_image: Image.Image | None = None,
        strength: float = 0.75,
    ) -> Image.Image:
        _ = (wrapped_prompt, mode, strength)
        if reference_image is None:
            raise ValueError("Upload or paste an image first to process it directly.")
        return reference_image.convert("RGBA")
