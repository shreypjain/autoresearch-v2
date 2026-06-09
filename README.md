---
name: autoresearch-v2
kind: project
status: active
current_best: runs/baseline_classifier/001_baseline
---

# Autoresearch V2

Fork this repo, add your data, and run schema-checked ML experiments with Codex.

The harness owns data loading, validation, scoring, and run logging. The agent proposes candidates. The evaluator decides what worked.

## Quickstart

```bash
git clone <your-fork-url>
cd autoresearch-v2
make start
source .venv/bin/activate
autoresearch onboard
autoresearch loop --ui
```

That is the normal path:

- `make start` creates the virtualenv, installs the CLI, creates starter files, and verifies the baseline.
- `autoresearch onboard` guides API key entry, problem scope, data import, label fields, and train/validation/holdout split setup.
- `autoresearch loop --ui` opens the readable Codex UI with the autoresearch loop prompt injected.

In every new terminal:

```bash
cd autoresearch-v2
source .venv/bin/activate
autoresearch monitor
```

If `autoresearch` is missing or stale after local code changes:

```bash
make setup
source .venv/bin/activate
```

## Daily Commands

| Command | Use |
| --- | --- |
| `autoresearch onboard` | Guided first-time setup. You can leave data blank if it is not ready. |
| `autoresearch loop --ui` | Start the classic Codex UI with the loop instructions injected. Best default. |
| `autoresearch loop` | Run the recursive non-interactive loop. |
| `autoresearch monitor` | See the active session, best score, unfinished runs, and summary stats. |
| `autoresearch monitor --watch` | Keep the monitor open. |
| `autoresearch nudge "message"` | Add a human instruction for the next loop turn or restarted UI session. |
| `autoresearch index` | Traverse run README metadata. |
| `autoresearch verify <run_dir>` | Run the evaluator for one candidate. |
| `autoresearch data validate` | Validate data files against the configured contract. |
| `autoresearch data import <file>` | Import CSV/JSON/JSONL into the repo data layout. |
| `autoresearch new-experiment <name> --idea-id IDEA-001` | Create the next numbered experiment in the current branch. |

## Steering The Loop

Use `nudge` when the running direction is wrong:

```bash
autoresearch nudge "Stop adding validation-selected clauses; start a train-fitted model branch or run stress/holdout before trusting this candidate."
autoresearch nudge --file note.md
autoresearch nudge --clear "Replace the old steering with this instruction."
```

Nudges are written to `runs/agent/inbox.md`. The next non-interactive loop turn reads them automatically. If a classic Codex UI session is already open, restart or resume it so the prompt includes the new inbox content.

For session recovery:

```bash
autoresearch loop --once
autoresearch loop --resume <codex-session-id>
```

## Make Shortcuts

Use `autoresearch` as the primary interface after activation. Use `make` for bootstrap and convenience:

```bash
make start          # first-time setup
make setup          # repair/install the local CLI shims
make onboard        # autoresearch onboard
make loop-ui        # autoresearch loop --ui
make loop           # autoresearch loop
make monitor        # autoresearch monitor
make monitor-watch  # autoresearch monitor --watch
make test           # smoke-test the harness
```

`make monitor` and the other shortcuts reuse the existing virtualenv. They should not reinstall dependencies unless `pyproject.toml` changed or the editable install is missing.

## Experiment Flow

```bash
autoresearch data import ./data.csv --id-field id --label-field label --input-fields text
autoresearch data validate
cd runs/baseline_classifier
autoresearch new-experiment threshold_tuning --idea-id IDEA-001
cd ../..
autoresearch verify runs/baseline_classifier/002_threshold_tuning
autoresearch monitor
```

## Files That Matter

- `problem.md`: human problem scope. Create it once during onboarding, then treat scope changes as a new project direction.
- `data/`: train, validation, holdout, stress, and manifest files.
- `scoring_config.yaml`: schema and scorer contract.
- `runs/`: experiment tree and artifacts.
- `results.tsv`: append-only experiment ledger.
- `ideas.md`: backlog and high-level results.
- `skills/autoresearch/SKILL.md`: agent operating contract.
- `architecture.md`: deeper rules for maintainers.

Loop artifacts live under `runs/agent/`. Experiment artifacts live under `runs/<branch>/<numbered_experiment>/`.

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
