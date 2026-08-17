import pytest
from zenplayer.audio.extractor import TrackInfo


@pytest.fixture
def tmp_zen_config(tmp_path, monkeypatch):
    """Redirect config to temp directory."""
    monkeypatch.setattr("zenplayer.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("zenplayer.config.CONFIG_FILE", tmp_path / "config.json")


@pytest.fixture
def tmp_zen_cache(tmp_path, monkeypatch):
    """Redirect cache to temp directory."""
    monkeypatch.setattr("zenplayer.utils.cache.CACHE_DIR", tmp_path)
    monkeypatch.setattr("zenplayer.utils.cache.CACHE_FILE", tmp_path / "search_cache.json")


@pytest.fixture
def tmp_zen_history(tmp_path, monkeypatch):
    """Redirect history to temp directory."""
    monkeypatch.setattr("zenplayer.utils.history.CACHE_DIR", tmp_path)
    monkeypatch.setattr("zenplayer.utils.history.HISTORY_FILE", tmp_path / "history.json")


@pytest.fixture
def mock_track():
    """Returns a TrackInfo with test data."""
    return TrackInfo(
        id="test123",
        title="Test Song",
        artist="Test Artist",
        duration=240,
        url="https://example.com/track",
    )
