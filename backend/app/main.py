"""FastAPI application entry point for the Minecraft Texture Generator backend."""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict, deque
from typing import Annotated, Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.pixel_pipeline import (
    base64_to_image,
    extract_hex_palette,
    image_to_base64_png,
    image_to_png_bytes,
    process_texture,
    validate_and_open_image_bytes,
    wrap_prompt,
)
from app.providers.registry import get_provider, list_providers
from app.schemas import (
    GenerateResponse,
    ProviderId,
    ProvidersResponse,
    ReprocessRequest,
    TargetSize,
    TextureMode,
)

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jfif",
    "image/jiff",
    "image/pjpeg",
    "image/webp",
    "image/bmp",
    "image/gif",
    "application/octet-stream",
    "",
}
ALLOWED_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".jfif",
    ".jiff",
    ".pjpeg",
    ".pjp",
    ".webp",
    ".bmp",
    ".gif",
}

settings = get_settings()

# TODO(security): Add OAuth2 / OIDC authentication & MFA if deploying as a multi-tenant public SaaS.
# Currently designed as a single-user / local studio container tool using the BFF pattern.
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Converts text prompts and optional reference images into crisp 16x16, 32x32, and 64x64 "
        "Minecraft item and block textures."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

# Simple sliding-window rate limiter per client IP
_REQUEST_TIMESTAMPS: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def security_headers_and_rate_limit_middleware(request: Request, call_next) -> Response:
    """Enforce HTTP method allow-list, per-IP rate limiting, and strict security headers."""
    if request.method not in {"GET", "POST", "OPTIONS", "HEAD"}:
        return JSONResponse(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            content={"detail": "HTTP method not allowed."},
        )

    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.monotonic()
    bucket = _REQUEST_TIMESTAMPS[client_ip]
    while bucket and (now - bucket[0]) > 60.0:
        bucket.popleft()

    limit = get_settings().rate_limit_per_minute
    if len(bucket) >= limit:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Please wait before generating more textures."},
        )
    bucket.append(now)

    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; "
        "script-src 'self'; object-src 'none'; frame-ancestors 'none';"
    )
    return response


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok"}


@app.get("/api/providers", response_model=ProvidersResponse)
async def get_available_providers() -> ProvidersResponse:
    """List all supported AI inference providers and whether each is configured."""
    return list_providers()


async def _validate_uploaded_reference_image(upload: UploadFile):
    """Validate uploaded reference image MIME type, extension, byte size, and magic header."""
    # TODO(security): Integrate an external malware/CDR scanner if accepting untrusted public file uploads.
    content_type = (upload.content_type or "").lower().strip()
    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES and not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image MIME type. Allowed: PNG, JPEG, JFIF/JIFF, WEBP, BMP, GIF.",
        )

    if upload.filename:
        safe_name = os.path.basename(upload.filename)
        _, ext = os.path.splitext(safe_name.lower())
        if ext and ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file extension. Allowed: .png, .jpg, .jpeg, .jfif, .jiff, .webp, .bmp, .gif.",
            )

    max_bytes = get_settings().max_upload_bytes
    raw_bytes = await upload.read(max_bytes + 1)
    if len(raw_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Reference image exceeds maximum size of {max_bytes // (1024 * 1024)} MB.",
        )

    try:
        return validate_and_open_image_bytes(raw_bytes)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_texture(
    prompt: Annotated[
        str,
        Form(max_length=600, description="Text description of the Minecraft item or block (optional for upload_only)."),
    ] = "",
    mode: Annotated[TextureMode, Form(description="'item' (transparent sprite) or 'block' (seamless tile).")] = TextureMode.ITEM,
    size: Annotated[int, Form(description="Target pixel resolution: 16, 32, or 64.")] = 16,
    provider: Annotated[ProviderId | None, Form(description="AI provider ID override.")] = None,
    strength: Annotated[float, Form(ge=0.05, le=1.0, description="Reference image denoising strength.")] = 0.75,
    palette_colors: Annotated[int, Form(ge=2, le=64, description="Number of colors for MedianCut quantization.")] = 24,
    alpha_threshold: Annotated[int, Form(ge=1, le=254, description="Binary alpha threshold (0-254).")] = 128,
    response_format: Annotated[Literal["json", "png"], Form(description="Return JSON metadata + base64 or direct PNG stream.")] = "json",
    reference_image: Annotated[UploadFile | None, File(description="Optional reference or custom image (.png, .jpg, .jfif, .jiff, .webp).")] = None,
):
    """Generate or process a Minecraft item or block texture and apply the strict pixel-art pipeline."""
    if size not in (16, 32, 64):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid target size. Must be 16, 32, or 64.",
        )
    target_size: TargetSize = size  # type: ignore[assignment]

    ref_pil = None
    if reference_image is not None and reference_image.filename:
        ref_pil = await _validate_uploaded_reference_image(reference_image)

    try:
        active_provider = get_provider(provider)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    cleaned_prompt = prompt.strip()
    if active_provider.provider_id == "upload_only":
        if ref_pil is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please upload an image (.jfif, .jiff, .png, .jpg, .webp) to run the pixel pipeline without AI.",
            )
        wrapped = "Direct custom image upload (AI generation skipped — ran rembg + binary alpha + Nearest-Neighbor + MedianCut pipeline)"
    else:
        if not cleaned_prompt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prompt cannot be empty when using an AI provider.",
            )
        wrapped = wrap_prompt(cleaned_prompt, mode=mode)

    try:
        raw_image = await active_provider.generate(
            wrapped_prompt=wrapped,
            mode=mode,
            reference_image=ref_pil,
            strength=strength,
        )
        processed_image = process_texture(
            image=raw_image,
            mode=mode,
            target_size=target_size,
            palette_colors=palette_colors,
            alpha_threshold=alpha_threshold,
            strip_background=(mode == TextureMode.ITEM),
        )
    except HTTPException:
        raise
    except Exception as exc:
        err_msg = str(exc).strip()
        if hasattr(exc, "response") and getattr(exc, "response", None) is not None:
            resp_obj = getattr(exc, "response")
            try:
                err_msg = f"HTTP {resp_obj.status_code}: {resp_obj.text[:400]}"
            except Exception:
                pass
        logger.error(
            "Texture generation failed with provider %s (%s): %s",
            active_provider.provider_id,
            exc.__class__.__name__,
            err_msg,
        )
        detail_msg = (
            f"Provider '{active_provider.name}' error: {err_msg}"
            if err_msg
            else f"Failed to generate texture from '{active_provider.name}'."
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail_msg,
        ) from exc

    if response_format == "png":
        png_bytes = image_to_png_bytes(processed_image)
        return Response(
            content=png_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": f'attachment; filename="mc_{mode.value}_{target_size}x{target_size}.png"',
                "X-Content-Type-Options": "nosniff",
            },
        )

    return GenerateResponse(
        processed_image_b64=image_to_base64_png(processed_image),
        raw_image_b64=image_to_base64_png(raw_image),
        wrapped_prompt=wrapped,
        mode=mode,
        size=target_size,
        provider=active_provider.provider_id,
        palette_colors=palette_colors,
        palette=extract_hex_palette(processed_image),
    )


@app.post("/api/reprocess", response_model=GenerateResponse)
async def reprocess_existing_image(payload: ReprocessRequest) -> GenerateResponse:
    """Re-run the pixel pipeline on an existing raw high-res image (e.g. when changing 16/32/64 or palette size)."""
    try:
        raw_image = base64_to_image(payload.raw_image_b64)
        processed = process_texture(
            image=raw_image,
            mode=payload.mode,
            target_size=payload.size,
            palette_colors=payload.palette_colors,
            alpha_threshold=payload.alpha_threshold,
            strip_background=(payload.mode == TextureMode.ITEM and payload.strip_background),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Reprocessing failed: %s", exc.__class__.__name__)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not reprocess the provided image payload.",
        ) from exc

    return GenerateResponse(
        processed_image_b64=image_to_base64_png(processed),
        raw_image_b64=image_to_base64_png(raw_image),
        wrapped_prompt="",
        mode=payload.mode,
        size=payload.size,
        provider="mock",
        palette_colors=payload.palette_colors,
        palette=extract_hex_palette(processed),
    )

