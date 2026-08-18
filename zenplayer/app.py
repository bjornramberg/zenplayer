import time
from typing import Optional

from textual.app import App, Binding
from textual.binding import BindingType

from zenplayer.audio.analyzer import AudioAnalyzer
from zenplayer.audio.extractor import TrackInfo
from zenplayer.audio.player import MpvPlayer
from zenplayer import diagnostics, nonblocking_output
from zenplayer.config import load_config, save_config
from zenplayer.screens.history_screen import HistoryScreen
from zenplayer.screens.player_screen import PlayerScreen
from zenplayer.screens.search_screen import SearchScreen
from zenplayer.utils.history import add_to_history, update_history_position
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
    padding: 1 0 0 1;
}

#search-panel-header {
    dock: top;
    color: #555555;
    padding: 0 1;
    height: 1;
}

ResumePrompt {
    dock: top;
    height: 3;
    align: center middle;
    padding: 0 1;
}

Footer {
    height: 1;
}

ZenNowPlaying { display: none; }

/* Zen mode: hide everything, show only ZenNowPlaying */
Screen.zen #main-area,
Screen.zen QueueView,
Screen.zen Controls,
Screen.zen Footer { display: none; }

Screen.zen ZenNowPlaying { display: block; }

ZenNowPlaying {
    align: center middle;
    height: 1fr;
}

#zen-info {
    align: center middle;
    height: auto;
}

#zen-title {
    color: #c0c0c0;
    text-style: bold;
    text-align: center;
    width: auto;
}

#zen-artist {
    color: #555555;
    text-align: center;
    width: auto;
}

#zen-progress {
    color: #555555;
    text-align: center;
    width: auto;
}

#zen-controls {
    align: center middle;
}

.zen-btn {
    background: transparent;
    border: solid transparent;
    padding: 0 1;
    min-width: 0;
    height: auto;
}

.zen-btn:hover {
    background: #1a1a1a;
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
    background: transparent;
    border: solid transparent;
    padding: 0 1;
    min-width: 0;
    height: auto;
}

.control-btn:hover {
    background: #1a1a1a;
}

.control-btn.-active {
    background: #222222;
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
    margin: 0 1;
    background: #0a0a0a;
}

ListView:focus {
    border: none;
}

ListItem {
    margin: 0 1;
    padding: 0;
    color: #c0c0c0;
}

ListItem:hover {
    background: #1a1a1a;
}

ListItem.-highlight {
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

#history-header {
    color: #555555;
    text-style: bold;
    padding: 1 1;
    dock: top;
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
    TITLE = "zenplayer"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS: list[BindingType] = [
        Binding("space", "play_pause", "Play/Pause"),
        Binding("right", "seek_forward", "Forward"),
        Binding("left", "seek_backward", "Backward"),
        Binding("shift+right", "seek_forward_large", "Forward 30s"),
        Binding("shift+left", "seek_backward_large", "Backward 30s"),
        Binding("+", "volume_up", "Vol Up"),
        Binding("-", "volume_down", "Vol Down"),
        Binding("shift++", "volume_up_large", "Vol Up 15%"),
        Binding("shift+-", "volume_down_large", "Vol Down 15%"),
        Binding("j", "next_track", "Next"),
        Binding("k", "previous_track", "Prev"),
        Binding("f", "focus_search", "Search"),
        Binding("/", "focus_search", "Search"),
        Binding("h", "toggle_history", "History"),
        Binding("r", "resume_session", "Resume"),
        Binding("q", "quit", "Quit"),
        Binding("u", "update_ytdlp", "Update yt-dlp"),
        Binding("escape", "unfocus", "Back"),
    ]

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.player = MpvPlayer(volume=int(self.config.get("volume", 50)))
        self.analyzer = AudioAnalyzer()
        # Clear mpv log from previous session
        try:
            from zenplayer.audio.player import MPV_LOG_FILE
            if MPV_LOG_FILE.exists():
                MPV_LOG_FILE.unlink()
        except Exception:
            pass
        self._bass_smooth = 0.0
        self._bass_trail = 0.0
        self._bass_peak = 1e-6
        self._bass_energy = 0.0
        self._bass_sent = 0.0
        self._bass_sent_at = 0.0
        self.queue: list[TrackInfo] = []
        self.current_track: Optional[TrackInfo] = None
        self._playback_monitor = None
        self._playback_check_count = 0

    def on_mount(self):
        self.install_screen(
            PlayerScreen(volume=int(self.config.get("volume", 50)), name="player"),
            name="player",
        )
        self.install_screen(SearchScreen(name="search"), name="search")
        self.install_screen(HistoryScreen(name="history"), name="history")
        self.push_screen("player")
        fps = int(self.config.get("reactive_fps", 24))
        self._bass_interval = 1.0 / max(1, fps)
        self.set_interval(self._bass_interval, self._reactive_tick)
        self.set_interval(0.5, self._repaint_if_dropped)
        if self.config.get("last_track"):
            pass  # ResumePrompt will show on mount
        # Check for yt-dlp updates in background
        self.set_timer(2.0, self._check_ytdlp_update)

    def _normalize_version(self, version: str) -> str:
        """Normalize version string by removing leading zeros from each part."""
        parts = version.split(".")
        return ".".join(str(int(p)) for p in parts)

    def _check_ytdlp_update(self):
        """Check if yt-dlp has a newer version available."""
        try:
            import subprocess
            result = subprocess.run(
                ["yt-dlp", "--version"],
                capture_output=True, text=True, timeout=5
            )
            current = result.stdout.strip()

            import urllib.request
            import json
            url = "https://pypi.org/pypi/yt-dlp/json"
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
                latest = data["info"]["version"]

            if self._normalize_version(current) != self._normalize_version(latest):
                self.notify(
                    f"yt-dlp update available: {latest} (you have {current})\n"
                    f"Press u to update",
                    severity="info",
                    timeout=15
                )
        except Exception:
            pass

    def action_update_ytdlp(self):
        """Update yt-dlp to latest version."""
        self.notify("Updating yt-dlp...", severity="info", timeout=30)
        try:
            import subprocess
            result = subprocess.run(
                ["pip", "install", "-U", "yt-dlp"],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                self.notify("yt-dlp updated successfully!", severity="success", timeout=5)
            else:
                self.notify("Update failed — try manually:\npip install -U yt-dlp", severity="error", timeout=10)
        except Exception:
            self.notify("Update failed — try manually:\npip install -U yt-dlp", severity="error", timeout=10)

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

    def action_toggle_history(self) -> None:
        if self.screen is not None and self.screen.name == "history":
            self.pop_screen()
        else:
            self.push_screen("history")

    def action_resume_session(self) -> None:
        track_dict = self.config.get("last_track")
        if not track_dict:
            self.notify("No saved session", severity="warning")
            return
        track = self._track_from_dict(track_dict)
        position = self.config.get("last_position", 0)
        self.play_track(track)
        self._resume_position = position
        self._resume_attempts = 0
        self._resume_timer = self.set_interval(0.5, self._poll_for_resume)
        del self.config["last_track"]
        del self.config["last_position"]
        save_config(self.config)
        try:
            prompt = self.screen.query_one("ResumePrompt")
            prompt.hide()
        except Exception:
            pass
        self.set_timer(0.05, lambda: self.screen.query_one("#player-search").focus())

    def _poll_for_resume(self) -> None:
        """Wait for mpv to start playing, then seek to saved position."""
        self._resume_attempts += 1
        time_pos = self.player.time_pos

        if time_pos > 0:
            self.player.seek_to(self._resume_position)
            self.notify("Resumed from last session")
            self._resume_timer.stop()
            return

        if self.player.process is None:
            self._resume_timer.stop()
            self.notify("Couldn't resume — playback interrupted", severity="error")
            return

        if self._resume_attempts > 20:
            diag = self.player.get_diagnostics()
            log = self.player.log_path
            if diag.get("paused-for-cache"):
                msg = f"Resume is still loading — buffering the track\n(Log: {log})"
            elif diag.get("idle-active"):
                msg = f"Couldn't resume — track failed to load\n(Log: {log})"
            else:
                msg = f"Couldn't resume — try playing the track again\n(Log: {log})"
            self.player.seek_to(self._resume_position)
            self.notify(msg, severity="warning", timeout=10)
            self._resume_timer.stop()

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

    def action_unfocus(self) -> None:
        if self.screen is not None and hasattr(self.screen, "query_one"):
            try:
                self.screen.query_one("#player-search").blur()
            except Exception:
                pass
            try:
                self.screen.query_one("#search-input").blur()
            except Exception:
                pass

    def action_play_pause(self) -> None:
        self.player.toggle_pause()

    def action_seek_forward(self) -> None:
        self.player.seek(5)

    def action_seek_forward_large(self) -> None:
        self.player.seek(30)

    def action_seek_backward(self) -> None:
        self.player.seek(-5)

    def action_seek_backward_large(self) -> None:
        self.player.seek(-30)

    def action_volume_up(self) -> None:
        self._set_volume(min(100, self.player.volume + 5))

    def action_volume_up_large(self) -> None:
        self._set_volume(min(100, self.player.volume + 15))

    def action_volume_down(self) -> None:
        self._set_volume(max(0, self.player.volume - 5))

    def action_volume_down_large(self) -> None:
        self._set_volume(max(0, self.player.volume - 15))

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
        if self.current_track and self.player.time_pos > 0:
            update_history_position(self.current_track.id, self.player.time_pos)
        self.current_track = track
        if track not in self.queue:
            self.queue.insert(0, track)
        add_to_history(track, int(self.config.get("history_limit", 100)))

        self._stop_playback_monitor()
        self._playback_track = track
        self._playback_retry = True

        try:
            self.player.start(track.url)
        except Exception:
            self.notify("Playback failed — try again", severity="error")
            return

        self._playback_monitor = self.set_interval(1.0, self._check_playback_started)

    def _check_playback_started(self) -> None:
        """Warn user if mpv hasn't started playing after a few seconds."""
        if self._playback_monitor is None:
            return
        if self.player.time_pos > 0:
            self._stop_playback_monitor()
            self._cleanup_log_on_success()
            return
        if self.player.process is None:
            self._stop_playback_monitor()
            if self._playback_retry:
                self._retry_playback()
            else:
                self.notify("Playback interrupted — try playing again", severity="error")
            return
        self._playback_check_count += 1
        if self._playback_check_count >= 5:
            diag = self.player.get_diagnostics()
            if self._playback_retry and self._should_retry(diag):
                self._retry_playback()
            else:
                msg = self._diagnose_playback_failure(diag)
                self._stop_playback_monitor()
                self.notify(msg, severity="warning", timeout=10)

    def _should_retry(self, diag: dict) -> bool:
        """Only retry for transient errors, not permanent ones."""
        if diag.get("eof-reached"):
            return False
        return True

    def _retry_playback(self) -> None:
        """Retry playback once with a short delay."""
        self._stop_playback_monitor()
        self._playback_retry = False
        self.notify("Retrying...", severity="info", timeout=2)
        self.set_timer(1.0, self._do_retry)

    def _do_retry(self) -> None:
        try:
            self.player.start(self._playback_track.url)
        except Exception:
            self.notify("Playback failed — try again", severity="error")
            return
        self._playback_monitor = self.set_interval(1.0, self._check_playback_started)

    def _diagnose_playback_failure(self, diag: dict) -> str:
        log = self.player.log_path
        if diag.get("paused-for-cache"):
            return f"Still loading — buffering the track\n(Log: {log})"
        if diag.get("idle-active"):
            return f"Couldn't load this track — check your connection\n(Log: {log})"
        if diag.get("eof-reached"):
            return f"This track isn't available — it may be restricted\n(Log: {log})"
        if diag.get("duration", 0) == 0:
            return f"Track failed to load — try another one\n(Log: {log})"
        return f"Something went wrong — try again\n(Log: {log})"

    def _stop_playback_monitor(self) -> None:
        if self._playback_monitor is not None:
            self._playback_monitor.stop()
            self._playback_monitor = None
        self._playback_check_count = 0

    def _cleanup_log_on_success(self) -> None:
        """Delete mpv log when playback starts successfully."""
        try:
            from zenplayer.audio.player import MPV_LOG_FILE
            if MPV_LOG_FILE.exists():
                MPV_LOG_FILE.unlink()
        except Exception:
            pass

    def action_quit(self) -> None:
        self._stop_playback_monitor()
        if self.current_track and self.player.time_pos > 0:
            update_history_position(self.current_track.id, self.player.time_pos)
            self.config["last_track"] = self._track_to_dict(self.current_track)
            self.config["last_position"] = max(0, self.player.time_pos - 10)
            try:
                save_config(self.config)
            except Exception:
                pass
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

    def _track_to_dict(self, track: TrackInfo) -> dict:
        return {
            "id": track.id,
            "title": track.title or "Unknown",
            "artist": track.artist or "Unknown",
            "duration": track.duration,
            "url": track.url,
            "thumbnail": getattr(track, "thumbnail", None),
            "description": getattr(track, "description", ""),
        }
