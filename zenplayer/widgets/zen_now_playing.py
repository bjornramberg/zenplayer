from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Label

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
            with Horizontal(id="zen-controls"):
                yield Button("⏮", id="zen-prev", classes="zen-btn")
                yield Button("⏸", id="zen-play", classes="zen-btn")
                yield Button("⏭", id="zen-next", classes="zen-btn")

    def update_state(self, track, paused, time_pos, duration):
        self._track = track
        self._paused = paused
        self._time_pos = time_pos
        self._duration = duration

        title = self.query_one("#zen-title", Label)
        artist = self.query_one("#zen-artist", Label)
        progress = self.query_one("#zen-progress", Label)
        play = self.query_one("#zen-play", Button)

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

        play.label = "▶" if paused else "⏸"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action_map = {
            "zen-prev": "action_previous_track",
            "zen-play": "action_play_pause",
            "zen-next": "action_next_track",
        }
        action = action_map.get(event.button.id)
        if action:
            getattr(self.app, action)()
