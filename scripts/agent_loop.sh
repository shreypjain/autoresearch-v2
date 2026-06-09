#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
AGENT_DIR="${ROOT_DIR}/runs/agent"
MODE="${1:-exec}"
RUN_FOREVER=1

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI is not installed or not on PATH" >&2
  exit 127
fi

PROMPT="Read problem.md, architecture.md, and skills/autoresearch/SKILL.md. First do an interrupt/recovery scan: run autoresearch index, inspect results.tsv, ideas.md, best/README.md, and the current runs tree; find runs that were created but not verified, verified but not logged, or logged but not summarized. Continue the most recent useful unfinished run before creating anything new. If no unfinished run exists, create new candidates by cd'ing into the chosen runs/<branch> directory and running new-experiment, then verify with scripts/verify.sh. Do not use scripts/new-experiment. Do not summarize unless blocked. If the last experiment finished, generate the next candidate and run it."

usage() {
  cat <<'EOF'
usage: scripts/agent_loop.sh [--ui | --once | --resume SESSION_ID]

Modes:
  default              run recursive non-interactive Codex exec loop
  --once               run one non-interactive Codex exec iteration
  --ui                 open the classic interactive Codex UI with the autoresearch prompt
  --resume SESSION_ID  resume a saved Codex session in the classic UI
EOF
}

extract_session_id() {
  local json_log="$1"
  local output_path="$2"
  python3 - "$json_log" "$output_path" <<'PY'
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

json_log = Path(sys.argv[1])
output_path = Path(sys.argv[2])
pattern = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
ids: list[str] = []

def visit(value: Any) -> None:
    if isinstance(value, str):
        ids.extend(pattern.findall(value))
    elif isinstance(value, dict):
        for child in value.values():
            visit(child)
    elif isinstance(value, list):
        for child in value:
            visit(child)

if json_log.exists():
    for line in json_log.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            visit(json.loads(line))
        except json.JSONDecodeError:
            ids.extend(pattern.findall(line))

unique = list(dict.fromkeys(ids))
output_path.write_text((unique[-1] if unique else "") + "\n", encoding="utf-8")
PY
}

write_agent_state() {
  local status="$1"
  AGENT_STATE_PATH="${AGENT_DIR}/current.json" \
  AGENT_STARTED_AT="${STARTED_AT:-}" \
  AGENT_STATUS="${status}" \
  AGENT_SESSION_ID="${SESSION_ID:-}" \
  AGENT_RUN_DIR="${RUN_DIR#${ROOT_DIR}/}" \
  AGENT_JSON_LOG="${JSON_LOG#${ROOT_DIR}/}" \
  AGENT_LAST_MESSAGE="${LAST_MESSAGE#${ROOT_DIR}/}" \
  AGENT_STDERR_LOG="${STDERR_LOG#${ROOT_DIR}/}" \
  AGENT_PROMPT="${PROMPT}" \
  python3 - <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path

state = {
    "started_at": os.environ.get("AGENT_STARTED_AT", ""),
    "status": os.environ.get("AGENT_STATUS", ""),
    "session_id": os.environ.get("AGENT_SESSION_ID", ""),
    "run_dir": os.environ.get("AGENT_RUN_DIR", ""),
    "json_log": os.environ.get("AGENT_JSON_LOG", ""),
    "last_message": os.environ.get("AGENT_LAST_MESSAGE", ""),
    "stderr_log": os.environ.get("AGENT_STDERR_LOG", ""),
    "prompt": os.environ.get("AGENT_PROMPT", ""),
}
path = Path(os.environ["AGENT_STATE_PATH"])
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

if [[ "${MODE}" == "--help" || "${MODE}" == "-h" ]]; then
  usage
  exit 0
fi

if [[ "${MODE}" == "--ui" ]]; then
  cd "${ROOT_DIR}"
  echo "Opening Codex UI. Resume later with: codex resume --include-non-interactive --last"
  exec codex --cd "${ROOT_DIR}" --no-alt-screen "${PROMPT}"
fi

if [[ "${MODE}" == "--resume" ]]; then
  SESSION_ID="${2:-}"
  if [[ -z "${SESSION_ID}" ]]; then
    usage >&2
    exit 2
  fi
  cd "${ROOT_DIR}"
  exec codex resume --include-non-interactive --cd "${ROOT_DIR}" "${SESSION_ID}"
fi

if [[ "${MODE}" == "--once" ]]; then
  RUN_FOREVER=0
elif [[ "${MODE}" != "exec" ]]; then
  usage >&2
  exit 2
fi

mkdir -p "${AGENT_DIR}"
INDEX_PATH="${AGENT_DIR}/index.tsv"
if [[ ! -f "${INDEX_PATH}" ]]; then
  printf "started_at\tstatus\tsession_id\tjson_log\tlast_message\tstderr_log\n" > "${INDEX_PATH}"
fi

while true; do
  STARTED_AT="$(date -u +%Y%m%dT%H%M%SZ)"
  RUN_DIR="${AGENT_DIR}/${STARTED_AT}"
  JSON_LOG="${RUN_DIR}/events.jsonl"
  LAST_MESSAGE="${RUN_DIR}/last_message.md"
  STDERR_LOG="${RUN_DIR}/stderr.log"
  SESSION_FILE="${RUN_DIR}/session_id.txt"
  SESSION_ID=""
  mkdir -p "${RUN_DIR}"
  write_agent_state "running"

  echo "codex exec started_at=${STARTED_AT}"
  echo "  events: ${JSON_LOG#${ROOT_DIR}/}"
  echo "  last_message: ${LAST_MESSAGE#${ROOT_DIR}/}"

  set +e
  codex exec --json --cd "${ROOT_DIR}" --output-last-message "${LAST_MESSAGE}" "${PROMPT}" > "${JSON_LOG}" 2> "${STDERR_LOG}"
  STATUS=$?
  set -e

  extract_session_id "${JSON_LOG}" "${SESSION_FILE}"
  SESSION_ID="$(tr -d '[:space:]' < "${SESSION_FILE}")"
  if [[ -z "${SESSION_ID}" ]]; then
    SESSION_ID="unknown"
  fi
  if [[ "${STATUS}" -eq 0 ]]; then
    write_agent_state "finished"
  else
    write_agent_state "failed:${STATUS}"
  fi

  printf "%s\t%s\t%s\t%s\t%s\t%s\n" \
    "${STARTED_AT}" \
    "${STATUS}" \
    "${SESSION_ID}" \
    "${JSON_LOG#${ROOT_DIR}/}" \
    "${LAST_MESSAGE#${ROOT_DIR}/}" \
    "${STDERR_LOG#${ROOT_DIR}/}" >> "${INDEX_PATH}"

  echo "codex exec finished status=${STATUS} session_id=${SESSION_ID}"
  if [[ "${SESSION_ID}" != "unknown" ]]; then
    echo "  resume UI: codex resume --include-non-interactive ${SESSION_ID}"
  else
    echo "  resume UI: codex resume --include-non-interactive --last"
  fi
  echo "  index: ${INDEX_PATH#${ROOT_DIR}/}"

  if [[ "${STATUS}" -ne 0 ]]; then
    exit "${STATUS}"
  fi
  if [[ "${RUN_FOREVER}" -eq 0 ]]; then
    break
  fi
  sleep 1
done
