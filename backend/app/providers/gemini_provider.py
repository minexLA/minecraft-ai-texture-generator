"""Google Gemini / Imagen API Provider."""

from __future__ import annotations

import base64
import io

import httpx
from PIL import Image

from app.config import get_settings
from app.pixel_pipeline import image_to_base64_png
from app.providers.base import BaseImageProvider
from app.schemas import ProviderId, TextureMode

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _extract_google_error(resp: httpx.Response) -> str:
    try:
        data = resp.json()
        if isinstance(data, dict) and "error" in data:
            err = data["error"]
            if isinstance(err, dict):
                status_str = err.get("status", "")
                msg = err.get("message", resp.text)
                return f"HTTP {resp.status_code} ({status_str}): {msg}"
    except Exception:
        pass
    return f"HTTP {resp.status_code}: {resp.text[:400]}"


class GeminiProvider(BaseImageProvider):
    """Generates textures using Google Gemini / Imagen API.

    Supports both Imagen (`:predict`) and Gemini native image generation (`:generateContent`)
    models, with automatic fallback if the configured model is restricted on the user's tier.
    """

    provider_id: ProviderId = "gemini"
    name = "Google Gemini / Imagen"
    description = "Cloud inference via Google Gemini & Imagen API (requires GEMINI_API_KEY)."
    supports_img2img = True

    def is_configured(self) -> bool:
        return bool(get_settings().gemini_api_key)

    async def generate(
        self,
        wrapped_prompt: str,
        mode: TextureMode,
        reference_image: Image.Image | None = None,
        strength: float = 0.75,
    ) -> Image.Image:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured in environment.")

        _ = (mode, strength)
        configured_model = settings.gemini_model.strip()
        if not all(c.isalnum() or c in "-_." for c in configured_model):
            raise ValueError(f"Invalid GEMINI_IMAGE_MODEL identifier: '{configured_model}'.")

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": settings.gemini_api_key,
        }

        errors: list[str] = []

        async with httpx.AsyncClient(timeout=65.0) as client:
            # 1. If a reference image is provided or configured model is a gemini-* model,
            #    try generateContent first.
            candidate_models = [configured_model]
            for fallback in (
                "gemini-2.5-flash-image",
                "imagen-4.0-generate-001",
                "imagen-3.0-generate-002",
            ):
                if fallback not in candidate_models:
                    candidate_models.append(fallback)

            for model_name in candidate_models:
                if model_name.startswith("imagen-"):
                    img, err = await self._try_imagen_predict(
                        client, model_name, headers, wrapped_prompt
                    )
                else:
                    img, err = await self._try_gemini_generate_content(
                        client, model_name, headers, wrapped_prompt, reference_image
                    )
                if img is not None:
                    return img
                if err:
                    errors.append(f"[{model_name}] {err}")
                    # If the error is an account-level billing/prepayment 402 or invalid key 401/403,
                    # stop trying fallback models and surface the billing/auth error cleanly.
                    if "HTTP 402" in err or "API_KEY_INVALID" in err:
                        break

        raise RuntimeError(" | ".join(errors) if errors else "Gemini API returned no image.")

    async def _try_imagen_predict(
        self,
        client: httpx.AsyncClient,
        model_name: str,
        headers: dict[str, str],
        wrapped_prompt: str,
    ) -> tuple[Image.Image | None, str | None]:
        endpoint = f"{GEMINI_API_BASE}/{model_name}:predict"
        payload = {
            "instances": [{"prompt": wrapped_prompt}],
            "parameters": {"sampleCount": 1, "aspectRatio": "1:1"},
        }
        resp = await client.post(endpoint, headers=headers, json=payload)
        if resp.status_code != 200:
            return None, _extract_google_error(resp)

        body = resp.json()
        predictions = body.get("predictions") or []
        if not predictions or "bytesBase64Encoded" not in predictions[0]:
            return None, "Response did not contain predictions[0].bytesBase64Encoded."

        raw_bytes = base64.b64decode(predictions[0]["bytesBase64Encoded"])
        return Image.open(io.BytesIO(raw_bytes)).convert("RGBA"), None

    async def _try_gemini_generate_content(
        self,
        client: httpx.AsyncClient,
        model_name: str,
        headers: dict[str, str],
        wrapped_prompt: str,
        reference_image: Image.Image | None,
    ) -> tuple[Image.Image | None, str | None]:
        endpoint = f"{GEMINI_API_BASE}/{model_name}:generateContent"
        parts: list[dict[str, object]] = [
            {"text": f"Generate a square 1:1 image: {wrapped_prompt}"}
        ]
        if reference_image is not None:
            b64_ref = image_to_base64_png(reference_image.convert("RGBA").resize((512, 512)))
            parts.append(
                {
                    "inlineData": {
                        "mimeType": "image/png",
                        "data": b64_ref,
                    }
                }
            )

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
        }
        resp = await client.post(endpoint, headers=headers, json=payload)
        if resp.status_code != 200:
            return None, _extract_google_error(resp)

        body = resp.json()
        candidates = body.get("candidates") or []
        for candidate in candidates:
            content = candidate.get("content") or {}
            for part in content.get("parts") or []:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and "data" in inline:
                    raw_bytes = base64.b64decode(inline["data"])
                    return Image.open(io.BytesIO(raw_bytes)).convert("RGBA"), None

        return None, "Response did not include inlineData image bytes."
