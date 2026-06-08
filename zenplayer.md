# zenplayer — Terminal YouTube Music Client

## Overview

**zenplayer** is a minimal terminal-based YouTube Music client with a circular audio visualizer. It runs in any modern terminal emulator, uses `mpv` for playback, and `yt-dlp` for audio extraction.

---

## Tech Stack

| Component | Choice | Why |
|---|---|---|
| **Language** | Python 3.11+ | Rich ecosystem, great TUI libs, yt-dlp native bindings |
| **TUI Framework** | [Textual](https://github.com/Textualize/textual) | Modern, reactive, minimal by default, excellent widget system |
| **Audio Extraction** | yt-dlp (Python API) | Extracts audio stream URLs + metadata without API keys |
| **Playback Engine** | mpv via subprocess | Lightweight, handles streaming, pitch correction, gapless |
| **Visualizer Math** | numpy + FFT | Frequency analysis from raw PCM data piped from mpv |
| **Visualizer Render** | Unicode braille + block chars in Textual Canvas widget | Works in any terminal, no external deps |

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│                  Textual TUI App                  │
│                                                   │
│  ┌────────────────────────────────────────────┐   │
│  │            Header (app name, time)          │   │
│  ├─────────────────────┬──────────────────────┤   │
│  │    Search Panel      │   Now Playing +      │   │
│  │    (results list)    │   Circular Visualizer │   │
│  │                      │                      │   │
│  │  ┌─────────────────┐ │  ┌────────────────┐  │   │
│  │  │ Query input      │ │  │   ╭─────╮     │  │   │
│  │  │ Result 1         │ │  │  ╱ ● ● ● ╲    │  │   │
│  │  │ Result 2         │ │  │ │ ◉ ◉ ◉ ◉ │   │  │   │
│  │  │ Result 3         │ │  │  ╲ ◉ ◉ ◉ ╱    │  │   │
│  │  └─────────────────┘ │  │   ╰─────╯     │  │   │
│  │                      │  │  Track Title    │  │   │
│  │                      │  │  Artist Name    │  │   │
│  │                      │  └────────────────┘  │   │
│  ├─────────────────────┴──────────────────────┤   │
│  │           Queue Bar (up next list)          │   │
│  ├────────────────────────────────────────────┤   │
│  │           Controls: ⏮ ⏸ ⏭ 🔇 Vol:███      │   │
│  └────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
          │                  │              │
          ▼                  ▼              ▼
   ┌────────────┐   ┌────────────┐   ┌────────────┐
   │  yt-dlp    │   │    mpv     │   │  PCM FIFO  │
   │ (search +  │──▶│ (playback) │──▶│  → FFT →   │
   │  extract)  │   │            │   │  Visualizer│
   └────────────┘   └────────────┘   └────────────┘
```

---

## Data Flow

```
1. User types search query
2. yt-dlp search extracts results (title, artist, duration, URL)
3. User selects a track → added to mpv's internal playlist
4. mpv plays audio, outputs raw PCM data via --audio-file or FIFO
5. Python reads PCM, runs numpy FFT → frequency bin magnitudes
6. Visualizer widget maps bins to radial spokes, renders every frame
7. User controls playback via keyboard (Space=play/pause, etc.)
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
│   │   └── player_screen.py     # Main player + visualizer view
│   │
│   ├── widgets/
│   │   ├── visualizer.py        # Circular radial visualizer (Textual Canvas)
│   │   ├── search_results.py    # Results list widget
│   │   ├── queue_view.py        # Queue/up-next display
│   │   └── controls.py          # Playback controls bar
│   │
│   ├── audio/
│   │   ├── extractor.py         # yt-dlp: search, extract stream URL, metadata
│   │   ├── player.py            # mpv subprocess manager (start/stop/seek/volume)
│   │   └── analyzer.py          # PCM → FFT → frequency bins (numpy)
│   │
│   └── utils/
│       ├── cache.py             # Search result cache (SQLite/simple JSON)
│       └── format.py            # Duration formatting, etc.
```

---

## Circular Visualizer Design

```
       Low ──── Freq ────► High
         ╭─────────────╮
         │  ╭───────╮  │
         │  │ ╭───╮ │  │
         │  │ │ ● │ │  │
         │  │ ╰───╯ │  │
         │  ╰───────╯  │
         ╰─────────────╯
```

**How it works:**

1. mpv outputs raw PCM audio data (16-bit signed, 44100 Hz) to a FIFO pipe
2. `analyzer.py` reads chunks (e.g. 2048 samples), applies Hann window, runs numpy FFT
3. FFT output is divided into N frequency bands (e.g. 32 bands)
4. Magnitudes are smoothed with exponential moving average (avoid jitter)
5. `visualizer.py` maps each band to a radial spoke:
   - Angle = evenly spaced around 0°–360°
   - Length = normalized magnitude (0.0–1.0), mapped to radius range
   - Inner radius for low freqs, outer radius for high freqs
6. Braille characters (`⣀⣤⣶⣿` etc.) or block chars (`░▒▓█`) rendered at spoke endpoints on Textual's Canvas widget
7. Refreshes at ~30 fps using Textual's `set_interval`

**Technical details:**

- FFT size: 2048 (good frequency resolution, low latency)
- Bands: 32 equally spaced on log scale (perceptual)
- Smoothing: α = 0.3 EMA per band
- Render: Textual `Canvas` widget with braille/block characters, drawn in `compose()` or `render_line()`
- Fallback: if terminal doesn't support braille, falls back to ASCII `.,-~=*#`

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
- Visualizer uses accent color with varying brightness for depth

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
pip install textual yt-dlp numpy
sudo apt install mpv           # Or pacman -S mpv / brew install mpv

# Run
python -m zenplayer
```

---

## Future / Optional Features (Phase 2)

- **Login support** — youtube-authentication for playlists/library
- **Album art** — display via kitty terminal protocol
- **Equalizer** — adjust frequency bands interactively
- **Presets** — multiple visualizer color palettes
- **MPRIS integration** — media keys / desktop integration
- **Download mode** — offline playback of cached tracks

---

## Open Questions

1. **Visualizer rendering:** Unicode braille/block chars on Textual Canvas (works everywhere) vs terminal pixel graphics (kitty protocol, smoother) vs separate small GTK window (best visuals)
2. **Search source:** Just search YouTube Music videos? Filter to music only?
3. **Playlist/auth:** Login to YouTube Music for library access, or public search only?
4. **Python dependency management:** Poetry / pip + venv / plain pip?
