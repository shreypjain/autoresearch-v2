# Experiment Loop Reference

## Recovery Scan

Run this before creating new work:

```bash
autoresearch index --status active
```

Then inspect:

- `results.tsv`
- `ideas.md`
- `best/README.md`
- branch README front matter under `runs/*/README.md`
- recent numbered runs with `candidate.py`, `config.json`, `README.md`, `metrics.json`, and `run.log`

Common unfinished states:

- run folder exists but `metrics.json` is missing
- `metrics.json` exists but `results.tsv` has no row
- README still says `running`, `TODO`, or lacks findings after verification
- result row exists but branch README and `ideas.md` were not updated
- schema failed but the candidate was incorrectly recorded as a scored rejection

Continue the most recent useful unfinished run unless it is clearly wrong, plateaued, or superseded.

## Creating Runs

From the branch directory:

```bash
cd runs/<branch>
autoresearch new-experiment <short_name> --idea-id <idea_id>
```

Create a new branch folder under `runs/` only when the experiment family changes materially. Small parameter changes, output-format fixes, and ablations stay in the same branch.

## Verification

Use one of:

```bash
scripts/verify.sh runs/<branch>/<NNN_name>
autoresearch verify runs/<branch>/<NNN_name>
```

After verification, read:

- `metrics.json`
- `run.log`
- generated `plots/` when present
- the run README

If schema validation failed, fix the same candidate and rerun. Do not append a scored result until schema validation passes or the run is explicitly blocked.

## Results Ledger

`results.tsv` is append-only. Add one row per verified result. If a previous row is wrong, append a correction row using `correction_of` or `supersedes_run_id`; do not edit history.

Useful notes should state why the candidate moved, tied, or failed, not just the score.

## README Expectations

Before verification, a run README should include:

- hypothesis
- candidate family
- what `fit(train_rows)` learns, or that no training happens
- what `predict(row)` depends on
- primary comparison and promotion/rejection bar
- leakage and overfit risks

After verification, add:

- train, validation, holdout/stress if scheduled, runtime, and schema status
- comparison to mode baseline and current best
- whether the result came from broad train-learned signal or narrow selected clauses
- why it might generalize or why it is suspicious
- next action: continue, reject, archive, stress/holdout/resplit, or start a new branch

## Status Values

Use these consistently in front matter and logs:

- `running`
- `schema_failed`
- `failed`
- `rejected`
- `accepted`
- `promoted`
- `archived`
- `stale_due_to_rescore`
