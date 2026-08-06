import subprocess
import threading
import numpy as np


class AudioCapture:
    def __init__(self, rate=48000, chunk=2048):
        self.rate = rate
        self.chunk = chunk
        self._proc = None
        self._buffer = np.zeros(chunk, dtype=np.float32)
        self._window = np.hanning(chunk)
        self._running = False
        self._thread = None
        self._source = None

    def _get_monitor(self) -> str:
        try:
            sink = subprocess.run(
                ["pactl", "get-default-sink"],
                capture_output=True, text=True, timeout=3
            ).stdout.strip()
            if sink:
                return f"{sink}.monitor"
        except Exception:
            pass
        return ""

    def start(self):
        if self._running:
            return
        self._source = self._get_monitor()
        if not self._source:
            return

        try:
            self._proc = subprocess.Popen(
                [
                    "parec",
                    "--raw",
                    f"--format=float32le",
                    f"--rate={self.rate}",
                    "--channels=1",
                    f"--latency-msec=50",
                    "-d", self._source,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            self._proc = None
            return

        self._running = True
        self._buffer.fill(0.0)
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self):
        while self._running and self._proc and self._proc.stdout:
            try:
                raw = self._proc.stdout.read(self.chunk * 4)
                if not raw:
                    break
                data = np.frombuffer(raw, dtype=np.float32)
                if len(data) == 0:
                    continue
                shift = min(len(data), self.chunk)
                self._buffer = np.roll(self._buffer, -shift)
                self._buffer[-shift:] = data[-shift:]
            except Exception:
                break

    def get_fft(self) -> np.ndarray:
        windowed = self._buffer * self._window
        spectrum = np.abs(np.fft.rfft(windowed))
        return spectrum

    def stop(self):
        self._running = False
        proc = self._proc
        if proc is not None:
            try:
                proc.terminate()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=1)
            self._thread = None
        if proc is not None:
            try:
                proc.wait(timeout=1)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        self._proc = None
        self._buffer.fill(0.0)
