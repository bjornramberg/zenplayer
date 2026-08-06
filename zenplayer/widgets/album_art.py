import hashlib

import numpy as np
from PIL import Image, ImageOps
from rich.style import Style
from rich.text import Text
from textual import work
from textual.widget import Widget

from zenplayer.utils.thumbnail import load_thumbnail


PALETTE_COLORS = 128


def _hex(rgb) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _fallback_image(width, height, seed):
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


class AlbumArt(Widget):
    auto_links = False

    def __init__(self):
        super().__init__()
        self._track = None
        self._image = None
        self._art_key = None
        self._art_rows = []

    def set_track(self, track):
        self._track = track
        self._image = None
        self._art_key = None
        self.refresh()
        self._load()

    @work(thread=True, exclusive=True, group="albumart")
    def _load(self):
        track = self._track
        img = None
        if track is not None and getattr(track, "id", None):
            img = load_thumbnail(track.id)
        if self._track is track:
            self.app.call_from_thread(self._apply_image, img)

    def _apply_image(self, img):
        self._image = img
        self._art_key = None
        self.refresh()

    def render(self) -> Text:
        w, h = self.size.width, self.size.height
        if w <= 0 or h <= 0:
            return Text("")

        rows = self._art_rows_for(w, h)
        result = Text()
        for i, row in enumerate(rows):
            result.append_text(row)
            if i < len(rows) - 1:
                result.append("\n")
        return result

    def _art_rows_for(self, w, art_h):
        if art_h <= 0 or w <= 0:
            return []
        track_id = self._track.id if self._track is not None else None
        key = (w, art_h, id(self._image), track_id)
        if key == self._art_key:
            return self._art_rows

        px = self._pixels_for(w, art_h * 2)
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
        self._art_rows = rows
        self._art_key = key
        return rows

    def _pixels_for(self, w, px_h) -> np.ndarray:
        if self._image is None:
            seed = self._track.id if self._track is not None and self._track.id else "idle"
            img = _fallback_image(w, px_h, seed)
        else:
            img = self._image
        fitted = ImageOps.fit(img, (w, px_h), Image.LANCZOS)
        if fitted.mode != "RGB":
            fitted = fitted.convert("RGB")
        quantized = fitted.quantize(
            colors=PALETTE_COLORS, method=Image.FASTOCTREE, dither=Image.Dither.NONE
        ).convert("RGB")
        return np.asarray(quantized).astype(np.uint8)
