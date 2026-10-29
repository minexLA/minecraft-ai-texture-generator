"""Pydantic schemas for request validation and response serialization."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class TextureMode(str, Enum):
    """Supported Minecraft asset generation modes."""

    ITEM = "item"
    BLOCK = "block"


TargetSize = Literal[16, 32, 64]

ProviderId = Literal[
    "upload_only",
    "pollinations",
    "mock",
    "huggingface",
    "openai",
    "gemini",
    "replicate",
    "fal",
    "local_sd",
]


class ProviderInfo(BaseModel):
    """Metadata describing an inference provider and its availability."""

    id: ProviderId
    name: str
    description: str
    configured: bool
    supports_img2img: bool
    is_default: bool = False


class ProvidersResponse(BaseModel):
    """Response listing all supported AI generation providers."""

    default_provider: ProviderId
    providers: list[ProviderInfo]


class GenerateResponse(BaseModel):
    """Response returned after generating and post-processing a texture."""

    processed_image_b64: str = Field(
        ..., description="Base64-encoded PNG of the final pixel-art texture."
    )
    raw_image_b64: str = Field(
        ..., description="Base64-encoded PNG of the high-resolution image before pixel pipeline."
    )
    wrapped_prompt: str = Field(
        ..., description="Full prompt sent to the model after mode-specific wrapping."
    )
    mode: TextureMode
    size: TargetSize
    provider: ProviderId
    palette_colors: int = Field(
        ..., description="Number of palette colors used during MedianCut quantization."
    )
    palette: list[str] = Field(
        default_factory=list,
        description="Extracted hex colors (#RRGGBB) present in the final texture.",
    )


class ReprocessRequest(BaseModel):
    """Request to re-run the pixel pipeline on an existing raw image without re-invoking AI."""

    raw_image_b64: str = Field(
        ..., description="Base64-encoded PNG (with or without data URL prefix)."
    )
    mode: TextureMode = TextureMode.ITEM
    size: TargetSize = 16
    alpha_threshold: int = Field(default=128, ge=1, le=254)
    palette_colors: int = Field(default=24, ge=2, le=64)
    strip_background: bool = Field(
        default=True,
        description="Whether to run background removal when mode is 'item'.",
    )

