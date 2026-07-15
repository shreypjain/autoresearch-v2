| strategy | hot path does | n | p50 | p90 | p99 | max | mean | hot-path throughput |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `noop_baseline` | nothing (loop + dispatch only) | 100,000 | 214 ns | 233 ns | 392 ns | 50.42 us | 237 ns | 4,226,748/s |
| `serialize_only` | json.dumps Mezmo payload, no send | 100,000 | 3.00 us | 3.14 us | 8.65 us | 111.64 us | 3.36 us | 297,636/s |
| `local_file` | append line to local file (buffered) | 100,000 | 1.41 us | 2.30 us | 32.83 us | 1.81 ms | 2.71 us | 369,247/s |
| `async_shmem_enqueue` | enqueue to in-memory queue (drainer works off hot path) | 100,000 | 1.13 us | 2.74 us | 106.34 us | 1.32 ms | 6.30 us | 158,633/s |
| `sync_outbound` | blocking POST per update -> api.github.com (reachable HTTPS stand-in; Mezmo egress blocked in this sandbox) | 30 | 340.61 ms | 446.08 ms | 504.88 ms | 504.88 ms | 357.12 ms | 3/s |
| `sync_outbound_batched` | buffer 50, blocking POST every 50th update | 200 | 173 ns | 359 ns | 356.24 ms | 429.14 ms | 7.51 ms | 133/s |
