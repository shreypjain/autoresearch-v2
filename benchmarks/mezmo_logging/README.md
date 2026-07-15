---
kind: benchmark
status: complete
name: mezmo-logging-latency
summary: Real-HTTP load test measuring the hot-path latency cost of outbound (Mezmo) logging vs an async shmem-style queue for orderbook updates.
tags: [logging, latency, mezmo, load-test, hot-path]
---

# Mezmo outbound-logging latency benchmark

A self-contained, dependency-free (stdlib-only) load test that measures how much
**outbound logging costs on the hot path** of a high-frequency market-data loop
(orderbook updates), using **real HTTP** — the outbound logger is never mocked,
so the network round-trip is a genuine latency read.

It exists to answer a concrete question from the DKEX market-data thread: *is
calling the logger inline on the hot path slowing us down, and does moving to a
shmem-style async queue fix it?*

## Strategies compared

| strategy | what the hot path does |
|---|---|
| `noop_baseline` | nothing — loop + dispatch overhead only |
| `serialize_only` | build the Mezmo JSON payload, no I/O |
| `local_file` | append the line to a local file (buffered) |
| `async_shmem_enqueue` | push the record onto an in-memory queue; a background thread drains + sends (the proposed shmem / quote-server pattern) |
| `sync_outbound` | blocking HTTP POST to the ingest endpoint **per update** (log_info/log_critical inline) |
| `sync_outbound_batched` | buffer N updates, blocking POST every Nth |

## Running it

From the repo root:

```bash
# True Mezmo read (needs egress to logs.mezmo.com + a key):
MEZMO_INGESTION_KEY=xxxxxxxx python3 -m benchmarks.mezmo_logging.bench \
    --endpoint https://logs.mezmo.com/logs/ingest

# Against any reachable HTTPS endpoint as a WAN round-trip stand-in:
python3 -m benchmarks.mezmo_logging.bench \
    --endpoint https://api.github.com/ \
    --label "api.github.com (reachable HTTPS stand-in)"

# Local strategies only (no network):
python3 -m benchmarks.mezmo_logging.bench --skip-network
```

Nothing is mocked: `OutboundLogClient` opens a real TLS connection (honoring
`HTTPS_PROXY` and the CA bundle) and issues a real POST. Point `--endpoint` at
Mezmo with a key for a true read; any HTTPS POST target works as a stand-in for
the network cost when Mezmo egress isn't available.

## Output

Artifacts are written to `results/`:
- `latency.md` — the tabular latency comparison
- `latency.tsv` — same numbers, tab-separated
- `raw.json` — full stats + run metadata

See `ANALYSIS.md` for the interpreted results and the take-away for hot-path logging.
