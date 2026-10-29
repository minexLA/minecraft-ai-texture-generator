"""OpenAI Image Generation Provider (gpt-image-1 / dall-e-3)."""

from __future__ import annotations

import base64
import io

import httpx
from PIL import Image

from app.config import get_settings
from app.pixel_pipeline import image_to_png_bytes
from app.providers.base import BaseImageProvider
from app.schemas import ProviderId, TextureMode

OPENAI_GENERATIONS_URL = "https://api.openai.com/v1/images/generations"
OPENAI_EDITS_URL = "https://api.openai.com/v1/images/edits"


def _extract_openai_error(resp: httpx.Response) -> str:
    try:
        data = resp.json()
        if isinstance(data, dict) and "error" in data:
            err = data["error"]
            if isinstance(err, dict) and "message" in err:
                return f"HTTP {resp.status_code}: {err['message']}"
    except Exception:
        pass
    return f"HTTP {resp.status_code}: {resp.text[:400]}"


class OpenAIProvider(BaseImageProvider):
    """Generates textures via the OpenAI Images API (supports txt2img and img2img edits)."""

    provider_id: ProviderId = "openai"
    name = "OpenAI (gpt-image-1 / DALL-E 3)"
    description = "Cloud inference via OpenAI Images API (requires OPENAI_API_KEY)."
    supports_img2img = True

    def is_configured(self) -> bool:
        return bool(get_settings().openai_api_key)

    async def generate(
        self,
        wrapped_prompt: str,
        mode: TextureMode,
        reference_image: Image.Image | None = None,
        strength: float = 0.75,
    ) -> Image.Image:
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured in environment.")

        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        _ = (mode, strength)

        async with httpx.AsyncClient(timeout=65.0) as client:
            if reference_image is not None:
                png_bytes = image_to_png_bytes(reference_image.convert("RGBA").resize((1024, 1024)))
                files = {"image": ("reference.png", png_bytes, "image/png")}
                data = {
                    "model": settings.openai_model,
                    "prompt": wrapped_prompt,
                    "size": "1024x1024",
                }
                response = await client.post(OPENAI_EDITS_URL, headers=headers, data=data, files=files)
                if response.status_code != 200:
                    raise RuntimeError(_extract_openai_error(response))
                body = response.json()
            else:
                models_to_try = [settings.openai_model]
                if "dall-e-3" not in models_to_try:
                    models_to_try.append("dall-e-3")

                errors: list[str] = []
                body = None
                for model_name in models_to_try:
                    payload: dict[str, object] = {
                        "model": model_name,
                        "prompt": wrapped_prompt,
                        "size": "1024x1024",
                        "n": 1,
                    }
                    if model_name != "gpt-image-1":
                        payload["response_format"] = "b64_json"
                    response = await client.post(OPENAI_GENERATIONS_URL, headers=headers, json=payload)
                    if response.status_code == 200:
                        body = response.json()
                        break
                    errors.append(f"[{model_name}] {_extract_openai_error(response)}")

                if body is None:
                    raise RuntimeError(" | ".join(errors))

        item = body["data"][0]
        if "b64_json" in item and item["b64_json"]:
            raw_bytes = base64.b64decode(item["b64_json"])
            return Image.open(io.BytesIO(raw_bytes)).convert("RGBA")

        raise RuntimeError("OpenAI response did not include base64 image data.")
