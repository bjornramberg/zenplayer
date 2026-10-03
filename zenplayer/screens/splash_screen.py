import time
from importlib import resources

from textual.app import ComposeResult
from textual.containers import Center, Middle
from textual.screen import Screen
from textual.widgets import Static


def load_splash_art() -> str:
    try:
        return resources.files("zenplayer").joinpath("assets/splash.txt").read_text()
    except Exception:
        return "zenplayer"


class SplashScreen(Screen):
    """Full-screen splash with fade in/out."""

    def __init__(self, on_complete=None):
        super().__init__()
        self._on_complete = on_complete
        self._opacity = 0.0
        self._start_time = 0.0

    def compose(self) -> ComposeResult:
        art = load_splash_art()
        with Center():
            with Middle():
                yield Static(art, id="splash-art")

    def on_mount(self):
        self._start_time = time.monotonic()
        self._opacity = 0.0
        self.query_one("#splash-art").styles.opacity = 0.0
        self.set_interval(0.05, self._tick)

    def _tick(self):
        elapsed = time.monotonic() - self._start_time

        if elapsed < 0.5:
            self._opacity = elapsed / 0.5
        elif elapsed < 1.5:
            self._opacity = 1.0
        else:
            self._opacity = max(0.0, 1.0 - (elapsed - 1.5) / 0.5)

        if self._opacity <= 0.0 and elapsed >= 2.0:
            if self._on_complete:
                self._on_complete()
            return

        self.query_one("#splash-art").styles.opacity = self._opacity
