---
name: autoresearch-v2
kind: project
status: active
current_best: runs/baseline_classifier/001_baseline
---

# Autoresearch V2

Autoresearch V2 is a forkable experiment harness for agent-driven ML iteration. The harness owns data loading, schema validation, scoring, and result logging. The agent proposes candidates and edits only the generated `predict(row)` function.

## Quickstart

```bash
git clone <your-fork-url>
cd autoresearch-v2
make start
source .venv/bin/activate
autoresearch onboard
```

`make start` creates a virtual environment, installs the package, copies `.env.example` to `.env`, writes demo data if needed, creates the initial experiment, verifies it, and writes `frozen.lock`.

`autoresearch onboard` opens a guided setup flow for API-key entry, problem scope, data import, id/input/label column selection, train/validation/holdout split fractions, and baseline verification.

If your data is not ready yet, leave the data-file prompt blank. Onboarding will keep going. Later, either rerun onboarding with a CSV/JSON/JSONL file, run `autoresearch data import`, or give the coding agent one representative source file and ask it to migrate that source into `data/*.jsonl`.

After that:

```bash
# Replace data/*.jsonl with your data, then validate/index the project.
make clean-data
make index

# Create a new experiment from inside a branch.
cd runs/baseline_classifier
new-experiment threshold_tuning --idea-id IDEA-001
cd ../..
make verify RUN=runs/baseline_classifier/002_threshold_tuning
```

If you do not want to activate the venv, use the repo script directly from a branch:

```bash
../../scripts/new-experiment threshold_tuning --idea-id IDEA-001
```

For neural-network experiments, install the optional deep-learning extra after setup:

```bash
.venv/bin/pip install -e '.[deep]'
```

## CLI

```bash
autoresearch onboard
autoresearch tui
autoresearch index
autoresearch data validate
autoresearch data import ./data.csv --id-field id --label-field label --input-fields text
autoresearch verify runs/baseline_classifier/001_baseline
autoresearch loop
```

## Data Contract

The default task is classification. Each row should be JSONL with:

```json
{"id": "row-1", "text": "example input", "label": "accept"}
```

The candidate receives label-stripped rows and must return:

```json
{"id": "row-1", "predicted_label": "accept", "confidence": 0.5}
```

Edit `scoring_config.yaml` and rerun experiments when you need a different schema or scorer.

## Agent Loop

Once your data and `problem.md` are set, start the loop:

```bash
make loop
```

The loop expects `codex` on PATH. It repeatedly reads `problem.md`, indexes run metadata, creates the next experiment with `new-experiment`, and verifies it through `scripts/verify.sh`.
