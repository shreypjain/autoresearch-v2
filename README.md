---
name: autoresearch-v2
kind: project
status: active
current_best: runs/baseline_classifier/001_baseline
---

# Autoresearch V2

Fork this repo, add your data, and let an agent run schema-checked ML experiments.

The harness owns data loading, validation, scoring, and run logging. The agent edits generated candidates and the evaluator decides what worked.

## Start

```bash
git clone <your-fork-url>
cd autoresearch-v2
make start
make onboard
make loop
```

That is the intended path:

1. `make start` installs the local CLI and verifies the starter baseline.
2. `make onboard` asks for your API key, problem scope, and data mapping.
3. `make loop` starts the recursive Codex experiment loop.

If your data is not ready, leave the onboarding data prompt blank. Later you can rerun onboarding, import a CSV/JSON/JSONL file, or give the coding agent one representative source file and ask it to migrate it into `data/*.jsonl`.

## Useful Commands

```bash
make start      # install and verify the starter project
make onboard    # guided setup
make loop       # recursive agent loop
make test       # smoke-test the harness
make verify RUN=runs/baseline_classifier/001_baseline
```

Activate the environment when you want direct CLI access:

```bash
source .venv/bin/activate
autoresearch --help
```

## Files That Matter

- `problem.md`: human problem scope. Create it once during onboarding.
- `data/`: train, validation, holdout, stress, and manifest files.
- `scoring_config.yaml`: schema and scorer contract.
- `runs/`: experiment tree and artifacts.
- `results.tsv`: append-only experiment ledger.
- `architecture.md`: deeper rules for agents and maintainers.

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
