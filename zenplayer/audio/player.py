import json
import os
import queue
import socket
import subprocess
import threading
import time
from itertools import count
from pathlib import Path
from typing import Callable, Optional

POLL_INTERVAL = 0.25
SOCKET_WAIT = 5.0
RECV_TIMEOUT = 0.25

MPV_LOG_DIR = Path.home() / ".cache" / "zenplayer"
MPV_LOG_FILE = MPV_LOG_DIR / "mpv.log"


class MpvPlayer:
    def __init__(self, volume: int = 50):
        self.process: Optional[subprocess.Popen] = None
        self.sock_path: Optional[str] = None
        self._lock = threading.Lock()
        self._volume = volume
        self._paused = True
        self._duration = 0.0
        self._time_pos = 0.0
        self._cmd_queue: "queue.Queue[Optional[tuple]]" = queue.Queue()
        self._stop_evt = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._sock: Optional[socket.socket] = None
        self._next_id = count(1)
        # Diagnostic state (polled by IO loop)
        self._idle = True
        self._core_idle = True
        self._paused_for_cache = False
        self._eof_reached = False

    @property
    def log_path(self) -> str:
        return str(MPV_LOG_FILE)

    def get_diagnostics(self) -> dict:
        """Return diagnostic state polled by the IO loop (thread-safe)."""
        with self._lock:
            return {
                "idle-active": self._idle,
                "paused-for-cache": self._paused_for_cache,
                "eof-reached": self._eof_reached,
                "duration": self._duration,
            }

    @property
    def volume(self) -> int:
        with self._lock:
            return self._volume

    @volume.setter
    def volume(self, value: int):
        value = max(0, min(100, int(value)))
        with self._lock:
            self._volume = value
        self._enqueue(["set_property", "volume", value])

    @property
    def paused(self) -> bool:
        with self._lock:
            return self._paused

    @property
    def duration(self) -> float:
        with self._lock:
            return self._duration

    @property
    def time_pos(self) -> float:
        with self._lock:
            return self._time_pos

    def start(self, url: str):
        self.stop()
        self.sock_path = f"/tmp/zenplayer-mpv-{os.getpid()}.sock"

        MPV_LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.process = subprocess.Popen(
            [
                "mpv",
                "--no-video",
                "--audio-display=no",
                f"--log-file={MPV_LOG_FILE}",
                f"--input-ipc-server={self.sock_path}",
                f"--volume={self._volume}",
                url,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with self._lock:
            self._paused = False
        self._start_thread()

    def stop(self):
        self._stop_thread()
        proc = self.process
        self.process = None
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
            threading.Thread(target=self._reap, args=(proc,), daemon=True).start()
        if self.sock_path:
            try:
                Path(self.sock_path).unlink()
            except Exception:
                pass
        with self._lock:
            self._paused = True
            self._time_pos = 0.0
            self._duration = 0.0
            self._idle = True
            self._core_idle = True
            self._paused_for_cache = False
            self._eof_reached = False

    @staticmethod
    def _reap(proc: subprocess.Popen):
        try:
            proc.wait(timeout=2)
        except Exception:
            pass
        try:
            if proc.poll() is None:
                proc.kill()
        except Exception:
            pass

    def _start_thread(self):
        self._stop_thread()
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._io_loop, daemon=True)
        self._thread.start()

    def _stop_thread(self):
        self._stop_evt.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)
        self._thread = None
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def toggle_pause(self):
        self._enqueue(["cycle", "pause"])

    def seek(self, seconds: float):
        self._enqueue(["seek", seconds, "relative"])

    def seek_to(self, position: float):
        """Seek to an absolute position in seconds."""
        self._enqueue(["seek", max(0, position), "absolute"])

    def next_track(self):
        self._enqueue(["playlist-next"])

    def previous_track(self):
        self._enqueue(["playlist-prev"])

    def poll_properties(self):
        # Values are maintained by the background thread; kept for API compat.
        return

    def _enqueue(self, command: list) -> None:
        self._cmd_queue.put((command, None))

    def _io_loop(self):
        path = self.sock_path
        if not path:
            return

        deadline = time.time() + SOCKET_WAIT
        while not self._stop_evt.is_set() and time.time() < deadline:
            if Path(path).exists():
                break
            time.sleep(0.05)
        if self._stop_evt.is_set() or not Path(path).exists():
            return

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(RECV_TIMEOUT)
        try:
            sock.connect(path)
        except Exception:
            try:
                sock.close()
            except Exception:
                pass
            return
        self._sock = sock

        # Ensure mpv is not paused after IPC connects
        self._cmd_queue.put((["set_property", "pause", False], None))

        pending: dict[int, Optional[Callable]] = {}
        buf = b""
        last_poll = 0.0
        try:
            while not self._stop_evt.is_set():
                now = time.time()
                poll_pending = any(h is not None for h in pending.values())
                if now - last_poll >= POLL_INTERVAL and not poll_pending:
                    last_poll = now
                    for prop, handler in (
                        ("time-pos", self._on_time_pos),
                        ("duration", self._on_duration),
                        ("pause", self._on_pause),
                        ("volume", self._on_volume),
                        ("idle-active", self._on_idle),
                        ("core-idle", self._on_core_idle),
                        ("paused-for-cache", self._on_paused_for_cache),
                        ("eof-reached", self._on_eof_reached),
                    ):
                        self._cmd_queue.put((["get_property", prop], handler))

                while True:
                    try:
                        command, handler = self._cmd_queue.get_nowait()
                    except queue.Empty:
                        break
                    if command is None:
                        return
                    req_id = next(self._next_id)
                    pending[req_id] = handler
                    self._send(sock, req_id, command)

                try:
                    chunk = sock.recv(4096)
                except socket.timeout:
                    continue
                if chunk == b"":
                    break
                buf += chunk
                while b"\n" in buf:
                    line, _, buf = buf.partition(b"\n")
                    self._handle_line(line, pending)
        finally:
            pending.clear()
            try:
                sock.close()
            except Exception:
                pass
            self._sock = None

    def _send(self, sock: socket.socket, req_id: int, command: list) -> None:
        msg = json.dumps({"command": command, "request_id": req_id}) + "\n"
        sock.sendall(msg.encode())

    def _handle_line(self, line: bytes, pending: dict) -> None:
        try:
            data = json.loads(line)
        except Exception:
            return
        req_id = data.get("request_id")
        if req_id is None or req_id not in pending:
            return
        handler = pending.pop(req_id)
        if handler is not None:
            try:
                handler(data.get("data"))
            except Exception:
                pass

    def _on_time_pos(self, value):
        with self._lock:
            self._time_pos = float(value) if value is not None else 0.0

    def _on_duration(self, value):
        if value:
            with self._lock:
                self._duration = float(value)

    def _on_pause(self, value):
        if value is not None:
            with self._lock:
                self._paused = bool(value)

    def _on_volume(self, value):
        if value is not None:
            with self._lock:
                self._volume = int(value)

    def _on_idle(self, value):
        if value is not None:
            with self._lock:
                self._idle = bool(value)

    def _on_core_idle(self, value):
        if value is not None:
            with self._lock:
                self._core_idle = bool(value)

    def _on_paused_for_cache(self, value):
        if value is not None:
            with self._lock:
                self._paused_for_cache = bool(value)

    def _on_eof_reached(self, value):
        if value is not None:
            with self._lock:
                self._eof_reached = bool(value)
