"""Logging strategies compared by the benchmark.

Each strategy exposes the same ``hot_path(record)`` call — the thing invoked
once per orderbook update, whose latency steals time from the trading strategy.
"""
from __future__ import annotations

import json
import os
import queue
import threading
from typing import Any

from .mezmo_client import OutboundLogClient, PostResult


def make_orderbook_line(seq: int) -> dict[str, Any]:
    """A representative orderbook-update log line the hot path would emit."""
    payload = {
        "seq": seq,
        "sym": "DKEX-PERP",
        "ts": seq,
        "bids": [[10000 + (seq % 7), 5 + (seq % 3)], [9999, 12], [9998, 30]],
        "asks": [[10001 + (seq % 5), 4 + (seq % 4)], [10002, 9], [10003, 21]],
    }
    return {"line": json.dumps(payload), "app": "orderbook", "level": "INFO", "timestamp": seq}


class Sink:
    """Destination for a batch of log lines."""

    def send(self, batch: list[dict[str, Any]]) -> PostResult | None:
        raise NotImplementedError

    def close(self) -> None:
        pass


class NullSink(Sink):
    """Discard — isolates loop/dispatch overhead (the noop baseline)."""

    def send(self, batch):
        return None


class SerializeSink(Sink):
    """Encode the Mezmo JSON payload but do not transmit — isolates encode cost."""

    def send(self, batch):
        json.dumps({"lines": batch}).encode("utf-8")
        return None


class FileSink(Sink):
    """Append log lines to a local file (the drain-to-disk alternative)."""

    def __init__(self, path: str, fsync: bool = False) -> None:
        self._fh = open(path, "a", encoding="utf-8")
        self._fsync = fsync

    def send(self, batch):
        for record in batch:
            self._fh.write(record["line"])
            self._fh.write("\n")
        self._fh.flush()
        if self._fsync:
            os.fsync(self._fh.fileno())
        return None

    def close(self):
        try:
            self._fh.close()
        except Exception:
            pass


class NetworkSink(Sink):
    """Real outbound POST to the ingest endpoint (Mezmo or a reachable stand-in)."""

    def __init__(self, client: OutboundLogClient) -> None:
        self.client = client
        self.results: list[PostResult] = []

    def send(self, batch):
        result = self.client.post(batch)
        self.results.append(result)
        return result

    def close(self):
        self.client.close()


class Strategy:
    name = "base"

    def start(self) -> None:
        ...

    def hot_path(self, record: dict[str, Any]) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        ...

    def info(self) -> dict[str, Any]:
        return {}


class InlineStrategy(Strategy):
    """Do the logging synchronously on the hot path.

    batch_size=1 models per-call synchronous logging (log_info/log_critical
    inline). batch_size>1 models inline batching: the hot path buffers and pays
    the full sink cost every Nth call.
    """

    def __init__(self, name: str, sink: Sink, batch_size: int = 1) -> None:
        self.name = name
        self.sink = sink
        self.batch_size = batch_size
        self._buf: list[dict[str, Any]] = []
        self.flushes = 0

    def hot_path(self, record):
        self._buf.append(record)
        if len(self._buf) >= self.batch_size:
            self.sink.send(self._buf)
            self.flushes += 1
            self._buf = []

    def stop(self):
        if self._buf:
            self.sink.send(self._buf)
            self.flushes += 1
            self._buf = []
        self.sink.close()

    def info(self):
        data: dict[str, Any] = {"flushes": self.flushes, "batch_size": self.batch_size}
        if isinstance(self.sink, NetworkSink) and self.sink.results:
            data["reconnects"] = self.sink.client.reconnects
            data["statuses"] = _status_hist(self.sink.results)
            errs = sorted({r.error for r in self.sink.results if r.error})
            if errs:
                data["errors"] = errs
        return data


class AsyncQueueStrategy(Strategy):
    """shmem / quote-server analog: the hot path only enqueues.

    A background thread drains the queue and hands batches to the sink, so the
    network (or disk) cost lives entirely off the hot path. This is the pattern
    proposed in the thread.
    """

    def __init__(self, name: str, sink: Sink, batch_size: int = 500,
                 maxsize: int = 0, drain_timeout: float = 0.05) -> None:
        self.name = name
        self.sink = sink
        self.batch_size = batch_size
        self.drain_timeout = drain_timeout
        self._q: queue.Queue = queue.Queue(maxsize=maxsize)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.enqueued = 0
        self.dropped = 0
        self.drained = 0
        self.max_depth = 0

    def start(self):
        self._thread = threading.Thread(target=self._drain, name=f"{self.name}-drain", daemon=True)
        self._thread.start()

    def hot_path(self, record):
        try:
            self._q.put_nowait(record)
            self.enqueued += 1
        except queue.Full:
            # In production this is a shmem ring-buffer overwrite or backpressure.
            self.dropped += 1

    def _drain(self):
        buf: list[dict[str, Any]] = []
        while not (self._stop.is_set() and self._q.empty()):
            try:
                buf.append(self._q.get(timeout=self.drain_timeout))
            except queue.Empty:
                if buf:
                    self.sink.send(buf)
                    self.drained += len(buf)
                    buf = []
                continue
            depth = self._q.qsize()
            if depth > self.max_depth:
                self.max_depth = depth
            if len(buf) >= self.batch_size:
                self.sink.send(buf)
                self.drained += len(buf)
                buf = []
        if buf:
            self.sink.send(buf)
            self.drained += len(buf)

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=60)
        self.sink.close()

    def info(self):
        return {
            "enqueued": self.enqueued, "dropped": self.dropped,
            "drained": self.drained, "max_queue_depth": self.max_depth,
            "batch_size": self.batch_size,
        }


def _status_hist(results: list[PostResult]) -> dict[str, int]:
    hist: dict[str, int] = {}
    for r in results:
        key = str(r.status)
        hist[key] = hist.get(key, 0) + 1
    return hist
