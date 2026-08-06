# zenplayer — Terminal YouTube Music Client

## Overview

**zenplayer** is a minimal terminal-based YouTube Music client with an album-art now-playing display. It runs in any modern terminal emulator, uses `mpv` for playback, and `yt-dlp` for audio extraction.

---

## Tech Stack

| Component | Choice | Why |
|---|---|---|
| **Language** | Python 3.11+ | Rich ecosystem, great TUI libs, yt-dlp native bindings |
| **TUI Framework** | [Textual](https://github.com/Textualize/textual) | Modern, reactive, minimal by default, excellent widget system |
| **Audio Extraction** | yt-dlp (Python API) | Extracts audio stream URLs + metadata without API keys |
| **Playback Engine** | mpv via subprocess | Lightweight, handles streaming, pitch correction, gapless |
| **Album Art Render** | Pillow + numpy, truecolor half-blocks | Downscales thumbnails; per-cell fg/bg half-block art |
| **Thumbnail Fetch** | urllib + disk cache | Instant replays via `~/.cache/zenplayer/thumbs/` |

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│                  Textual TUI App                  │
│                                                   │
│  ┌────────────────────────────────────────────┐   │
│  │            Header (app name, time)          │   │
│  ├─────────────────────┬──────────────────────┤   │
│  │    Search Panel      │   Now Playing        │   │
│  │    (results list)    │   ┌──────────────┐   │   │
│  │                      │   │  █▀▄▀▄██▀▄█▀ │   │   │
│  │  ┌─────────────────┐ │   │  █▄▀████▀▄██▀ │   │   │
│  │  │ Query input      │ │   │  █████▄▀███▀  │   │   │
│  │  │ Result 1         │ │   │  ▀▄▀██████▀▄█ │   │   │
│  │  │ Result 2         │ │   │  Track Title   │   │   │
│  │  │ Result 3         │ │   │  Artist         │   │   │
│  │  └─────────────────┘ │   │  ▓▓▓▓░░ 1:34    │   │   │
│  │                      │   └──────────────┘   │   │
│  ├─────────────────────┴──────────────────────┤   │
│  │           Queue Bar (up next list)          │   │
│  ├────────────────────────────────────────────┤   │
│  │           Controls: ⏮ ⏸ ⏭ 🔇 Vol:███      │   │
│  └────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
          │                  │              │
          ▼                  ▼              ▼
   ┌────────────┐   ┌────────────┐   ┌────────────┐
   │  yt-dlp    │   │    mpv     │   │  Thumbnail │
   │ (search +  │──▶│ (playback) │   │  fetch →   │
   │  extract)  │   │            │   │  disk cache│
   └────────────┘   └────────────┘   └─────┬──────┘
                                           ▼
                                    AlbumArt widget
```

---

## Data Flow

```
1. User types search query
2. yt-dlp search extracts results (title, artist, duration, thumbnail URL)
3. User selects a track → added to queue, mpv starts playback
4. PlayerScreen polls mpv every 0.5s for time/volume/paused state
5. AlbumArt fetches the thumbnail in a background worker (cached on disk)
6. Thumbnail is center-cropped to the panel, downscaled to W×2H, rendered as half-blocks
7. Title, artist, and progress bar are composited over a scrim at the bottom
8. User controls playback via keyboard (Space=play/pause, etc.)
```

---

## Project Structure

```
zenplayer/
├── pyproject.toml
├── requirements.txt
├── zenplayer/
│   ├── __init__.py
│   ├── __main__.py              # Entry point: python -m zenplayer
│   ├── app.py                   # Textual App class, key bindings, theming
│   ├── config.py                # Config loading/saving (~/.config/zenplayer/)
│   │
│   ├── screens/
│   │   ├── search_screen.py     # Full-screen search view
│   │   └── player_screen.py     # Main player + album art view
│   │
│   ├── widgets/
│   │   ├── album_art.py         # AlbumArt: half-block truecolor art + overlay
│   │   ├── search_results.py    # Results list widget
│   │   ├── queue_view.py        # Queue/up-next display
│   │   └── controls.py          # Playback controls bar
│   │
│   ├── audio/
│   │   ├── extractor.py         # yt-dlp: search, extract stream URL, metadata
│   │   └── player.py            # mpv subprocess manager (start/stop/seek/volume)
│   │
│   └── utils/
│       ├── thumbnail.py         # Thumbnail fetch, disk cache, decode
│       ├── cache.py             # Search result cache (SQLite/simple JSON)
│       └── format.py            # Duration formatting, etc.
```

---

## Album Art Design

```
┌──────────────────────────────────────┐
│  ██▀▄▄▀▄█████▀▄▄████▄▀▀▄▄█▄▀████▀▄██ │  ← real thumbnail,
│  ▄▀████▀▄█████▄████▄▀████▄████▀▄████▀ │    half-block truecolor art
│  ███▄▀▄████▀▄████████▀▄████▄▀▄██████  │    filling the whole panel
│  ──────────────────────────────────── │  ← scrim gradient
│  Midnight City                     M83 │  ← title / artist
│  █████████████████░░░░░░░   2:14 / 4:04│  ← progress bar + time
└──────────────────────────────────────┘
```

**How it works:**

1. `AlbumArt.set_track()` runs a Textual worker that fetches the YouTube thumbnail (`https://i.ytimg.com/vi/{id}/hqdefault.jpg`) and caches it at `~/.cache/zenplayer/thumbs/{id}.jpg`
2. The image is center-cropped to the panel's aspect ratio (`ImageOps.fit`) and downscaled to `W×2H` pixels, where `W×H` is the widget size in cells
3. Each cell is rendered with the `▀` half-block character: the **top pixel → foreground color**, the **bottom pixel → background color** — giving full 2× vertical resolution in a single terminal row
4. A dark scrim gradient is composited over the bottom rows so overlaid text stays readable
5. Title (bold white), artist (muted), and a coral progress bar with times are drawn onto the scrim
6. Pausing dims the art ~50% and appends "(paused)"; a deterministic gradient cover derived from the track id is shown while loading or if the thumbnail is unavailable
7. The art pixel rows are cached; only the overlay rows regenerate on the 0.5s progress tick

**Technical details:**

- Colors: per-cell truecolor hex via Rich `Style`; Textual degrades gracefully on 256-color terminals
- Aspect: full-bleed center-crop (Spotify-style), so no dead space in the player panel
- Threading: `@work(thread=True, exclusive=True)` worker; result applied via `App.call_from_thread`
- Resolution needs are tiny (~W×2H ≈ 150×50 px), so the 480×360 thumbnail is more than enough

---

## UI Theme (Minimal Aesthetic)

```python
# Color scheme — true minimal, monochrome with single accent
COLORS = {
    "background": "#000000",    # True black
    "surface":   "#0a0a0a",    # Near-black for panels
    "text":      "#c0c0c0",    # Soft silver
    "text_dim":  "#555555",    # Dimmed text
    "accent":    "#ff6b6b",    # Soft coral red (single accent)
    "success":   "#00ff88",    # Active/playing indicator
    "border":    "#222222",    # Subtle borders
}
```

- No unnecessary borders or padding
- Text-only controls (no unicode symbols unless essential)
- Album art renders in its natural colors; overlay text uses the accent for the progress bar

---

## Key Bindings

| Key | Action |
|---|---|
| `Ctrl+P` | Toggle between search and player screen |
| `Ctrl+F` | Focus search input |
| `/` | Focus search input (vim-like) |
| `↑`/`↓` | Navigate results/queue |
| `Enter` | Play selected track |
| `Space` | Play/Pause |
| `→`/`←` | Seek forward/backward 5s |
| `+`/`-` | Volume up/down |
| `n` | Next track |
| `p` | Previous track |
| `q` / `Ctrl+C` | Quit |

---

## Setup & Installation

```bash
# Dependencies
pip install textual yt-dlp numpy pillow
sudo apt install mpv           # Or pacman -S mpv / brew install mpv

# Run
python -m zenplayer
```

---

## Future / Optional Features (Phase 2)

- **Login support** — youtube-authentication for playlists/library
- **Full-res album art** — `maxresdefault.jpg` when available (bigger terminals)
- **MPRIS integration** — media keys / desktop integration
- **Download mode** — offline playback of cached tracks
- **Reactive visualizer** — a polished audio-reactive mode (needs audio capture re-added)

---

## Open Questions

1. **Album art source:** `hqdefault.jpg` (always available) vs `maxresdefault.jpg` (higher res, sometimes 404) with fallback?
2. **Search source:** Just search YouTube Music videos? Filter to music only?
3. **Playlist/auth:** Login to YouTube Music for library access, or public search only?
4. **Python dependency management:** Poetry / pip + venv / plain pip?
