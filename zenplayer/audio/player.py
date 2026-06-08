import json
import os
import signal
import socket
import subprocess
import time
from pathlib import Path
from typing import Optional


class MpvPlayer:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.sock_path: Optional[str] = None
        self.sock: Optional[socket.socket] = None
        self._volume = 50
        self._paused = True
        self._duration = 0.0
        self._time_pos = 0.0

    @property
    def volume(self) -> int:
        return self._volume

    @volume.setter
    def volume(self, value: int):
        self._volume = max(0, min(100, value))
        if self.sock:
            self._send(["set_property", "volume", self._volume])

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def time_pos(self) -> float:
        return self._time_pos

    def start(self, url: str):
        self.stop()
        self.sock_path = f"/tmp/zenplayer-mpv-{os.getpid()}.sock"

        self.process = subprocess.Popen(
            [
                "mpv",
                "--no-video",
                "--audio-display=no",
                "--quiet",
                "--no-terminal",
                f"--input-ipc-server={self.sock_path}",
                f"--volume={self._volume}",
                url,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        for _ in range(20):
            if Path(self.sock_path).exists():
                break
            time.sleep(0.1)

        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.connect(self.sock_path)
            self.sock.settimeout(0.5)
            self._paused = False
        except Exception:
            self.sock = None

    def stop(self):
        if self.process:
            try:
                self.process.send_signal(signal.SIGTERM)
                self.process.wait(timeout=3)
            except Exception:
                self.process.kill()
            self.process = None
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        if self.sock_path and Path(self.sock_path).exists():
            try:
                Path(self.sock_path).unlink()
            except Exception:
                pass
        self._paused = True
        self._time_pos = 0.0
        self._duration = 0.0

    def toggle_pause(self):
        if self.sock:
            self._send(["cycle", "pause"])
            self._paused = not self._paused

    def seek(self, seconds: float):
        if self.sock:
            self._send(["seek", seconds, "relative"])

    def next_track(self):
        if self.sock:
            self._send(["playlist-next"])

    def previous_track(self):
        if self.sock:
            self._send(["playlist-prev"])

    def poll_properties(self):
        if not self.sock:
            return
        self._time_pos = self._send(["get_property", "time-pos"]) or 0.0
        dur = self._send(["get_property", "duration"])
        if dur:
            self._duration = dur

    def _send(self, command) -> Optional[any]:
        if not self.sock:
            return None
        try:
            msg = json.dumps({"command": command}) + "\n"
            self.sock.send(msg.encode())
            resp = self.sock.recv(4096).decode()
            data = json.loads(resp)
            if "error" in data and data["error"] != "success":
                return None
            return data.get("data")
        except (socket.timeout, ConnectionError, json.JSONDecodeError):
            return None
