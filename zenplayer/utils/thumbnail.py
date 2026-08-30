from pathlib import Path
from typing import Optional

from PIL import Image

CACHE_DIR = Path.home() / ".cache" / "zenplayer" / "thumbs"

_TIMEOUT = 5

# hqdefault.jpg is 480x360 and letterboxes 16:9 video with black bars, which
# makes the album art look like a rectangle inside the turntable. Prefer true
# 16:9 thumbnails without bars.
_THUMB_NAMES = ("maxresdefault", "mqdefault", "hqdefault")


def thumbnail_url(video_id: str, name: str = "maxresdefault") -> str:
    return f"https://i.ytimg.com/vi/{video_id}/{name}.jpg"


def _cache_path(video_id: str, name: str) -> Path:
    return CACHE_DIR / f"{video_id}_{name}.jpg"


def load_thumbnail(video_id: str, max_size: int = 512) -> Optional[Image.Image]:
    # Try each source in preference order, reusing any cached copy and
    # downloading the first available one.
    for name in _THUMB_NAMES:
        path = _cache_path(video_id, name)
        if not path.exists():
            _download(video_id, name, path)
        if not path.exists():
            continue
        try:
            with Image.open(path) as img:
                img.load()
                img = img.convert("RGB")
            if max_size and max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.LANCZOS)
            return img
        except Exception:
            continue
    return None


def _download(video_id: str, name: str, path: Path) -> None:
    import urllib.request

    tmp = path.with_suffix(".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(
            thumbnail_url(video_id, name),
            headers={"User-Agent": "zenplayer/0.1"},
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp, open(tmp, "wb") as f:
            f.write(resp.read())
        tmp.rename(path)
    except Exception:
        pass
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass
