from pathlib import Path
from typing import Optional

from PIL import Image

CACHE_DIR = Path.home() / ".cache" / "zenplayer" / "thumbs"

_TIMEOUT = 5


def thumbnail_url(video_id: str) -> str:
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


def _cache_path(video_id: str) -> Path:
    return CACHE_DIR / f"{video_id}.jpg"


def load_thumbnail(video_id: str, max_size: int = 512) -> Optional[Image.Image]:
    path = _cache_path(video_id)
    if not path.exists():
        _download(video_id, path)
    if not path.exists():
        return None
    try:
        with Image.open(path) as img:
            img.load()
            img = img.convert("RGB")
        if max_size and max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.LANCZOS)
        return img
    except Exception:
        return None


def _download(video_id: str, path: Path) -> None:
    import urllib.request

    tmp = path.with_suffix(".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(
            thumbnail_url(video_id), headers={"User-Agent": "zenplayer/0.1"}
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp, open(tmp, "wb") as f:
            f.write(resp.read())
        tmp.rename(path)
    except Exception:
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass
