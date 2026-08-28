import hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageOps
from rich.style import Style
from rich.text import Text

PALETTE_COLORS = 128


def _hex(rgb) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def create_circular_mask(size):
    """Create a circular mask for the given size."""
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size - 1, size - 1), fill=255)
    return mask


def apply_circle_mask(img, size):
    """Center-crop artwork to a square and mask its corners as a disc."""
    source = crop_square(img).convert("RGB")
    # Each terminal cell represents two vertical pixels via the half-block
    # character, so the pixel buffer is twice as tall as it is wide.
    source = source.resize((size, size * 2), Image.LANCZOS)

    mask = Image.new("L", (size, size * 2), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size - 1, size * 2 - 1), fill=255)
    result = Image.new("RGB", (size, size * 2), (0, 0, 0))
    result.paste(source, mask=mask)

    # A subtle rim makes the record boundary visible against the black panel.
    draw = ImageDraw.Draw(result)
    draw.ellipse((1, 1, size - 2, size * 2 - 2), outline=(70, 70, 70), width=1)
    draw.ellipse((size // 2 - 1, size - 2, size // 2 + 1, size + 2), fill=(170, 170, 170))
    return result


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


def quantize_image(img, w, px_h, palette_colors=PALETTE_COLORS, fit=True):
    fitted = ImageOps.fit(img, (w, px_h), Image.LANCZOS) if fit else img
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
