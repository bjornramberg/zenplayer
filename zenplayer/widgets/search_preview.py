from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static

from zenplayer.widgets._art import (
    fallback_image,
    crop_square,
    image_to_rows,
)
from zenplayer.utils.thumbnail import load_thumbnail

ART_W = 24
ART_H = 12


def _word_wrap(text, width):
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = ""
        for word in words:
            test = f"{line} {word}".strip()
            if len(test) <= width:
                line = test
            elif line:
                lines.append(line)
                line = word
            else:
                lines.append(word[:width])
                line = ""
        if line:
            lines.append(line)
    return "\n".join(lines)


class SearchPreviewArt(Widget):
    auto_links = False

    def __init__(self):
        super().__init__()
        self._track = None
        self._image = None

    def set_track(self, track):
        self._track = track
        self._image = None
        self._load()

    def clear(self):
        self._track = None
        self._image = None
        self.refresh()

    @work(thread=True, exclusive=True, group="searchpreview")
    def _load(self):
        track = self._track
        img = None
        if track is not None and getattr(track, "id", None):
            img = load_thumbnail(track.id)
        if self._track is track:
            self.app.call_from_thread(self._apply_image, img)

    def _apply_image(self, img):
        self._image = img
        self.refresh()

    def render(self):
        from rich.text import Text

        w = self.size.width
        h = self.size.height
        if w <= 0 or h <= 0:
            return Text("")

        if self._image is not None:
            img = crop_square(self._image)
        else:
            seed = self._track.id if self._track and getattr(self._track, "id", None) else "idle"
            img = fallback_image(w, h * 2, seed)

        rows = image_to_rows(img, w, h)
        result = Text()
        for i, row in enumerate(rows):
            result.append_text(row)
            if i < len(rows) - 1:
                result.append("\n")
        return result


class SearchPreviewInfo(Static):
    def __init__(self):
        super().__init__("")
        self._track = None

    def set_track(self, track):
        self._track = track
        self.refresh()

    def render(self):
        from rich.text import Text

        track = self._track
        w = self.size.width if self.size.width > 0 else 24
        if not track:
            return Text("")
        title = track.title or "Unknown"
        artist = track.artist or "Unknown"
        duration_s = getattr(track, "duration", None) or ""
        if isinstance(duration_s, (int, float)) and duration_s > 0:
            m, s = divmod(int(duration_s), 60)
            duration_str = f"{m}:{s:02d}"
        else:
            duration_str = ""
        parts = [title, f"{artist}  {duration_str}" if duration_str else artist]
        desc = getattr(track, "description", None) or ""
        if desc:
            parts.append("")  # blank line before description
            parts.append(desc[:300])
        raw = "\n".join(parts)
        return Text(_word_wrap(raw, w))


class SearchPreview(Horizontal):
    def compose(self) -> ComposeResult:
        yield SearchPreviewArt()
        yield SearchPreviewInfo()

    def set_track(self, track):
        self.query_one(SearchPreviewArt).set_track(track)
        self.query_one(SearchPreviewInfo).set_track(track)

    def clear(self):
        self.query_one(SearchPreviewArt).clear()
        self.query_one(SearchPreviewInfo).set_track(None)
