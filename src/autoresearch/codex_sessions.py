from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SESSION_ID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


@dataclass(frozen=True)
class CodexSession:
    id: str
    timestamp: str
    path: Path
    cwd: str


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def _parse_time(value: str) -> datetime:
    raw = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y%m%dT%H%M%SZ"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.fromtimestamp(0, tz=timezone.utc)


def _session_from_file(path: Path) -> CodexSession | None:
    try:
        first_line = path.open("r", encoding="utf-8", errors="replace").readline()
        event = json.loads(first_line)
    except Exception:
        return None
    if event.get("type") != "session_meta":
        return None
    payload = event.get("payload")
    if not isinstance(payload, dict):
        return None
    session_id = str(payload.get("id") or "")
    cwd = str(payload.get("cwd") or "")
    timestamp = str(payload.get("timestamp") or event.get("timestamp") or "")
    if not SESSION_ID_RE.fullmatch(session_id) or not cwd:
        return None
    return CodexSession(id=session_id, timestamp=timestamp, path=path, cwd=cwd)


def latest_session_for_root(root: Path, *, limit: int = 300) -> CodexSession | None:
    sessions_root = codex_home() / "sessions"
    if not sessions_root.exists():
        return None
    root_resolved = str(root.resolve())
    paths = sorted(
        sessions_root.glob("**/*.jsonl"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    matches: list[CodexSession] = []
    for path in paths[:limit]:
        session = _session_from_file(path)
        if session and str(Path(session.cwd).resolve()) == root_resolved:
            matches.append(session)
    if not matches:
        return None
    return max(matches, key=lambda session: _parse_time(session.timestamp))


def read_agent_state(root: Path) -> dict[str, Any]:
    path = root / "runs/agent/current.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def write_agent_state(root: Path, state: dict[str, Any]) -> None:
    path = root / "runs/agent/current.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sync_latest_session(root: Path) -> dict[str, Any]:
    state = read_agent_state(root)
    session = latest_session_for_root(root)
    if not session:
        return state
    current_id = str(state.get("session_id") or "")
    current_ts = _parse_time(str(state.get("session_updated_at") or state.get("started_at") or ""))
    latest_ts = _parse_time(session.timestamp)
    if not current_id or current_id == "unknown" or latest_ts >= current_ts:
        state.update(
            {
                "session_id": session.id,
                "session_updated_at": session.timestamp,
                "session_path": str(session.path),
                "session_source": "codex_sessions",
            }
        )
        write_agent_state(root, state)
    return state
