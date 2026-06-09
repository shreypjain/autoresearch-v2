---
name: autoresearch-v2
kind: project
status: active
current_best: runs/baseline_classifier/001_baseline
---

# Autoresearch V2

Fork this repo, add your data, and let an agent run schema-checked ML experiments.

The harness owns data loading, validation, scoring, and run logging. The agent edits generated candidates. The evaluator decides what worked.

## Start

```bash
git clone <your-fork-url>
cd autoresearch-v2
make start
source .venv/bin/activate
autoresearch onboard
autoresearch loop --ui
```

Use the `autoresearch` CLI as the primary interface. In each new terminal window, run `source .venv/bin/activate` before calling `autoresearch`. If the editable console script is stale, use the repo-local wrapper instead:

```bash
./autoresearch monitor
./autoresearch nudge "Run a train-fitted model branch next."
```

`make` is kept as a thin bootstrap/convenience layer for fresh clones and for commands you want to run without activating the venv.

## CLI

```bash
autoresearch onboard
```

Guided setup for `.env`, problem scope, data import, labels, split fractions, and baseline verification. If your data is not ready, leave the data-file prompt blank and come back later.

```bash
autoresearch loop --ui
```

Open the classic Codex UI with the autoresearch prompt injected. This is the best default while developing because it is readable and steerable.

```bash
autoresearch loop
```

Run the recursive non-interactive Codex loop. Each iteration writes `runs/agent/<timestamp>/events.jsonl`, `last_message.md`, `stderr.log`, and `session_id.txt`, plus an index at `runs/agent/index.tsv`.

```bash
autoresearch loop --once
autoresearch loop --resume <codex-session-id>
```

Run one non-interactive iteration, or resume a captured session in the classic UI.

```bash
autoresearch monitor
autoresearch monitor --watch
```

Show the active session, what it is trying to accomplish, unfinished runs, current best scores, and summary stats.

```bash
autoresearch nudge "Stop adding validation-selected clauses; run stress or holdout before trusting the current best."
autoresearch nudge --file note.md
autoresearch nudge --clear "New instruction"
```

Append a human instruction to `runs/agent/inbox.md`. Future loop turns and restarted `autoresearch loop --ui` sessions read it as the latest steering. For an already-running classic Codex UI session, restart/resume the session so the prompt includes the new inbox content.

```bash
autoresearch index
autoresearch index --status active
autoresearch verify runs/baseline_classifier/001_baseline
autoresearch data validate
autoresearch data import ./data.csv --id-field id --label-field label --input-fields text
autoresearch new-experiment <short_name> --idea-id IDEA-001
```

Project traversal, evaluation, data validation/import, and run generation.

## Make Shortcuts

```bash
make start          # create .venv, install CLI, verify starter baseline
make onboard        # same as autoresearch onboard
make loop-ui        # same as autoresearch loop --ui
make loop           # same as autoresearch loop
make monitor        # same as autoresearch monitor
make monitor-watch  # same as autoresearch monitor --watch
make test           # smoke-test the harness
```

Make shortcuts reuse the existing virtualenv. They should not reinstall dependencies unless `pyproject.toml` changed or the editable install is missing.

## Files That Matter

- `problem.md`: human problem scope. Create it once during onboarding.
- `data/`: train, validation, holdout, stress, and manifest files.
- `scoring_config.yaml`: schema and scorer contract.
- `runs/`: experiment tree and artifacts.
- `results.tsv`: append-only experiment ledger.
- `ideas.md`: backlog and high-level results.
- `skills/autoresearch/SKILL.md`: agent operating contract.
- `architecture.md`: deeper rules for maintainers.

## Default Data Shape

Rows default to:

```json
{"id": "row-1", "text": "example input", "label": "accept"}
```

Predictions default to:

```json
{"id": "row-1", "predicted_label": "accept", "confidence": 0.5}
```

Change `scoring_config.yaml` when your task needs a different schema or scorer.
