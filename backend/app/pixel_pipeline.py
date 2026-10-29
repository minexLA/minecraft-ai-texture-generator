"""Pixel-art image post-processing pipeline for Minecraft item and block textures.

Enforces strict pixel-art constraints required by Minecraft:
1. Prompt wrapping for Item vs. Block modes.
2. Background stripping via `rembg` (with corner-flood-fill fallback when offline).
3. Binary alpha thresholding (`alpha > 128 ? 255 : 0`) to remove semi-transparent fringes.
4. Strict Nearest-Neighbor downscaling (`Image.Resampling.NEAREST`) to 16x16, 32x32, or 64x64.
5. MedianCut color quantization (`Image.Quantize.MEDIANCUT`, no dithering) preserving binary alpha.
"""

from __future__ import annotations

import base64
import io
import logging
from typing import Literal

import numpy as np
from PIL import Image

from app.schemas import TargetSize, TextureMode

logger = logging.getLogger(__name__)

ITEM_PROMPT_SUFFIX = (
    ", 16-bit pixel art sprite, centered isolated icon, solid neutral background, "
    "flat 2D orthographic, hard crisp edges, no soft shadows"
)

BLOCK_PROMPT_SUFFIX = (
    ", seamless tileable texture, flat orthographic 2D pattern, pixel art, "
    "square pattern, continuous repeating edges, 16-bit texture"
)

_REMBG_SESSION = None


def wrap_prompt(prompt: str, mode: TextureMode | Literal["item", "block"]) -> str:
    """Append the mandatory Minecraft pixel-art constraints to a user prompt."""
    cleaned = prompt.strip().rstrip(",")
    resolved_mode = TextureMode(mode)
    if resolved_mode == TextureMode.ITEM:
        return f"{cleaned}{ITEM_PROMPT_SUFFIX}"
    return f"{cleaned}{BLOCK_PROMPT_SUFFIX}"


def _fallback_corner_background_removal(image: Image.Image, tolerance: int = 36) -> Image.Image:
    """Fallback background removal when rembg or its ONNX weights are unavailable offline.

    Samples the corner pixels of the image and masks out contiguous or matching neutral
    background pixels while preserving any existing alpha transparency.
    """
    rgba = image.convert("RGBA")
    arr = np.array(rgba, dtype=np.int16)
    # If the image already has transparent pixels, keep its alpha channel
    if np.any(arr[:, :, 3] < 250):
        return rgba

    h, w, _ = arr.shape
    corners = np.array(
        [
            arr[0, 0, :3],
            arr[0, w - 1, :3],
            arr[h - 1, 0, :3],
            arr[h - 1, w - 1, :3],
        ],
        dtype=np.float32,
    )
    bg_color = np.median(corners, axis=0)
    diff = np.linalg.norm(arr[:, :, :3].astype(np.float32) - bg_color, axis=2)
    mask = diff <= tolerance

    out = arr.astype(np.uint8)
    out[mask, 3] = 0
    return Image.fromarray(out, mode="RGBA")


def remove_background(image: Image.Image) -> Image.Image:
    """Strip background from an item sprite using `rembg` with corner color-key fallback."""
    global _REMBG_SESSION
    rgba = image.convert("RGBA")
    arr = np.asarray(rgba)
    transparent_ratio = float(np.mean(arr[:, :, 3] < 128))

    try:
        from rembg import new_session, remove  # type: ignore[import-untyped]

        if transparent_ratio < 0.10:
            if _REMBG_SESSION is None:
                _REMBG_SESSION = new_session("u2net")
            result = remove(rgba, session=_REMBG_SESSION)
            if isinstance(result, Image.Image):
                return result.convert("RGBA")
            return Image.open(io.BytesIO(result)).convert("RGBA")
        return rgba
    except Exception as exc:
        logger.warning(
            "rembg unavailable (%s); falling back to corner color-key segmentation.",
            exc.__class__.__name__,
        )
        return _fallback_corner_background_removal(rgba)


def apply_binary_alpha_threshold(image: Image.Image, threshold: int = 128) -> Image.Image:
    """Enforce strict binary alpha (`alpha > threshold ? 255 : 0`) and zero out transparent RGB.

    Eliminates semi-transparent fringe/halos that break Minecraft item rendering.
    """
    if not 0 <= threshold <= 254:
        raise ValueError("threshold must be between 0 and 254")

    rgba = image.convert("RGBA")
    arr = np.array(rgba, dtype=np.uint8, copy=True)
    alpha = arr[:, :, 3]
    binary_alpha = np.where(alpha > threshold, 255, 0).astype(np.uint8)
    arr[:, :, 3] = binary_alpha
    # Zero out RGB channels on transparent pixels to prevent color bleeding and improve PNG compression
    transparent_mask = binary_alpha == 0
    arr[transparent_mask, 0] = 0
    arr[transparent_mask, 1] = 0
    arr[transparent_mask, 2] = 0
    return Image.fromarray(arr, mode="RGBA")


def downscale_nearest(image: Image.Image, target_size: TargetSize = 16) -> Image.Image:
    """Downscale image to `(target_size, target_size)` strictly using Nearest Neighbor."""
    if target_size not in (16, 32, 64):
        raise ValueError(f"Unsupported target_size={target_size}. Expected 16, 32, or 64.")
    return image.resize((target_size, target_size), resample=Image.Resampling.NEAREST)


def quantize_with_binary_alpha(
    image: Image.Image,
    num_colors: int = 24,
    alpha_threshold: int = 128,
) -> Image.Image:
    """Quantize RGB colors using MedianCut without dithering while preserving binary alpha.

    Ensures transparent pixels do not pollute the color palette calculation and that the
    resulting alpha channel remains strictly binary (`0` or `255`).
    """
    if not 2 <= num_colors <= 256:
        raise ValueError("num_colors must be between 2 and 256")

    rgba = apply_binary_alpha_threshold(image, threshold=alpha_threshold)
    arr = np.array(rgba, dtype=np.uint8)
    alpha_channel = arr[:, :, 3]
    opaque_mask = alpha_channel == 255

    if not np.any(opaque_mask):
        # Fully transparent image
        return Image.fromarray(np.zeros_like(arr), mode="RGBA")

    # Fill transparent pixels with the median opaque color before RGB quantization
    # so the background color (0,0,0) does not steal a palette slot or bias MedianCut.
    opaque_pixels = arr[opaque_mask][:, :3]
    fill_color = np.median(opaque_pixels, axis=0).astype(np.uint8)

    rgb_filled = arr[:, :, :3].copy()
    rgb_filled[~opaque_mask] = fill_color

    rgb_image = Image.fromarray(rgb_filled, mode="RGB")
    quantized_p = rgb_image.quantize(
        colors=num_colors,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    )
    quantized_rgb = np.array(quantized_p.convert("RGB"), dtype=np.uint8)

    # Recombine quantized RGB with the exact binary alpha channel
    out = np.zeros_like(arr)
    out[:, :, :3] = quantized_rgb
    out[:, :, 3] = alpha_channel
    out[~opaque_mask, :3] = 0
    return Image.fromarray(out, mode="RGBA")


def extract_hex_palette(image: Image.Image) -> list[str]:
    """Extract unique opaque `#RRGGBB` hex colors sorted by frequency (most common first)."""
    rgba = image.convert("RGBA")
    arr = np.asarray(rgba, dtype=np.uint8)
    opaque_rgb = arr[arr[:, :, 3] > 0][:, :3]
    if opaque_rgb.size == 0:
        return []
    unique_colors, counts = np.unique(opaque_rgb, axis=0, return_counts=True)
    order = np.argsort(-counts)
    return [
        f"#{int(r):02x}{int(g):02x}{int(b):02x}"
        for r, g, b in unique_colors[order]
    ]


def process_texture(
    image: Image.Image,
    mode: TextureMode | Literal["item", "block"] = TextureMode.ITEM,
    target_size: TargetSize = 16,
    palette_colors: int = 24,
    alpha_threshold: int = 128,
    strip_background: bool = True,
) -> Image.Image:
    """Execute the complete Minecraft pixel-art post-processing pipeline on an input image.

    Steps:
    1. Convert to square aspect ratio (center crop if non-square).
    2. For Item mode: strip background via `rembg` and apply binary alpha thresholding.
       For Block mode: force opaque alpha (`255`) across the full tile.
    3. Downscale to `(target_size, target_size)` using `Image.Resampling.NEAREST`.
    4. Quantize colors via `Image.Quantize.MEDIANCUT` without dithering while preserving binary alpha.
    """
    resolved_mode = TextureMode(mode)
    rgba = image.convert("RGBA")

    # Center-crop to square if input has non-square dimensions
    w, h = rgba.size
    if w != h:
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        rgba = rgba.crop((left, top, left + side, top + side))

    if resolved_mode == TextureMode.ITEM:
        if strip_background:
            rgba = remove_background(rgba)
        rgba = apply_binary_alpha_threshold(rgba, threshold=alpha_threshold)
    else:
        # Blocks in Minecraft standard opaque textures fill the entire tile with alpha=255
        arr = np.array(rgba, dtype=np.uint8, copy=True)
        arr[:, :, 3] = 255
        rgba = Image.fromarray(arr, mode="RGBA")

    downscaled = downscale_nearest(rgba, target_size=target_size)
    quantized = quantize_with_binary_alpha(
        downscaled,
        num_colors=palette_colors,
        alpha_threshold=alpha_threshold,
    )
    return quantized


def image_to_png_bytes(image: Image.Image) -> bytes:
    """Encode a PIL Image as lossless PNG bytes."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=False)
    return buffer.getvalue()


def image_to_base64_png(image: Image.Image) -> str:
    """Encode a PIL Image as a raw base64 PNG string."""
    return base64.b64encode(image_to_png_bytes(image)).decode("ascii")


def base64_to_image(b64_data: str) -> Image.Image:
    """Decode a base64 PNG/JPEG/WebP string (with or without data URI header) into a PIL Image."""
    cleaned = b64_data.strip()
    if "," in cleaned and cleaned.startswith("data:"):
        cleaned = cleaned.split(",", 1)[1]
    raw_bytes = base64.b64decode(cleaned, validate=True)
    return validate_and_open_image_bytes(raw_bytes)


def validate_and_open_image_bytes(raw_bytes: bytes, max_pixels: int = 4096 * 4096) -> Image.Image:
    """Safely validate image magic bytes, structure, and dimensions before loading pixels."""
    if not raw_bytes:
        raise ValueError("Empty image payload.")

    # Verify structural integrity first
    with Image.open(io.BytesIO(raw_bytes)) as probe:
        fmt = (probe.format or "").upper()
        if fmt not in {"PNG", "JPEG", "MPO", "WEBP", "BMP", "GIF"}:
            raise ValueError(
                f"Unsupported image format '{fmt}'. Allowed: PNG, JPEG/JFIF/JIFF, WEBP, BMP, GIF."
            )
        w, h = probe.size
        if w <= 0 or h <= 0 or (w * h) > max_pixels:
            raise ValueError(f"Image dimensions {w}x{h} exceed allowed safety limits.")
        probe.verify()

    # Re-open after verify() to decode pixel data into memory
    with Image.open(io.BytesIO(raw_bytes)) as img:
        return img.convert("RGBA").copy()

