import time
from typing import Optional

from textual.app import App, Binding
from textual.binding import BindingType

from zenplayer.audio.analyzer import AudioAnalyzer
from zenplayer.audio.extractor import TrackInfo
from zenplayer.audio.player import MpvPlayer
from zenplayer import diagnostics, nonblocking_output
from zenplayer.config import load_config, save_config
from zenplayer.screens.player_screen import PlayerScreen
from zenplayer.screens.search_screen import SearchScreen
from zenplayer.widgets.album_art import AlbumArt
from zenplayer.widgets.now_playing import NowPlayingOverlay


ZENPLAYER_CSS = """
Screen {
    background: #000000;
}

#main-area {
    height: 1fr;
}

#search-panel {
    width: 40%;
    background: #0a0a0a;
    border-right: solid #222222;
}

#search-panel Input {
    dock: top;
    margin: 0 1;
    background: #111111;
    color: #c0c0c0;
    border: none;
}

#player-panel {
    width: 60%;
    layers: art overlay;
}

AlbumArt {
    layer: art;
    width: 1fr;
    height: 1fr;
}

NowPlayingOverlay {
    layer: overlay;
    dock: bottom;
    height: 5;
}

Controls {
    height: 3;
    background: #0a0a0a;
    border-top: solid #222222;
    color: #c0c0c0;
}

QueueView {
    height: 3;
    background: #0a0a0a;
    border-top: solid #222222;
    color: #555555;
}

.control-btn {
    color: #c0c0c0;
    margin: 0 0;
}

.control-btn:hover {
    color: #ff6b6b;
}

.vol-bar {
    color: #ff6b6b;
}

.time {
    color: #555555;
    padding: 0 1;
}

SearchResults {
    height: 1fr;
}

SearchPreview {
    width: 1fr;
    height: 12;
}

SearchPreviewArt {
    width: 24;
    height: 12;
    border: solid #222222;
}

SearchPreviewInfo {
    width: 1fr;
    height: 12;
    padding: 1 1 0 1;
    content-align: left top;
}

ListView {
    background: #0a0a0a;
}

ListView:focus {
    border: none;
}

ListItem {
    padding: 0 1;
    color: #c0c0c0;
}

ListItem:hover {
    background: #1a1a1a;
}

ListItem > Label {
    padding: 0;
}

.result-meta {
    color: #555555;
}

#search-header {
    color: #ff6b6b;
    text-style: bold;
    padding: 1 1;
}

#search-input {
    background: #111111;
    color: #c0c0c0;
    border: none;
    margin: 0 1;
}

#search-status {
    color: #555555;
    padding: 0 1;
    height: 1;
}
"""


class ZenPlayer(App):
    CSS = ZENPLAYER_CSS
    ENABLE_COMMAND_PALETTE = False

    BINDINGS: list[BindingType] = [
        Binding("ctrl+p", "toggle_screen", "Toggle Screen"),
        Binding("ctrl+f", "focus_search", "Search"),
        Binding("/", "focus_search", "Search"),
        Binding("space", "play_pause", "Play/Pause"),
        Binding("right", "seek_forward", "Forward"),
        Binding("left", "seek_backward", "Backward"),
        Binding("+", "volume_up", "Vol Up"),
        Binding("-", "volume_down", "Vol Down"),
        Binding("n", "next_track", "Next"),
        Binding("p", "previous_track", "Prev"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.player = MpvPlayer(volume=int(self.config.get("volume", 50)))
        self.analyzer = AudioAnalyzer()
        self._bass_smooth = 0.0
        self._bass_trail = 0.0
        self._bass_peak = 1e-6
        self._bass_energy = 0.0
        self._bass_sent = 0.0
        self._bass_sent_at = 0.0
        self.queue: list[TrackInfo] = []
        self.current_track: Optional[TrackInfo] = None

    def on_mount(self):
        self.install_screen(
            PlayerScreen(volume=int(self.config.get("volume", 50)), name="player"),
            name="player",
        )
        self.install_screen(SearchScreen(name="search"), name="search")
        self.push_screen("player")
        fps = int(self.config.get("reactive_fps", 24))
        self._bass_interval = 1.0 / max(1, fps)
        self.set_interval(self._bass_interval, self._reactive_tick)
        self.set_interval(0.5, self._repaint_if_dropped)

    def _repaint_if_dropped(self):
        if nonblocking_output.full():
            return
        if nonblocking_output.consume_drops() and self.screen is not None:
            self.screen.refresh(repaint=True)

    def _reset_bass(self):
        self._bass_smooth = 0.0
        self._bass_trail = 0.0
        self._bass_peak = 1e-6
        self._bass_energy = 0.0
        self._bass_sent = 0.0
        self._bass_sent_at = 0.0

    def _reactive_tick(self):
        diagnostics.mark_tick()
        player = self.player
        playing = player.process is not None and not player.paused
        self.analyzer.set_playing(playing)
        self.analyzer.update()
        diagnostics.set_state(
            playing=playing,
            focus=self.app_focus,
            screen=self.screen.name if self.screen is not None else None,
            active=self.analyzer.is_active,
        )
        if not playing:
            self._reset_bass()
            return
        screen = self.screen
        if screen is None or screen.name != "player":
            self._reset_bass()
            return
        if not self.analyzer.is_active:
            self._reset_bass()
            return
        self._bass_tick(self.analyzer.get_bass_power())

    def _bass_tick(self, now: float):
        # Fast smoothing kills frame-to-frame FFT jitter while keeping beats.
        self._bass_smooth += (now - self._bass_smooth) * 0.7
        now = self._bass_smooth

        # Auto-gain against a slowly-adapting peak so a constant loud bass
        # never pins the glow at full brightness.
        self._bass_peak = max(now, self._bass_peak * 0.998)
        norm = now / max(self._bass_peak, 1e-6)

        # Onset detection: the jump above a trailing average is what "bounces"
        # with the beat; a steady bass keeps it near zero.
        self._bass_trail += (now - self._bass_trail) * 0.15
        bump = max(0.0, now - self._bass_trail)

        target = min(1.0, norm * 0.35 + bump * 1.2)
        if target > self._bass_energy:
            self._bass_energy = target
        else:
            self._bass_energy *= 0.92

        level = self._bass_energy
        if abs(level - self._bass_sent) > 0.005:
            now_t = time.monotonic()
            if now_t - self._bass_sent_at >= self._bass_interval:
                overlay = self.screen.query_one(NowPlayingOverlay, None)
                if overlay is not None and not nonblocking_output.full():
                    self._bass_sent = level
                    self._bass_sent_at = now_t
                    overlay.set_bass(level)
                    diagnostics.mark_set_bass()

    def action_toggle_screen(self) -> None:
        if self.screen is not None and self.screen.name == "player":
            self.push_screen("search")
        else:
            self.pop_screen()

    def action_focus_search(self) -> None:
        if self.screen is not None and hasattr(self.screen, "query_one"):
            try:
                search_input = self.screen.query_one("#player-search")
                search_input.focus()
            except Exception:
                try:
                    search_input = self.screen.query_one("#search-input")
                    search_input.focus()
                except Exception:
                    pass

    def action_play_pause(self) -> None:
        self.player.toggle_pause()

    def action_seek_forward(self) -> None:
        self.player.seek(5)

    def action_seek_backward(self) -> None:
        self.player.seek(-5)

    def action_volume_up(self) -> None:
        self._set_volume(min(100, self.player.volume + 5))

    def action_volume_down(self) -> None:
        self._set_volume(max(0, self.player.volume - 5))

    def _set_volume(self, value: int) -> None:
        self.player.volume = value
        self.config["volume"] = value
        try:
            save_config(self.config)
        except Exception:
            pass

    def action_next_track(self) -> None:
        self.player.next_track()

    def action_previous_track(self) -> None:
        self.player.previous_track()

    def play_track(self, track: TrackInfo) -> None:
        self.current_track = track
        if track not in self.queue:
            self.queue.insert(0, track)

        try:
            self.player.start(track.url)
        except Exception:
            self.notify("Failed to play track", severity="error")

    def action_quit(self) -> None:
        t0 = time.monotonic()
        self.player.stop()
        t1 = time.monotonic()
        self.analyzer.stop()
        t2 = time.monotonic()
        self.exit()
        t3 = time.monotonic()
        diagnostics.log_line(
            "quit: player.stop=%.3fs analyzer.stop=%.3fs exit=%.3fs"
            % (t1 - t0, t2 - t1, t3 - t2)
        )

    def _track_from_dict(self, data: dict) -> TrackInfo:
        return TrackInfo(
            id=data.get("id", ""),
            title=data.get("title", "Unknown"),
            artist=data.get("artist", "Unknown"),
            duration=data.get("duration", 0),
            url=data.get("url", ""),
            thumbnail=data.get("thumbnail"),
            description=data.get("description", ""),
        )
