"""Real outbound log client used by the latency benchmark.

Nothing in this module is mocked: ``OutboundLogClient.post`` opens a genuine
TLS connection and issues a real HTTP POST. Point it at Mezmo's ingest API
(``https://logs.mezmo.com/logs/ingest`` with a ``MEZMO_INGESTION_KEY``) for a
true Mezmo latency read, or at any HTTPS endpoint that accepts a POST as a
reachable stand-in for the network round-trip cost.
"""
from __future__ import annotations

import base64
import http.client
import json
import os
import ssl
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

DEFAULT_MEZMO_ENDPOINT = "https://logs.mezmo.com/logs/ingest"


@dataclass
class PostResult:
    ok: bool
    status: int
    elapsed_ns: int
    reconnected: bool = False
    error: str | None = None


def _default_ca_bundle() -> str | None:
    for candidate in (
        os.environ.get("REQUESTS_CA_BUNDLE"),
        os.environ.get("SSL_CERT_FILE"),
        "/root/.ccr/ca-bundle.crt",
    ):
        if candidate and os.path.exists(candidate):
            return candidate
    return None


class OutboundLogClient:
    """Keep-alive HTTPS client that POSTs log batches to an ingest endpoint."""

    def __init__(
        self,
        endpoint: str,
        ingestion_key: str | None = None,
        hostname: str = "autoresearch-bench",
        timeout: float = 15.0,
        ca_bundle: str | None = None,
    ) -> None:
        parsed = urlparse(endpoint)
        if parsed.scheme != "https":
            raise ValueError(f"endpoint must be https://, got {endpoint!r}")
        self.endpoint = endpoint
        self.host = parsed.hostname or ""
        self.port = parsed.port or 443
        self.path = parsed.path or "/"
        self.query = parsed.query
        self.ingestion_key = ingestion_key
        self.hostname = hostname
        self.timeout = timeout
        self._ca_bundle = ca_bundle if ca_bundle is not None else _default_ca_bundle()
        self._ctx = ssl.create_default_context(cafile=self._ca_bundle)
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        self._proxy = urlparse(proxy) if proxy else None
        self._conn: http.client.HTTPSConnection | None = None
        self.reconnects = 0

    def _new_connection(self) -> http.client.HTTPSConnection:
        if self._proxy and self._proxy.hostname:
            conn = http.client.HTTPSConnection(
                self._proxy.hostname, self._proxy.port or 80,
                timeout=self.timeout, context=self._ctx,
            )
            conn.set_tunnel(self.host, self.port)
        else:
            conn = http.client.HTTPSConnection(
                self.host, self.port, timeout=self.timeout, context=self._ctx,
            )
        return conn

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "autoresearch-logbench/1.0",
        }
        if self.ingestion_key:
            token = base64.b64encode(f"{self.ingestion_key}:".encode()).decode()
            headers["Authorization"] = f"Basic {token}"
        return headers

    def _full_path(self) -> str:
        q = f"hostname={self.hostname}&now=0"
        if self.query:
            q = f"{self.query}&{q}"
        return f"{self.path}?{q}"

    def post(self, lines: list[dict[str, Any]]) -> PostResult:
        body = json.dumps({"lines": lines}).encode("utf-8")
        headers = self._headers()
        path = self._full_path()
        reconnected = False
        start = time.perf_counter_ns()
        try:
            if self._conn is None:
                self._conn = self._new_connection()
                reconnected = True
            try:
                self._conn.request("POST", path, body=body, headers=headers)
                resp = self._conn.getresponse()
                status = resp.status
                resp.read()
            except (http.client.HTTPException, ConnectionError, OSError):
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = self._new_connection()
                self.reconnects += 1
                reconnected = True
                self._conn.request("POST", path, body=body, headers=headers)
                resp = self._conn.getresponse()
                status = resp.status
                resp.read()
            elapsed = time.perf_counter_ns() - start
            if resp.getheader("Connection", "").lower() == "close":
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None
            return PostResult(
                ok=200 <= status < 300, status=status,
                elapsed_ns=elapsed, reconnected=reconnected,
            )
        except Exception as exc:  # proxy CONNECT refusal / TLS / timeout — real timing
            elapsed = time.perf_counter_ns() - start
            self._conn = None
            return PostResult(
                ok=False, status=0, elapsed_ns=elapsed,
                reconnected=reconnected, error=f"{type(exc).__name__}: {exc}",
            )

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
