"""Hugging Face Free Serverless Inference Provider (FLUX.1-schnell)."""

from __future__ import annotations

import io

import httpx
from PIL import Image

from app.config import get_settings
from app.providers.base import BaseImageProvider
from app.schemas import ProviderId, TextureMode

HF_ROUTER_BASE = "https://router.huggingface.co/hf-inference/models"


class HuggingFaceProvider(BaseImageProvider):
    """Generates textures via Hugging Face Serverless Inference API (free account token, no card needed)."""

    provider_id: ProviderId = "huggingface"
    name = "Hugging Face (FLUX.1-schnell)"
    description = "Serverless inference via Hugging Face Router (HF_TOKEN)."
    supports_img2img = False

    def is_configured(self) -> bool:
        return bool(get_settings().hf_token)

    async def generate(
        self,
        wrapped_prompt: str,
        mode: TextureMode,
        reference_image: Image.Image | None = None,
        strength: float = 0.75,
    ) -> Image.Image:
        settings = get_settings()
        if not settings.hf_token:
            raise RuntimeError("HF_TOKEN is not configured in environment.")

        _ = (mode, reference_image, strength)
        model_slug = settings.hf_model.strip("/")
        parts = model_slug.split("/")
        if len(parts) != 2 or not all(
            all(c.isalnum() or c in "-_." for c in part) for part in parts
        ):
            raise ValueError("Invalid HF_MODEL format. Expected 'org/model'.")

        url = f"{HF_ROUTER_BASE}/{parts[0]}/{parts[1]}"
        headers = {
            "Authorization": f"Bearer {settings.hf_token}",
            "Accept": "image/png",
        }
        payload = {"inputs": wrapped_prompt}

        async with httpx.AsyncClient(timeout=65.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:400]}")
            return Image.open(io.BytesIO(resp.content)).convert("RGBA")

