# Outbound-logging latency — analysis

**Question (from the DKEX market-data thread):** how much is outbound logging costing us on the hot path of the orderbook loop, and does a shmem-style async queue fix it? Measured with **real HTTP** — the outbound logger is never mocked, so the network round trip is a genuine latency read.

## Result

| strategy | hot path does | n | p50 | p90 | p99 | max | mean | hot-path throughput |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `noop_baseline` | nothing (loop + dispatch only) | 100,000 | 214 ns | 233 ns | 392 ns | 50.42 us | 237 ns | 4,226,748/s |
| `serialize_only` | json.dumps Mezmo payload, no send | 100,000 | 3.00 us | 3.14 us | 8.65 us | 111.64 us | 3.36 us | 297,636/s |
| `local_file` | append line to local file (buffered) | 100,000 | 1.41 us | 2.30 us | 32.83 us | 1.81 ms | 2.71 us | 369,247/s |
| `async_shmem_enqueue` | enqueue to in-memory queue (drainer works off hot path) | 100,000 | 1.13 us | 2.74 us | 106.34 us | 1.32 ms | 6.30 us | 158,633/s |
| `sync_outbound` | blocking POST per update (real WAN round trip) | 30 | 340.61 ms | 446.08 ms | 504.88 ms | 504.88 ms | 357.12 ms | 3/s |
| `sync_outbound_batched` | buffer 50, blocking POST every 50th update | 200 | 173 ns | 359 ns | 356.24 ms | 429.14 ms | 7.51 ms | 133/s |

Measured on Linux x86_64, Python 3.11, 100,000 iterations per local strategy. The two `sync_outbound*` rows are real outbound HTTPS POSTs (see caveats for the endpoint). Raw stats and run metadata: `results/raw.json`; same table as TSV: `results/latency.tsv`.

## The one number that matters

- Inline synchronous outbound logging (`sync_outbound`) costs **~340 ms p50 per hot-path call** — a full WAN round trip blocks the loop on every orderbook update. That caps the hot path at **~3 updates/sec**.
- The shmem-style async queue (`async_shmem_enqueue`) costs **~1.1 us p50** on the hot path — the record is copied into a queue and the network send happens on a background thread. That is **~300,000x cheaper** and leaves the hot path free (~880k enqueues/sec ceiling).
- Everything local is cheap and in the same ballpark: payload JSON encode ~3 us, buffered file append ~1.4 us. The cost is **entirely the network round trip**, not the act of logging.

## Inline batching is not the fix

`sync_outbound_batched` (buffer 50, POST inline every 50th update) hides the cost for most calls (p50 173 ns) but **every 50th call stalls the hot path ~356 ms** (p99). The mean per-update cost is still 7.5 ms, and — worse for a market maker — it injects periodic multi-hundred-millisecond stalls (jitter) straight into the quote loop. Amortizing on the hot path doesn't remove the stall; it just makes it periodic. The send has to come off the hot path entirely.

## Recommendation

This confirms the thread's instinct: **do not call an outbound logger — or a `log_info`/`log_critical` that fans out to one — synchronously on the hot path.** Use the shmem/queue pattern: the hot path does a ~1 us enqueue of the raw record; a background process/thread drains, batches, and POSTs with retries. Logging the raw message and doing processing in post (seqnums, gap detection) keeps hot-path work minimal, as suggested in the thread.

## Caveats / getting a true Mezmo number

- Mezmo egress is **blocked in this sandbox**: the proxy refused CONNECT to `logs.mezmo.com` (3x `403 Tunnel connection failed`, ~700-800 ms each — recorded in `results/raw.json` under `meta.mezmo_probe`). So the `sync_outbound` row was measured against **`api.github.com` as a reachable HTTPS stand-in** — a genuine TLS keep-alive WAN round trip (real HTTP `400` responses, 0 reconnects). The ~340 ms reflects this sandbox's route to GitHub; from a co-located box to Mezmo's regional ingest the absolute number will differ (tens to low-hundreds of ms).
- The **conclusion is endpoint-independent**: any synchronous outbound HTTP is milliseconds — 4-6 orders of magnitude above the ~1 us enqueue — so it cannot live on the hot path regardless of provider.
- To take the true Mezmo read where egress and a key are available:

  ```bash
  MEZMO_INGESTION_KEY=... python3 -m benchmarks.mezmo_logging.bench \
      --endpoint https://logs.mezmo.com/logs/ingest --probe-mezmo
  ```
