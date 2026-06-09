from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from .frontmatter import read_frontmatter
from .paths import find_repo_root

console = Console()


@dataclass
class RunSummary:
    path: str
    branch: str
    status: str
    score: str
    validation: str
    idea_id: str
    summary: str
    next_step: str
    needs: str


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _read_results(root: Path) -> list[dict[str, str]]:
    path = root / "results.tsv"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _score(row: dict[str, str]) -> float:
    try:
        return float(row.get("primary_score") or "-inf")
    except ValueError:
        return float("-inf")


def _latest_agent_state(root: Path) -> dict[str, str]:
    current = root / "runs/agent/current.json"
    if current.exists():
        data = _read_json(current)
        return {key: str(value) for key, value in data.items()}

    index = root / "runs/agent/index.tsv"
    if not index.exists():
        return {}
    with index.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    return rows[-1] if rows else {}


def _run_summaries(root: Path, results: list[dict[str, str]]) -> list[RunSummary]:
    logged = {row.get("branch", "") for row in results}
    summaries: list[RunSummary] = []
    for candidate in sorted(root.glob("runs/*/*/candidate.py")):
        run_dir = candidate.parent
        rel = str(run_dir.relative_to(root))
        readme_path = run_dir / "README.md"
        frontmatter: dict[str, Any] = {}
        if readme_path.exists():
            frontmatter, _ = read_frontmatter(readme_path)
        metrics = _read_json(run_dir / "metrics.json")
        splits = metrics.get("splits", {}) if isinstance(metrics.get("splits"), dict) else {}
        validation = splits.get("validation", {}) if isinstance(splits.get("validation"), dict) else {}
        needs: list[str] = []
        if not (run_dir / "metrics.json").exists():
            needs.append("verify")
        if rel not in logged:
            needs.append("ledger")
        if not frontmatter.get("summary"):
            needs.append("summary")
        next_items = frontmatter.get("next") or []
        if isinstance(next_items, list):
            next_step = "; ".join(str(item) for item in next_items[:2])
        else:
            next_step = str(next_items)
        status = str(metrics.get("status") or frontmatter.get("status") or "unknown")
        summaries.append(
            RunSummary(
                path=rel,
                branch=str(run_dir.parent.relative_to(root / "runs")),
                status=status,
                score=str(metrics.get("primary_score", "")),
                validation=str(validation.get("accuracy", "")),
                idea_id=str(frontmatter.get("idea_id", "")),
                summary=str(frontmatter.get("summary", "")),
                next_step=next_step,
                needs=", ".join(needs),
            )
        )
    return summaries


def _build_dashboard(root: Path) -> Panel:
    results = _read_results(root)
    runs = _run_summaries(root, results)
    agent = _latest_agent_state(root)
    scored = [row for row in results if row.get("primary_score")]
    scored.sort(key=_score, reverse=True)
    latest_result = results[-1] if results else {}

    title = Table.grid(expand=True)
    title.add_column(ratio=1)
    title.add_column(ratio=1)
    active_status = agent.get("status") or "not tracked"
    session_id = agent.get("session_id") or ""
    prompt = agent.get("prompt") or ""
    if len(prompt) > 140:
        prompt = prompt[:137] + "..."
    title.add_row("[bold]Agent[/bold]", f"[bold]Best score[/bold] {scored[0].get('primary_score', '') if scored else 'none'}")
    title.add_row(f"status: {active_status}", f"best run: {scored[0].get('branch', '') if scored else ''}")
    title.add_row(f"session: {session_id or 'unknown'}", f"latest run: {latest_result.get('branch', '')}")
    title.add_row(f"started: {agent.get('started_at', '')}", f"latest status: {latest_result.get('status', '')}")
    if prompt:
        title.add_row("hoping to get:", prompt)

    active = Table(title="Active / Needs Attention", expand=True)
    active.add_column("run", overflow="fold")
    active.add_column("status")
    active.add_column("score")
    active.add_column("needs")
    active.add_column("next", overflow="fold")
    needs_attention = [
        run
        for run in runs
        if run.needs or run.status in {"created", "running", "schema_failed", "failed"}
    ]
    for run in needs_attention[-8:]:
        active.add_row(run.path, run.status, run.score, run.needs, run.next_step or run.summary)
    if not needs_attention:
        active.add_row("none", "", "", "", "no unfinished run detected")

    best = Table(title="Best / Interesting Results", expand=True)
    best.add_column("score")
    best.add_column("status")
    best.add_column("run", overflow="fold")
    best.add_column("idea")
    best.add_column("notes", overflow="fold")
    for row in scored[:8]:
        best.add_row(
            row.get("primary_score", ""),
            row.get("status", ""),
            row.get("branch", ""),
            row.get("idea_id", ""),
            row.get("notes", ""),
        )
    if not scored:
        best.add_row("", "", "none", "", "no scored rows yet")

    stats = Table.grid(expand=True)
    stats.add_column(ratio=1)
    stats.add_column(ratio=1)
    statuses: dict[str, int] = {}
    for row in results:
        status = row.get("status") or "unknown"
        statuses[status] = statuses.get(status, 0) + 1
    stats.add_row(f"runs on disk: {len(runs)}", f"ledger rows: {len(results)}")
    stats.add_row(
        "statuses: " + ", ".join(f"{key}={value}" for key, value in sorted(statuses.items())),
        f"dataset: {latest_result.get('dataset_version', '')}",
    )
    if agent.get("json_log"):
        stats.add_row(f"events: {agent.get('json_log')}", f"last message: {agent.get('last_message', '')}")

    grid = Table.grid(expand=True)
    grid.add_row(title)
    grid.add_row(active)
    grid.add_row(best)
    grid.add_row(stats)
    return Panel(grid, title="Autoresearch Monitor", subtitle="runnable with `autoresearch monitor` or `make monitor`")


def render_monitor(*, watch: bool = False, interval: float = 5.0) -> None:
    root = find_repo_root()
    if watch:
        with Live(_build_dashboard(root), console=console, refresh_per_second=2, screen=False) as live:
            while True:
                time.sleep(interval)
                live.update(_build_dashboard(root))
    console.print(_build_dashboard(root))
