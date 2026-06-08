from rich.style import Style
from rich.text import Text
from textual.widget import Widget

SHADES = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
NUM_BANDS = 7


class SymmetricalSpectrum(Widget):
    def __init__(self):
        super().__init__()
        self._smooth_bands = [0.0] * NUM_BANDS

    def on_mount(self):
        self.set_interval(1 / 30, self._tick)

    def _tick(self):
        if hasattr(self.app, "analyzer"):
            self.app.analyzer.update()
            raw = self.app.analyzer.get_bands()
            n = min(len(raw), NUM_BANDS)
            for i in range(n):
                val = raw[i]
                smooth = self._smooth_bands[i]
                if val > smooth:
                    self._smooth_bands[i] += (val - smooth) * 0.5
                else:
                    self._smooth_bands[i] += (val - smooth) * 0.12
                self._smooth_bands[i] = max(0.0, min(1.0, self._smooth_bands[i]))
        self.refresh()

    def render(self) -> Text:
        w, h = self.size.width, self.size.height
        if w < 3 or h < 1:
            return Text("")

        total_cols = 2 * NUM_BANDS
        display_w = min(total_cols, w)
        side = NUM_BANDS
        padding = (w - display_w) // 2

        result = Text()
        bg = Style(bgcolor="#000000")

        for row in range(h):
            line = Text()
            if padding > 0:
                line.append(" " * padding, bg)

            dist = abs((row + 0.5) / h - 0.5)

            for col in range(display_w):
                if col < side:
                    band_idx = side - 1 - col
                else:
                    band_idx = col - side
                band_idx = max(0, min(band_idx, NUM_BANDS - 1))

                val = self._smooth_bands[band_idx]
                fullness = val ** 0.5
                half_bar = fullness * 0.5
                falloff = half_bar * 0.5 + 1.0 / h

                if dist <= half_bar:
                    intensity = 1.0
                elif dist <= half_bar + falloff:
                    intensity = (half_bar + falloff - dist) / falloff
                else:
                    intensity = 0.0

                shade_idx = int(intensity * 8)
                shade_idx = max(0, min(8, shade_idx))

                gb = int(0x6B * intensity)
                color = Style(color=f"#ff{gb:02x}{gb:02x}")
                line.append(SHADES[shade_idx], color + bg)

            remaining = w - (padding + display_w)
            if remaining > 0:
                line.append(" " * remaining, bg)

            line.append("\n" if row < h - 1 else "")
            result.append_text(line)

        return result
