# Autoresearch V2

## Purpose

This document defines a lightweight harness for using coding agents to rapidly improve ML-driven or algorithmic systems through controlled experimentation.

The motivating example is `prcm-dkex`: improving the pricing algorithm for a DKEX market-making system. The same structure should generalize to other ML, simulation, ranking, forecasting, optimization, and strategy-search problems.

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
   - Agents may not edit the evaluator / evaluation harness, holdout data, scoring rules, or replay construction.
   - The harness must prevent reward hacking wherever possible.
     - Important to generate adversarial tests to mitigate against this.

3. **Parallel candidate generation**
   - Multiple agents or multiple branches should be able to test ideas concurrently.
     - Should be in different branches of code, so not an issue to have separate agents creating and running these experiments.
   - Good ideas should be merged into a best-so-far branch.
     - Space for improvement should be measured here (ability to hill climb train dataset accuracy)
   - Bad ideas should be discarded but logged.
     - There should be high level descriptions alongside `name`, `description`, and `tags` when describing these files (like YAML file for skills `name` and `description` tags).

4. **Generalized beyond LLMs**
   - Works for pricing algorithms, ranking models, feature engineering, forecasting, optimization, RL-like policies, and classical ML.
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
     - Graphs and loss curves are highly encouraged to look at and ingested, and replay sessions should be deduced at pretty in depth levels as well.

---

## Mental Model

Inspired by `karpathy/autoresearch`, but shaped for a frozen evaluator and a file-backed experiment tree:

```text
skills/autoresearch = skill breakdown for how to run autoresearch
strategy.py         = editable candidate surface
evaluator.py        = frozen evaluation harness
data/               = frozen train / validation / holdout jsonl datasets
results.tsv         = experiment ledger
ideas.md            = running idea log, branch notes, and high-level results
best/               = current best-so-far implementation
runs/               = file-tree of experiment branches, versions, logs, plots, and findings
scripts/verify.sh   = shell entrypoint for one complete evaluation loop
pr                  = external Ralph loop around Codex
```

The coding agent is not the source of truth. The harness is.

The agent proposes mutations. The evaluator decides whether the mutation helped.

Every experiment must be reproducible from the files it leaves behind: candidate Python, frozen evaluator command, metrics, graphs, and a short human-readable README. Hyperparameter tuning stays inside the current run branch. Structural architecture changes create a new branch folder. Completely different ideas should step back up the tree and start from a different branch or from the root.

---

## Recommended Repository Structure

```text
agentic-experiments/
  README.md
  architecture.md

  skills/
    autoresearch/
      SKILL.md                  # how the agent runs the loop

  strategy.py                   # editable candidate surface
  features.py                   # optionally editable
  models.py                     # optionally editable
  config.py                     # editable only if allowed

  evaluator.py                  # frozen
  replay.py                     # frozen
  metrics.py                    # frozen
  scoring.py                    # frozen

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
    heuristic_spread/           # experiment type / idea branch
      README.md                 # findings and best hyperparameters for this branch
      001_baseline/
        candidate.py
        config.json
        run.log
        metrics.json
        plots/
          loss_curve.png
          score_curve.png
      002_wider_spread/
        candidate.py
        config.json
        run.log
        metrics.json
        plots/
          loss_curve.png
          score_curve.png
    learned_fill_model/         # new structural branch
      README.md
      001_logistic_fill/
        candidate.py
        config.json
        run.log
        metrics.json
        plots/

  scripts/
    verify.sh
    run_experiment.sh
    run_parallel_candidates.sh
    agent_loop.sh
    compare_results.py
```

For `prcm-dkex`, the equivalent would be:

```text
strategy.py        = quote pricing algorithm
replay.py          = historical book / trade / order replay
evaluator.py       = fixed market-making simulator
metrics.py         = PnL, drawdown, adverse selection, fill quality, inventory risk
data_splits.py     = train / validation / holdout market-date splits
```

---

## Editable vs Frozen Boundary

### Editable by the agent

The agent may modify:

```text
strategy.py
features.py
models.py
config.py, if explicitly allowed
```

For DKEX pricing, this includes:

```text
midprice estimation
spread logic
skew logic
inventory adjustment
volatility adjustment
market regime features
fill-probability estimates
adverse-selection avoidance
cancel/replace thresholds
stale-book behavior
simple learned pricing models
```

### Frozen / not editable by the agent

The agent may not modify:

```text
evaluator.py
replay.py
metrics.py
scoring.py
data/
scripts/compare_results.py
```

For DKEX, the agent must not alter:

```text
historical replay data
train/validation/holdout splits
fee assumptions
latency assumptions
fill simulation rules
slippage assumptions
market close / suspend rules
scoring weights
risk penalties
```

If the agent believes the evaluator is wrong, it should write a note in `evaluator_issues.md`, not edit the evaluator.

---

## Run Tree Discipline

`runs/` is a tree of experiment branches, not a bag of logs.

The top-level folder is the kind of experiment or architectural idea:

```text
runs/
  fixed_spread/
  volatility_adjusted_spread/
  inventory_skew/
  learned_fill_model/
  sequence_model/
```

Inside that folder, each numbered child is one runnable experiment variant:

```text
runs/inventory_skew/
  README.md
  001_linear_skew/
  002_stronger_skew/
  003_skew_with_volatility_gate/
```

Each numbered run must include:

```text
candidate.py        = exact Python candidate that was evaluated
config.json         = hyperparameters and dataset split references
run.log             = raw execution log
metrics.json        = frozen evaluator output
plots/              = generated graphs, including loss / score curves where applicable
README.md           = short finding, accept/reject call, and next idea
```

The branch-level `README.md` should summarize the most interesting result in that folder, including the strongest hyperparameters and why they mattered.

Use the same folder when only hyperparameters change. Create a new top-level folder when the model architecture or search direction changes. If a candidate is unrelated to the current thread, step back to the nearest shared parent or create a new root-level branch under `runs/`.

`ideas.md` should stay append-only and should record:

```text
idea id
run folder
hypothesis
status
best observed score
interesting hyperparameters
high-level result
next branch to try
```

---

## Evaluation Harness

The evaluation harness should produce a single primary score plus a set of diagnostic metrics.

`evaluator.py` should be structured enough that the frozen boundary is obvious:

```text
load_manifest()
load_split(split_name)
run_replay(candidate, dataset)
compute_metrics(events)
compute_primary_score(metrics)
write_artifacts(run_dir)
main()
```

The evaluator owns dataset loading, split selection, replay, scoring, artifact writing, and guardrail failures. Candidate code should only expose the strategy interface.

### Primary score

The primary score should be a scalar that the agent can optimize.

For DKEX pricing, a possible score:

```text
score =
  normalized_pnl
  - inventory_penalty
  - drawdown_penalty
  - adverse_selection_penalty
  - quote_instability_penalty
  - stale_quote_penalty
```

The score should reward profit, but not profit alone.

A pricing strategy that makes money by taking extreme inventory risk should lose. A strategy that overfits a replay by quoting unrealistically should lose. A strategy that achieves good PnL but violates operational constraints should lose.

### Required DKEX metrics

Each experiment should report:

```text
gross_pnl
net_pnl_after_fees
max_drawdown
sharpe_like_score
inventory_mean_abs
inventory_max_abs
fill_count
maker_fill_ratio
taker_fill_ratio
quote_uptime_pct
cancel_replace_count
average_spread_bps
average_edge_bps
adverse_selection_bps
stale_quote_count
crossed_quote_count
unquotable_market_count
latency_budget_violations
risk_limit_violations
primary_score
```

### Example `metrics.json`

```json
{
  "run_id": "000042",
  "commit": "abc1234",
  "primary_score": 1.184,
  "net_pnl": 823.15,
  "max_drawdown": -211.44,
  "inventory_max_abs": 18,
  "adverse_selection_bps": -3.7,
  "quote_uptime_pct": 91.2,
  "cancel_replace_count": 1849,
  "risk_limit_violations": 0,
  "holdout": false
}
```

---

## Train / Validation / Holdout Structure

The harness should separate data into at least four groups:

```text
train       = used for candidate development
validation  = used for accept/reject
holdout     = rarely used, final check only
stress      = adversarial or weird regimes
```

Keep the data directory explicit and boring:

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

For DKEX:

```text
train:
  ordinary liquid markets
  normal pre-game and in-game periods
  varied but non-extreme examples

validation:
  different dates, teams, sports, and market types
  same broad distribution as train

holdout:
  unseen dates and market types
  only evaluated after meaningful improvements

stress:
  suspended markets
  stale books
  large spreads
  sudden odds jumps
  partial fills while cancel pending
  disconnect/reconnect periods
  low-liquidity markets
  high-volatility late-game periods
```

The agent should optimize against train and validation. It should not see holdout results on every run, otherwise it will overfit the holdout.

Recommended policy:

```text
Run train + validation every experiment.
Run holdout every 10 accepted improvements.
Run stress every 5 accepted improvements or before merge.
```

---

## Candidate Generation

The agent should not make one random edit at a time forever. It should maintain an idea backlog.

Candidate categories:

```text
classical heuristic
feature engineering
hyperparameter sweep
model class change
risk-control change
regime-specific branch
latency/performance optimization
ablation
ensemble
learned component
```

For DKEX pricing, initial candidates should start simple:

```text
fixed spread around mid
spread widens with volatility
inventory-skewed mid
liquidity-aware spread
fill-probability-aware spread
adverse-selection-aware skew
market age / time-to-event adjustment
sports-specific parameters
state-dependent quote size
```

Only after those are exhausted should the agent move into heavier learned models:

```text
linear regression edge model
logistic fill model
gradient boosted trees
small MLP
sequence model over book states
transformer-style model over event/book history
```

The system should strongly prefer the simplest strategy that improves the metric.

---

## Parallel Candidate Runs

A useful harness should support parallel exploration.

Recommended pattern:

```text
main-best
  branch/candidate-001-inventory-skew
  branch/candidate-002-vol-adjusted-spread
  branch/candidate-003-fill-prob-model
  branch/candidate-004-cancel-threshold
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
learned fill model
new volatility estimator
nonlinear inventory skew
market-type-specific quoting policy
```

### `ablation`

Remove or isolate a component to understand whether it is actually helping.

Examples:

```text
disable inventory skew
disable volatility widening
disable adverse-selection filter
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
inventory_skew = 0.05 improves score
try 0.075
try 0.10
try 0.035
test with wider base spread
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
wider spreads reduce fills too much
try conditional widening only during volatility spikes
```

### When results are noisy

If results are noisy:

```text
rerun the same commit
increase replay coverage
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

The agent should not immediately reach for transformers.

Recommended progression:

```text
1. Fixed heuristic baseline
2. Hand-tuned parameters
3. Feature-conditioned heuristic
4. Linear model
5. Tree-based model
6. Small neural net
7. Sequence-aware model
8. Transformer-style architecture
```

For DKEX pricing:

### Stage 1: classical baseline

```text
mid = best_bid_ask_mid
spread = fixed
size = fixed
inventory_skew = simple linear adjustment
```

### Stage 2: feature-conditioned heuristic

```text
spread = base + volatility_component + liquidity_component
skew = inventory_weight * inventory + adverse_selection_weight * recent_move
size = base_size adjusted by confidence
```

### Stage 3: learned fill / adverse-selection models

Predict:

```text
probability_of_fill
expected_short_term_price_move_after_fill
expected_edge
```

Use the model to adjust:

```text
spread
skew
size
whether to quote
```

### Stage 4: sequence models

Use short book/trade history to estimate:

```text
microprice
toxicity
volatility
event regime
fill probability
```

### Stage 5: transformer-style models

Only consider this if:

```text
classical and small models plateau
there is enough replay data
evaluation is robust
latency constraints are understood
the model can be distilled or cached for hot-path use
```

For a market maker, a complex model that cannot run safely in the hot path is not a real improvement.

---

## Agent Loop: How to Keep It Running

The markdown instruction alone is not enough. Many coding agents eventually stop.

Use an external loop, and keep a one-command verification path.

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

### Simple shell loop

```bash
#!/usr/bin/env bash
set -euo pipefail

while true; do
  codex exec \
    "Read skills/autoresearch/SKILL.md, ideas.md, results.tsv, and the current runs tree. Run the next experiment cycle. Use scripts/verify.sh. Do not summarize unless blocked. If the last experiment finished, generate the next candidate and run it." \
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
    "Continue from the last state. Run the next experiment from skills/autoresearch/SKILL.md. Use scripts/verify.sh. If an experiment completed, inspect results, plots, README findings, and metrics; log it, accept/reject it, and start the next one." \
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
```

If blocked, the agent should write:

```text
BLOCKED: <reason>
NEEDED: <specific human action>
```

Otherwise it should keep generating and testing candidates.

---

## `skills/autoresearch/SKILL.md` Template

The following is the lightweight skill given to the coding agent.

````md
# Program

You are an autonomous ML experimentation agent.

Your job is to improve the primary validation score by proposing, implementing, running, evaluating, and logging experiments.

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
- `replay.py`
- `metrics.py`
- `scoring.py`
- `data/`
- `scripts/compare_results.py`
- existing rows in `results.tsv`

## Required loop

Repeat forever:

1. Inspect `results.tsv`, `ideas.md`, `best/`, and the current `runs/` tree.
2. Choose one candidate idea.
3. Choose the correct run branch folder, or create a new one if this is a structural change.
4. Edit only allowed files.
5. Copy the evaluated candidate into a numbered `runs/<branch>/<NNN_name>/candidate.py`.
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

- risk limit violations
- crossed quotes
- stale quote violations above threshold
- worse max drawdown beyond tolerance
- worse adverse selection beyond tolerance
- materially lower quote uptime without compensating score improvement
- evaluator errors
- data leakage
- holdout degradation after holdout check

## Experiment row format

Append to `results.tsv`:

```tsv
timestamp commit branch idea_id status primary_score net_pnl max_drawdown inventory_max_abs adverse_selection_bps quote_uptime_pct notes
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

Do not introduce a transformer unless simpler models have plateaued and the result can satisfy latency constraints.

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

## DKEX-Specific Pricing Harness

For `prcm-dkex`, the first useful target is not a live trading agent.

The first target should be an offline pricing/replay harness.

### Inputs

```text
market metadata
order book snapshots
order book deltas
trade prints
market status changes
fills / simulated fills
latency assumptions
fee model
risk limits
```

### Strategy API

The editable strategy should expose a small interface:

```python
class Strategy:
    def on_market_state(self, state: MarketState) -> QuoteDecision:
        ...
```

The output should be:

```python
@dataclass
class QuoteDecision:
    bid_price: float | None
    ask_price: float | None
    bid_size: float
    ask_size: float
    reason: str
    confidence: float
```

The strategy should not know whether it is running on train, validation, or holdout.

### Evaluator responsibilities

The frozen evaluator should:

```text
replay book state in chronological order
call strategy on each decision point
simulate order placement / cancel / fills
enforce tick sizes and price bands
enforce maker-only rules
track positions and PnL
apply fees
apply latency assumptions
penalize stale or crossed quotes
write metrics.json
```

### First baseline

Start with an intentionally simple baseline:

```text
quote around midpoint
fixed spread
fixed size
linear inventory skew
do not quote stale or suspended markets
respect tick size and price bands
```

Then let the agent improve from there.

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
it creates hot-path CPU or latency problems
it requires data unavailable in production
```

---

## Anti-Overfitting Rules

1. Do not run holdout every experiment.
2. Do not let the agent edit holdout data or scoring.
3. Keep stress scenarios separate from normal validation.
4. Prefer improvements that work across market types and dates.
5. Track complexity cost.
6. Rerun top candidates on multiple seeds or replay windows.
7. Use ablations to remove unnecessary complexity.
8. Require production-feasible features only.

For DKEX, reject any feature that depends on future information or replay-only artifacts.

---

## Minimum Viable Implementation

The minimum useful version requires:

```text
one editable strategy file
one frozen replay evaluator
one train/validation split
one scalar primary score
one results.tsv
one `skills/autoresearch/SKILL.md`
one loop script
```

Do not start by building a giant framework.

Build the smallest thing that lets an agent run 50 experiments safely.

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
latency checks
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

For DKEX, the goal is not to create an agent that can trade live.

The goal is to create an agentic research loop that can repeatedly improve a pricing strategy against fixed replay data, under realistic market-making constraints, before any idea is considered for staging or production.
