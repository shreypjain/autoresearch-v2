from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from .codex_sessions import sync_latest_session
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


def _latest_nudge_event(root: Path) -> dict[str, str]:
    path = root / "runs/agent/nudges.jsonl"
    if not path.exists():
        return {}
    latest: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            latest = {key: str(item) for key, item in value.items()}
    return latest


def _score(row: dict[str, str]) -> float:
    try:
        return float(row.get("primary_score") or "-inf")
    except ValueError:
        return float("-inf")


def _format_score(value: str | float | None) -> str:
    if value in {None, ""}:
        return ""
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def _relative_time(value: datetime, now: datetime) -> str:
    seconds = int((now - value).total_seconds())
    if seconds < 0:
        return ""
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 7:
        return f"{days}d ago"
    return ""


def _format_timestamp(value: str | None, *, compact: bool = False) -> str:
    if not value:
        return "not tracked"
    raw = value.strip()
    formats = [
        "%Y%m%dT%H%M%SZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
    ]
    parsed: datetime | None = None
    for fmt in formats:
        try:
            parsed = datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            break
        except ValueError:
            continue
    if parsed is None:
        return raw
    local = parsed.astimezone()
    now = datetime.now().astimezone()
    if compact:
        if local.date() == now.date():
            return local.strftime("%-I:%M %p")
        return local.strftime("%b %-d %-I:%M %p")
    suffix = _relative_time(local, now)
    rendered = local.strftime("%b %-d, %Y %-I:%M %p")
    return f"{rendered} ({suffix})" if suffix else rendered


def _human_status(status: str) -> str:
    labels = {
        "accepted": "accepted",
        "promoted": "promoted",
        "rejected": "rejected",
        "failed": "failed",
        "schema_failed": "schema failed",
        "running": "running",
        "created": "created",
        "archived": "archived",
        "stale_due_to_rescore": "stale after rescore",
        "ui_running": "classic UI running",
        "ui_resuming": "classic UI resuming",
        "not tracked": "not tracked",
    }
    if status.startswith("failed:"):
        return f"failed with exit {status.split(':', 1)[1]}"
    return labels.get(status, status.replace("_", " "))


def _status_style(status: str) -> str:
    styles = {
        "accepted": "green",
        "promoted": "bold green",
        "rejected": "red",
        "failed": "bold red",
        "schema_failed": "magenta",
        "running": "yellow",
        "created": "yellow",
        "archived": "dim",
        "stale_due_to_rescore": "yellow",
        "ui_running": "cyan",
        "ui_resuming": "cyan",
        "not tracked": "dim",
    }
    if status.startswith("failed:"):
        return "bold red"
    return styles.get(status, "white")


def _styled_status(status: str) -> str:
    if not status:
        return ""
    return f"[{_status_style(status)}]{_human_status(status)}[/{_status_style(status)}]"


def _display_session(agent: dict[str, str]) -> str:
    session_id = agent.get("session_id") or ""
    status = agent.get("status") or ""
    if session_id and session_id != "unknown":
        return session_id
    if status in {"ui_running", "ui_resuming"}:
        return "classic UI; session id not exposed"
    return "not captured"


def _resume_hint(agent: dict[str, str]) -> str:
    session_id = agent.get("session_id") or ""
    status = agent.get("status") or ""
    if session_id and session_id != "unknown":
        return f"codex resume --include-non-interactive {session_id}"
    if status in {"ui_running", "ui_resuming"}:
        return "codex resume --include-non-interactive --last"
    return ""


def _summarize_prompt(prompt: str) -> str:
    if not prompt:
        return ""
    if "interrupt/recovery scan" in prompt and "inbox.md" in prompt:
        return "Read human nudges, recover unfinished runs, then create and verify the next useful experiment."
    return prompt[:137] + "..." if len(prompt) > 140 else prompt


def _summarize_nudge(message: str) -> str:
    compact = " ".join(message.split())
    return compact[:117] + "..." if len(compact) > 120 else compact


def _reconcile_results(results: list[dict[str, str]]) -> list[dict[str, str]]:
    """Collapse append-only ledger rows to the current row for each run."""
    current_by_run: dict[str, dict[str, str]] = {}
    corrections: set[str] = set()
    superseded: set[str] = set()

    for row in results:
        branch = row.get("branch", "")
        correction_of = row.get("correction_of", "")
        supersedes = row.get("supersedes_run_id", "")
        if correction_of:
            corrections.add(correction_of)
        if supersedes:
            superseded.add(supersedes)
        if branch:
            current_by_run[branch] = row

    reconciled: list[dict[str, str]] = []
    for branch, row in current_by_run.items():
        if branch in corrections and row.get("correction_of") != branch:
            continue
        if branch in superseded and row.get("supersedes_run_id") != branch:
            continue
        reconciled.append(row)
    reconciled.sort(key=lambda row: (row.get("timestamp", ""), row.get("branch", "")))
    return reconciled


def _latest_agent_state(root: Path) -> dict[str, str]:
    sync_latest_session(root)
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
    reconciled = _reconcile_results(results)
    runs = _run_summaries(root, reconciled)
    agent = _latest_agent_state(root)
    latest_nudge = _latest_nudge_event(root)
    scored = [row for row in reconciled if row.get("primary_score")]
    scored.sort(key=_score, reverse=True)
    latest_result = reconciled[-1] if reconciled else {}

    title = Table.grid(expand=True)
    title.add_column(ratio=1)
    title.add_column(ratio=1)
    active_status = agent.get("status") or "not tracked"
    prompt = _summarize_prompt(agent.get("prompt") or "")
    best_score = _format_score(scored[0].get("primary_score", "")) if scored else "none"
    title.add_row("[bold cyan]Agent[/bold cyan]", f"[bold cyan]Best score[/bold cyan] [bold green]{best_score}[/bold green]")
    title.add_row(f"agent status: {_styled_status(active_status)}", f"best run: {scored[0].get('branch', '') if scored else ''}")
    title.add_row(f"session: {_display_session(agent)}", f"latest run: {latest_result.get('branch', '')}")
    title.add_row(f"started: {_format_timestamp(agent.get('started_at'))}", f"latest result: {_styled_status(latest_result.get('status', ''))}")
    title.add_row("", f"latest result time: {_format_timestamp(latest_result.get('timestamp'))}")
    if _resume_hint(agent):
        title.add_row("resume:", _resume_hint(agent))
    if prompt:
        title.add_row("loop goal:", prompt)
    if latest_nudge:
        sent_label = "sent now" if latest_nudge.get("sent_now") == "True" else "queued"
        title.add_row(
            "last nudge:",
            f"{sent_label} at {_format_timestamp(latest_nudge.get('timestamp'))}: {_summarize_nudge(latest_nudge.get('message', ''))}",
        )

    active = Table(title="[bold italic]Active / Needs Attention[/bold italic]", expand=True, border_style="cyan")
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
        active.add_row(run.path, _styled_status(run.status), _format_score(run.score), run.needs, run.next_step or run.summary)
    if not needs_attention:
        active.add_row("none", "", "", "", "no unfinished run detected")

    best = Table(title="[bold italic]Best / Interesting Results[/bold italic]", expand=True, border_style="green")
    best.add_column("score")
    best.add_column("status")
    best.add_column("time")
    best.add_column("run", overflow="fold")
    best.add_column("idea")
    best.add_column("notes", overflow="fold")
    for row in scored[:8]:
        best.add_row(
            f"[bold green]{_format_score(row.get('primary_score', ''))}[/bold green]",
            _styled_status(row.get("status", "")),
            _format_timestamp(row.get("timestamp"), compact=True),
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
    for row in reconciled:
        status = row.get("status") or "unknown"
        statuses[status] = statuses.get(status, 0) + 1
    status_text = ", ".join(f"{_human_status(key)} {value}" for key, value in sorted(statuses.items()))
    stats.add_row(f"runs on disk: {len(runs)}", f"raw ledger rows: {len(results)}")
    stats.add_row("current statuses:", status_text)
    stats.add_row("dataset:", latest_result.get("dataset_version", ""))
    if len(reconciled) != len(results):
        stats.add_row(f"current ledger runs: {len(reconciled)}", f"older superseded rows hidden: {len(results) - len(reconciled)}")
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
