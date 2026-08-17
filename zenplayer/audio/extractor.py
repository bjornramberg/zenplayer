from dataclasses import dataclass
from typing import Optional

from yt_dlp import YoutubeDL


@dataclass
class TrackInfo:
    id: str
    title: str
    artist: str
    duration: int
    url: str
    thumbnail: Optional[str] = None
    description: Optional[str] = None
    source: str = "youtube"


def search(query: str, limit: int = 10) -> list[TrackInfo]:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "force_generic_extractor": False,
        "socket_timeout": 10,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
        if not info or "entries" not in info:
            return []
        results = []
        for entry in info["entries"]:
            if not entry:
                continue
            results.append(TrackInfo(
                id=entry.get("id", ""),
                title=entry.get("title", "Unknown"),
                artist=entry.get("uploader") or entry.get("channel", "Unknown"),
                duration=entry.get("duration", 0),
                url=entry.get("url") or f"https://www.youtube.com/watch?v={entry['id']}",
                thumbnail=entry.get("thumbnail"),
                description=entry.get("description", ""),
            ))
        return results


def extract_audio_url(url: str) -> Optional[str]:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if info and "url" in info:
            return info["url"]
        return None
