import queue
import threading
import time

from textual.drivers import _writer_thread as wt

_lock = threading.Lock()
_drops = 0
_items = 0
_bytes_enqueued = 0
_last_drain_at = 0.0
_active_thread: "wt.WriterThread | None" = None
_installed = False

WRITE_TIMEOUT = 2.0


def drop_count() -> int:
    with _lock:
        return _drops


def consume_drops() -> int:
    global _drops
    with _lock:
        seen = _drops
        _drops = 0
    return seen


def stats() -> dict:
    with _lock:
        return {
            "drops": _drops,
            "items": _items,
            "bytes_enqueued": _bytes_enqueued,
            "last_drain_at": _last_drain_at,
        }


def qsize() -> int:
    thread = _active_thread
    return thread._queue.qsize() if thread is not None else 0


def full() -> bool:
    """True when the output queue is sitting at capacity (terminal stalled)."""
    thread = _active_thread
    return thread is not None and thread._queue.full()


def _tracking_write(self, text: str) -> None:
    global _drops, _items, _bytes_enqueued, _active_thread
    try:
        self._queue.put_nowait(text)
    except queue.Full:
        with _lock:
            _drops += 1
            _active_thread = self
        return
    with _lock:
        _items += 1
        _bytes_enqueued += len(text)
        _active_thread = self


def _tracking_run(self) -> None:
    global _last_drain_at
    write = self._file.write
    flush = self._file.flush
    get = self._queue.get
    qsize = self._queue.qsize
    while True:
        text: str | None = get()
        if text is None:
            break
        write(text)
        with _lock:
            _last_drain_at = time.monotonic()
        if qsize() == 0:
            flush()
    flush()


def _nonblocking_stop(self) -> None:
    t0 = time.monotonic()
    try:
        self._queue.put(None, timeout=0.5)
    except queue.Full:
        pass
    t1 = time.monotonic()
    self.join(timeout=WRITE_TIMEOUT)
    t2 = time.monotonic()
    if t2 - t0 > 0.05:
        from zenplayer import diagnostics

        diagnostics.log_line("writer.stop: put=%.3fs join=%.3fs" % (t1 - t0, t2 - t1))


def install() -> None:
    global _installed
    if _installed:
        return
    wt.WriterThread.write = _tracking_write
    wt.WriterThread.run = _tracking_run
    wt.WriterThread.stop = _nonblocking_stop
    _installed = True
