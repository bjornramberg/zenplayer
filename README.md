# zenplayer

A terminal-based YouTube Music client with a real-time audio-reactive spectrum visualizer.

## Features

- **Search & play** YouTube music directly from the terminal
- **Audio-reactive visualizer** — center-out symmetrical spectrum that reacts to real audio output (captured via PulseAudio monitor)
- **Dual-screen layout** — player view with search sidebar toggled via `ctrl+p`
- **mpv-backed playback** with seek, volume, pause, next/previous
- **Search result caching** with 5-minute TTL

## Requirements

- Python 3.11+
- [mpv](https://mpv.io/) (tested with 0.41.0)
- PulseAudio (or PipeWire with pulse-compat) for audio capture
- `parec` (part of `pulseaudio-utils`)

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
├── app.py              # App shell, CSS, keybindings, play_track
├── config.py           # JSON config (~/.config/zenplayer/config.json)
├── audio/
│   ├── player.py       # mpv subprocess manager (IPC via Unix socket)
│   ├── analyzer.py     # FFT → log-spaced frequency bands, EMA smoothing
│   ├── capture.py      # PulseAudio monitor capture via parec, numpy circular buffer
│   └── extractor.py    # yt-dlp search + TrackInfo dataclass
├── screens/
│   ├── player_screen.py  # Main player layout (visualizer + controls + search sidebar)
│   └── search_screen.py  # Full-screen search overlay
├── widgets/
│   ├── visualizer.py     # SymmetricalSpectrum — center-out bar spectrum
│   ├── controls.py       # Playback controls bar
│   ├── queue_view.py     # Current playlist queue
│   └── search_results.py # Search result list items
└── utils/
    ├── cache.py          # Search result disk cache with TTL
    └── format.py         # Duration formatting helpers
```

## How the visualizer works

1. `parec` captures raw float32 PCM from the default PulseAudio sink's monitor source
2. A daemon thread reads PCM data into a 2048-sample circular buffer
3. On each frame (30 fps), `AudioAnalyzer` applies a Hanning window and `rfft` to get the magnitude spectrum
4. Spectrum is divided into 12 log-spaced frequency bands; each band's energy is normalized relative to the total spectral energy for volume-independent response
5. `SymmetricalSpectrum` maps 7 of these bands to each side of a center-out display (bass in the middle, treble at edges), using Unicode shade characters (` ▁▂▃▄▅▆▇█`) with a coral gradient

## Configuration

`~/.config/zenplayer/config.json`:

```json
{
  "volume": 50,
  "visualizer_bands": 24,
  "visualizer_fps": 30
}
```

## License

MIT
