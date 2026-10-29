"""Pollinations.ai image provider."""

from __future__ import annotations

import io
import secrets
from urllib.parse import quote

import httpx
from PIL import Image

from app.providers.base import BaseImageProvider
from app.schemas import ProviderId, TextureMode

POLLINATIONS_BASE_URL = "https://image.pollinations.ai/prompt"


class PollinationsProvider(BaseImageProvider):
    """Generates images via Pollinations.ai (Flux)."""

    provider_id: ProviderId = "pollinations"
    name = "Pollinations (Flux)"
    description = "Cloud generation via Pollinations.ai. No API key required."
    supports_img2img = False

    def is_configured(self) -> bool:
        return True

    async def generate(
        self,
        wrapped_prompt: str,
        mode: TextureMode,
        reference_image: Image.Image | None = None,
        strength: float = 0.75,
    ) -> Image.Image:
        _ = (mode, reference_image, strength)
        encoded_prompt = quote(wrapped_prompt, safe="")
        seed = secrets.randbelow(1_000_000_000)
        url = (
            f"{POLLINATIONS_BASE_URL}/{encoded_prompt}"
            f"?model=flux&width=512&height=512&nologo=true&seed={seed}"
        )

        async with httpx.AsyncClient(timeout=65.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
            return Image.open(io.BytesIO(resp.content)).convert("RGBA")
