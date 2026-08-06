# zenplayer

A terminal-based YouTube Music client with an album-art now-playing display.

## Features

- **Search & play** YouTube music directly from the terminal
- **Album art now-playing** — the current track's thumbnail rendered as truecolor half-block art that fills the player panel, with a title/artist/progress-bar overlay
- **Bass-reactive glow** — the overlay background pulses with the music's low-end energy (40–240 Hz)
- **Dual-screen layout** — player view with search sidebar toggled via `ctrl+p`
- **mpv-backed playback** with seek, volume, pause, next/previous (commands dispatched over a dedicated thread)
- **Thumbnail caching** — cover art cached on disk for instant replays
- **Debounced, cached search** — async results with a 5-minute cache TTL and 300 ms debounce; result depth is configurable via `search_limit` (default 30)
- **Search preview** — arrow through results to see a square thumbnail and word-wrapped description (title, artist, duration, YouTube description) in the sidebar
- **Volume persistence** — volume changes are saved to the config file
- **Stall-resistant output** — a non-blocking terminal writer with drop detection that self-recovers on slow terminals

## Requirements

- Python 3.11+
- [mpv](https://mpv.io/) (tested with 0.41.0)
- A truecolor-capable terminal for full-quality album art (falls back gracefully otherwise)

## Install

```bash
git clone https://github.com/bjornramberg/zenplayer.git
cd zenplayer
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Usage

```bash
zenplayer
```

### Controls

| Key | Action |
|---|---|
| `ctrl+p` | Toggle player / search screen |
| `ctrl+f` or `/` | Focus search input |
| `space` | Play / Pause |
| `→` / `←` | Seek forward / backward 5s |
| `+` / `-` | Volume up / down |
| `n` / `p` | Next / Previous track |
| `q` | Quit |

## Architecture

```
zenplayer/
├── app.py              # App shell, CSS, keybindings, bass-reactive tick
├── config.py           # JSON config (~/.config/zenplayer/config.json)
├── diagnostics.py      # Stall sampler + tick/state logging (troubleshooting)
├── nonblocking_output.py  # Non-blocking terminal writer w/ drop detection
├── audio/
│   ├── analyzer.py     # AudioCapture FFT + bass-power extraction
│   ├── capture.py      # Soundcard capture thread (via ffmpeg/arecord)
│   ├── player.py       # mpv subprocess manager (IPC over Unix socket)
│   └── extractor.py    # yt-dlp search + TrackInfo dataclass
├── screens/
│   ├── player_screen.py  # Main player layout (album art + controls + search sidebar)
│   └── search_screen.py  # Full-screen search overlay
├── widgets/
│   ├── _art.py             # Shared half-block render helpers (quantize, run-merge)
│   ├── album_art.py        # AlbumArt — full-panel truecolor art (quantized, run-merged)
│   ├── search_preview.py   # SearchPreview — square thumbnail + description on highlight
│   ├── now_playing.py      # NowPlayingOverlay — title/artist/progress + bass glow
│   ├── controls.py         # Playback controls bar
│   ├── queue_view.py       # Current playlist queue
│   └── search_results.py   # Search result list items
└── utils/
    ├── cache.py          # Search result disk cache with TTL
    ├── thumbnail.py      # Thumbnail fetch + disk cache
    └── format.py         # Duration formatting helpers
```

## How the album art works

1. When a track starts, `AlbumArt` kicks off a background worker that fetches the YouTube thumbnail (`hqdefault.jpg`) and caches it at `~/.cache/zenplayer/thumbs/`
2. The image is center-cropped to the player panel's aspect ratio, downscaled to `W×2H` pixels (W×H terminal cells), and quantized to a 128-color palette (no dithering)
3. Each cell is rendered with the `▀` half-block: the top pixel as foreground color and the bottom pixel as background color, giving full 2× vertical resolution. Consecutive cells sharing the same color pair are run-length-merged into a single span, so a 188×78 panel renders ~1.2k spans instead of ~14.7k (about 12× fewer rich styles and ~12× faster repaints)
4. A `NowPlayingOverlay` docked at the bottom shows the title, artist, and a progress bar; its background glows and tints red in sync with bass energy from a 40–240 Hz FFT band
5. While a thumbnail loads (or if none is available) a deterministic gradient cover derived from the track id is shown instead; pausing appends "(paused)" to the artist line

## Configuration

`~/.config/zenplayer/config.json`:

```json
{
  "volume": 50,
  "reactive_fps": 24,
  "search_limit": 30
}
```

- `volume` — initial volume (0–100); also updated when you change it in-app
- `reactive_fps` — how often the bass analysis runs and the glow updates (default 24)
- `search_limit` — how many results each search fetches (default 30)

## License

MIT
