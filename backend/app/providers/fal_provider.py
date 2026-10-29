"""Fal.ai Inference Provider."""

from __future__ import annotations

import io
from urllib.parse import urlparse

import httpx
from PIL import Image

from app.config import get_settings
from app.pixel_pipeline import image_to_base64_png
from app.providers.base import BaseImageProvider
from app.schemas import ProviderId, TextureMode

FAL_BASE_URL = "https://fal.run"
ALLOWED_FAL_ASSET_HOSTS = {"fal.media", "v3.fal.media", "storage.googleapis.com"}


def _validate_fal_asset_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_FAL_ASSET_HOSTS:
        raise ValueError("Untrusted asset delivery hostname returned by Fal.ai.")
    return url


class FalProvider(BaseImageProvider):
    """Generates textures via Fal.ai synchronous inference endpoint."""

    provider_id: ProviderId = "fal"
    name = "Fal.ai (Flux / Fast SDXL)"
    description = "Fast cloud inference via Fal.ai REST API (requires FAL_KEY)."
    supports_img2img = True

    def is_configured(self) -> bool:
        return bool(get_settings().fal_api_key)

    async def generate(
        self,
        wrapped_prompt: str,
        mode: TextureMode,
        reference_image: Image.Image | None = None,
        strength: float = 0.75,
    ) -> Image.Image:
        settings = get_settings()
        if not settings.fal_api_key:
            raise RuntimeError("FAL_KEY is not configured in environment.")

        _ = mode
        model_path = settings.fal_model.strip("/")
        if not all(c.isalnum() or c in "-_/" for c in model_path) or ".." in model_path:
            raise ValueError("Invalid FAL_MODEL path.")

        endpoint = f"{FAL_BASE_URL}/{model_path}"
        headers = {
            "Authorization": f"Key {settings.fal_api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, object] = {
            "prompt": wrapped_prompt,
            "image_size": "square",
            "num_images": 1,
        }
        if reference_image is not None:
            b64_png = image_to_base64_png(reference_image.convert("RGBA"))
            payload["image_url"] = f"data:image/png;base64,{b64_png}"
            payload["strength"] = float(strength)

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

            images = data.get("images") or []
            if not images or "url" not in images[0]:
                raise RuntimeError("Fal.ai response did not include an output image URL.")

            safe_url = _validate_fal_asset_url(images[0]["url"])
            img_resp = await client.get(safe_url)
            img_resp.raise_for_status()
            return Image.open(io.BytesIO(img_resp.content)).convert("RGBA")

