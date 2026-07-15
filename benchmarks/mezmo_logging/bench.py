"""Outbound-logging latency benchmark.

Measures the hot-path cost of several logging strategies for high-frequency
market-data (orderbook) updates using REAL outbound HTTP (no mocking), and
writes a simple tabular latency analysis.

Run from the repo root:
    python3 -m benchmarks.mezmo_logging.bench --help
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import time
from pathlib import Path
from typing import Any

from .mezmo_client import DEFAULT_MEZMO_ENDPOINT, OutboundLogClient
from .strategies import (
    AsyncQueueStrategy, FileSink, InlineStrategy, NetworkSink, NullSink,
    SerializeSink, Strategy, make_orderbook_line,
)

NS_PER_US = 1_000.0
NS_PER_MS = 1_000_000.0


def _percentile(sorted_ns: list[int], p: float) -> int:
    if not sorted_ns:
        return 0
    if len(sorted_ns) == 1:
        return sorted_ns[0]
    k = int(round((p / 100.0) * (len(sorted_ns) - 1)))
    k = max(0, min(len(sorted_ns) - 1, k))
    return sorted_ns[k]


def summarize(latencies_ns: list[int]) -> dict[str, Any]:
    s = sorted(latencies_ns)
    n = len(s)
    total = sum(s)
    mean = total / n if n else 0.0
    return {
        "n": n,
        "mean_us": mean / NS_PER_US,
        "p50_us": _percentile(s, 50) / NS_PER_US,
        "p90_us": _percentile(s, 90) / NS_PER_US,
        "p99_us": _percentile(s, 99) / NS_PER_US,
        "max_us": (s[-1] if s else 0) / NS_PER_US,
        "min_us": (s[0] if s else 0) / NS_PER_US,
        "throughput_ops_s": (1e9 / mean) if mean else 0.0,
    }


def run_strategy(strategy: Strategy, records: list[dict[str, Any]], warmup: int) -> list[int]:
    strategy.start()
    pc = time.perf_counter_ns
    for i in range(min(max(warmup, 0), len(records))):
        strategy.hot_path(records[i])
    latencies: list[int] = []
    append = latencies.append
    for record in records:
        t0 = pc()
        strategy.hot_path(record)
        append(pc() - t0)
    strategy.stop()
    return latencies


def build_records(n: int) -> list[dict[str, Any]]:
    return [make_orderbook_line(i) for i in range(n)]


def _unit(us: float) -> str:
    if us >= 1000:
        return f"{us / 1000:.2f} ms"
    if us >= 1:
        return f"{us:.2f} us"
    return f"{us * 1000:.0f} ns"


def write_reports(rows: list[dict[str, Any]], meta: dict[str, Any], out_dir: Path) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    tsv_cols = ["strategy", "hot_path", "n", "p50_us", "p90_us", "p99_us",
                "max_us", "mean_us", "throughput_ops_s"]
    tsv_lines = ["\t".join(tsv_cols)]
    for r in rows:
        cells = []
        for c in tsv_cols:
            if c in ("strategy", "hot_path", "n"):
                cells.append(str(r[c]))
            else:
                cells.append(f"{r[c]:.4f}")
        tsv_lines.append("\t".join(cells))
    (out_dir / "latency.tsv").write_text("\n".join(tsv_lines) + "\n", encoding="utf-8")

    md = ["| strategy | hot path does | n | p50 | p90 | p99 | max | mean | hot-path throughput |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        md.append(
            "| `{s}` | {d} | {n:,} | {p50} | {p90} | {p99} | {mx} | {mean} | {tp:,.0f}/s |".format(
                s=r["strategy"], d=r["hot_path"], n=r["n"],
                p50=_unit(r["p50_us"]), p90=_unit(r["p90_us"]), p99=_unit(r["p99_us"]),
                mx=_unit(r["max_us"]), mean=_unit(r["mean_us"]), tp=r["throughput_ops_s"],
            )
        )
    table = "\n".join(md)
    (out_dir / "latency.md").write_text(table + "\n", encoding="utf-8")
    (out_dir / "raw.json").write_text(
        json.dumps({"meta": meta, "rows": rows}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return table


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Outbound-logging latency benchmark (real HTTP, no mocking).")
    parser.add_argument("--endpoint", default=os.environ.get("BENCH_LOG_ENDPOINT", DEFAULT_MEZMO_ENDPOINT),
                        help="HTTPS ingest endpoint for network strategies (default: Mezmo ingest).")
    parser.add_argument("--ingestion-key", default=os.environ.get("MEZMO_INGESTION_KEY"),
                        help="Mezmo ingestion key (basic-auth username). Env: MEZMO_INGESTION_KEY.")
    parser.add_argument("--mezmo-endpoint", default=DEFAULT_MEZMO_ENDPOINT,
                        help="Endpoint used only for the reachability probe.")
    parser.add_argument("--local-iters", type=int, default=100_000,
                        help="Iterations for local (non-network) strategies.")
    parser.add_argument("--net-iters", type=int, default=30,
                        help="Real network round-trips for the sync strategy.")
    parser.add_argument("--net-batch", type=int, default=50,
                        help="Batch size for the inline-batched network strategy.")
    parser.add_argument("--warmup", type=int, default=200,
                        help="Warmup iterations for local strategies (not measured).")
    parser.add_argument("--net-warmup", type=int, default=2,
                        help="Warmup posts for network strategies (dropped from stats).")
    parser.add_argument("--async-batch", type=int, default=500,
                        help="Drain batch size for the async/shmem strategy.")
    parser.add_argument("--out-dir", default=str(Path(__file__).parent / "results"),
                        help="Directory for report artifacts.")
    parser.add_argument("--label", default=None,
                        help="Label describing the network endpoint for the report.")
    parser.add_argument("--skip-network", action="store_true",
                        help="Skip real outbound strategies (local only).")
    parser.add_argument("--probe-mezmo", action="store_true",
                        help="Add a reachability probe against --mezmo-endpoint.")
    args = parser.parse_args(argv)

    rows: list[dict[str, Any]] = []
    meta: dict[str, Any] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "endpoint": args.endpoint,
        "endpoint_label": args.label or args.endpoint,
        "ingestion_key_present": bool(args.ingestion_key),
        "local_iters": args.local_iters,
        "net_iters": args.net_iters,
        "net_batch": args.net_batch,
        "async_batch": args.async_batch,
    }
    out_dir = Path(args.out_dir)

    def add_row(name: str, desc: str, latencies: list[int], info: dict[str, Any]) -> None:
        summary = summarize(latencies)
        rows.append({"strategy": name, "hot_path": desc, **summary, "info": info})
        print(f"  {name:24s} n={summary['n']:>7d} "
              f"p50={_unit(summary['p50_us']):>10s} p99={_unit(summary['p99_us']):>10s} "
              f"max={_unit(summary['max_us']):>10s} thrpt={summary['throughput_ops_s']:>14,.0f}/s")

    print(f"[local] {args.local_iters:,} iters/strategy ...")
    local_records = build_records(args.local_iters)

    s = InlineStrategy("noop_baseline", NullSink())
    add_row("noop_baseline", "nothing (loop + dispatch only)",
            run_strategy(s, local_records, args.warmup), s.info())

    s = InlineStrategy("serialize_only", SerializeSink())
    add_row("serialize_only", "json.dumps Mezmo payload, no send",
            run_strategy(s, local_records, args.warmup), s.info())

    log_path = out_dir / "bench_local.log"
    out_dir.mkdir(parents=True, exist_ok=True)
    s = InlineStrategy("local_file", FileSink(str(log_path)))
    add_row("local_file", "append line to local file (buffered)",
            run_strategy(s, local_records, args.warmup), s.info())

    s = AsyncQueueStrategy("async_shmem", SerializeSink(), batch_size=args.async_batch)
    add_row("async_shmem_enqueue", "enqueue to in-memory queue (drainer works off hot path)",
            run_strategy(s, local_records, args.warmup), s.info())
    try:
        log_path.unlink()
    except Exception:
        pass

    if not args.skip_network:
        endpoint_label = args.label or args.endpoint
        print(f"[network] real HTTP POST -> {endpoint_label} ...")
        net_needed = max(args.net_iters + 2 * args.net_warmup, args.net_batch * 4 + args.net_warmup + 4)
        net_records = build_records(net_needed)

        client = OutboundLogClient(args.endpoint, ingestion_key=args.ingestion_key)
        s = InlineStrategy("sync_outbound", NetworkSink(client), batch_size=1)
        lat = run_strategy(s, net_records[: args.net_iters + args.net_warmup], args.net_warmup)
        add_row("sync_outbound", f"blocking POST per update -> {endpoint_label}",
                lat[args.net_warmup:], s.info())

        client2 = OutboundLogClient(args.endpoint, ingestion_key=args.ingestion_key)
        nb = args.net_batch
        s = InlineStrategy("sync_outbound_batched", NetworkSink(client2), batch_size=nb)
        count = nb * 4 + args.net_warmup
        lat = run_strategy(s, net_records[:count], args.net_warmup)
        add_row("sync_outbound_batched", f"buffer {nb}, blocking POST every {nb}th update",
                lat[args.net_warmup:], s.info())

    if args.probe_mezmo:
        print(f"[probe] real Mezmo reachability -> {args.mezmo_endpoint} ...")
        probe = OutboundLogClient(args.mezmo_endpoint, ingestion_key=args.ingestion_key)
        probe_results = [probe.post([make_orderbook_line(i)]) for i in range(3)]
        probe.close()
        meta["mezmo_probe"] = [
            {"status": r.status, "ok": r.ok, "elapsed_ms": round(r.elapsed_ns / NS_PER_MS, 3),
             "error": r.error}
            for r in probe_results
        ]
        for pr in meta["mezmo_probe"]:
            print(f"    probe status={pr['status']} ok={pr['ok']} "
                  f"elapsed={pr['elapsed_ms']}ms error={pr['error']}")

    table = write_reports(rows, meta, out_dir)
    print("\nWrote:", out_dir / "latency.md", out_dir / "latency.tsv", out_dir / "raw.json")
    print("\n" + table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
