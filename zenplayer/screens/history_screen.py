from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Label
from textual.widgets._list_view import ListView

from zenplayer.utils.history import get_history, remove_from_history, clear_history
from zenplayer.widgets.search_results import SearchResults


class HistoryScreen(Screen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Close"),
        Binding("backspace", "remove_entry", "Remove"),
        Binding("delete", "remove_entry", "Remove"),
        Binding("ctrl+x", "clear_all", "Clear All"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("  History", id="history-header")
            yield SearchResults()
            yield Footer()

    def on_mount(self):
        self._load_history()

    def _load_history(self):
        from zenplayer.audio.extractor import TrackInfo

        raw = get_history()
        self._raw = raw
        tracks = []
        for entry in raw:
            tracks.append(TrackInfo(
                id=entry.get("id", ""),
                title=entry.get("title", "Unknown"),
                artist=entry.get("artist", "Unknown"),
                duration=entry.get("duration", 0),
                url=entry.get("url", ""),
                thumbnail=entry.get("thumbnail"),
                description=entry.get("description", ""),
            ))
        results = self.query_one(SearchResults)
        positions = [e.get("position", 0) for e in raw]
        results.set_results(tracks, autofocus=True, positions=positions)
        header = self.query_one("#history-header", Label)
        header.update(f"  History ({len(tracks)})")

    def on_list_view_selected(self, event: ListView.Selected):
        item = event.item
        if not (hasattr(item, "track") and item.track):
            return
        idx = results.list_view.index if (results := self.query_one(SearchResults)).list_view.index is not None else None
        position = 0
        if idx is not None and idx < len(self._raw):
            position = self._raw[idx].get("position", 0)
        self.app.play_track(item.track)
        if position > 0:
            self.app.set_timer(1.5, lambda p=position: self.app.player.seek(p))
        self.app.pop_screen()

    def action_pop_screen(self):
        self.app.pop_screen()

    def action_remove_entry(self):
        results = self.query_one(SearchResults)
        idx = results.list_view.index
        if idx is not None:
            remove_from_history(idx)
            self._load_history()
            self.app.notify("Removed from history")

    def action_clear_all(self):
        clear_history()
        self._load_history()
        self.app.notify("History cleared")
