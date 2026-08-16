# zenplayer

A terminal-based YouTube Music client with album-art now-playing display, bass-reactive glow, and session persistence.

## Features

- **Search & play** YouTube music directly from the terminal
- **Album art now-playing** — track thumbnails rendered as truecolor half-block art filling the player panel, with a title/artist/progress-bar overlay
- **Bass-reactive glow** — the overlay background pulses with the music's low-end energy (40–240 Hz FFT)
- **Dual-screen layout** — player view with search sidebar, toggled via `ctrl+p`
- **Full-screen search** — debounced (300ms), cached (5min TTL) async search with configurable result depth
- **Search preview** — arrow through results to see a thumbnail and word-wrapped description in the sidebar
- **mpv-backed playback** — seek, volume, pause, next/previous via IPC over Unix socket
- **Clickable controls** — prev/play/next buttons in the controls bar are mouse-clickable
- **Volume persistence** — volume changes are saved to the config file
- **History** — last played tracks stored with playback position; browse, play, remove, or clear entries
- **Session persistence** — quitting saves the current track + position (−10s); on restart, press `r` to resume
- **Zen mode** — minimal, visually dampened full-screen view with just title, artist, and basic controls
- **Stall-resistant output** — a non-blocking terminal writer with drop detection that self-recovers on slow terminals
- **Thumbnail caching** — cover art cached on disk for instant replays

## Requirements

- Python 3.11+
- [mpv](https://mpv.io/) — audio playback engine (tested with 0.41.0)
- A truecolor-capable terminal for full-quality album art (falls back gracefully otherwise)

### Optional (for bass-reactive glow)

- [PulseAudio](https://www.freedesktop.org/wiki/Software/PulseAudio/) — `pactl` and `parec` are used to capture live audio for the FFT bass analysis. Without these, the bass-reactive glow is disabled but all other features work.

## Install

### From PyPI

```bash
pip install zenplayer
```

### From source

```bash
git clone https://github.com/bjornramberg/zenplayer.git
cd zenplayer
pip install .
```

### Platform-specific mpv install

```bash
# macOS
brew install mpv

# Ubuntu / Debian
sudo apt install mpv

# Arch
sudo pacman -S mpv

# Fedora
sudo dnf install mpv
```

## Usage

```bash
zenplayer
```

Or run as a Python module:

```bash
python -m zenplayer
```

The search bar is focused on startup — just start typing to search. Press `escape` to unfocus it and use keyboard shortcuts.

### Keyboard shortcuts

Global (all screens):

| Key | Action |
|---|---|
| `ctrl+p` | Toggle player / search screen |
| `ctrl+f` or `/` | Focus search input |
| `space` | Play / Pause |
| `→` / `←` | Seek forward / backward 5s |
| `+` / `-` | Volume up / down (5% steps) |
| `n` / `p` | Next / Previous track |
| `h` | Toggle history screen |
| `r` | Resume last session |
| `q` | Quit |

Player screen:

| Key | Action |
|---|---|
| `f1` | Toggle zen mode |

History screen:

| Key | Action |
|---|---|
| `enter` | Play selected track (resumes from saved position) |
| `backspace` / `delete` | Remove selected entry |
| `ctrl+x` | Clear all history |
| `escape` | Close history |

### Zen mode

Press `f1` to toggle zen mode — a minimal, visually dampened view that hides the search panel, album art, queue, and controls bar. Only the track title, artist, duration, and prev/play/next buttons are shown. Press `f1` again to return to the full view.

### History

Press `h` to open the history screen — a full-screen overlay showing all previously played tracks (newest first). Select a track and press `enter` to play it from where you last left off. History entries show the saved position next to the duration.

### Session persistence

When you quit the app (`q`), the current track and playback position (−10s) are saved. On the next startup, a "Press r to resume where you left off" banner appears. Press `r` to continue from the saved position.

## Configuration

`~/.config/zenplayer/config.json`:

```json
{
  "volume": 50,
  "reactive_fps": 24,
  "search_limit": 30,
  "history_limit": 100
}
```

| Key | Description | Default |
|---|---|---|
| `volume` | Initial volume (0–100); updated in-app and persisted | `50` |
| `reactive_fps` | How often the bass analysis runs and the glow updates | `24` |
| `search_limit` | How many results each search fetches | `30` |
| `history_limit` | Max entries stored in play history | `100` |

## Data files

| Path | Contents |
|---|---|
| `~/.config/zenplayer/config.json` | Volume, FPS, limits, last session |
| `~/.cache/zenplayer/thumbs/` | Cached YouTube thumbnails |
| `~/.cache/zenplayer/history.json` | Play history with positions |
| `~/.cache/zenplayer/search/` | Cached search results (JSON, 5min TTL) |

## Architecture

```
zenplayer/
├── __init__.py             # Package version
├── __main__.py             # Entry point: main()
├── app.py                  # ZenPlayer(App) shell, CSS, keybindings, bass-reactive tick
├── config.py               # JSON config at ~/.config/zenplayer/config.json
├── diagnostics.py          # Stall sampler + tick/state logging (troubleshooting)
├── nonblocking_output.py   # Non-blocking terminal writer w/ drop detection
├── audio/
│   ├── analyzer.py         # AudioAnalyzer — FFT + bass-power extraction via numpy
│   ├── capture.py          # AudioCapture — parec/arecord subprocess for live audio
│   ├── extractor.py        # yt-dlp search + TrackInfo dataclass
│   └── player.py           # MpvPlayer — mpv subprocess + Unix socket IPC
├── screens/
│   ├── player_screen.py    # Main player layout (album art + search sidebar + controls)
│   ├── search_screen.py    # Full-screen search overlay (debounced, 300ms)
│   └── history_screen.py   # Full-screen history overlay
├── widgets/
│   ├── _art.py             # Shared half-block render helpers (quantize, run-merge)
│   ├── album_art.py        # AlbumArt — full-panel truecolor half-block art
│   ├── controls.py         # Controls — prev/play/next buttons + volume bar + time
│   ├── now_playing.py      # NowPlayingOverlay — title/artist/progress + bass glow
│   ├── queue_view.py       # QueueView — horizontal queue display
│   ├── resume_prompt.py    # ResumePrompt — "Press r to resume" banner
│   ├── search_preview.py   # SearchPreview — square thumbnail + description
│   ├── search_results.py   # SearchResults — ListView of SearchResultItems
│   └── zen_now_playing.py  # ZenNowPlaying — minimal centered view for zen mode
└── utils/
    ├── cache.py            # Search result disk cache with TTL
    ├── format.py           # Duration formatting helpers
    ├── history.py          # Play history persistence with positions
    └── thumbnail.py        # Thumbnail fetch + disk cache
```

## How the album art works

1. When a track starts, `AlbumArt` kicks off a background worker that fetches the YouTube thumbnail (`hqdefault.jpg`) and caches it at `~/.cache/zenplayer/thumbs/`
2. The image is center-cropped to the player panel's aspect ratio, downscaled to `W×2H` pixels (W×H terminal cells), and quantized to a 128-color palette (no dithering)
3. Each cell is rendered with the `▀` half-block: the top pixel as foreground color and the bottom pixel as background color, giving full 2× vertical resolution. Consecutive cells sharing the same color pair are run-length-merged into a single span, so a 188×78 panel renders ~1.2k spans instead of ~14.7k (about 12× fewer rich styles and ~12× faster repaints)
4. A `NowPlayingOverlay` docked at the bottom shows the title, artist, and a progress bar; its background glows and tints red in sync with bass energy from a 40–240 Hz FFT band
5. While a thumbnail loads (or if none is available) a deterministic gradient cover derived from the track id is shown instead; pausing appends "(paused)" to the artist line

## License

MIT License
