from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import ListView, ListItem, Label

from zenplayer.utils.format import format_duration


class SearchResultItem(ListItem):
    def __init__(self, track, position=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.track = track
        self.position = position

    def compose(self) -> ComposeResult:
        title = self.track.title or "Unknown"
        artist = self.track.artist or "Unknown"
        duration = format_duration(self.track.duration)
        if self.position > 0:
            pos = format_duration(self.position)
            yield Label(f"{title}")
            yield Label(f"{artist}  {pos} / {duration}", classes="result-meta")
        else:
            yield Label(f"{title}")
            yield Label(f"{artist}  {duration}", classes="result-meta")


class SearchResults(Vertical):
    def __init__(self):
        super().__init__()
        self._results: list = []
        self.list_view = ListView()

    def compose(self) -> ComposeResult:
        yield self.list_view

    def set_results(self, tracks: list, autofocus: bool = False, positions: list | None = None) -> None:
        self._results = tracks
        self.list_view.clear()
        for i, track in enumerate(tracks):
            pos = positions[i] if positions and i < len(positions) else 0
            self.list_view.append(SearchResultItem(track, position=pos))
        if autofocus and tracks:
            self.list_view.focus()

    def get_selected_track(self):
        if self.list_view.index is None:
            return None
        idx = self.list_view.index
        if 0 <= idx < len(self._results):
            return self._results[idx]
        return None
