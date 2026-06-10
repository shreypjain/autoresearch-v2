from __future__ import annotations

from datetime import datetime, timezone
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .codex_sessions import sync_latest_session
from .onboarding import run_onboarding
from .paths import find_repo_root
from .prepare_data import validate_data, write_demo
from .readme_index import collect

app = typer.Typer(help="Autoresearch V2 command line interface.")
data_app = typer.Typer(help="Data onboarding and validation commands.")
app.add_typer(data_app, name="data")
console = Console()


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=find_repo_root(), check=True)


def _latest_nudge(inbox: Path) -> str:
    if not inbox.exists():
        return ""
    current: list[str] = []
    latest: list[str] = []
    for line in inbox.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            if current:
                latest = current
            current = []
            continue
        if line.startswith("session_id:"):
            continue
        current.append(line)
    if current:
        latest = current
    return "\n".join(latest).strip()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@app.command()
def onboard() -> None:
    """Run the guided first-time setup flow."""
    raise typer.Exit(run_onboarding())


@app.command()
def tui() -> None:
    """Open the full-screen terminal dashboard."""
    from .tui import run_tui

    run_tui()


@app.command()
def monitor(
    watch: bool = typer.Option(False, "--watch", "-w", help="Refresh the monitor until interrupted."),
    interval: float = typer.Option(5.0, "--interval", help="Refresh interval in seconds for --watch."),
) -> None:
    """Show the active agent, unfinished runs, best scores, and interesting stats."""
    from .monitor import render_monitor

    render_monitor(watch=watch, interval=interval)


@app.command()
def nudge(
    message: Optional[str] = typer.Argument(None, help="Instruction to append for the next agent loop turn."),
    file: Optional[Path] = typer.Option(None, "--file", "-f", exists=True, help="Read the instruction from a file."),
    clear: bool = typer.Option(False, "--clear", help="Clear pending nudges before writing the new one."),
    send_now: bool = typer.Option(False, "--send-now", help="Send the nudge through codex exec resume immediately."),
) -> None:
    """Append a human instruction for future loop iterations to read."""
    root = find_repo_root()
    inbox = root / "runs/agent/inbox.md"
    queue = root / "runs/agent/nudges.jsonl"
    inbox.parent.mkdir(parents=True, exist_ok=True)
    state = sync_latest_session(root)
    session_id = str(state.get("session_id") or "")
    if clear:
        inbox.write_text("", encoding="utf-8")
    chunks: list[str] = []
    if file:
        chunks.append(file.read_text(encoding="utf-8").strip())
    if message:
        chunks.append(message.strip())
    if not chunks:
        if send_now:
            latest = _latest_nudge(inbox)
            if not latest:
                console.print("[yellow]No pending nudge to send.[/yellow]")
                raise typer.Exit(2)
            chunks.append(latest)
        else:
            console.print(f"[bold]{inbox.relative_to(root)}[/bold]")
            if inbox.exists() and inbox.read_text(encoding="utf-8").strip():
                console.print(inbox.read_text(encoding="utf-8"))
            else:
                console.print("[dim]No pending nudges.[/dim]")
            return
    append_to_inbox = bool(file or message)
    timestamp = _utc_timestamp()
    entry = "\n\n".join(chunk for chunk in chunks if chunk)
    if append_to_inbox:
        with inbox.open("a", encoding="utf-8") as handle:
            session_line = f"\n\nsession_id: {session_id}" if session_id else ""
            handle.write(f"\n\n## {timestamp}{session_line}\n\n{entry}\n")
    with queue.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "timestamp": timestamp,
                    "session_id": session_id,
                    "message": entry,
                    "sent_now": send_now,
                },
                sort_keys=True,
            )
            + "\n"
        )
    if append_to_inbox:
        console.print(f"[green]Wrote nudge to {inbox.relative_to(root)}[/green]")
    else:
        console.print(f"[green]Sending latest nudge from {inbox.relative_to(root)}[/green]")
    if session_id:
        console.print(f"[green]Queued for Codex session {session_id}[/green]")
    else:
        console.print("[yellow]No Codex session id found for this repo yet.[/yellow]")
    if send_now:
        if not session_id:
            raise typer.Exit(2)
        prompt = f"Human nudge from autoresearch:\n\n{entry}\n\nRead runs/agent/inbox.md, then continue the current autoresearch loop."
        _run(["codex", "exec", "resume", session_id, prompt])
        console.print("[green]Sent through background codex exec resume.[/green]")
        console.print("[dim]An already-open Codex TUI pane may not repaint; use autoresearch monitor to confirm delivery.[/dim]")


@app.command("stop-loop")
def stop_loop(
    message: Optional[str] = typer.Argument(None, help="Reason to record with the stop request."),
) -> None:
    """Ask the supervised autoresearch loop to stop after the current Codex turn."""
    root = find_repo_root()
    agent_dir = root / "runs/agent"
    inbox = agent_dir / "inbox.md"
    stop_file = agent_dir / "stop_loop.json"
    queue = agent_dir / "nudges.jsonl"
    agent_dir.mkdir(parents=True, exist_ok=True)
    state = sync_latest_session(root)
    session_id = str(state.get("session_id") or "")
    timestamp = _utc_timestamp()
    reason = (message or "Stop the supervised autoresearch loop after the current turn.").strip()
    stop_entry = {
        "timestamp": timestamp,
        "session_id": session_id,
        "reason": reason,
    }
    stop_file.write_text(json.dumps(stop_entry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    inbox_message = (
        "STOP_LOOP requested.\n\n"
        f"Reason: {reason}\n\n"
        "Finish any in-flight verification/logging, summarize current state, and do not create another experiment."
    )
    with inbox.open("a", encoding="utf-8") as handle:
        session_line = f"\n\nsession_id: {session_id}" if session_id else ""
        handle.write(f"\n\n## {timestamp}{session_line}\n\n{inbox_message}\n")
    with queue.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "timestamp": timestamp,
                    "session_id": session_id,
                    "message": inbox_message,
                    "sent_now": False,
                    "type": "stop_loop",
                },
                sort_keys=True,
            )
            + "\n"
        )
    console.print(f"[green]Wrote stop request to {stop_file.relative_to(root)}[/green]")
    console.print("[dim]A supervised `autoresearch loop` exits after the current Codex turn completes.[/dim]")
    if session_id:
        console.print(f"[green]Recorded against Codex session {session_id}[/green]")


@app.command()
def index(
    kind: Optional[str] = typer.Option(None, help="Filter by front matter kind."),
    status: Optional[str] = typer.Option(None, help="Filter by front matter status."),
) -> None:
    """Print README/problem front matter index."""
    root = find_repo_root()
    rows = collect(root)
    if kind:
        rows = [row for row in rows if row.get("kind") == kind]
    if status:
        rows = [row for row in rows if row.get("status") == status]
    table = Table(title="Autoresearch Index")
    for column in ["kind", "status", "name", "path", "summary"]:
        table.add_column(column)
    for row in rows:
        table.add_row(*(str(row.get(column, "")) for column in ["kind", "status", "name", "path", "summary"]))
    console.print(table)


@app.command()
def verify(run: str = typer.Argument(..., help="Run directory, e.g. runs/baseline_classifier/001_baseline")) -> None:
    """Verify one experiment run."""
    _run(["scripts/verify.sh", run])


@app.command()
def loop(
    ui: bool = typer.Option(False, "--ui", help="Open the classic interactive Codex UI."),
    once: bool = typer.Option(False, "--once", help="Run one non-interactive Codex exec iteration."),
    resume: Optional[str] = typer.Option(None, "--resume", help="Resume a saved Codex session id in the classic UI."),
) -> None:
    """Start the Codex autoresearch loop."""
    command = ["scripts/agent_loop.sh"]
    if ui:
        console.print("[yellow]Opening manual Codex UI mode. This is readable, but it is not the infinite supervisor.[/yellow]")
        command.append("--ui")
    elif once:
        console.print("[yellow]Running one supervised loop iteration.[/yellow]")
        command.append("--once")
    elif resume:
        console.print("[yellow]Resuming a Codex UI session. This is manual UI mode, not the infinite supervisor.[/yellow]")
        command.extend(["--resume", resume])
    else:
        console.print("[green]Starting infinite supervised autoresearch loop. Stop it with `autoresearch stop-loop`.[/green]")
    _run(command)


@app.command("new-experiment")
def new_experiment(
    short_name: Optional[str] = typer.Argument(None),
    idea_id: Optional[str] = typer.Option(None),
    root: bool = typer.Option(False, "--root"),
) -> None:
    """Create a numbered experiment inside the current runs/<branch> directory."""
    command = [sys.executable, "-m", "autoresearch.new_experiment"]
    if short_name:
        command.append(short_name)
    if idea_id:
        command.extend(["--idea-id", idea_id])
    if root:
        command.append("--root")
    subprocess.run(command, check=True)


@data_app.command("demo")
def data_demo() -> None:
    """Write demo data."""
    write_demo(find_repo_root())
    validate_data(find_repo_root())


@data_app.command("validate")
def data_validate() -> None:
    """Validate current data manifest and split files."""
    validate_data(find_repo_root())


@data_app.command("import")
def data_import(
    input_path: Path = typer.Argument(..., exists=True),
    id_field: str = typer.Option(...),
    label_field: str = typer.Option(...),
    input_fields: list[str] = typer.Option(...),
    validation_pct: float = typer.Option(0.2),
    holdout_pct: float = typer.Option(0.1),
    dataset_version: str = typer.Option("dataset-v1"),
) -> None:
    """Import CSV/JSON/JSONL data without the interactive wizard."""
    from .prepare_data import read_tabular, write_dataset_from_rows

    root = find_repo_root()
    rows = read_tabular(input_path)
    write_dataset_from_rows(
        root,
        rows,
        id_field=id_field,
        input_fields=input_fields,
        label_field=label_field,
        validation_pct=validation_pct,
        holdout_pct=holdout_pct,
        dataset_version=dataset_version,
    )
    validate_data(root)


if __name__ == "__main__":
    app()
