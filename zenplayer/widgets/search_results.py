from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import ListView, ListItem, Label

from zenplayer.utils.format import format_duration


class SearchResultItem(ListItem):
    def __init__(self, track, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.track = track

    def compose(self) -> ComposeResult:
        title = self.track.title or "Unknown"
        artist = self.track.artist or "Unknown"
        duration = format_duration(self.track.duration)
        yield Label(f"{title}")
        yield Label(f"{artist}  {duration}", classes="result-meta")


class SearchResults(Vertical):
    def __init__(self):
        super().__init__()
        self._results: list = []
        self.list_view = ListView()

    def compose(self) -> ComposeResult:
        yield self.list_view

    def set_results(self, tracks: list, autofocus: bool = False) -> None:
        self._results = tracks
        self.list_view.clear()
        for track in tracks:
            self.list_view.append(SearchResultItem(track))
        if autofocus and tracks:
            self.list_view.focus()

    def get_selected_track(self):
        if self.list_view.index is None:
            return None
        idx = self.list_view.index
        if 0 <= idx < len(self._results):
            return self._results[idx]
        return None
