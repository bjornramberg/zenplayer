from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Input, Label
from textual.widgets._list_view import ListView

from zenplayer.audio.extractor import search
from zenplayer.utils.cache import get_cached, set_cached
from zenplayer.widgets.search_results import SearchResults, SearchResultItem


class SearchScreen(Screen):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("  Search YouTube Music", id="search-header")
            yield Input(placeholder="Type to search...", id="search-input")
            yield Label("", id="search-status")
            yield SearchResults()

    def on_input_submitted(self, event: Input.Submitted):
        query = event.value.strip()
        if not query:
            return
        self._do_search(query)

    def on_input_changed(self, event: Input.Changed):
        query = event.value.strip()
        if len(query) < 2:
            return
        self._do_search(query)

    def _do_search(self, query: str):
        status = self.query_one("#search-status", Label)
        results_widget = self.query_one(SearchResults)

        status.update("  Searching...")

        cached = get_cached(query)
        if cached:
            tracks = [self.app._track_from_dict(t) for t in cached]
            results_widget.set_results(tracks, autofocus=True)
            status.update(f"  Found {len(tracks)} results (cached)")
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
            status.update(f"  Found {len(tracks)} results")
        except Exception as e:
            status.update(f"  Search error: {e}")

    def on_list_view_selected(self, event: ListView.Selected):
        item = event.item
        if hasattr(item, "track") and item.track:
            self.app.play_track(item.track)
            self.app.pop_screen()
