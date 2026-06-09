# Autoresearch V2

## Purpose

This document defines a lightweight harness for using coding agents to rapidly improve ML-driven or algorithmic systems through controlled experimentation.

The intended use is improving an ML model, scoring function, ranking system, forecasting model, optimizer, or algorithmic policy against a fixed evaluation harness.

The core idea is:

```text
experiment candidate generation (1-5 experiments)
→ controlled and finite scoped experiment
→ test on structured evaluation dataset
→ accept / reject
→ log result and analyze what worked / what didn't
→ branch promising ideas
→ repeat
```

This should feel like Karpathy-style `autoresearch`, but generalized beyond LLM training and made more durable for real engineering work and far more expansive in terms of the ML techniques that can be trained.

---

## Design Goals

1. **Fast experimentation**
   - Agents should be able to propose and test 1-5 candidate changes quickly.
   - Experiments should run locally, in CI, or on single H100s with minimal setup.
   - Results should be easy to compare across branches and runs.
     - All results should have tags, be grouped by experiment types, and have a pointer to previous inspiration experiments.

2. **Strong evaluation boundaries**
   - Agents may edit the candidate surface.
   - Agents may not edit the evaluator / evaluation harness, holdout data, scoring rules, or dataset construction.
   - The harness must prevent reward hacking wherever possible.
     - Important to generate adversarial tests to mitigate against this.

3. **Parallel candidate generation**
   - The initial system should run as a single-agent loop to preserve context and avoid burning tokens across poorly coordinated agents.
   - Multiple branches should still be supported in the file tree, but multi-agent execution is a later capability, not the default.
   - Good ideas should be merged into a best-so-far branch.
     - Space for improvement should be measured here (ability to hill climb train dataset accuracy)
   - Bad ideas should be discarded but logged.
     - There should be high level descriptions alongside `name`, `description`, and `tags` when describing these files (like YAML file for skills `name` and `description` tags).

4. **Generalized beyond LLMs**
   - Works for classification, regression, ranking models, feature engineering, forecasting, optimization, RL-like policies, and classical ML.
   - Does not require transformer training as the starting point. In fact, should be discouraged until upgrades are essential.
   - Prioritize CPU bound smaller models, grow larger as signs of additional train set accuracy continues to go up.
     - The bitter lesson scaling laws can be prioritized here, until it doesn't work and you need to destroy what you do completely.
     - If you are hitting a complete wall, you might need to traverse multiple levels back and stop making additional improvements to this architecture that doesn't matter.
   - **Important caveat**: There will be clear cases where you just don't have a feature rich enough dataset to improve accuracy on the test or hold out set. Data cleanliness, interpretability, and diversity is incredibly important as a result.

5. **Progressive search path**
   - Start with simple, classical, interpretable approaches.
     - Simple regressions, classifications, random forests, simple GANs, single head attentions if you need to and progress.
     - The skill we build should have a progression function.
   - Only move toward more complex models when simple baselines stop improving.
     - There should be a clear mechanism for determining how you should improve.
   - Maintain a clear record of why complexity was introduced and how to reverse your way out of it when you are hitting a local maxima.

6. **Persistent autonomous loop**
   - The agent should not stop after one experiment.
   - A wrapper should repeatedly invoke or resume the agent.
     - It should be scoped to only do work with Codex to start given third party usage is counted against baseline limits.
     - There should be messages like "Keep reviewing the autoresearch skill and loop on additional work and testing."
     - This message can be purely deterministic until a human interrupts it's work.
   - The agent should read outputs, diagnose failures, generate the next candidate, and keep looping.
     - Graphs, loss curves, logs, and failed validation examples are highly encouraged to inspect and summarize.

---

## Mental Model

Inspired by `karpathy/autoresearch`, but shaped for a frozen evaluator and a file-backed experiment tree:

```text
skills/autoresearch = skill breakdown for how to run autoresearch
problem.md          = guided problem scope, goal, application, and baseline target
strategy.py         = editable candidate surface
evaluator.py        = frozen evaluation harness
data/               = frozen train / validation / holdout jsonl datasets
results.tsv         = experiment ledger
ideas.md            = running idea log, branch notes, and high-level results
best/               = current best-so-far implementation
runs/               = file-tree of experiment branches, versions, logs, plots, and findings
scripts/verify.sh   = shell entrypoint for one complete evaluation loop
external loop       = repeatable wrapper around the coding agent
```

The coding agent is built to ingest information and generate candidates and run the evaluation on it. The harness evaluates it's efficacy with its source of truth.

The agent proposes mutations. The evaluator decides whether the mutation helped and feeds the evaluation results back to the agent to let it decide whether the mutation was useful.

Every experiment must be reproducible from the files it leaves behind: candidate Python, frozen evaluator command, metrics, graphs, and a short human-readable README. Hyperparameter tuning stays inside the current run branch (folder). Structural architecture changes create a new branch folder. Completely different ideas should step back up the tree and start from a different branch that it will work off of or from the root `runs` folder.

---

## Recommended Repository Structure

```text
agentic-experiments/
  README.md
  architecture.md
  problem.md                    # human-readable problem scope and baseline goal
  .env.example
  .env                          # created from .env.example, not committed
  pyproject.toml
  Makefile

  skills/
    autoresearch/
      SKILL.md                  # how the agent runs the loop

  strategy.py                   # editable candidate surface
  features.py                   # optionally editable
  models.py                     # optionally editable
  config.py                     # editable only if allowed

  evaluator.py                  # frozen to agent – marked in the skill
  dataset_loader.py             # frozen to agent – marked in the skill
  metrics.py                    # frozen to agent – marked in the skill
  scoring.py                    # frozen to agent – marked in the skill
  scoring_config.yaml           # frozen selected scorer and prediction schema

  results.tsv                   # append-only experiment ledger
  ideas.md                      # running backlog and high-level results
  evaluator_issues.md           # notes if the frozen harness looks wrong

  data/
    README.md
    manifest.json
    train.jsonl
    validation.jsonl
    holdout.jsonl
    stress.jsonl

  runs/
    baseline_classifier/        # experiment type / idea branch
      README.md                 # findings and best hyperparameters for this branch
      001_baseline/
        candidate.py
        config.json
        run.log
        metrics.json
        plots/
          loss_curve.png
          score_curve.png
      002_threshold_tuning/
        candidate.py
        config.json
        run.log
        metrics.json
        plots/
          loss_curve.png
          score_curve.png
    feature_engineering/        # new structural branch
      README.md
      001_add_text_features/
        candidate.py
        config.json
        run.log
        metrics.json
        plots/
          loss_curve.png
          score_curve.png

  scripts/
    new_experiment.py
    new-experiment              # terminal entrypoint / wrapper
    verify.sh
    run_experiment.sh
    run_parallel_candidates.sh
    agent_loop.sh
    compare_results.py
```

---

## CLI and TUI

The installed package should expose a single `autoresearch` command for humans and agents:

```bash
autoresearch onboard
autoresearch tui
autoresearch index
autoresearch data validate
autoresearch data import ./data.csv --id-field id --label-field label --input-fields text
autoresearch verify runs/baseline_classifier/001_baseline
autoresearch loop
```

The onboarding flow should guide:

```text
API key / .env setup
problem.md creation
CSV / JSON / JSONL data import
id field selection
input column selection
label field selection
train / validation / holdout split fractions
baseline verification
```

The TUI should be a dashboard, not the source of truth. It should display project state, README front matter, run statuses, and metrics, while all durable state remains in files.

---

## Problem Scope Document

Every project should include a guided `problem.md` before agents begin experimenting.

This file describes what problem the loop is trying to solve, where the winning candidate is expected to be used, what counts as a useful baseline, and which constraints matter outside the evaluator. It gives the agent enough product and domain context to generate relevant ideas without making the evaluator editable.

`problem.md` should be human-readable, but structured enough that an agent can skim it quickly:

```md
---
name: example_classification_task
kind: problem_scope
status: active
primary_metric: validation_accuracy
baseline_goal: beat_majority_class_baseline
target_application: batch_decision_support
problem_scope_id: example_classification_task-v1
owner: human
---

# Problem

Describe the real-world problem in plain language.

## Goal

State the measurable objective the research loop should improve.

Example: improve validation accuracy over the baseline while preserving schema validity, runtime limits, and holdout discipline.

## Eventual Application

Describe where the winning candidate will be used:

- offline batch scoring
- online prediction endpoint
- ranking pipeline
- forecasting job
- optimization routine
- human decision-support workflow

## Baseline Goal

Define the first useful bar to clear:

- majority-class baseline
- simple threshold rule
- linear model
- existing production heuristic
- previous best run in `best/`

## Inputs and Outputs

Summarize the dataset rows the candidate receives and the prediction record it must emit. Link to `data/README.md` and `scoring_config.yaml` for exact schemas.

## Constraints

List practical constraints:

- runtime budget
- memory budget
- allowed dependencies
- interpretability needs
- production feature availability
- privacy or data-use restrictions

## Non-Goals

Name ideas the agent should avoid unless a human changes the scope.

## Useful Starting Ideas

Seed the initial backlog with a few plausible branches.
```

The agent should treat `problem.md` as guidance, not as scoring authority. The evaluator, scoring config, and datasets remain the source of truth for accept/reject decisions.

The baseline goal in `problem.md` should be intentionally modest. It is not the final ambition; it is the first sanity check that the harness, schema, scoring, and experiment generator are all working.

`problem.md` is a creation-time scope artifact. It should be written during project setup and then treated as immutable by the experiment loop. If the problem, application, baseline goal, or constraints materially change, create a new `problem_scope_id` and a new experiment scope rather than editing the existing file in place. The root `README.md` should document this rule so humans and agents know that post-creation scope changes invalidate the current experiment thread.

---

## Environment Defaults

The repo should ship with a reproducible local environment.

Required files:

```text
pyproject.toml     = pinned runtime and ML dependencies
Makefile           = setup, test, verify, and loop commands
.env.example       = documented environment variables
.env               = local copy created from .env.example, not committed
```

Default `.env.example` values should include:

```dotenv
AUTORESEARCH_SEED=42
AUTORESEARCH_TIMEOUT_SECONDS=3600
AUTORESEARCH_MAX_MEMORY_MB=0
OPENAI_API_KEY=placeholder
```

Candidates should default to deterministic execution with seed `42`. The seed should be configurable through `.env`, written into `config.json`, and copied into `metrics.json` so reruns are explainable.

Dependencies should be predeclared in `pyproject.toml`; candidates should not freely add new packages during ordinary runs. Start with standard scientific and ML dependencies such as NumPy, pandas, scikit-learn, PyTorch, matplotlib, and lightweight utility packages. New dependencies require a scope or harness-level decision, not a candidate-only mutation.

Project setup should copy `.env.example` to `.env` immediately, leaving placeholder values such as `OPENAI_API_KEY=placeholder` until a human supplies real credentials.

---

## Editable vs Frozen Boundary

### Editable by the agent

The agent has strict scope on what it can modify:

```text
strategy.py
features.py
models.py
config.py, if explicitly allowed
```

### Frozen / not editable by the agent

The agent may not modify:

```text
evaluator.py
dataset_loader.py
metrics.py
scoring.py
scoring_config.yaml
data/
scripts/compare_results.py
```

If the agent believes the evaluator is wrong, it should write a note in `evaluator_issues.md`, not edit the evaluator. The agent may read evaluator errors and consistency-check output, but it should not create ad hoc files to work around data or evaluator problems. If the blocker is a data issue, holdout leak, malformed split, or evaluator inconsistency, stop the loop and report a `data_blockage` or `data_analysis_issue` with the specific evidence needed for a human to decide whether the frozen layer should change.

### Enforcing the boundary mechanically

Policy alone is not enough; a single bad agent turn can silently edit the evaluator. The freeze must be enforced by the harness:

```text
freeze manifest    = frozen.lock file at repo root listing each frozen path and its sha256
verify-freeze      = scripts/verify_freeze.py recomputes hashes and fails on any drift
pre-run gate       = verify.sh runs verify-freeze before every evaluation; a dirty frozen
                     layer is a hard failure (status: frozen_layer_modified), not a warning
git enforcement    = pre-commit hook rejects commits touching frozen paths unless
                     AUTORESEARCH_HUMAN_OVERRIDE=1 is set by a human
filesystem         = chmod a-w on frozen files at setup time; cheap, reversible only
                     by an explicit human action
```

`metrics.json` must record the freeze state it was produced under:

```json
{
  "evaluator_sha256": "…",
  "scoring_config_sha256": "…",
  "dataset_manifest_sha256": "…",
  "frozen_lock_verified": true
}
```

Any result row whose recorded hashes do not match the current `frozen.lock` is automatically `stale_due_to_rescore`. This makes "the agent quietly bent the evaluator" detectable after the fact, not just forbidden in prose.

---

## Run Tree Discipline

`runs/` is a tree of experiment branches, not a bag of logs.

The top-level folder is the kind of experiment or architectural idea:

```text
runs/
  baseline_classifier/
  threshold_tuning/
  feature_engineering/
  calibrated_model/
  sequence_model/
```

Inside that folder, each numbered child is one runnable experiment variant:

```text
runs/threshold_tuning/
  README.md
  001_default_threshold/
  002_lower_threshold/
  003_calibrated_threshold/
```

Each numbered run must include:

```text
candidate.py        = exact Python candidate that was evaluated
config.json         = hyperparameters and dataset split references
run.log             = raw execution log
metrics.json        = frozen evaluator output
plots/              = generated graphs, including loss / score curves where applicable
README.md           = short finding, accept/reject call, and potential follow up candidates
```

The `plots/` directory should always exist. Plots are conditional on the system being evaluated: learned models should emit loss/score curves, deterministic heuristics can emit score comparison plots or a README note explaining why a plot is not applicable.

The branch-level `README.md` should summarize the most interesting result in that folder, including the strongest hyperparameters and why they mattered.

Use the same folder when only hyperparameters change. Create a new top-level folder when the model architecture or search direction changes. If a candidate is unrelated to the current thread, step back to the nearest shared parent or create a new root-level branch under `runs/`.

Structural changes that should create a new branch include:

```text
new feature family
new model class
new architecture
new attention head or sequence mechanism
new dependency
new training procedure
```

Schema-compatible output formatting inside `predict(row)` is a candidate correctness fix inside the current run. A new output post-processor outside `predict(row)` is not a run-level experiment; it is a harness/generator scope change and should stop the loop for human review.

`ideas.md` should stay append-only and should record:

```text
idea id
run folder path
hypothesis
status
best observed score
interesting hyperparameters tuned
high-level result
next branch to try
```

The source of truth for the current best candidate is the actual accepted run directory, not a mutable copy in `best/`. `best/` may exist as a convenience pointer or materialized export, but it must be regenerable from `runs/`, `results.tsv`, and the selected run metadata.

---

## Experiment Generator

Agents should not create experiment files by hand.

Use a terminal command, analogous to a database migration generator, from inside the experiment branch directory. It creates the next numbered experiment folder in the current directory with the evaluation wiring already in place:

```bash
cd runs/threshold_tuning
new-experiment calibrated_threshold --idea-id IDEA-014
```

The command should create:

```text
runs/threshold_tuning/
  README.md
  001_default_threshold/
  002_lower_threshold/
  003_calibrated_threshold/
    README.md
    candidate.py
    config.json
    run.log
    metrics.json
    plots/
```

The command infers the branch from the current directory, finds the highest existing numeric prefix, increments it, and writes the new folder beside the previous experiments. It should use atomic directory creation so a collision fails cleanly instead of overwriting an existing run. Multi-agent execution is not the initial target, but this guard prevents accidental duplicate run numbers.

A repo-root script can still back the command, but the human and agent interface should feel like this:

```bash
cd runs/<branch>
new-experiment <short_name> --idea-id <idea_id>
```

For root-level architectural branches, create the branch folder first, then run the generator inside it:

```bash
mkdir -p runs/feature_engineering
cd runs/feature_engineering
new-experiment add_text_features --idea-id IDEA-021 --root
```

The generated `candidate.py` should include all imports, evaluator adapter code, schema references, and scoring hooks. The agent should only edit one clearly marked function:

```python
def predict(row: dict) -> dict:
    """Return one schema-valid prediction for one dataset row."""
    # Agent edits only this function.
    return {
        "id": row["id"],
        "predicted_label": "accept",
        "confidence": 0.5,
    }
```

Everything outside `predict()` is boilerplate owned by the generator:

```text
load scoring_config.yaml
load prediction schema metadata
adapt evaluator row input into predict(row)
validate local output shape before evaluator submission
emit structured predictions for train / validation
write candidate metadata for the run
```

The generated `config.json` should point at the frozen scorer and schema:

```json
{
  "idea_id": "IDEA-014",
  "problem_scope_id": "example_classification_task-v1",
  "branch": "threshold_tuning",
  "run_name": "003_calibrated_threshold",
  "parent": "runs/threshold_tuning/002_lower_threshold",
  "created_from_directory": "runs/threshold_tuning",
  "scoring_config": "scoring_config.yaml",
  "primary_scorer": "accuracy",
  "scorer_id": "accuracy-v1",
  "schema_version": 1,
  "dataset_version": "dataset-v1",
  "seed": 42,
  "prediction_schema": "scoring_config.yaml:prediction_schema",
  "splits": ["train", "validation"]
}
```

The generated `README.md` should include parseable front matter immediately:

```yaml
---
name: 003_calibrated_threshold
kind: experiment_run
status: created
parent: runs/threshold_tuning/002_lower_threshold
idea_id: IDEA-014
problem_scope_id: example_classification_task-v1
primary_scorer: accuracy
scorer_id: accuracy-v1
schema_version: 1
dataset_version: dataset-v1
seed: 42
prediction_schema: scoring_config.yaml:prediction_schema
tags:
  - threshold
  - hyperparameter_sweep
summary: Created from IDEA-014. Awaiting first verification run.
next:
  - Edit only predict(row) in candidate.py.
  - Run scripts/verify.sh runs/threshold_tuning/003_calibrated_threshold.
---
```

The generator should refuse to run if:

```text
scoring_config.yaml is missing
prediction_schema is missing
the current directory is not inside runs/
the next numeric run directory already exists
there is no previous run and --root is not explicitly passed
the command would create files outside the current branch folder
```

`new-experiment` should be reliable from any `runs/<branch>` directory. If required fields are missing, it should prompt on stdin using clean text prompts or simple multiple-choice selections so a coding agent can fill them in without a GUI:

```text
short name:
idea id:
parent run:
tags:
```

This keeps experiment creation boring and repeatable. The creative surface is one function; the harness, schema, scorer, metadata, and directory shape are created deterministically.

---

## README Front Matter Index

Every `README.md` inside of `/runs` should start with YAML front matter that is easy for a CLI to parse.

The front matter is useful for quick traversal layer and function. It lets an agent scan the tree, find stale branches, identify promising runs, and decide where to poke next without rereading every artifact. O(n) max and min look ups across the tree without a sorted replica list of experiments.

Recommended front matter:

```yaml
---
name: threshold_tuning
kind: experiment_branch
status: active
parent: baseline_classifier/001_baseline
best_run: 003_calibrated_threshold
best_score: 1.184
best_metric: primary_score
tags:
  - threshold
  - heuristic
  - hyperparameter_sweep
summary: Threshold tuning improved validation accuracy until calibration became the limiting factor.
next:
  - Test calibrated confidence scores.
  - Compare against feature_engineering branch.
---
```

Run status must use a fixed enum:

```text
created
running
schema_failed
failed
rejected
accepted
promoted
archived
stale_due_to_rescore
sandbox_violation
frozen_layer_modified
```

Use `archived` for runs that are intentionally kept for history but no longer active. Use `stale_due_to_rescore` when a scorer, schema, or dataset version changed and the old metrics are no longer comparable.

Use the same shape at different levels:

```text
README.md                         = project metadata and current best branch
problem.md                        = problem scope, target application, and baseline goal
data/README.md                    = dataset schema, split names, and source notes
runs/<branch>/README.md           = branch hypothesis, status, best run, best hyperparameters
runs/<branch>/<NNN_name>/README.md = run finding, decision, metrics pointer, next step
```

The front matter should be useful but not authoritative for scoring. `metrics.json`, `config.json`, `results.tsv`, and the frozen evaluator output remain the source of truth.

Every run-level README front matter and `config.json` must include:

```text
problem_scope_id
dataset_version
schema_version
scorer_id
seed
status
```

Add a walk / traversal command or function in the shell files and scripts:

```bash
python scripts/readme_index.py --root . --format table
python scripts/readme_index.py --root . --kind experiment_branch --status active
python scripts/readme_index.py --root . --format json > runs/readme_index.json
```

`scripts/readme_index.py` should:

```text
walk the repo for README.md files
parse YAML front matter if present
include README path and containing directory
emit table, json, or tsv
support filters for kind, status, tag, and parent
sort by kind, status, best_score, and updated timestamp when available
```

This gives the agent a cheap first pass to get up to speed when invoking a new session:

```text
1. Run `python scripts/readme_index.py --root . --status active`.
2. Find active branches with no recent accepted run.
3. Find failed branches with useful next ideas.
4. Pick the next branch before opening larger logs or plots.
```

---

## Evaluation Harness

The evaluation harness should be able to provide a single primary score plus a set of diagnostic metrics.

`evaluator.py` should be structured enough that the frozen boundary is obvious:

```text
load_manifest()
load_split(split_name)
load_scoring_config()
load_expected_output_schema()
run_candidate(candidate, dataset)
validate_candidate_outputs(predictions, schema)
run_consistency_checks(predictions, dataset)
compute_metrics(predictions, labels)
compute_primary_score(metrics)
write_artifacts(run_dir)
main()
```

The evaluator owns dataset loading, split selection (`train`, `validation`, `holdout`, or `stress` as your options), candidate execution, scoring, artifact writing, and guardrail failures. Candidate code should only expose the prediction interface.

### Candidate Execution Sandbox

The single largest reward-hacking surface is that `candidate.py` is arbitrary Python. Without isolation, a candidate can `open("data/validation.jsonl")`, read the labels, and emit a perfect score. The evaluator must treat candidate code as untrusted:

```text
label stripping     = the evaluator must remove label / target fields from every row
                      before it reaches predict(row); candidates never see labels at
                      inference time, on any split
subprocess isolation = run the candidate in a separate process, not in the evaluator's
                      interpreter, so it cannot monkeypatch scoring or read evaluator state
filesystem scope    = run the candidate with cwd set to its run directory; deny reads of
                      data/ (especially validation labels and holdout.jsonl) via OS-level
                      controls where available (sandbox-exec on macOS, bwrap/landlock on
                      Linux, or at minimum file permissions owned by an evaluator user)
no network          = candidate runs get no network egress by default; a candidate that
                      needs the network is a scope change, not an experiment
resource limits     = enforce AUTORESEARCH_TIMEOUT_SECONDS and AUTORESEARCH_MAX_MEMORY_MB
                      with hard kills (ulimit / rlimit / cgroup), and a per-run disk quota
                      so a runaway candidate cannot fill the volume
import allowlist    = the evaluator should reject candidates importing subprocess, socket,
                      ctypes, or other escape-hatch modules unless explicitly allowed in
                      scoring_config.yaml
```

Training is the one place candidates legitimately need labeled train data. Handle this by having the evaluator (or generator boilerplate) pass the train split *with labels* as an in-memory argument to a `fit(train_rows)` hook, while validation/holdout/stress rows always arrive label-stripped through `predict(row)`. The candidate never gets a path to the raw split files.

Any sandbox violation (denied file access, network attempt, killed by limit) should be written as a structured evaluator failure with `status: sandbox_violation` and treated as an automatic rejection — and repeated violations in one branch should stop the loop for human review, since they suggest the agent is probing the boundary.

### Prediction Schema and Scoring

Each dataset row should define the fields the candidate must predict or produce. The evaluator validates the candidate output against that expected schema before any scoring happens.

Default behavior:

```text
candidate reads one dataset row
candidate emits one structured prediction record
evaluator validates the record against the frozen schema
evaluator scores valid predictions against labels / expected fields
primary_score defaults to validation accuracy
```

The evaluator should run consistency checks before scoring:

```text
all required splits produced predictions
row counts match expected split row counts, unless missing-row tolerance applies
row IDs are present
row IDs are unique
row IDs belong to the evaluated split
no extra predictions are emitted
ordering is deterministic or explicitly normalized before scoring
prediction records match the configured schema
metrics.json is well-formed and complete
```

Invalid records may be dropped only within the configured tolerance. The default tolerance is `5%` faulty rows for train/validation evaluation. If failures exceed the tolerance, the evaluator should return `schema_validation_failed` or `consistency_check_failed` and skip scoring. Holdout should default to stricter behavior unless the scoring config explicitly says otherwise.

The schema should live in frozen harness config, not in editable candidate code:

```yaml
task: classification
schema_version: 1
scorer_id: accuracy-v1
primary_scorer: accuracy
fault_tolerance:
  validation_invalid_row_pct: 5.0
  holdout_invalid_row_pct: 0.0
prediction_schema:
  type: object
  required:
    - id
    - predicted_label
    - confidence
  properties:
    id:
      type: string
    predicted_label:
      type: string
      enum: ["accept", "reject"]
    confidence:
      type: number
      minimum: 0.0
      maximum: 1.0
```

If a candidate emits the wrong shape, the evaluator should fail before scoring and write a structured validation error:

```json
{
  "status": "schema_validation_failed",
  "run_id": "runs/classifier_baseline/004_confidence_head",
  "expected_schema": "scoring_config.yaml:prediction_schema",
  "issues": [
    {
      "row_id": "validation-0182",
      "path": "$.predicted_label",
      "message": "required field missing"
    },
    {
      "row_id": "validation-0187",
      "path": "$.confidence",
      "message": "expected number between 0.0 and 1.0, got string"
    }
  ]
}
```

This is not a harness failure. It is candidate feedback. The coding agent should read the validation error, fix `strategy.py` / model output formatting, and rerun the same experiment.

### Primary score

The primary score should be a scalar that the agent can optimize after schema validation passes.

Initially, `primary_score` is a decimal between `0.000` and `1.000` representing validation accuracy against the dataset labels.

Other scoring mechanisms are allowed, but they must be selected by frozen harness config, not edited by the experiment agent. This lets the same evaluator support accuracy, balanced accuracy, regression loss, ranking metrics, weighted business metrics, or future reinforcement-learning objectives without letting the agent redefine winning mid-run.

Example:

```yaml
primary_scorer: accuracy
available_scorers:
  accuracy:
    kind: classification_accuracy
    split: validation
  balanced_accuracy:
    kind: balanced_classification_accuracy
    split: validation
  regression_rmse:
    kind: regression_rmse
    split: validation
    maximize: false
```

The rule is:

```text
candidate output schema = frozen
scoring function = frozen
selected primary scorer = frozen for a run
candidate implementation = editable
```

Schema and scorer changes roll forward. Do not keep a growing pile of old schema files in the repo. When the schema or scorer changes:

```text
increment schema_version and/or scorer_id
overwrite the current scoring_config.yaml intentionally
use git diff to review the changed scoring/schema delta
mark previous run rows stale_due_to_rescore
rerun relevant experiments against the current evaluator and scoring config
append new rows to results.tsv with the new schema_version and scorer_id
```

Old runs remain as historical artifacts, but old scores should not be compared against new scores unless they have been rerun under the current schema and scorer.

---

## Train / Validation / Holdout Structure

The harness should separate data into at least four groups:

```text
train       = used for candidate development
validation  = used for accept/reject
holdout     = rarely used, final check only
stress      = adversarial or weird regimes
```

Keep the data directory explicit, simple, and concise:

```text
data/
  README.md
  manifest.json
  train.jsonl
  validation.jsonl
  holdout.jsonl
  stress.jsonl
```

`manifest.json` should define split names, schema version, row counts, source notes, allowed evaluator modes, and any immutable assumptions. `README.md` should explain the fields at a human level. The agent may read these files but may not edit them.

The agent should optimize against train and validation. It should not see holdout results on every run, otherwise it will overfit the holdout.

The agent is allowed to comb through the evaluation dataset, but it is not allowed to see or comb through the holdout set. The holdout set should never go in context of the language model. Policy is the floor, not the mechanism — enforce it from day one:

```text
ownership      = data/holdout.jsonl is owned by a separate evaluator user (or stored
                 outside the repo working tree entirely) and is unreadable by the user
                 the agent runs as; the evaluator subprocess escalates to read it
deny rules     = the agent harness config (e.g. permission deny rules) blocks Read/Bash
                 access to data/holdout.jsonl and any holdout-derived artifact paths
output hygiene = the evaluator never writes raw holdout rows, per-row holdout errors,
                 or holdout label distributions into run.log, metrics.json, or plots;
                 holdout results surface only as the aggregate primary score and a
                 pass/fail guardrail flag
validation cap = track how many times each candidate lineage has been scored against
                 validation; a branch that has consumed hundreds of validation reads is
                 overfitting validation the same way holdout leakage would — surface an
                 evaluation-count warning in the branch README front matter
```

If the agent sees holdout labels, holdout distributions, or derived holdout leakage in `data/README.md`, `manifest.json`, logs, or artifacts, it should stop and report a data blockage issue. The data should be pruned or regenerated before the loop continues, and the agent should clear that leaked context before using holdout-derived information.

The evaluation dataset can use basic transformation functions to parse through large pieces of data using `pandas` with those transformations sitting inside of scripts. You should do this because some of the datasets you'll wrangle with will be quite large (250k+ rows). Translation to columnar data formats and reads from that might become useful.

`stress.jsonl` should contain adversarial, rare, corrupted, shifted, or boundary-condition examples. Later, a dedicated generation agent or script can propose new stress rows from observed failure modes, but those generated stress cases should be reviewed before they become part of the frozen evaluator set.

Recommended policy:

```text
Run train + validation every experiment.
Run holdout every 10 accepted improvements.
Run stress every 5 accepted improvements or before merge.
```

`results.tsv` is append-only. If a row is wrong, do not edit it in place. Append a correction row with:

```text
correction_of
supersedes_run_id
correction_reason
```

Consumers should treat the latest non-superseded row for a run as the active ledger entry.

Append-only must also be enforced, not just requested: `verify.sh` should fail if `git diff` shows modified or deleted existing lines in `results.tsv` (new trailing lines only), and each row should carry the `metrics.json` sha256 it was derived from so a hand-edited score is detectable against the run artifacts.

---

## Candidate Generation

The agent should not make one random edit at a time forever. It should maintain an idea backlog informed by both the general problem statement and the previous outcomes from ideas and observed outcomes.

Candidate categories (initial):

```text
classical heuristic
classical polynomial regression
hyperparameter sweep
model class change
constraint handling change
regime-specific branch
performance optimization
ablation
ensemble
learned component
```

Only after those are exhausted should the agent move into heavier learned models and can do research on ArXiv to find additional papers to go model after:

```text
linear regression model
logistic classifier
gradient boosted trees
small MLP
sequence model over ordered examples
transformer-style model over structured history
```

The system should strongly prefer the simplest strategy that improves the metric with the greatest model interpretability.

---

## Parallel Candidate Runs

A useful harness should support parallel exploration in the file tree, but the initial execution model should stay single-agent.

Do not run multiple coding agents by default. It burns tokens quickly and loses context between agents. Parallel branches can still exist as candidate directions, but one agent should choose, run, and evaluate them sequentially until there is enough infrastructure to coordinate multi-agent work safely.

Recommended pattern:

```text
main-best
  branch/candidate-001-threshold-tuning
  branch/candidate-002-feature-normalization
  branch/candidate-003-calibrated-classifier
  branch/candidate-004-tree-model
```

Each branch gets:

```text
one candidate idea
one run tree folder
one numbered run directory per variant
one candidate.py per run
one plots/ directory per run
one metrics.json
one log
one readable README
one row in results.tsv
```

Parallel candidates should be merged only if they improve validation and do not degrade holdout/stress checks.

### Parallel execution loop

```text
1. Spawn N candidate branches from current best.
2. Give each branch a different idea from ideas.md.
3. Run experiments independently.
4. Compare primary_score on validation.
5. Promote the best candidate if it clears guardrails.
6. Archive failed candidates with notes.
7. Generate new candidates from observed results.
```

This is better than a single linear hill climb because it reduces local optimum risk.

---

## Branching Strategy

The agent should maintain three classes of branches:

```text
best
exploration
ablation
```

### `best`

The current best validated strategy.

Only promoted changes land here.

### `exploration`

Riskier ideas that may fail but can discover new directions.

Examples:

```text
calibrated classifier
new feature transform
nonlinear decision boundary
dataset-segment-specific policy
```

### `ablation`

Remove or isolate a component to understand whether it is actually helping.

Examples:

```text
disable calibration layer
disable one feature transform
disable segment-specific rule
remove one feature from learned model
```

Ablations are critical because coding agents will otherwise accumulate complexity that appears useful but is not.

Branching in `runs/` should mirror this discipline:

```text
runs/best/
runs/exploration/<idea_name>/
runs/ablation/<component_name>/
```

Do not keep hill-climbing inside a dead branch indefinitely. If the results say the current architecture has plateaued, walk back up the tree, pick another promising branch from `ideas.md`, or start a new root-level idea.

---

## Hyperparameter Hill-Climbing Heuristics

The agent should follow simple search discipline before making architecture-level changes.

### When a change helps

If a parameter change improves validation:

```text
try a slightly larger move in the same direction
try a smaller move in the same direction
test interaction with the nearest related parameter
run stress check
```

Example:

```text
decision_threshold = 0.55 improves score
try 0.60
try 0.65
try 0.525
test with calibrated confidence
```

### When a change hurts

If a change hurts:

```text
revert
try the opposite direction if the hypothesis is still plausible
or mark the idea as failed
```

Example:

```text
lowering the threshold increases false positives too much
try conditional thresholding only for high-confidence examples
```

### When results are noisy

If results are noisy:

```text
rerun the same commit
increase evaluation coverage
compare median score across seeds / shards
prefer robust improvements over one-off wins
```

### Prefer coarse-to-fine search

```text
large sweep
→ identify promising range
→ refine range
→ test interactions
→ freeze simple default
```

---

## Progression From Classical to Learned Models

The agent should not immediately reach for highest and most complex work. Most additional experimentation should be conscious of scaling up cores in the box it's working against.

Also important to start blocking if you can't run additional experiments unless you have a larger box or a GPU. This should inform how you generate candidates.

Recommended progression (can exponentiate through these quickly):

```text
1. Fixed heuristic baseline
2. Hand-tuned parameters
3. Feature-conditioned heuristic
4. Linear model
5. Tree-based model
6. Small neural net -> Scaled neural net
7. Sequence-aware model
8. Transformer-style architecture
```

### Stage 1: classical baseline

```text
predict the majority class, mean value, or simplest valid default
apply one or two hand-tuned thresholds
emit schema-valid confidence values
```

### Stage 2: feature-conditioned heuristic

```text
condition decisions on simple, inspectable input fields
add normalized numeric features
add basic text or categorical transforms when available
```

### Stage 3: learned tabular / text models

Predict:

```text
class label, score, ranking position, or regression value
confidence or uncertainty
calibration diagnostics
```

Use the model to adjust:

```text
prediction label
decision threshold
confidence
abstain / fallback behavior
```

### Stage 4: sequence models

Use ordered history or multi-row context only when the dataset actually supports it:

```text
recent events
temporal trend
group-level context
prior predictions
```

### Stage 5: transformer-style models

Only consider this if:

```text
classical and small models plateau
there is enough data
evaluation is robust
runtime constraints are understood
the model can be served within the intended budget
```

A complex model that cannot run in the intended environment is not a real improvement.

---

## Plateau Detection

The agent should inspect generated plots, score curves, loss curves, and noisy-run summaries before deciding that a branch has plateaued.

Useful plateau signals:

```text
no accepted improvement after several valid runs
loss curves flatten while validation score stops improving
multiple epochs produce negligible metric movement
candidate improvements are smaller than run-to-run noise
validation changes are unstable across seeds or shards
stress checks regress even when validation improves
```

When a branch plateaus, the agent should summarize the evidence in the branch README, mark the branch `archived` if appropriate, and walk back up the run tree to a different branch or root-level idea.

---

## Agent Loop: How to Keep It Running

The markdown instruction alone is not enough. Many coding agents eventually stop.

Use an external loop, and keep a one-command verification path.

Experiment commands may be long-running. Scripts should use generous default timeouts, write logs continuously, and keep the evaluation in a background process when appropriate so progress can be tailed without losing artifacts:

```text
timeout defaults should come from .env
stdout/stderr should stream into run.log
process id should be recorded when a background run starts
timeouts, memory exits, dependency import errors, disk-full errors, and malformed metrics.json should become structured evaluator failures
```

### Verification script

Every candidate should be runnable through the same shell entrypoint:

```bash
#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="${1:?usage: scripts/verify.sh <run-dir>}"
CANDIDATE="${RUN_DIR}/candidate.py"

test -f "$CANDIDATE"
python evaluator.py \
  --candidate "$CANDIDATE" \
  --data-manifest data/manifest.json \
  --splits train,validation \
  --run-dir "$RUN_DIR"
```

The agent loop may wrap this script, but it should not invent a separate verification path per experiment.

`verify.sh` should resolve the repo root from the script location rather than trusting the caller's current directory. If required values are missing, it should prompt on stdin with simple text or multiple-choice fields that a coding agent can answer:

```text
run directory:
splits to evaluate:
background run? [yes/no]
timeout seconds:
```

### Simple shell loop

```bash
#!/usr/bin/env bash
set -euo pipefail

while true; do
  codex exec \
    "Read problem.md and skills/autoresearch/SKILL.md, run scripts/readme_index.py, inspect ideas.md, results.tsv, and the current runs tree. Create new candidates by cd'ing into the chosen runs/<branch> directory and running new-experiment, then run scripts/verify.sh. Do not summarize unless blocked. If the last experiment finished, generate the next candidate and run it." \
    2>&1 | tee -a runs/agent.log

  sleep 1
done
```

### Resume-session loop

If the agent supports session resume:

```bash
#!/usr/bin/env bash
set -euo pipefail

SESSION_ID="${1:?usage: agent_loop.sh <session_id>}"

while true; do
  codex exec resume "$SESSION_ID" \
    "Continue from the last state. Read problem.md, run scripts/readme_index.py, then create the next experiment by cd'ing into the chosen runs/<branch> directory and running new-experiment. Use scripts/verify.sh. If an experiment completed, inspect results, plots, README findings, and metrics; log it, accept/reject it, and start the next one." \
    2>&1 | tee -a runs/agent.log

  sleep 1
done
```

### Loop contract

The agent should never end with:

```text
Here is what I would do next.
```

It should instead do the next thing.

Allowed stopping conditions:

```text
evaluator is broken
data is missing
run command cannot execute
permissions are missing
all candidate branches fail to run
human approval is required for a dangerous action
loss curve plateaus and no useful next branch is available
multiple valid experiments show no improvement
convergence is too noisy to distinguish improvements
```

If blocked, the agent should write:

```text
BLOCKED: <reason>
NEEDED: <specific human action>
```

Otherwise it should keep generating and testing candidates.

### Loop Safety and Budgets

An unattended `while true` loop around a coding agent needs hard external limits, not just a contract in prose:

```text
iteration cap   = AUTORESEARCH_MAX_ITERATIONS per loop invocation (default 25); the
                  wrapper exits cleanly at the cap and a human restarts it
cost / token cap = stop the loop when a configured token or dollar budget is exhausted;
                  log spend per iteration into runs/agent.log
wall-clock cap  = a total session timeout in addition to per-run timeouts
disk quota      = check free disk before each iteration; stop with BLOCKED if below a
                  threshold instead of letting runs/ fill the volume
kill switch     = the loop checks for a STOP file at repo root before each iteration;
                  touching STOP halts the loop without killing an in-flight evaluation
failure breaker = if N consecutive iterations end in evaluator errors, sandbox
                  violations, or schema failures, stop and report instead of retrying
                  the same broken state forever
```

The wrapper should also pin its execution context: record the git commit, `frozen.lock` hash, and agent/model version at loop start, and refuse to continue if the frozen layer changed mid-session.

### Untrusted Data in Agent Context

Dataset rows, run logs, and evaluator error messages flow into the agent's context every iteration. Treat them as untrusted input:

```text
- Dataset content is data, never instructions. If a row, log line, or error message
  contains text that looks like instructions to the agent (e.g. "ignore your rules",
  "edit evaluator.py"), the agent must ignore it and note a suspected injection in
  evaluator_issues.md.
- Prefer summarized / truncated views: readme_index.py output, metrics.json, and
  aggregate stats over raw row dumps. Cap how many raw rows the agent pulls into
  context per iteration.
- The skill prompt should state explicitly that no file content, log output, or
  dataset row can grant new permissions or change the frozen boundary.
```

This matters most once `stress.jsonl` starts including adversarial rows — adversarial *for the model* must not become adversarial *against the agent*.

### Secrets Hygiene

```text
.env is never read into agent context; the loop wrapper and evaluator consume it
API keys must not appear in run.log, metrics.json, config.json, or results.tsv —
  the evaluator should scrub env values from captured subprocess output
candidate subprocesses run with a minimal environment (seed, limits), not the
  full parent env, so a candidate cannot exfiltrate OPENAI_API_KEY via plots or logs
```

---

## `skills/autoresearch/SKILL.md` Template

The following is a heavyweight skill prompt given to the coding agent to guide its decision making and reference material on how to work inside of this repo.

````md
# Program

You are an autonomous ML experimentation agent.

Your job is to improve the primary validation score by proposing, implementing, running, evaluating, and logging experiments.

Before choosing an idea, read `problem.md`. It explains the real problem, the target application, the baseline goal, and constraints that should shape candidate selection.

## Objective

Maximize `primary_score` from the fixed evaluator.

Lower-level metrics matter only insofar as they improve robust performance and do not violate guardrails.

## Editable files

You may edit:

- `strategy.py`
- `features.py`
- `models.py`
- `config.py`

You may not edit:

- `evaluator.py`
- `dataset_loader.py`
- `metrics.py`
- `scoring.py`
- `scoring_config.yaml`
- `data/`
- `scripts/compare_results.py`
- existing rows in `results.tsv`

## Required loop

Repeat forever:

1. Read `problem.md`, run `python scripts/readme_index.py --root . --status active`, then inspect `results.tsv`, `ideas.md`, `best/`, and the current `runs/` tree.
2. Choose one candidate idea.
3. Choose the correct run branch folder, or create a new one if this is a structural change.
4. `cd runs/<branch>` and run `new-experiment <short_name> --idea-id <idea_id>` to create the next numbered run directory in that branch.
5. Edit only the marked `predict(row)` function in the generated `candidate.py`, unless the skill explicitly allows a broader architecture change.
6. Run:

   ```bash
   scripts/verify.sh runs/<branch>/<NNN_name>
   ```

7. Read `metrics.json`, `run.log`, generated plots, and the run README.
8. Append one row to `results.tsv`.
9. If validation `primary_score` improved and guardrails passed, keep the commit and mark it accepted.
10. If not, reset to the previous best commit and mark it rejected.
11. Update `ideas.md` with the high-level result and next branch to try.
12. Start the next experiment.

Do not stop after one experiment.

## Guardrails

Reject any candidate with:

- schema validation failures that the candidate cannot fix
- evaluator errors
- data leakage
- holdout degradation after holdout check
- materially worse secondary metrics without compensating primary-score improvement
- excessive runtime or memory usage
- unsupported dependencies

If the evaluator returns `schema_validation_failed`, do not mark it as a scored rejection. Treat it as candidate feedback, fix the output shape in editable code, and rerun the same numbered experiment until it either validates or is abandoned.

## Experiment row format

Append to `results.tsv`:

```tsv
timestamp commit branch idea_id status primary_score validation_accuracy holdout_score runtime_seconds memory_mb scorer_id schema_version dataset_version correction_of supersedes_run_id notes
```

## Candidate discipline

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

## Stopping

You may only stop if blocked.

If blocked, write:

```text
BLOCKED: <reason>
NEEDED: <specific human action>
```

Otherwise continue looping.
````

---

## Acceptance Policy

A candidate is accepted only if:

```text
validation primary_score improves
no hard guardrails fail
diagnostic metrics are not suspicious
implementation remains simple enough to reason about
```

A candidate is promoted to best only if:

```text
validation improves
stress does not degrade materially
holdout passes when scheduled
```

A candidate should be rejected if:

```text
it improves score by exploiting evaluator weakness
it increases hidden risk
it adds large complexity for tiny gain
it creates runtime, memory, or dependency problems
it requires data unavailable in production
```

---

## Anti-Overfitting Rules

1. Do not run holdout every experiment.
2. Do not let the agent edit holdout data or scoring.
3. Keep stress scenarios separate from normal validation.
4. Prefer improvements that work across dataset segments and time periods.
5. Track complexity cost.
6. Rerun top candidates on multiple seeds or evaluation shards.
7. Use ablations to remove unnecessary complexity.
8. Require production-feasible features only.

Reject any feature that depends on future information, labels, holdout leakage, or evaluator-only artifacts.

---

## Minimum Viable Implementation

The minimum useful version requires:

```text
one editable strategy file
one frozen evaluator
one train/validation split
one scalar primary score
one `problem.md`
one results.tsv
one `skills/autoresearch/SKILL.md`
one loop script
one `.env.example`
one `pyproject.toml`
one `Makefile`
```

Do not start by building a giant framework.

Build the smallest thing that lets an agent run 25 experiments safely.

---

## Roadmap

### Phase 1: single-agent serial hill climb

```text
fixed evaluator
single strategy.py
single agent loop
results.tsv
accept/reject by validation score
```

### Phase 2: parallel candidates

```text
N branches
N agents or N sequential candidate slots
leaderboard
automatic comparison
best promotion
```

### Phase 3: holdout and stress

```text
holdout schedule
stress suite
guardrail thresholds
complexity tracking
```

### Phase 4: learned components

```text
feature store
linear / tree / small NN models
model serialization
runtime checks
production feature availability checks
```

### Phase 5: production handoff

```text
convert winning strategy into production-safe module
add tests
add monitoring
add kill switches
add explainability logs
```

---

## Core Principle

The agent should be creative, but the harness should be conservative.

A good harness makes it easy for the agent to discover real improvements and hard for the agent to fake progress.

The goal is to create an agentic research loop that can repeatedly improve a candidate implementation against fixed datasets, schemas, and scoring rules before any idea is considered for production.

Good luck.
