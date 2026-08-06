import numpy as np

from zenplayer.audio.capture import AudioCapture

BASS_LO_HZ = 40.0
BASS_HI_HZ = 240.0


class AudioAnalyzer:
    def __init__(self, num_bands: int = 16, smoothing: float = 0.3):
        self.num_bands = num_bands
        self._smoothing = smoothing
        self.bands = [0.0] * num_bands
        self._targets = [0.0] * num_bands
        self.bass_power = 0.0
        self._capture = AudioCapture()
        self._playing = False

    def set_playing(self, playing: bool):
        was = self._playing
        self._playing = playing
        if playing and not was:
            self._capture.start()
        elif not playing and was:
            self._capture.stop()

    @property
    def is_active(self) -> bool:
        return self._playing and self._capture._proc is not None

    def update(self):
        if not self._playing or self._capture._proc is None:
            for i in range(self.num_bands):
                self.bands[i] *= 0.92
                if self.bands[i] < 0.005:
                    self.bands[i] = 0.0
            return

        fft = self._capture.get_fft()
        n = len(fft)

        bin_hz = self._capture.rate / self._capture.chunk
        b_lo = max(1, min(int(BASS_LO_HZ / bin_hz), n - 1))
        b_hi = max(b_lo + 1, min(int(BASS_HI_HZ / bin_hz) + 1, n))
        self.bass_power = float(np.mean(fft[b_lo:b_hi]))

        total = float(np.sum(fft[1:])) + 1e-10
        avg = total / (n - 1)

        for i in range(self.num_bands):
            lo = int((i / self.num_bands) ** 2 * n)
            hi = int(((i + 1) / self.num_bands) ** 2 * n)
            lo = max(1, min(lo, n - 1))
            hi = max(lo + 1, min(hi, n))
            band_avg = float(np.mean(fft[lo:hi]))
            target = min(1.0, band_avg / avg * 0.6)
            self._targets[i] = target
            self.bands[i] += (self._targets[i] - self.bands[i]) * self._smoothing

    def get_bands(self) -> list[float]:
        return self.bands

    def get_bass_power(self) -> float:
        return self.bass_power

    def stop(self):
        self._playing = False
        self._capture.stop()
        for i in range(self.num_bands):
            self.bands[i] = 0.0
            self._targets[i] = 0.0
