from textual import work
from textual.widget import Widget
from PIL import Image

from zenplayer.widgets._art import (
    PALETTE_COLORS,
    apply_circle_mask,
    fallback_image,
    quantize_image,
    pixels_to_rows,
)
from zenplayer.utils.thumbnail import load_thumbnail


class AlbumArt(Widget):
    auto_links = False

    def __init__(self):
        super().__init__()
        self._track = None
        self._image = None
        self._art_key = None
        self._art_rows = []
        self._rotation = 0.0
        self._turntable_mode = False
        self._spin_timer = None

    def toggle_turntable(self):
        """Toggle turntable mode on/off."""
        self._turntable_mode = not self._turntable_mode
        if self._turntable_mode:
            self._start_spinning()
        else:
            self._stop_spinning()
            self._rotation = 0.0
            self._art_key = None
            self.refresh()

    def set_track(self, track):
        self._track = track
        self._image = None
        self._art_key = None
        self._rotation = 0.0
        if self._turntable_mode:
            self._start_spinning()
        self.refresh()
        self._load()

    def _start_spinning(self):
        """Start the turntable rotation animation."""
        self._stop_spinning()
        self._spin_timer = self.set_interval(0.1, self._rotate_tick)

    def _stop_spinning(self):
        """Stop the turntable rotation animation."""
        if self._spin_timer is not None:
            self._spin_timer.stop()
            self._spin_timer = None

    def _rotate_tick(self):
        """Rotate the image by a small amount and refresh."""
        if self._image is not None:
            self._rotation = (self._rotation + 3.0) % 360
            self._art_key = None
            self.refresh()

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

    def render(self):
        from rich.text import Text

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
        key = (w, art_h, id(self._image), track_id, self._rotation, self._turntable_mode)
        if key == self._art_key:
            return self._art_rows

        if self._image is not None:
            img = self._image
        else:
            seed = track_id or "idle"
            img = fallback_image(w, art_h * 2, seed)

        if self._turntable_mode:
            circle_size = int(min(w, art_h * 2) * 0.7)
            img = apply_circle_mask(img, circle_size)
            if self._rotation != 0:
                img = img.rotate(self._rotation, resample=Image.BICUBIC, fillcolor=(0, 0, 0))
            canvas = Image.new("RGB", (w, art_h * 2), (0, 0, 0))
            offset_x = (w - circle_size) // 2
            offset_y = (art_h * 2 - circle_size) // 2
            canvas.paste(img, (offset_x, offset_y))
            img = canvas

        px = quantize_image(img, w, art_h * 2)
        self._art_rows = pixels_to_rows(px, w, art_h)
        self._art_key = key
        return self._art_rows
