import json

from zenplayer.config import DEFAULT_CONFIG, load_config, save_config


def test_load_config_no_file_returns_defaults(tmp_zen_config):
    assert load_config() == DEFAULT_CONFIG


def test_load_config_corrupted_json_returns_defaults(tmp_zen_config, tmp_path):
    (tmp_path / "config.json").write_text("not valid json {{{")
    assert load_config() == DEFAULT_CONFIG


def test_load_config_partial_keys_merges_with_defaults(tmp_zen_config, tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"volume": 75}))
    result = load_config()
    assert result["volume"] == 75
    assert result["reactive_fps"] == DEFAULT_CONFIG["reactive_fps"]
    assert result["search_limit"] == DEFAULT_CONFIG["search_limit"]
    assert result["history_limit"] == DEFAULT_CONFIG["history_limit"]


def test_load_config_extra_keys_preserved(tmp_zen_config, tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"custom_key": "value"}))
    result = load_config()
    assert result["custom_key"] == "value"
    assert result["volume"] == DEFAULT_CONFIG["volume"]


def test_load_config_empty_json_returns_defaults(tmp_zen_config, tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({}))
    assert load_config() == DEFAULT_CONFIG


def test_save_config_creates_file(tmp_zen_config, tmp_path):
    save_config({"volume": 80})
    assert (tmp_path / "config.json").exists()


def test_save_config_creates_directory(tmp_path, monkeypatch):
    nested = tmp_path / "subdir"
    monkeypatch.setattr("zenplayer.config.CONFIG_DIR", nested)
    monkeypatch.setattr("zenplayer.config.CONFIG_FILE", nested / "config.json")
    save_config({"volume": 80})
    assert (nested / "config.json").exists()


def test_save_config_roundtrip(tmp_zen_config):
    original = {"volume": 75, "reactive_fps": 30, "search_limit": 50, "history_limit": 200}
    save_config(original)
    loaded = load_config()
    assert loaded == original
