from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Label

from zenplayer.utils.format import format_duration


class Controls(Horizontal):
    def __init__(self, volume: int = 50):
        super().__init__()
        self.paused = True
        self.volume = volume
        self.time_pos = 0.0
        self.duration = 0.0

    def compose(self) -> ComposeResult:
        yield Label("  ⏮", id="btn-prev", classes="control-btn")
        yield Label(" ⏸", id="btn-play", classes="control-btn")
        yield Label(" ⏭", id="btn-next", classes="control-btn")
        yield Label("   Vol:", id="vol-label")
        filled = max(0, min(10, self.volume // 10))
        yield Label(
            "█" * filled + "░" * (10 - filled), id="vol-bar", classes="vol-bar"
        )
        yield Label("", id="time-display", classes="time")

    def update_state(
        self, paused: bool, volume: int, time_pos: float, duration: float
    ):
        old_paused, old_volume = self.paused, self.volume
        self.paused = paused
        self.volume = volume
        self.time_pos = time_pos
        self.duration = duration

        play_btn = self.query_one("#btn-play", Label)
        if paused != old_paused:
            play_btn.update(" ▶" if paused else " ⏸")

        vol_bar = self.query_one("#vol-bar", Label)
        if volume != old_volume:
            filled = volume // 10
            vol_bar.update("█" * filled + "░" * (10 - filled))

        time_label = self.query_one("#time-display", Label)
        current = format_duration(time_pos)
        total = format_duration(duration) if duration > 0 else "0:00"
        time_label.update(f"  {current}/{total}")
