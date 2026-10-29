"""Replicate API Provider (Flux / SDXL / Pixel-Art models)."""

from __future__ import annotations

import io
from urllib.parse import urlparse

import httpx
from PIL import Image

from app.config import get_settings
from app.pixel_pipeline import image_to_base64_png
from app.providers.base import BaseImageProvider
from app.schemas import ProviderId, TextureMode

REPLICATE_MODELS_BASE = "https://api.replicate.com/v1/models"
ALLOWED_REPLICATE_ASSET_HOSTS = {"replicate.delivery", "pbxt.replicate.delivery"}


def _validate_replicate_asset_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_REPLICATE_ASSET_HOSTS:
        raise ValueError("Untrusted asset delivery hostname returned by Replicate.")
    return url


class ReplicateProvider(BaseImageProvider):
    """Generates textures via Replicate HTTP API with synchronous `Prefer: wait` header."""

    provider_id: ProviderId = "replicate"
    name = "Replicate (Flux / SDXL)"
    description = "Cloud inference via Replicate API (requires REPLICATE_API_TOKEN)."
    supports_img2img = True

    def is_configured(self) -> bool:
        return bool(get_settings().replicate_api_token)

    async def generate(
        self,
        wrapped_prompt: str,
        mode: TextureMode,
        reference_image: Image.Image | None = None,
        strength: float = 0.75,
    ) -> Image.Image:
        settings = get_settings()
        if not settings.replicate_api_token:
            raise RuntimeError("REPLICATE_API_TOKEN is not configured in environment.")

        _ = mode
        model_slug = settings.replicate_model.strip("/")
        parts = model_slug.split("/")
        if len(parts) != 2 or not all(
            all(c.isalnum() or c in "-_." for c in part) for part in parts
        ):
            raise ValueError("Invalid REPLICATE_MODEL format. Expected 'owner/name'.")

        url = f"{REPLICATE_MODELS_BASE}/{parts[0]}/{parts[1]}/predictions"
        headers = {
            "Authorization": f"Bearer {settings.replicate_api_token}",
            "Content-Type": "application/json",
            "Prefer": "wait=55",
        }
        model_input: dict[str, object] = {
            "prompt": wrapped_prompt,
            "aspect_ratio": "1:1",
            "output_format": "png",
        }
        if reference_image is not None:
            b64_png = image_to_base64_png(reference_image.convert("RGBA"))
            model_input["image"] = f"data:image/png;base64,{b64_png}"
            model_input["prompt_strength"] = float(strength)

        async with httpx.AsyncClient(timeout=65.0) as client:
            resp = await client.post(url, headers=headers, json={"input": model_input})
            resp.raise_for_status()
            data = resp.json()

            output = data.get("output")
            output_url = output[0] if isinstance(output, list) and output else output
            if not isinstance(output_url, str):
                raise RuntimeError("Replicate prediction did not return an output URL.")

            safe_url = _validate_replicate_asset_url(output_url)
            img_resp = await client.get(safe_url)
            img_resp.raise_for_status()
            return Image.open(io.BytesIO(img_resp.content)).convert("RGBA")

