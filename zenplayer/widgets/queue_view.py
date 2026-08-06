from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Label

from zenplayer.utils.format import format_duration


class QueueView(Horizontal):
    def __init__(self):
        super().__init__()
        self._queue: list = []
        self.display = False

    def compose(self) -> ComposeResult:
        yield Label("", id="queue-label")

    def set_queue(self, tracks: list) -> None:
        if tracks == self._queue:
            return
        self._queue = tracks
        self.display = bool(tracks)
        label = self.query_one("#queue-label", Label)
        if not tracks:
            label.update("  Queue: (empty)")
            return
        parts = []
        for t in tracks[:5]:
            dur = format_duration(t.duration)
            parts.append(f"{t.title} [{dur}]")
        label.update("  Queue: " + "  ▶  ".join(parts))
