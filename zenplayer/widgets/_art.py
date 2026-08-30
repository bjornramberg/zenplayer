import hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageOps
from rich.style import Style
from rich.text import Text

PALETTE_COLORS = 128


def _hex(rgb) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def apply_circle_mask(img, width_cells, height_cells):
    """Render a turntable: a vinyl disc with the square artwork filling it.

    The artwork is center-cropped to a square, stretched onto the full disc,
    then its corners are cut by a circular mask. A vinyl ring and rim are drawn
    *outside* the artwork so the record boundary reads as a clean outer line
    rather than a groove over the picture.
    """
    source = crop_square(img).convert("RGB")
    # Each terminal cell represents two vertical pixels via the half-block
    # character, so the pixel buffer is twice as tall as the disc radius.
    pixel_height = height_cells * 2
    source = source.resize((width_cells, pixel_height), Image.LANCZOS)

    disc = Image.new("RGB", (width_cells, pixel_height), (0, 0, 0))
    draw = ImageDraw.Draw(disc)

    # Outer vinyl face and its rim sit at the very edge, behind everything.
    draw.ellipse((0, 0, width_cells - 1, pixel_height - 1), fill=(16, 16, 16))
    draw.ellipse((0, 0, width_cells - 1, pixel_height - 1), outline=(90, 90, 90), width=1)

    # The artwork fills the disc but leaves a thin vinyl groove + rim around it.
    margin = max(2, int(min(width_cells, pixel_height) * 0.03))
    mask = Image.new("L", (width_cells, pixel_height), 0)
    ImageDraw.Draw(mask).ellipse(
        (margin, margin, width_cells - 1 - margin, pixel_height - 1 - margin),
        fill=255,
    )
    disc.paste(source, (0, 0), mask)

    # Center spindle.
    center_x, center_y = width_cells // 2, pixel_height // 2
    ImageDraw.Draw(disc).ellipse(
        (center_x - 1, center_y - 2, center_x + 1, center_y + 2),
        fill=(170, 170, 170),
    )
    return disc


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
