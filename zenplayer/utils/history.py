import json
import time
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "zenplayer"
HISTORY_FILE = CACHE_DIR / "history.json"


def _load_raw() -> list:
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save(entries: list) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(entries, f)


def get_history(limit: int = 100) -> list[dict]:
    return _load_raw()[:limit]


def add_to_history(track, limit: int = 100) -> None:
    entries = _load_raw()
    existing = next((e for e in entries if e.get("id") == track.id), None)
    position = existing.get("position", 0) if existing else 0
    entry = {
        "id": track.id,
        "title": track.title or "Unknown",
        "artist": track.artist or "Unknown",
        "duration": track.duration,
        "url": track.url,
        "thumbnail": getattr(track, "thumbnail", None),
        "description": getattr(track, "description", ""),
        "played_at": time.time(),
        "position": position,
    }
    entries = [e for e in entries if e.get("id") != track.id]
    entries.insert(0, entry)
    _save(entries[:limit])


def update_history_position(track_id: str, position: float) -> None:
    entries = _load_raw()
    for e in entries:
        if e.get("id") == track_id:
            e["position"] = max(0, position)
            break
    _save(entries)


def remove_from_history(index: int) -> None:
    entries = _load_raw()
    if 0 <= index < len(entries):
        entries.pop(index)
        _save(entries)


def clear_history() -> None:
    _save([])
