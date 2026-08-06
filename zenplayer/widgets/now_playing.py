from rich.style import Style
from rich.text import Text
from textual.widget import Widget

from zenplayer.utils.format import format_duration

TITLE = "#ffffff"
ARTIST = "#9a9a9a"
BAR_FILL = "#ff6b6b"
BAR_TRACK = "#333333"
TIME = "#7a7a7a"
IDLE = "#555555"
GLOW_BASE = (10, 10, 10)
GLOW_TINT = (48, 20, 14)


def _hex(rgb) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _clip(text, width):
    if width <= 0:
        return ""
    text = text or ""
    if len(text) <= width:
        return text
    if width == 1:
        return text[:1]
    return text[: width - 1] + "…"


class NowPlayingOverlay(Widget):
    def __init__(self):
        super().__init__()
        self._track = None
        self._paused = False
        self._time_pos = 0.0
        self._duration = 0.0
        self._bass = 0.0

    def set_track(self, track):
        self._track = track
        self._time_pos = 0.0
        self._duration = 0.0
        self._bass = 0.0
        self.refresh()

    def set_paused(self, paused):
        if paused != self._paused:
            self._paused = paused
            self.refresh()

    def set_progress(self, time_pos, duration):
        self._time_pos = time_pos
        self._duration = duration
        self.refresh()

    def set_bass(self, level: float) -> None:
        level = max(0.0, min(1.0, level))
        if abs(level - self._bass) < 0.005:
            return
        self._bass = level
        self.refresh()

    def render(self) -> Text:
        w = self.size.width
        h = self.size.height
        if w <= 0 or h <= 0:
            return Text("")

        bg = self._glow_bg()
        rows = []
        track = self._track

        if track is not None:
            title = _clip(track.title or "Unknown", w - 2)
            artist_text = track.artist or "Unknown"
            if self._paused:
                artist_text += "  (paused)"
            artist = _clip(artist_text, w - 2)
            rows.append(
                self._text_row("  " + title, Style(color=TITLE, bold=True, bgcolor=bg), w)
            )
            rows.append(self._text_row("  " + artist, Style(color=ARTIST, bgcolor=bg), w))
            rows.append(self._progress_row(w, bg))
        else:
            rows.append(
                self._text_row("  zenplayer", Style(color=IDLE, bold=True, bgcolor=bg), w)
            )
            rows.append(self._text_row("  Nothing playing", Style(color=IDLE, bgcolor=bg), w))
            rows.append(self._text_row("  Press / to search", Style(color=IDLE, bgcolor=bg), w))

        rows.insert(0, Text(" " * w, Style(bgcolor=bg)))

        while len(rows) < h:
            rows.append(Text(" " * w, Style(bgcolor=bg)))

        result = Text()
        for i, row in enumerate(rows[:h]):
            result.append_text(row)
            if i < len(rows[:h]) - 1:
                result.append("\n")
        return result

    def _glow_bg(self) -> str:
        level = self._bass
        r = int(GLOW_BASE[0] + (GLOW_TINT[0] - GLOW_BASE[0]) * level)
        g = int(GLOW_BASE[1] + (GLOW_TINT[1] - GLOW_BASE[1]) * level)
        b = int(GLOW_BASE[2] + (GLOW_TINT[2] - GLOW_BASE[2]) * level)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _text_row(self, text, style, w) -> Text:
        line = Text()
        if len(text) >= w:
            line.append(_clip(text, w), style)
        else:
            line.append(text, style)
            line.append(" " * (w - len(text)), Style(bgcolor=style.bgcolor))
        return line

    def _progress_row(self, w, bg) -> Text:
        if self._duration > 0:
            frac = max(0.0, min(1.0, self._time_pos / self._duration))
        else:
            frac = 0.0
        cur = format_duration(self._time_pos)
        total = format_duration(self._duration) if self._duration > 0 else "0:00"
        time_str = f"{cur} / {total}"

        line = Text()
        if w < 12:
            text = _clip("  " + time_str, w - 1)
            line.append(text, Style(color=TIME, bgcolor=bg))
            line.append(" " * (w - len(text)), Style(bgcolor=bg))
            return line

        bar_w = max(0, w - 5 - len(time_str))
        filled = int(round(frac * bar_w))

        line.append("  ", Style(bgcolor=bg))
        line.append("█" * filled, Style(color=BAR_FILL, bgcolor=bg))
        line.append("░" * (bar_w - filled), Style(color=BAR_TRACK, bgcolor=bg))
        line.append("  ", Style(bgcolor=bg))
        line.append(time_str, Style(color=TIME, bgcolor=bg))
        pad = w - (4 + bar_w + len(time_str))
        if pad > 0:
            line.append(" " * pad, Style(bgcolor=bg))
        return line
