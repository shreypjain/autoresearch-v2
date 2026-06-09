#!/usr/bin/env bash
set -euo pipefail

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI is not installed or not on PATH" >&2
  exit 127
fi

while true; do
  codex exec \
    "Read problem.md, architecture.md, and skills/autoresearch/SKILL.md. Run autoresearch index, inspect ideas.md, results.tsv, and the current runs tree. Create new candidates by cd'ing into the chosen runs/<branch> directory and running new-experiment, then verify with scripts/verify.sh. Do not summarize unless blocked. If the last experiment finished, generate the next candidate and run it." \
    2>&1 | tee -a runs/agent.log
  sleep 1
done
