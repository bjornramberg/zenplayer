from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Input, Label
from textual.widgets._list_view import ListView

from zenplayer.audio.extractor import search
from zenplayer.utils.cache import get_cached, set_cached
from zenplayer.widgets.controls import Controls
from zenplayer.widgets.queue_view import QueueView
from zenplayer.widgets.search_results import SearchResults, SearchResultItem
from zenplayer.widgets.visualizer import SymmetricalSpectrum


class PlayerScreen(Screen):
    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal(id="main-area"):
                with Vertical(id="search-panel"):
                    yield Input(placeholder="Search...", id="player-search")
                    yield SearchResults()
                with Vertical(id="player-panel"):
                    yield Label("", id="now-playing", classes="np-info")
                    yield Label("", id="now-artist", classes="np-info")
                    yield SymmetricalSpectrum()
            yield QueueView()
            yield Controls()

    def on_mount(self):
        self.set_interval(0.5, self._update_controls)

    def _update_controls(self):
        app = self.app
        if app.player.process is None:
            return

        app.player.poll_properties()
        controls = self.query_one(Controls)
        controls.update_state(
            paused=app.player.paused,
            volume=app.player.volume,
            time_pos=app.player.time_pos,
            duration=app.player.duration,
        )

        if app.current_track:
            np_label = self.query_one("#now-playing", Label)
            np_artist = self.query_one("#now-artist", Label)
            np_label.update(f"  {app.current_track.title}")
            np_artist.update(f"  {app.current_track.artist}")

        queue_view = self.query_one(QueueView)
        queue_view.set_queue(app.queue)

    def on_input_submitted(self, event: Input.Submitted):
        query = event.value.strip()
        if not query:
            return

        results_widget = self.query_one(SearchResults)
        cached = get_cached(query)
        if cached:
            tracks = [self.app._track_from_dict(t) for t in cached]
            results_widget.set_results(tracks, autofocus=True)
            return

        try:
            tracks = search(query)
            results_widget.set_results(tracks, autofocus=True)
            cached_data = [
                {"id": t.id, "title": t.title, "artist": t.artist,
                 "duration": t.duration, "url": t.url}
                for t in tracks
            ]
            set_cached(query, cached_data)
        except Exception:
            pass

    def on_list_view_selected(self, event: ListView.Selected):
        item = event.item
        if hasattr(item, "track") and item.track:
            self.app.play_track(item.track)
