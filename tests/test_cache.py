import time

from zenplayer.utils.cache import (
    CACHE_TTL,
    _has_valid_urls,
    _key,
    get_cached,
    set_cached,
)


def test_has_valid_urls_empty_list_returns_true():
    assert _has_valid_urls([]) is True


def test_has_valid_urls_all_valid_returns_true():
    assert _has_valid_urls([{"url": "a"}, {"url": "b"}]) is True


def test_has_valid_urls_missing_url_returns_false():
    assert _has_valid_urls([{"url": "a"}, {"title": "no url"}]) is False


def test_has_valid_urls_empty_url_returns_false():
    assert _has_valid_urls([{"url": ""}]) is False


def test_has_valid_urls_non_dict_element_returns_false():
    assert _has_valid_urls(["not a dict"]) is False


def test_has_valid_urls_mixed_returns_false():
    assert _has_valid_urls([{"url": "a"}, "bad"]) is False


def test_key_with_limit():
    assert _key("rock", 30) == "rock|30"


def test_key_without_limit():
    assert _key("rock", None) == "rock"


def test_get_cached_no_file_returns_none(tmp_zen_cache):
    assert get_cached("query") is None


def test_get_cached_corrupted_json_returns_none(tmp_zen_cache, tmp_path):
    (tmp_path / "search_cache.json").write_text("bad json")
    assert get_cached("query") is None


def test_get_cached_expired_entry_returns_none(tmp_zen_cache):
    results = [{"url": "https://example.com"}]
    set_cached("query", results)
    # Monkeypatch time to be far in the future
    import zenplayer.utils.cache as cache_mod
    original_time = cache_mod.time.time
    cache_mod.time.time = lambda: original_time() + CACHE_TTL + 100
    try:
        assert get_cached("query") is None
    finally:
        cache_mod.time.time = original_time


def test_get_cached_valid_entry_returns_results(tmp_zen_cache):
    results = [{"url": "https://example.com"}]
    set_cached("query", results)
    assert get_cached("query") == results


def test_get_cached_valid_entry_invalid_urls_returns_none(tmp_zen_cache):
    results = [{"url": ""}]
    set_cached("query", results)
    assert get_cached("query") is None


def test_get_cached_no_results_key_returns_none(tmp_zen_cache):
    results = [{"url": "https://example.com"}]
    set_cached("query", results, limit=30)
    # Different limit = different key
    assert get_cached("query", limit=50) is None


def test_set_cached_empty_results_noop(tmp_zen_cache):
    set_cached("query", [])
    assert get_cached("query") is None


def test_set_cached_invalid_urls_noop(tmp_zen_cache):
    set_cached("query", [{"no_url": True}])
    assert get_cached("query") is None


def test_set_cached_stores_and_prunes_expired(tmp_zen_cache):
    import zenplayer.utils.cache as cache_mod
    original_time = cache_mod.time.time
    now = original_time()

    # Store first entry
    cache_mod.time.time = lambda: now
    set_cached("old", [{"url": "https://old.com"}])

    # Store second entry at current time
    cache_mod.time.time = lambda: now
    set_cached("new", [{"url": "https://new.com"}])

    # Move time forward past TTL — both should be pruned
    cache_mod.time.time = lambda: now + CACHE_TTL + 1
    set_cached("fresh", [{"url": "https://fresh.com"}])

    try:
        # Old entries should be pruned, fresh should exist
        cache_mod.time.time = lambda: now + CACHE_TTL + 1
        assert get_cached("old") is None
        assert get_cached("new") is None
        assert get_cached("fresh") == [{"url": "https://fresh.com"}]
    finally:
        cache_mod.time.time = original_time


def test_set_cached_creates_directory(tmp_path, monkeypatch):
    nested = tmp_path / "subdir"
    monkeypatch.setattr("zenplayer.utils.cache.CACHE_DIR", nested)
    monkeypatch.setattr("zenplayer.utils.cache.CACHE_FILE", nested / "search_cache.json")
    set_cached("query", [{"url": "https://example.com"}])
    assert (nested / "search_cache.json").exists()
