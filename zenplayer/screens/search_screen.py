from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Input, Label
from textual.widgets._list_view import ListView

from zenplayer.audio.extractor import search
from zenplayer.utils.cache import get_cached, set_cached
from zenplayer.widgets.search_results import SearchResults

SEARCH_DEBOUNCE = 0.3


class SearchScreen(Screen):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("  Search YouTube Music", id="search-header")
            yield Input(placeholder="Type to search...", id="search-input")
            yield Label("", id="search-status")
            yield SearchResults()

    def on_mount(self):
        self._current_query = ""
        self._debounce_timer = None

    def on_input_submitted(self, event: Input.Submitted):
        query = event.value.strip()
        if not query:
            return
        self._start_search(query)

    def on_input_changed(self, event: Input.Changed):
        query = event.value.strip()
        if len(query) < 2:
            return
        self._start_search(query)

    def _start_search(self, query: str):
        self._current_query = query
        if self._debounce_timer is not None:
            self._debounce_timer.stop()
        self._debounce_timer = self.set_timer(
            SEARCH_DEBOUNCE, lambda: self._run_search(query)
        )
        status = self.query_one("#search-status", Label)
        status.update("  Searching...")

    @work(thread=True, exclusive=True, group="search")
    def _run_search(self, query: str):
        cached = get_cached(query)
        if cached:
            tracks = [self.app._track_from_dict(t) for t in cached]
            self._post(self._apply_results, query, tracks, True)
            return
        try:
            tracks = search(query)
            cached_data = [
                {"id": t.id, "title": t.title, "artist": t.artist,
                 "duration": t.duration, "url": t.url}
                for t in tracks
            ]
            set_cached(query, cached_data)
            self._post(self._apply_results, query, tracks, False)
        except Exception as e:
            self._post(self._apply_error, query, str(e))

    def _post(self, callback, *args):
        try:
            self.app.call_from_thread(callback, *args)
        except Exception:
            pass

    def _apply_results(self, query: str, tracks: list, cached: bool):
        if self.app.screen is not self or query != self._current_query:
            return
        results_widget = self.query_one(SearchResults)
        results_widget.set_results(tracks, autofocus=True)
        status = self.query_one("#search-status", Label)
        suffix = " (cached)" if cached else ""
        status.update(f"  Found {len(tracks)} results{suffix}")

    def _apply_error(self, query: str, error: str):
        if self.app.screen is not self or query != self._current_query:
            return
        status = self.query_one("#search-status", Label)
        status.update(f"  Search error: {error}")

    def on_list_view_selected(self, event: ListView.Selected):
        item = event.item
        if hasattr(item, "track") and item.track:
            self.app.play_track(item.track)
            self.app.pop_screen()
