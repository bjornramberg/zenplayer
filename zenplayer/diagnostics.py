import os
import sys
import threading
import time
import traceback

from zenplayer import nonblocking_output

LOG_PATH = os.environ.get("ZENPLAYER_LOG", "/tmp/zenplayer-stats.log")
STACK_PATH = os.environ.get("ZENPLAYER_STACK", "/tmp/zenplayer-stall.log")
STALL_SECONDS = 1.5
INTERVAL = 5.0

_lock = threading.Lock()
_ticks = 0
_ticks_last = 0.0
_bass = 0
_bass_last = 0.0
_started = time.monotonic()
_thread = None
_state = {}
_last_stall_dump = 0.0
_MAIN_ID = threading.main_thread().ident


def set_state(**kw) -> None:
    global _state
    with _lock:
        _state = dict(kw)


def log_line(msg: str) -> None:
    try:
        with open(LOG_PATH, "a") as f:
            f.write("T %10.3f %s\n" % (time.monotonic() - _started, msg))
    except Exception:
        pass


def mark_tick() -> None:
    global _ticks, _ticks_last
    with _lock:
        _ticks += 1
        _ticks_last = time.monotonic()


def mark_set_bass() -> None:
    global _bass, _bass_last
    with _lock:
        _bass += 1
        _bass_last = time.monotonic()


def _decode_meta(meta):
    if meta is None:
        return None
    if isinstance(meta, bytes):
        try:
            import pickle
            return pickle.loads(meta)
        except Exception:
            return None
    if isinstance(meta, str):
        try:
            import json
            return json.loads(meta)
        except Exception:
            return None
    return meta


def _segment_stats(segments):
    total = 0
    with_meta = 0
    meta_sample = None
    for seg in segments:
        total += 1
        style = seg[1] if isinstance(seg, tuple) and len(seg) > 1 else None
        meta = getattr(style, "_meta", None)
        if meta is not None:
            if with_meta == 0:
                meta_sample = str(_decode_meta(meta))[:200]
            with_meta += 1
    return total, with_meta, meta_sample


def _frame_context(frame) -> list:
    rows = []
    f = frame
    prev = None
    while f is not None:
        try:
            mod = f.f_globals.get("__name__", "")
            name = f.f_code.co_name
            if mod == "textual.screen" and name == "_forward_event":
                event = f.f_locals.get("event")
                if event is not None:
                    row = (
                        "event: %s at (%s,%s)"
                        % (
                            type(event).__name__,
                            getattr(event, "screen_x", "?"),
                            getattr(event, "screen_y", "?"),
                        )
                    )
                    if row != prev:
                        rows.append(row)
                        prev = row
            elif mod == "textual.widget" and name in ("render_line", "_render_content"):
                self_ = f.f_locals.get("self")
                if self_ is not None:
                    dirty = len(getattr(self_, "_dirty_regions", ()) or ())
                    row = (
                        "widget: %s.%s size=%s dirty=%d"
                        % (
                            type(self_).__module__,
                            type(self_).__name__,
                            getattr(self_, "size", "?"),
                            dirty,
                        )
                    )
                    if row != prev:
                        rows.append(row)
                        prev = row
            elif mod == "textual.strip" and name == "_apply_link_style":
                segments = f.f_locals.get("segments")
                if segments is not None:
                    total, with_meta, meta_sample = _segment_stats(segments)
                    row = (
                        "segments: total=%d with_meta=%d meta_sample=%r"
                        % (total, with_meta, meta_sample)
                    )
                    if row != prev:
                        rows.append(row)
                        prev = row
            elif mod == "textual.visual" and name == "to_strips":
                strips = f.f_locals.get("strips")
                if strips is not None:
                    row = "strips: %d lines" % len(strips)
                    if row != prev:
                        rows.append(row)
                        prev = row
        except Exception:
            pass
        f = f.f_back
    return rows


def _dump_main_stack(reason: str) -> None:
    global _last_stall_dump
    now = time.monotonic()
    if now - _last_stall_dump < INTERVAL:
        return
    _last_stall_dump = now
    try:
        frames = sys._current_frames()
        frame = frames.get(_MAIN_ID)
        if frame is None:
            return
        stack = "".join(
            traceback.format_stack(frame, limit=30)
        )
        with open(STACK_PATH, "w") as f:
            f.write("=== stall at t=%6.1fs (%s) tick=%d bass=%d\n"
                    % (now - _started, reason, _ticks, _bass))
            f.write(stack)
            f.write("=== context ===\n")
            for row in _frame_context(frame):
                f.write("  " + row + "\n")
            f.write("=== state: %r\n" % _state)
    except Exception:
        pass


def _snapshot() -> None:
    with _lock:
        ticks = _ticks
        tick_last = _ticks_last
        bass = _bass
        bass_last = _bass_last
        state = _state
    st = nonblocking_output.stats()
    now = time.monotonic()
    dt = max(now - _started, 0.001)
    drain_gap = now - st["last_drain_at"] if st["last_drain_at"] else -1.0
    tick_gap = now - tick_last
    if tick_gap > STALL_SECONDS:
        _dump_main_stack("tick gap %.1fs" % tick_gap)
    line = (
        "t=%6.1fs ticks=%5d (%5.1f/s) tick_gap=%7.3fs bass=%5d (%5.1f/s) "
        "bass_gap=%7.3fs queue=%2d items=%6d bytes=%8d drops=%4d "
        "drain_gap=%7.3fs state=%s\n"
        % (
            dt,
            ticks,
            ticks / dt,
            now - tick_last,
            bass,
            bass / dt,
            now - bass_last,
            nonblocking_output.qsize(),
            st["items"],
            st["bytes_enqueued"],
            st["drops"],
            drain_gap,
            {k: state.get(k) for k in ("playing", "focus", "screen", "active")},
        )
    )
    try:
        with open(LOG_PATH, "a") as f:
            f.write(line)
    except Exception:
        pass


def _loop() -> None:
    while True:
        time.sleep(INTERVAL)
        try:
            _snapshot()
        except Exception:
            pass


def start() -> None:
    global _thread
    if _thread is not None:
        return
    _thread = threading.Thread(target=_loop, daemon=True, name="zenplayer-stats")
    _thread.start()
