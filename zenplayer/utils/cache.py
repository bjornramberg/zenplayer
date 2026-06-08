import json
import time
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "zenplayer"
CACHE_FILE = CACHE_DIR / "search_cache.json"
CACHE_TTL = 300


def load_cache() -> dict:
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_cache(cache: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


def _has_valid_urls(results: list) -> bool:
    return all(
        isinstance(r, dict) and r.get("url")
        for r in results
    )


def get_cached(query: str):
    cache = load_cache()
    entry = cache.get(query)
    if entry and time.time() - entry.get("timestamp", 0) < CACHE_TTL:
        results = entry.get("results")
        if results and _has_valid_urls(results):
            return results
    return None


def set_cached(query: str, results: list) -> None:
    if not results or not _has_valid_urls(results):
        return
    cache = load_cache()
    cache[query] = {"results": results, "timestamp": time.time()}
    now = time.time()
    cache = {k: v for k, v in cache.items() if now - v.get("timestamp", 0) < CACHE_TTL}
    save_cache(cache)
