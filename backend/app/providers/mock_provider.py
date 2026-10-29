"""Built-in Procedural/Mock Provider for instant offline testing and fallback."""

from __future__ import annotations

import hashlib
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from app.providers.base import BaseImageProvider
from app.schemas import ProviderId, TextureMode

# Named color themes mapped from prompt keywords
_COLOR_THEMES: dict[str, tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]] = {
    "ruby": ((210, 35, 60), (255, 110, 130), (110, 15, 30)),
    "crimson": ((200, 30, 50), (245, 95, 115), (95, 10, 25)),
    "red": ((210, 45, 45), (250, 120, 110), (115, 20, 20)),
    "emerald": ((30, 190, 85), (115, 245, 155), (15, 95, 40)),
    "green": ((50, 175, 70), (120, 230, 135), (25, 90, 35)),
    "moss": ((75, 145, 55), (130, 195, 95), (45, 85, 30)),
    "diamond": ((55, 215, 230), (175, 250, 255), (25, 115, 140)),
    "ice": ((110, 200, 250), (200, 240, 255), (55, 120, 180)),
    "blue": ((55, 120, 225), (130, 185, 255), (25, 60, 130)),
    "lapis": ((35, 75, 195), (95, 140, 240), (18, 38, 110)),
    "gold": ((245, 195, 45), (255, 240, 140), (160, 105, 15)),
    "yellow": ((240, 205, 50), (255, 245, 145), (155, 115, 20)),
    "amethyst": ((155, 75, 220), (215, 155, 255), (80, 30, 130)),
    "purple": ((145, 65, 210), (205, 140, 250), (75, 25, 120)),
    "obsidian": ((35, 25, 55), (85, 60, 125), (15, 10, 28)),
    "nether": ((135, 35, 35), (210, 95, 55), (65, 15, 18)),
    "lava": ((245, 105, 25), (255, 210, 75), (145, 35, 10)),
    "fire": ((245, 115, 30), (255, 220, 85), (150, 40, 15)),
    "copper": ((205, 115, 70), (240, 165, 120), (110, 65, 45)),
    "iron": ((195, 200, 210), (240, 245, 250), (105, 110, 125)),
    "stone": ((130, 132, 138), (175, 178, 185), (78, 80, 86)),
    "cobble": ((125, 128, 132), (168, 172, 178), (70, 72, 78)),
    "wood": ((155, 110, 62), (195, 148, 92), (95, 65, 35)),
    "oak": ((160, 115, 65), (200, 155, 98), (98, 68, 38)),
    "sand": ((225, 210, 150), (245, 235, 185), (170, 152, 98)),
}


def _select_theme(prompt: str, seed_bytes: bytes) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    lower = prompt.lower()
    for key, colors in _COLOR_THEMES.items():
        if key in lower:
            return colors
    # Deterministic fallback theme from prompt hash
    r = 60 + (seed_bytes[0] % 160)
    g = 60 + (seed_bytes[1] % 160)
    b = 60 + (seed_bytes[2] % 160)
    base = (r, g, b)
    light = (min(255, int(r * 1.35)), min(255, int(g * 1.35)), min(255, int(b * 1.35)))
    dark = (max(15, int(r * 0.5)), max(15, int(g * 0.5)), max(15, int(b * 0.5)))
    return base, light, dark


class MockProceduralProvider(BaseImageProvider):
    """Generates anti-aliased 256x256 synthetic sprites and seamless blocks for pipeline testing."""

    provider_id: ProviderId = "mock"
    name = "Procedural (Offline)"
    description = "Local procedural sprite and seamless pattern generator."
    supports_img2img = True

    def is_configured(self) -> bool:
        return True

    async def generate(
        self,
        wrapped_prompt: str,
        mode: TextureMode,
        reference_image: Image.Image | None = None,
        strength: float = 0.75,
    ) -> Image.Image:
        digest = hashlib.sha256(wrapped_prompt.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:4], "big")
        rng = np.random.default_rng(seed)
        base_col, light_col, dark_col = _select_theme(wrapped_prompt, digest)

        if mode == TextureMode.ITEM:
            generated = self._generate_item_sprite(wrapped_prompt, base_col, light_col, dark_col, rng)
        else:
            generated = self._generate_seamless_block(wrapped_prompt, base_col, light_col, dark_col, rng)

        if reference_image is not None:
            ref_resized = reference_image.convert("RGBA").resize((256, 256), Image.Resampling.BILINEAR)
            alpha_blend = float(np.clip(strength, 0.05, 0.95))
            generated = Image.blend(ref_resized, generated, alpha=alpha_blend)

        return generated

    def _generate_item_sprite(
        self,
        prompt: str,
        base_col: tuple[int, int, int],
        light_col: tuple[int, int, int],
        dark_col: tuple[int, int, int],
        rng: np.random.Generator,
    ) -> Image.Image:
        size = 256
        # Neutral background so rembg / fallback strips it and soft blur creates anti-aliased fringe
        img = Image.new("RGBA", (size, size), (238, 240, 244, 255))
        layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        lower = prompt.lower()

        handle_dark = (88, 56, 30, 255)
        handle_light = (145, 96, 52, 255)

        if any(w in lower for w in ("pickaxe", "pick")):
            # Diagonal handle
            draw.line([(48, 208), (184, 72)], fill=handle_dark, width=28)
            draw.line([(52, 204), (180, 76)], fill=handle_light, width=14)
            # Curved pickaxe head
            head_pts = [(112, 44), (180, 44), (212, 76), (212, 144), (188, 144), (172, 92), (112, 68)]
            draw.polygon(head_pts, fill=(*base_col, 255), outline=(*dark_col, 255))
            draw.line([(125, 54), (178, 54), (200, 78)], fill=(*light_col, 255), width=8)
        elif any(w in lower for w in ("apple", "fruit", "orb", "pearl", "potion", "heart", "gem")):
            # Rounded gem / apple / orb silhouette
            bbox = [48, 56, 208, 212]
            draw.ellipse(bbox, fill=(*dark_col, 255))
            draw.ellipse([58, 66, 198, 202], fill=(*base_col, 255))
            draw.ellipse([78, 82, 136, 134], fill=(*light_col, 255))
            # Stem & leaf
            draw.rectangle([120, 28, 136, 62], fill=handle_dark)
            draw.polygon([(136, 36), (176, 28), (160, 58)], fill=(65, 180, 65, 255))
        elif any(w in lower for w in ("axe", "hatchet", "hammer")):
            draw.line([(48, 208), (188, 68)], fill=handle_dark, width=26)
            draw.line([(52, 204), (184, 72)], fill=handle_light, width=12)
            blade = [(116, 42), (186, 42), (210, 96), (164, 142), (128, 102)]
            draw.polygon(blade, fill=(*base_col, 255), outline=(*dark_col, 255))
            draw.polygon([(126, 52), (176, 52), (194, 88), (160, 112)], fill=(*light_col, 255))
        else:
            # Default iconic Minecraft diagonal sword
            # Blade
            blade_outer = [(92, 140), (196, 36), (220, 36), (220, 60), (116, 164)]
            draw.polygon(blade_outer, fill=(*dark_col, 255))
            blade_inner = [(100, 136), (198, 38), (212, 38), (212, 52), (114, 150)]
            draw.polygon(blade_inner, fill=(*base_col, 255))
            draw.line([(108, 132), (204, 36)], fill=(*light_col, 255), width=8)
            # Crossguard
            guard = [(56, 116), (80, 104), (152, 176), (140, 200)]
            draw.polygon(guard, fill=(*dark_col, 255))
            draw.line([(68, 116), (140, 188)], fill=(*base_col, 255), width=12)
            # Grip & Pommel
            draw.line([(44, 212), (96, 160)], fill=handle_dark, width=26)
            draw.line([(48, 208), (92, 164)], fill=handle_light, width=12)
            draw.ellipse([24, 196, 60, 232], fill=(*dark_col, 255))
            draw.ellipse([30, 202, 54, 226], fill=(*light_col, 255))

        # Add subtle sparkle/noise and Gaussian blur to simulate anti-aliased high-res diffusion model output
        blurred = layer.filter(ImageFilter.GaussianBlur(radius=1.8))
        _ = rng.integers(0, 10)
        combined = Image.alpha_composite(img, blurred)
        # Also keep alpha channel on layer so remove_background or binary thresholding works deterministically
        out_arr = np.array(combined, dtype=np.uint8)
        alpha_arr = np.array(blurred, dtype=np.uint8)[:, :, 3]
        out_arr[:, :, 3] = alpha_arr
        return Image.fromarray(out_arr, mode="RGBA")

    def _generate_seamless_block(
        self,
        prompt: str,
        base_col: tuple[int, int, int],
        light_col: tuple[int, int, int],
        dark_col: tuple[int, int, int],
        rng: np.random.Generator,
    ) -> Image.Image:
        """Synthesize a strictly periodic (torus-wrapped) 256x256 seamless block texture."""
        size = 256
        lower = prompt.lower()
        grid = np.zeros((size, size, 3), dtype=np.float32)
        y_idx, x_idx = np.meshgrid(np.arange(size), np.arange(size), indexing="ij")

        # Periodic multi-octave cosine/sine field (guaranteed seamless at edges)
        field = np.zeros((size, size), dtype=np.float32)
        for freq in (1, 2, 4, 8):
            phase_x = float(rng.uniform(0, 2 * math.pi))
            phase_y = float(rng.uniform(0, 2 * math.pi))
            amp = 1.0 / (freq ** 0.75)
            angle = 2.0 * math.pi * freq / size
            field += amp * (
                np.sin(angle * x_idx + phase_x) * np.cos(angle * y_idx + phase_y)
                + 0.5 * np.cos(angle * (x_idx + y_idx) + phase_x)
            )

        if any(w in lower for w in ("brick", "planks", "tiles", "chiseled")):
            # Seamless brick pattern
            brick_h = 64
            brick_w = 128
            row = (y_idx // brick_h) % 4
            offset_x = (x_idx + (row % 2) * (brick_w // 2)) % size
            mortar = ((y_idx % brick_h) < 10) | ((offset_x % brick_w) < 10)
            field = np.where(mortar, -1.5, field * 0.4 + 0.35)
        elif any(w in lower for w in ("ore", "crystal", "gem", "diamond", "ruby", "emerald", "gold")):
            # Stone base with periodic ore clusters
            stone_base = np.array([122.0, 125.0, 130.0], dtype=np.float32)
            stone_dark = np.array([78.0, 80.0, 86.0], dtype=np.float32)
            norm = (field - field.min()) / (np.ptp(field) + 1e-6)
            for c in range(3):
                grid[:, :, c] = stone_dark[c] + norm * (stone_base[c] - stone_dark[c])

            # Add wrapped Voronoi-like ore flecks
            num_flecks = 14
            centers_y = rng.integers(0, size, size=num_flecks)
            centers_x = rng.integers(0, size, size=num_flecks)
            radii = rng.integers(12, 24, size=num_flecks)
            for cy, cx, rad in zip(centers_y, centers_x, radii):
                dy = np.minimum(np.abs(y_idx - cy), size - np.abs(y_idx - cy))
                dx = np.minimum(np.abs(x_idx - cx), size - np.abs(x_idx - cx))
                dist = np.sqrt(dx * dx + dy * dy)
                ore_mask = dist < rad
                highlight_mask = dist < (rad * 0.45)
                for c in range(3):
                    grid[ore_mask, c] = base_col[c]
                    grid[highlight_mask, c] = light_col[c]
            arr_u8 = np.clip(grid, 0, 255).astype(np.uint8)
            return Image.fromarray(arr_u8, mode="RGB").convert("RGBA")

        # Cellular / cobblestone / organic block interpolation
        num_cells = 18
        cy_list = rng.integers(0, size, size=num_cells)
        cx_list = rng.integers(0, size, size=num_cells)
        d1 = np.full((size, size), 1e9, dtype=np.float32)
        d2 = np.full((size, size), 1e9, dtype=np.float32)
        for cy, cx in zip(cy_list, cx_list):
            dy = np.minimum(np.abs(y_idx - cy), size - np.abs(y_idx - cy)).astype(np.float32)
            dx = np.minimum(np.abs(x_idx - cx), size - np.abs(x_idx - cx)).astype(np.float32)
            dist = np.sqrt(dx * dx + dy * dy)
            swap = dist < d1
            d2 = np.where(swap, d1, np.minimum(d2, dist))
            d1 = np.where(swap, dist, d1)

        edge_metric = (d2 - d1) / (np.max(d2 - d1) + 1e-6)
        combined = 0.55 * edge_metric + 0.45 * ((field - field.min()) / (np.ptp(field) + 1e-6))
        combined = (combined - combined.min()) / (np.ptp(combined) + 1e-6)

        for c in range(3):
            low_val = float(dark_col[c])
            mid_val = float(base_col[c])
            high_val = float(light_col[c])
            channel = np.where(
                combined < 0.5,
                low_val + (combined * 2.0) * (mid_val - low_val),
                mid_val + ((combined - 0.5) * 2.0) * (high_val - mid_val),
            )
            grid[:, :, c] = channel

        arr_u8 = np.clip(grid, 0, 255).astype(np.uint8)
        return Image.fromarray(arr_u8, mode="RGB").convert("RGBA")

