"""Local Stable Diffusion / Automatic1111 / Diffusers API Provider."""

from __future__ import annotations

import base64
import io
from urllib.parse import urlparse

import httpx
from PIL import Image

from app.config import get_settings
from app.pixel_pipeline import image_to_base64_png
from app.providers.base import BaseImageProvider
from app.schemas import ProviderId, TextureMode


def _validate_local_sd_base_url(raw_url: str) -> str:
    parsed = urlparse(raw_url.rstrip("/"))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("LOCAL_SD_URL must be a valid http:// or https:// base URL.")
    return f"{parsed.scheme}://{parsed.netloc}"


class LocalStableDiffusionProvider(BaseImageProvider):
    """Connects to a local Automatic1111 / Forge / Diffusers server (/sdapi/v1/txt2img & img2img)."""

    provider_id: ProviderId = "local_sd"
    name = "Local Stable Diffusion (A1111 / Diffusers API)"
    description = (
        "Local GPU inference via Stable Diffusion WebUI / Diffusers HTTP endpoint "
        "(requires LOCAL_SD_URL, e.g. http://127.0.0.1:7860)."
    )
    supports_img2img = True

    def is_configured(self) -> bool:
        return bool(get_settings().local_sd_url)

    async def generate(
        self,
        wrapped_prompt: str,
        mode: TextureMode,
        reference_image: Image.Image | None = None,
        strength: float = 0.75,
    ) -> Image.Image:
        settings = get_settings()
        if not settings.local_sd_url:
            raise RuntimeError("LOCAL_SD_URL is not configured in environment.")

        base_url = _validate_local_sd_base_url(settings.local_sd_url)
        # Enable native circular conv tiling when generating seamless Minecraft blocks
        enable_tiling = mode == TextureMode.BLOCK

        payload: dict[str, object] = {
            "prompt": wrapped_prompt,
            "negative_prompt": (
                "blurry, photo, realistic, 3d render, perspective, shadows, gradient, "
                "dithering, watermark, text, frame, border, anti-aliasing"
            ),
            "width": 512,
            "height": 512,
            "steps": 24,
            "cfg_scale": 7.0,
            "tiling": enable_tiling,
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            if reference_image is not None:
                b64_ref = image_to_base64_png(reference_image.convert("RGBA").resize((512, 512)))
                payload["init_images"] = [b64_ref]
                payload["denoising_strength"] = float(strength)
                endpoint = f"{base_url}/sdapi/v1/img2img"
            else:
                endpoint = f"{base_url}/sdapi/v1/txt2img"

            resp = await client.post(endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json()

        images = data.get("images") or []
        if not images:
            raise RuntimeError("Local Stable Diffusion API returned no images.")

        raw_bytes = base64.b64decode(images[0])
        return Image.open(io.BytesIO(raw_bytes)).convert("RGBA")

