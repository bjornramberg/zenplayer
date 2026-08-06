import hashlib
import numpy as np
from PIL import Image, ImageOps
from rich.style import Style
from rich.text import Text

PALETTE_COLORS = 128


def _hex(rgb) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def fallback_image(width, height, seed):
    palettes = [
        (0x66, 0x2C, 0x33),
        (0x2C, 0x45, 0x66),
        (0x4A, 0x2C, 0x66),
        (0x2C, 0x66, 0x52),
        (0x66, 0x5A, 0x2C),
    ]
    digest = int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16)
    r2, g2, b2 = palettes[digest % len(palettes)]
    base = 6.0

    x = np.arange(width, dtype=np.float32)
    y = np.arange(height, dtype=np.float32)
    t = (y / max(height - 1, 1)) ** 2
    rr = base + (r2 - base) * t
    gg = base + (g2 - base) * t
    bb = base + (b2 - base) * t

    gy, gx = np.meshgrid(y, x, indexing="ij")
    cx, cy = width * 0.5, height * 0.72
    d = np.sqrt(((gx - cx) / max(width, 1)) ** 2 + ((gy - cy) / max(height, 1)) ** 2)
    glow = np.clip(1.0 - d * 2.2, 0, 1)[..., None] * 26

    arr = np.stack([rr, gg, bb], axis=-1)[:, None, :] + glow
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def crop_square(img):
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))


def quantize_image(img, w, px_h, palette_colors=PALETTE_COLORS):
    fitted = ImageOps.fit(img, (w, px_h), Image.LANCZOS)
    if fitted.mode != "RGB":
        fitted = fitted.convert("RGB")
    quantized = fitted.quantize(
        colors=palette_colors, method=Image.FASTOCTREE, dither=Image.Dither.NONE
    ).convert("RGB")
    return np.asarray(quantized).astype(np.uint8)


def pixels_to_rows(px, w, art_h):
    rows = []
    for y in range(art_h):
        line = Text()
        start = 0
        cur = None
        for x in range(w):
            pair = (
                px[y * 2, x, 0], px[y * 2, x, 1], px[y * 2, x, 2],
                px[y * 2 + 1, x, 0], px[y * 2 + 1, x, 1], px[y * 2 + 1, x, 2],
            )
            if pair != cur:
                if cur is not None:
                    line.append("▀" * (x - start), Style(color=_hex(cur[:3]), bgcolor=_hex(cur[3:])))
                cur = pair
                start = x
        if cur is not None:
            line.append("▀" * (w - start), Style(color=_hex(cur[:3]), bgcolor=_hex(cur[3:])))
        rows.append(line)
    return rows


def image_to_rows(img, w, h):
    if img is None:
        return []
    return pixels_to_rows(quantize_image(img, w, h * 2), w, h)
