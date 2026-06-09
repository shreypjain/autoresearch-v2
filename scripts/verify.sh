#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
RUN_DIR="${1:-}"
export PYTHONPATH="${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

if [[ -z "${RUN_DIR}" ]]; then
  printf "run directory: "
  read -r RUN_DIR
fi

if [[ -z "${RUN_DIR}" ]]; then
  echo "usage: scripts/verify.sh runs/<branch>/<NNN_name>" >&2
  exit 2
fi

PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="${PYTHON:-python3}"
fi

cd "${ROOT_DIR}"

if [[ -f frozen.lock ]]; then
  "${PYTHON_BIN}" -m autoresearch.verify_freeze
fi

mkdir -p "${RUN_DIR}/plots"
touch "${RUN_DIR}/run.log"

{
  echo "== autoresearch verify =="
  echo "run_dir=${RUN_DIR}"
  echo "started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  "${PYTHON_BIN}" -m autoresearch.evaluator \
    --candidate "${RUN_DIR}/candidate.py" \
    --data-manifest data/manifest.json \
    --splits train,validation \
    --run-dir "${RUN_DIR}"
  echo "finished_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} 2>&1 | tee -a "${RUN_DIR}/run.log"
