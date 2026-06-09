# Agentic ML Experiment Harness

## Purpose

This document defines a lightweight harness for using coding agents to rapidly improve ML-driven or algorithmic systems through controlled experimentation.

The motivating example is `prcm-dkex`: improving the pricing algorithm for a DKEX market-making system. The same structure should generalize to other ML, simulation, ranking, forecasting, optimization, and strategy-search problems.

The core idea is:

```text
candidate generation
→ controlled experiment
→ fixed evaluation
→ accept/reject
→ log result
→ branch promising ideas
→ repeat
```

This should feel like Karpathy-style `autoresearch`, but generalized beyond LLM training and made more durable for real engineering work.

---

## Design Goals

1. **Fast experimentation**
   - Agents should be able to propose and test many candidate changes quickly.
   - Experiments should run locally, in CI, or on cloud runners with minimal setup.
   - Results should be easy to compare across branches and runs.

2. **Strong evaluation boundaries**
   - Agents may edit the candidate surface.
   - Agents may not edit the evaluator, holdout data, scoring rules, or replay construction.
   - The harness must prevent reward hacking wherever possible.

3. **Parallel candidate generation**
   - Multiple agents or multiple branches should be able to test ideas concurrently.
   - Good ideas should be merged into a best-so-far branch.
   - Bad ideas should be discarded but logged.

4. **Generalized beyond LLMs**
   - Works for pricing algorithms, ranking models, feature engineering, forecasting, optimization, RL-like policies, and classical ML.
   - Does not require transformer training as the starting point.

5. **Progressive search path**
   - Start with simple, classical, interpretable approaches.
   - Only move toward more complex models when simple baselines stop improving.
   - Maintain a clear record of why complexity was introduced.

6. **Persistent autonomous loop**
   - The agent should not stop after one experiment.
   - A wrapper should repeatedly invoke or resume the agent.
   - The agent should read outputs, diagnose failures, generate the next candidate, and keep looping.

---

## Mental Model

```text
program.md        = operating manual / lightweight skill
strategy.py       = editable candidate surface
evaluator.py      = frozen evaluation harness
data/             = frozen train/validation/holdout sets
results.tsv       = experiment ledger
ideas.md          = candidate backlog and branch notes
best/             = current best-so-far implementation
runs/             = logs and artifacts
agent_loop.sh     = durable external loop around the coding agent
```

The coding agent is not the source of truth. The harness is.

The agent proposes mutations. The evaluator decides whether the mutation helped.

---

## Recommended Repository Structure

```text
agentic-experiments/
  program.md
  README.md

  src/
    strategy.py                 # editable by agent
    features.py                 # optionally editable
    models.py                   # optionally editable
    config.py                   # editable only if allowed

  harness/
    evaluator.py                # frozen
    replay.py                   # frozen
    metrics.py                  # frozen
    data_splits.py              # frozen
    scoring.py                  # frozen

  data/
    train/
    validation/
    holdout/
    stress/
    metadata.json

  experiments/
    results.tsv
    ideas.md
    leaderboard.md
    failed_experiments.md

  runs/
    000001/
      run.log
      metrics.json
      plots/
      artifacts/

  scripts/
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
src/strategy.py
src/features.py
src/models.py
src/config.py, if explicitly allowed
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
harness/evaluator.py
harness/replay.py
harness/metrics.py
harness/scoring.py
harness/data_splits.py
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

If the agent believes the evaluator is wrong, it should write a note in `experiments/evaluator_issues.md`, not edit the evaluator.

---

## Evaluation Harness

The evaluation harness should produce a single primary score plus a set of diagnostic metrics.

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
one run directory
one metrics.json
one log
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

Use an external loop.

### Simple shell loop

```bash
#!/usr/bin/env bash
set -euo pipefail

while true; do
  codex exec \
    "Read program.md. Run the next experiment cycle. Do not summarize unless blocked. If the last experiment finished, generate the next candidate and run it." \
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
    "Continue from the last state. Run the next experiment in program.md. If an experiment completed, inspect results, log it, accept/reject it, and start the next one." \
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

## `program.md` Template

The following is the lightweight skill given to the coding agent.

```md
# Program

You are an autonomous ML experimentation agent.

Your job is to improve the primary validation score by proposing, implementing, running, evaluating, and logging experiments.

## Objective

Maximize `primary_score` from the fixed evaluator.

Lower-level metrics matter only insofar as they improve robust performance and do not violate guardrails.

## Editable files

You may edit:

- `src/strategy.py`
- `src/features.py`
- `src/models.py`
- `src/config.py`

You may not edit:

- `harness/`
- `data/`
- `scripts/compare_results.py`
- existing rows in `experiments/results.tsv`

## Required loop

Repeat forever:

1. Inspect `experiments/results.tsv`, `experiments/ideas.md`, and the current best implementation.
2. Choose one candidate idea.
3. Create a short experiment note.
4. Edit only allowed files.
5. Commit the candidate.
6. Run:

   ```bash
   scripts/run_experiment.sh
   ```

7. Read `runs/latest/metrics.json` and `runs/latest/run.log`.
8. Append one row to `experiments/results.tsv`.
9. If validation `primary_score` improved and guardrails passed, keep the commit and mark it accepted.
10. If not, reset to the previous best commit and mark it rejected.
11. Generate the next candidate idea.
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

Append to `experiments/results.tsv`:

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
```

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
one program.md
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
