---
name: autoresearch
description: Use when running, resuming, or reviewing evaluator-driven ML or algorithm experiments in an autoresearch repo. Guides coding agents through recovery scans, candidate creation, verification, logging, run-tree updates, and frozen-evaluator guardrails without editing data, scoring, or evaluator files.
metadata:
  short-description: Run safe evaluator-driven experiments
---

# Autoresearch

You are working inside a file-backed experiment harness. The agent proposes candidate code; the evaluator validates and scores it. Treat the harness, not your intuition, as the source of truth.

## Core Contract

Start from the current on-disk state. Do not assume a previous agent finished cleanly.

1. Read `problem.md`.
2. Run `autoresearch index --status active`.
3. Inspect `results.tsv`, `ideas.md`, `best/README.md`, and the active `runs/` branches.
4. Find runs that are created but unverified, verified but unlogged, logged but unsummarized, or marked `running` after their command finished.
5. Finish or cleanly reject the most useful unfinished run before starting a new one.

If `runs/agent/inbox.md` exists, read it before choosing the next action. Treat it as the latest human steering unless it conflicts with frozen-evaluator or data-leak rules.

## Normal Loop

Repeat while useful signal remains:

1. Choose one candidate idea from `ideas.md`, recent run findings, or an obvious ablation.
2. Stay in the current branch for local variants; create a new branch only for a materially different feature family, model family, objective, or training strategy.
3. From `runs/<branch>`, run `autoresearch new-experiment <short_name> --idea-id <idea_id>`.
4. Edit the generated `candidate.py` only inside the candidate surface unless the experiment explicitly requires candidate-local helper code.
5. Run `scripts/verify.sh runs/<branch>/<NNN_name>` or `autoresearch verify runs/<branch>/<NNN_name>`.
6. Read `metrics.json`, `run.log`, generated plots, and the run README.
7. Append one row to `results.tsv`; never rewrite old rows.
8. Update the run README, branch README, and `ideas.md` with the result and next action.
9. Continue, walk back up the tree, or stop with a specific blocker.

Do not stop merely because one experiment completed if the loop still has a clear next move.

## Edit Boundary

Allowed during normal experiments:

- `runs/<branch>/<NNN_name>/candidate.py`
- run and branch README findings/front matter
- `ideas.md`
- `results.tsv` by appending rows only

Not allowed during normal experiments:

- `src/autoresearch/evaluator.py`
- `src/autoresearch/dataset_loader.py`
- `src/autoresearch/scoring.py`
- `scoring_config.yaml`
- `data/`
- existing rows in `results.tsv`

If the evaluator, scoring config, or data split appears wrong, record evidence in `evaluator_issues.md` and stop with a clear `data_blockage` or `data_analysis_issue`.

## Search Discipline

Prefer the simplest plausible improvement that can generalize:

1. baseline or deterministic heuristic
2. feature-conditioned heuristic
3. hyperparameter sweep
4. train-fitted linear or ranking model
5. tree-based model
6. small neural model
7. sequence or transformer-style model only after simpler options plateau

Do not keep adding validation-selected subject, source, row, or category clauses after a few probes. Once that pattern appears, switch to train-only fitted models, resplit diagnostics, holdout/stress checks, or a materially different feature source.

## Acceptance Standard

Accept a candidate only when it improves validation `primary_score`, preserves schema validity, keeps runtime/dependencies reasonable, and does not show obvious leakage or overfit risk.

Promote to best only when validation improves and scheduled holdout/stress checks do not materially degrade. If holdout/stress contradict validation, record the conflict and continue research without promotion.

Reject or archive candidates that exploit evaluator weakness, require unavailable production data, add large complexity for tiny gains, leak labels, depend on holdout information, or repeatedly collapse to mode under train-only calibration.

## Load More When Needed

- Read [references/experiment-loop.md](references/experiment-loop.md) when creating, verifying, logging, or recovering runs.
- Read [references/frozen-boundaries.md](references/frozen-boundaries.md) when touching data, schemas, scoring, holdout/stress, or evaluator-related failures.
- Read [references/search-strategy.md](references/search-strategy.md) when deciding the next candidate tree, diagnosing overfit, or deciding whether a branch has plateaued.
