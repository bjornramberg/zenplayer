from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label

from zenplayer.utils.format import format_duration


class ZenNowPlaying(Widget):
    def __init__(self):
        super().__init__()
        self._track = None
        self._paused = True
        self._time_pos = 0.0
        self._duration = 0.0

    def compose(self) -> ComposeResult:
        with Vertical(id="zen-info"):
            yield Label("zenplayer", id="zen-title")
            yield Label("Nothing playing", id="zen-artist")
            yield Label("0:00 / 0:00", id="zen-progress")

    def update_state(self, track, paused, time_pos, duration):
        self._track = track
        self._paused = paused
        self._time_pos = time_pos
        self._duration = duration

        title = self.query_one("#zen-title", Label)
        artist = self.query_one("#zen-artist", Label)
        progress = self.query_one("#zen-progress", Label)

        if track:
            title.update(track.title or "Unknown")
            artist.update(track.artist or "Unknown")
            cur = format_duration(time_pos)
            total = format_duration(duration) if duration > 0 else "0:00"
            progress.update(f"{cur} / {total}")
        else:
            title.update("zenplayer")
            artist.update("Nothing playing")
            progress.update("0:00 / 0:00")
