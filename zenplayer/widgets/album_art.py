from textual import work
from textual.widget import Widget

from zenplayer.widgets._art import (
    PALETTE_COLORS,
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
        key = (w, art_h, id(self._image), track_id)
        if key == self._art_key:
            return self._art_rows

        if self._image is not None:
            img = self._image
        else:
            seed = track_id or "idle"
            img = fallback_image(w, art_h * 2, seed)
        px = quantize_image(img, w, art_h * 2)
        self._art_rows = pixels_to_rows(px, w, art_h)
        self._art_key = key
        return self._art_rows
