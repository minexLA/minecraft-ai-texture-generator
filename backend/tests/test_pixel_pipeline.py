"""Unit tests for the Minecraft pixel-art post-processing pipeline."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from app.pixel_pipeline import (
    BLOCK_PROMPT_SUFFIX,
    ITEM_PROMPT_SUFFIX,
    apply_binary_alpha_threshold,
    downscale_nearest,
    extract_hex_palette,
    image_to_base64_png,
    base64_to_image,
    process_texture,
    quantize_with_binary_alpha,
    wrap_prompt,
)
from app.schemas import TextureMode


def test_wrap_prompt_item_and_block() -> None:
    item_prompt = wrap_prompt("enchanted ruby sword", TextureMode.ITEM)
    assert item_prompt.startswith("enchanted ruby sword")
    assert ITEM_PROMPT_SUFFIX in item_prompt

    block_prompt = wrap_prompt("mossy cobblestone", TextureMode.BLOCK)
    assert block_prompt.startswith("mossy cobblestone")
    assert BLOCK_PROMPT_SUFFIX in block_prompt


def test_binary_alpha_thresholding_eliminates_semi_transparent_pixels() -> None:
    arr = np.zeros((32, 32, 4), dtype=np.uint8)
    arr[:, :, 0] = 200
    arr[:, :, 1] = 100
    arr[:, :, 2] = 50
    # Create gradient alpha from 0..255
    arr[:, :, 3] = np.linspace(0, 255, 32 * 32, dtype=np.uint8).reshape((32, 32))
    img = Image.fromarray(arr, mode="RGBA")

    thresholded = apply_binary_alpha_threshold(img, threshold=128)
    out_arr = np.asarray(thresholded)
    unique_alphas = set(np.unique(out_arr[:, :, 3]).tolist())
    assert unique_alphas.issubset({0, 255})
    assert 128 not in unique_alphas

    # Transparent pixels should also have zeroed RGB channels
    transparent_rgb = out_arr[out_arr[:, :, 3] == 0][:, :3]
    assert np.all(transparent_rgb == 0)


@pytest.mark.parametrize("target_size", [16, 32, 64])
def test_downscale_nearest_exact_dimensions(target_size: int) -> None:
    arr = np.zeros((256, 256, 4), dtype=np.uint8)
    arr[:128, :128] = [255, 0, 0, 255]
    arr[128:, 128:] = [0, 255, 0, 255]
    img = Image.fromarray(arr, mode="RGBA")

    resized = downscale_nearest(img, target_size=target_size)  # type: ignore[arg-type]
    assert resized.size == (target_size, target_size)

    # Nearest-neighbor on hard quadrants should never introduce blended yellow pixels
    out_arr = np.asarray(resized)
    colors = {tuple(px.tolist()) for px in out_arr.reshape(-1, 4)}
    assert colors.issubset({(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 0, 0)})


def test_quantize_with_binary_alpha_bounds_color_count() -> None:
    rng = np.random.default_rng(42)
    arr = rng.integers(0, 256, size=(32, 32, 4), dtype=np.uint8)
    img = Image.fromarray(arr, mode="RGBA")

    quantized = quantize_with_binary_alpha(img, num_colors=16, alpha_threshold=128)
    palette = extract_hex_palette(quantized)
    assert 1 <= len(palette) <= 16

    out_alpha = np.asarray(quantized)[:, :, 3]
    assert set(np.unique(out_alpha).tolist()).issubset({0, 255})


def test_process_texture_end_to_end_item_and_block() -> None:
    rng = np.random.default_rng(7)
    arr = rng.integers(40, 220, size=(128, 128, 4), dtype=np.uint8)
    img = Image.fromarray(arr, mode="RGBA")

    item_tex = process_texture(img, mode=TextureMode.ITEM, target_size=16, palette_colors=16)
    assert item_tex.size == (16, 16)
    item_alpha = np.asarray(item_tex)[:, :, 3]
    assert set(np.unique(item_alpha).tolist()).issubset({0, 255})

    block_tex = process_texture(img, mode=TextureMode.BLOCK, target_size=32, palette_colors=24)
    assert block_tex.size == (32, 32)
    block_alpha = np.asarray(block_tex)[:, :, 3]
    assert np.all(block_alpha == 255)

    # Roundtrip base64 PNG encoding
    b64 = image_to_base64_png(block_tex)
    decoded = base64_to_image(b64)
    assert decoded.size == (32, 32)

