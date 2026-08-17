import time

from zenplayer.utils.history import (
    add_to_history,
    clear_history,
    get_history,
    remove_from_history,
    update_history_position,
)


def test_get_history_empty_when_no_file(tmp_zen_history):
    assert get_history() == []


def test_get_history_respects_limit(tmp_zen_history, mock_track):
    add_to_history(mock_track, limit=5)
    # Add more tracks with different IDs
    for i in range(10):
        mock_track.id = f"track_{i}"
        add_to_history(mock_track, limit=5)
    assert len(get_history(limit=3)) == 3


def test_get_history_returns_most_recent_first(tmp_zen_history):
    from dataclasses import dataclass

    @dataclass
    class Track:
        id: str
        title: str
        artist: str
        duration: int
        url: str

    t1 = Track(id="first", title="First", artist="A", duration=100, url="u1")
    t2 = Track(id="second", title="Second", artist="B", duration=200, url="u2")
    add_to_history(t1)
    add_to_history(t2)
    history = get_history()
    assert history[0]["id"] == "second"
    assert history[1]["id"] == "first"


def test_add_to_history_creates_entry(tmp_zen_history, mock_track):
    add_to_history(mock_track)
    history = get_history()
    assert len(history) == 1
    assert history[0]["id"] == mock_track.id
    assert history[0]["title"] == mock_track.title
    assert history[0]["artist"] == mock_track.artist
    assert history[0]["duration"] == mock_track.duration
    assert history[0]["url"] == mock_track.url


def test_add_to_history_deduplicates_by_id(tmp_zen_history, mock_track):
    add_to_history(mock_track)
    add_to_history(mock_track)
    assert len(get_history()) == 1


def test_add_to_history_preserves_position_on_re_add(tmp_zen_history, mock_track):
    add_to_history(mock_track)
    update_history_position(mock_track.id, 42.0)
    add_to_history(mock_track)
    history = get_history()
    assert history[0]["position"] == 42.0


def test_add_to_history_coerces_none_title_to_unknown(tmp_zen_history, mock_track):
    mock_track.title = None
    add_to_history(mock_track)
    assert get_history()[0]["title"] == "Unknown"


def test_add_to_history_coerces_none_artist_to_unknown(tmp_zen_history, mock_track):
    mock_track.artist = None
    add_to_history(mock_track)
    assert get_history()[0]["artist"] == "Unknown"


def test_add_to_history_trims_to_limit(tmp_zen_history):
    from dataclasses import dataclass

    @dataclass
    class Track:
        id: str
        title: str
        artist: str
        duration: int
        url: str

    for i in range(5):
        add_to_history(Track(id=f"t{i}", title=f"T{i}", artist="A", duration=100, url="u"), limit=3)
    assert len(get_history()) == 3


def test_add_to_history_handles_missing_thumbnail_attribute(tmp_zen_history):
    from dataclasses import dataclass

    @dataclass
    class MinimalTrack:
        id: str
        title: str
        artist: str
        duration: int
        url: str

    t = MinimalTrack(id="m", title="M", artist="A", duration=100, url="u")
    add_to_history(t)
    assert get_history()[0]["thumbnail"] is None
    assert get_history()[0]["description"] == ""


def test_update_history_position_sets_position(tmp_zen_history, mock_track):
    add_to_history(mock_track)
    update_history_position(mock_track.id, 99.5)
    assert get_history()[0]["position"] == 99.5


def test_update_history_position_clamps_negative_to_zero(tmp_zen_history, mock_track):
    add_to_history(mock_track)
    update_history_position(mock_track.id, -10.0)
    assert get_history()[0]["position"] == 0


def test_update_history_position_nonexistent_id_noop(tmp_zen_history, mock_track):
    add_to_history(mock_track)
    update_history_position("nonexistent", 50.0)
    assert get_history()[0]["position"] == 0


def test_remove_from_history_valid_index(tmp_zen_history, mock_track):
    add_to_history(mock_track)
    remove_from_history(0)
    assert get_history() == []


def test_remove_from_history_out_of_range_noop(tmp_zen_history, mock_track):
    add_to_history(mock_track)
    remove_from_history(999)
    assert len(get_history()) == 1


def test_remove_from_history_negative_index_noop(tmp_zen_history, mock_track):
    add_to_history(mock_track)
    remove_from_history(-1)
    assert len(get_history()) == 1


def test_clear_history_empties_file(tmp_zen_history, mock_track):
    add_to_history(mock_track)
    clear_history()
    assert get_history() == []
