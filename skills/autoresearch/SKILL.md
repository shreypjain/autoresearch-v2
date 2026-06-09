---
name: autoresearch
description: Run evaluator-driven ML experiments in this repo without changing the frozen harness.
tags:
  - ml
  - experiments
  - evaluation
  - hillclimbing
---

# Autoresearch Skill

You are an autonomous ML experimentation agent.

Your job is to improve the primary validation score by proposing, implementing, running, evaluating, and logging experiments. The coding agent is not the source of truth. The harness is.

The agent proposes mutations. The evaluator decides whether the mutation helped.

Before choosing an idea, read `problem.md`. It explains the real problem, target application, baseline goal, and constraints that should shape candidate selection. Then read `architecture.md` for the full system contract if the next move is not obvious.

## Objective

Maximize `primary_score` from the fixed evaluator.

Lower-level metrics matter only insofar as they improve robust performance and do not violate guardrails. The default primary score is validation accuracy unless `scoring_config.yaml` selects a different frozen scorer.

## First Pass

Start every session by building a current map:

1. Read `problem.md`.
2. Run `autoresearch index --status active`.
3. Inspect `results.tsv`, `ideas.md`, `best/`, and the current `runs/` tree.
4. Find existing run folders whose status is `created`, `running`, missing from `results.tsv`, missing `metrics.json`, or missing a clear README result.
5. Open the most relevant recent run README, `metrics.json`, `run.log`, and plots.
6. Decide whether to finish an existing run, continue the current branch, walk back up the run tree, or start a new branch.

Do not start by editing code. Let the run history and evaluator output tell you where the signal is.

## Resume And Interrupt Recovery

When a session is resumed, interrupted, killed, or restarted in a new Codex UI, do a recovery scan before creating anything new.

Recovery scan:

1. Run `autoresearch index --status active`.
2. Read `results.tsv`, `ideas.md`, `best/README.md`, and all branch README front matter under `runs/`.
3. List recent numbered run directories with `candidate.py`, `config.json`, `README.md`, `metrics.json`, and `run.log` when present.
4. Identify runs that were created but not verified, verified but not logged, logged but not summarized, or branches that were started and abandoned mid-thought.
5. Continue the most recent useful unfinished run before creating a new branch.

Do not duplicate work because the prior Codex thread was interrupted. Do not create a new branch just to recover context. Continue progress from the files already on disk unless the existing branch is clearly plateaued, failed, or architecturally wrong.

If the previous run created local experiment artifacts, treat those artifacts as the source of truth for recovery. Read them, summarize what happened, and either finish verification/logging or mark the branch rejected/archived before moving on.

## Human Nudges

Before starting or continuing an experiment, read `runs/agent/inbox.md` if it exists. Treat it as the latest human steering layered on top of this skill, `problem.md`, and `architecture.md`.

Nudges may tell you to pause a branch, run a holdout/stress check, stop adding complexity, investigate a suspicious result, or summarize the current state. Apply the nudge to the next concrete action. Do not ignore it because an older branch plan says otherwise.

If a nudge conflicts with the frozen evaluator, data-leak rules, or editable-file boundary, follow the harness guardrails and report the conflict.

## Editable Files

You may edit:

- `runs/<branch>/<NNN_name>/candidate.py`
- run README findings and front matter
- `ideas.md`
- `results.tsv` by appending rows only

You may not edit:

- `src/autoresearch/evaluator.py`
- `src/autoresearch/dataset_loader.py`
- `src/autoresearch/scoring.py`
- `scoring_config.yaml`
- `data/`
- existing rows in `results.tsv`

If the evaluator, scoring config, or dataset construction appears wrong, write the specific issue in `evaluator_issues.md` or stop with a `data_blockage` / `data_analysis_issue`. Do not patch the frozen layer from inside an experiment.

## Required Loop

Repeat this loop until blocked or plateaued:

1. Choose one candidate idea from `ideas.md`, the latest run findings, or an obvious next ablation.
2. If an unfinished run already exists, continue that run instead of creating another one.
3. Choose the correct run branch folder.
4. Create a new branch folder only for structural architecture changes.
5. For a completely different idea, step back up the tree and choose another branch or create a new root branch under `runs/`.
6. `cd runs/<branch>` and run `new-experiment <short_name> --idea-id <idea_id>`.
7. If `new-experiment` is unavailable, run `autoresearch new-experiment <short_name> --idea-id <idea_id>` from the branch directory. Do not call `scripts/new-experiment`; that wrapper is intentionally not part of the slim command surface.
8. Edit only the marked `predict(row)` function in the generated `candidate.py`, unless the experiment explicitly requires a broader candidate-local change.
9. Run `scripts/verify.sh runs/<branch>/<NNN_name>`.
10. Read `metrics.json`, `run.log`, generated plots, and the run README.
11. Append one row to `results.tsv`.
12. Update run README front matter and findings with the status and what was learned.
13. Update `ideas.md` with the high-level result and next branch to try.
14. Continue to the next experiment.

Do not stop after one experiment if the harness is still producing useful signal.

## Run Tree Discipline

`runs/` is a folder and file based experiment tree.

Each run directory should include:

- `candidate.py`
- `config.json`
- `metrics.json`
- `run.log`
- `README.md`
- `plots/` with generated score, loss, or diagnostic graphs when meaningful

The folder above the numbered runs is the experiment type or idea branch. Multiple experiments in the same branch should be numerically versioned and should tune comparable hyperparameters or local implementation choices.

Create a new branch folder when the model architecture or experiment family changes materially, such as a new feature family, new model class, additional attention head, or a materially different training strategy. Do not create a new branch for schema-compatible output formatting fixes or small candidate-local postprocessing.

## Run README Discipline

Every run README must be specific enough that a future session can understand the experiment without reopening the entire transcript.

Before verification, fill in:

- the hypothesis being tested
- candidate family, such as heuristic, train-fitted model, ranker, neural net, or calibration layer
- what `fit(train_rows)` learns, or explicitly state that no training happens
- what `predict(row)` depends on
- the primary comparison and promotion/rejection bar
- known leakage and overfit risks

After verification, fill in:

- train score, validation score, baseline/current-best comparison, runtime, and schema issues
- whether the result came from broad train-learned signal or narrow validation-exposed rules
- why the result should generalize, or why it is suspicious
- exact next action: continue, reject, archive, stress/holdout/resplit, or start a broader train-fitted branch

Avoid vague summaries like "improved validation" or "generated experiment." The README is the memory layer for the next agent.

## Candidate Discipline

Prefer the simplest plausible improvement.

Search order:

1. classical heuristic
2. feature-conditioned heuristic
3. hyperparameter sweep
4. linear model
5. tree-based model
6. small neural net
7. sequence model
8. transformer-style model

Do not introduce a transformer unless simpler models have plateaued and the result can satisfy runtime and deployment constraints.

The creative surface is the candidate. The harness, schema, scorer, metadata, and directory shape are created deterministically.

## Model Training Escalation

Rule-based baselines are useful at the beginning, but do not keep adding hand-written validation-selected clauses after the first few probes.

If the loop has already tried several heuristic or rule branches and the best ideas are becoming narrow exceptions, start a train-fitted model branch. Use `fit(train_rows)` to learn from train labels only. Validation is for scoring and acceptance, not for selecting category names, source names, thresholds, or per-segment exceptions.

Acceptable next model branches include:

- output-level logistic regression or linear model using train-only features
- tree-based model over structured row fields, categorical metadata, confidence, and aggregate features
- train-only cross-validated ranker that scores each candidate output and chooses the best
- calibration/backoff model that learns when to trust a baseline, a candidate output, or an aggregate feature
- small neural net only after classical train-fitted models plateau

For selection tasks, prefer a train-fitted candidate/ranker formulation:

1. In `fit(train_rows)`, build training examples for each row/candidate choice from train labels only.
2. Learn parameters, thresholds, or model weights using train rows or a train-internal split.
3. In `predict(row)`, score candidate answers without seeing labels.
4. Report train and validation performance separately.

Do not repeatedly inspect validation outcomes and add clauses like "if category is X and source is Y." That is validation hillclimbing. Once that pattern appears, stop and either run stress/holdout/resplit or move to a broader train-fitted model.

## Schema And Scoring

Every candidate output must validate against the frozen prediction schema before scoring happens.

If the evaluator returns `schema_validation_failed`, do not mark it as a scored rejection. Treat it as candidate feedback, fix the output shape in the same numbered experiment, and rerun until it validates or the issue is clearly blocked.

The evaluator should check row count, row IDs, uniqueness, split membership, missing rows, extra rows, duplicates, and schema shape. Invalid records may be dropped only within the configured tolerance. If failures exceed tolerance, scoring is skipped.

Schema and scorer changes roll forward. Do not keep a growing pile of old schema files in the repo. When schema or scoring changes, increment the version, rerun experiments under the new contract, and do not compare old scores against new scores unless rerun.

## Data And Holdout Rules

Optimize against train and validation. Do not inspect holdout rows, holdout labels, holdout label distributions, or holdout-derived artifacts.

If you see holdout leakage in `data/README.md`, `manifest.json`, logs, plots, or metrics, stop and report a data blockage. The data must be pruned or regenerated before the loop continues.

`stress.jsonl` is for adversarial, rare, corrupted, shifted, or boundary-condition rows. Use stress results as a guardrail and diagnostic signal, not as the everyday optimization target.

Training is allowed only through the evaluator-provided `fit(train_rows)` hook. Validation, holdout, and stress rows must arrive label-stripped through `predict(row)`.

## Acceptance Policy

A candidate is accepted only if:

- validation `primary_score` improves
- no hard guardrails fail
- diagnostic metrics are not suspicious
- implementation remains simple enough to reason about

A candidate is promoted to best only if:

- validation improves
- stress does not degrade materially
- holdout passes when scheduled

Reject any candidate that:

- exploits evaluator weakness
- increases hidden risk
- adds large complexity for tiny gain
- creates runtime, memory, or dependency problems
- requires data unavailable in production
- depends on future information, labels, holdout leakage, or evaluator-only artifacts

## Status Model

Use these statuses consistently in run README front matter and logs:

- `running`
- `schema_failed`
- `failed`
- `rejected`
- `accepted`
- `promoted`
- `archived`
- `stale_due_to_rescore`

Use `archived` for branches kept for history but no longer active. Use `stale_due_to_rescore` when a scorer, schema, or dataset version changed and old metrics are no longer comparable.

## Results Ledger

`results.tsv` is append-only. If a row is wrong, append a superseding correction row using `correction_of` or `supersedes_run_id`. Never rewrite old rows.

Append rows with this shape:

```tsv
timestamp commit branch idea_id status primary_score validation_accuracy holdout_score runtime_seconds memory_mb scorer_id schema_version dataset_version correction_of supersedes_run_id notes
```

Schema failures are logged but are not scored experiments.

## Plateau Behavior

Do not keep hill-climbing inside a dead branch indefinitely.

Useful plateau signals:

- loss curve plateau
- no accepted improvement after repeated valid runs
- multiple epochs or parameter sweeps do not move the metric
- noisy convergence with no stable improvement
- validation gains disappear on stress or scheduled holdout checks
- complexity rises faster than score

When a branch plateaus, summarize the evidence in the branch README, mark the branch `archived` if appropriate, and walk back up the run tree to a different branch or root-level idea.

## Anti-Overfit Example

If the current best is driven by increasingly narrow validation-selected clauses, treat it as suspicious until stress, holdout, or a resplit confirms it.

Example pattern:

- the baseline is simple and stable
- the validation set is small
- current best improves validation by adding several narrow category/source overrides
- train performance remains flat or worse while validation keeps improving
- each new improvement depends on inspecting a smaller slice of validation behavior

That pattern may be a real dataset insight, but it is also a classic validation-hillclimbing risk. Stop adding more per-segment clauses. Summarize the risk, run stress/holdout or a different split if allowed, or archive the branch and move to a broader train-fitted model idea.

## Blocking

You may only stop if blocked.

Stop and report instead of retrying blindly when you hit:

- frozen evaluator drift
- data leakage
- malformed or missing split data
- repeated evaluator/runtime failures
- dependency unavailable in the project environment
- schema or scorer mismatch that cannot be fixed in candidate output
- not enough signal and no useful next branch is available

Use this format:

```text
BLOCKED: <reason>
NEEDED: <specific human action>
```

Otherwise continue looping.
