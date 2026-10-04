from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.content import Text
from textual.widgets import Input, Label, Static
from textual.widgets._list_view import ListView

from zenplayer.audio.extractor import search
from zenplayer import nonblocking_output
from zenplayer.utils.cache import get_cached, set_cached
from zenplayer.widgets.album_art import AlbumArt
from zenplayer.widgets.now_playing import NowPlayingOverlay
from zenplayer.widgets.queue_view import QueueView
from zenplayer.widgets.resume_prompt import ResumePrompt
from zenplayer.widgets.search_preview import SearchPreview
from zenplayer.widgets.search_results import SearchResults
from zenplayer.widgets.zen_now_playing import ZenNowPlaying


class FooterBar(Static):
    """Custom single-line footer with grouped keyboard shortcuts."""

    def __init__(self, volume: int = 50, **kwargs):
        super().__init__(**kwargs)
        self._volume = volume

    def render(self) -> Text:
        hints = (
            "[space] Play │ [↑↓] Vol │ [←→] Seek 5s │ "
            "[shift+←→] Seek 30s │ [/] Search │ [h] History │ "
            "[r] Resume last session │ [q] Quit"
        )
        vol_text = self._vol_text(self._volume)

        width = self.content_size.width
        hints_len = len(hints)
        vol_len = len(vol_text.plain)
        padding = max(0, width - hints_len - vol_len - 10)

        t = Text()
        t.append(hints)
        t.append(" " * padding)
        t.append("│ Volume ")
        t.append_text(vol_text)
        return t

    def _vol_text(self, volume: int) -> Text:
        filled = max(0, min(10, volume // 10))
        t = Text()
        t.append("█" * filled, style="#808080")
        t.append("░" * (10 - filled), style="#8a8a8a")
        return t

    def update_volume(self, volume: int):
        self._volume = volume
        self.refresh()


class PlayerScreen(Screen):
    BINDINGS = [
        Binding("f1", "toggle_zen", "Zen Mode"),
        Binding("f2", "toggle_turntable", "Turntable"),
    ]

    def __init__(self, volume: int = 50, **kwargs):
        super().__init__(**kwargs)
        self._volume = volume

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal(id="main-area"):
                with Vertical(id="search-panel"):
                    yield Label("  Search", id="search-panel-header")
                    yield ResumePrompt()
                    yield Input(placeholder="Search...", id="player-search")
                    yield SearchResults()
                    yield SearchPreview()
                with Vertical(id="player-panel"):
                    yield AlbumArt()
                    yield NowPlayingOverlay()
            yield QueueView()
            yield ZenNowPlaying()
            yield FooterBar(volume=self._volume)

    def on_mount(self):
        self._art_track = None
        self._current_query = ""
        self.set_interval(0.5, self._update_controls)
        if self.app.config.get("last_track"):
            try:
                prompt = self.query_one(ResumePrompt)
                prompt.show()
            except Exception:
                pass
        try:
            self.query_one("#player-search").focus()
        except Exception:
            pass

    def action_toggle_zen(self):
        self.set_class(not self.has_class("zen"), "zen")

    def action_toggle_turntable(self):
        """Toggle turntable mode on/off."""
        album_art = self.query_one(AlbumArt)
        album_art.toggle_turntable()

    def _update_controls(self):
        if self.app.screen is not self:
            return
        app = self.app
        if app.player.process is None:
            return
        if nonblocking_output.full():
            # The terminal isn't draining output right now; skip the repaint
            # work rather than fill the queue. When it drains again,
            # _repaint_if_dropped catches everything up.
            return

        footer = self.query_one(FooterBar)
        footer.update_volume(app.player.volume)

        album_art = self.query_one(AlbumArt)
        overlay = self.query_one(NowPlayingOverlay)
        if app.current_track is not None and app.current_track is not self._art_track:
            self._art_track = app.current_track
            album_art.set_track(app.current_track)
            overlay.set_track(app.current_track)
        overlay.set_progress(app.player.time_pos, app.player.duration)
        overlay.set_paused(app.player.paused)

        queue_view = self.query_one(QueueView)
        queue_view.set_queue(app.queue)

        # Update zen mode widget
        try:
            zen = self.query_one(ZenNowPlaying)
            zen.update_state(
                app.current_track,
                app.player.paused,
                app.player.time_pos,
                app.player.duration,
            )
        except Exception:
            pass

    def on_input_submitted(self, event: Input.Submitted):
        query = event.value.strip()
        if not query:
            return
        self._current_query = query
        self._run_search(query)

    @work(thread=True, exclusive=True, group="search")
    def _run_search(self, query: str):
        limit = int(self.app.config.get("search_limit", 30))
        cached = get_cached(query, limit)
        if cached:
            tracks = [self.app._track_from_dict(t) for t in cached]
            self._post(self._apply_results, query, tracks)
            return
        try:
            tracks = search(query, limit=limit)
            results = [
                {"id": t.id, "title": t.title, "artist": t.artist,
                 "duration": t.duration, "url": t.url,
                 "description": getattr(t, "description", "")}
                for t in tracks
            ]
            set_cached(query, results, limit)
            self._post(self._apply_results, query, tracks)
        except Exception as e:
            self._post(self._apply_error, query, str(e))

    def _post(self, callback, *args):
        try:
            self.app.call_from_thread(callback, *args)
        except Exception:
            pass

    def _apply_results(self, query: str, tracks: list):
        if not self.is_mounted or query != self._current_query:
            return
        results_widget = self.query_one(SearchResults)
        results_widget.set_results(tracks, autofocus=True)

    def _apply_error(self, query: str, error: str):
        if not self.is_mounted or query != self._current_query:
            return
        self.app.notify(f"Search failed: {error}", severity="error", timeout=5)

    def on_list_view_selected(self, event: ListView.Selected):
        item = event.item
        if hasattr(item, "track") and item.track:
            self.app.play_track(item.track)

    def on_list_view_highlighted(self, event: ListView.Highlighted):
        track = getattr(event.item, "track", None) if event.item else None
        try:
            self.query_one(SearchPreview).set_track(track)
        except Exception:
            pass
