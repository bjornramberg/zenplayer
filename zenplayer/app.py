from typing import Optional

from textual.app import App, Binding
from textual.binding import BindingType

from zenplayer.audio.analyzer import AudioAnalyzer
from zenplayer.audio.extractor import TrackInfo
from zenplayer.audio.player import MpvPlayer
from zenplayer.config import load_config
from zenplayer.screens.player_screen import PlayerScreen
from zenplayer.screens.search_screen import SearchScreen


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
    align: center middle;
}

#now-playing {
    color: #ff6b6b;
    text-style: bold;
    padding: 0 1;
    height: 1;
}

#now-artist {
    color: #555555;
    padding: 0 1;
    height: 1;
}

SymmetricalSpectrum {
    width: 1fr;
    height: 1fr;
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

.np-info {
    padding: 0 1;
}

ResultView {
    height: 1fr;
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
        self.player = MpvPlayer()
        self.analyzer = AudioAnalyzer()
        self.queue: list[TrackInfo] = []
        self.current_track: Optional[TrackInfo] = None
        self.config = load_config()

    def on_mount(self):
        self.install_screen(PlayerScreen(name="player"), name="player")
        self.install_screen(SearchScreen(name="search"), name="search")
        self.push_screen("player")

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
        self.analyzer.set_playing(not self.player.paused)

    def action_seek_forward(self) -> None:
        self.player.seek(5)

    def action_seek_backward(self) -> None:
        self.player.seek(-5)

    def action_volume_up(self) -> None:
        self.player.volume = min(100, self.player.volume + 5)

    def action_volume_down(self) -> None:
        self.player.volume = max(0, self.player.volume - 5)

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
            self.analyzer.set_playing(True)
        except Exception:
            self.notify("Failed to play track", severity="error")

    def action_quit(self) -> None:
        self.analyzer.stop()
        self.player.stop()
        self.exit()

    def _track_from_dict(self, data: dict) -> TrackInfo:
        return TrackInfo(
            id=data.get("id", ""),
            title=data.get("title", "Unknown"),
            artist=data.get("artist", "Unknown"),
            duration=data.get("duration", 0),
            url=data.get("url", ""),
            thumbnail=data.get("thumbnail"),
        )
