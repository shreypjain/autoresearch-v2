# Search Strategy Reference

## Candidate Progression

Use the smallest model class that can plausibly expose signal:

1. majority or mode baseline
2. deterministic heuristic
3. feature-conditioned heuristic
4. train-only hyperparameter sweep
5. linear model or ranker
6. tree model or random forest
7. small neural model
8. sequence or transformer-style model

Record why each complexity jump was necessary. If complexity increases but validation, holdout, or stress does not improve, walk back up the tree.

## Overfit Signals

Treat these as suspicious:

- train accuracy jumps sharply while validation does not
- validation improves through narrow subject/source/category clauses
- holdout or stress contradicts validation
- repeated ablations show one tiny selected component carries all lift
- grouped or repeated train-only resplits select mode while fixed validation improves
- runtime grows without meaningful score movement

Suspicious does not always mean reject immediately. It does mean schedule robustness checks, ablations, or a broader train-fitted alternative before promotion.

## Useful Branch Types

Good candidate trees usually fall into one of these:

- baseline branch: proves the evaluator and schema work
- feature branch: tests one coherent feature family
- model branch: trains a candidate using train labels only
- calibration branch: learns when to trust a baseline or candidate
- ablation branch: removes one suspected useful component
- diagnostic branch: tests split quality, leakage, resplit stability, or plateau causes

Do not create a new branch for every small hyperparameter tweak. Keep comparable variants in one branch.

## Plateau Handling

When a branch repeatedly ties mode, overfits train, or fails robustness checks:

1. Summarize the evidence in the branch README.
2. Mark the branch `archived` if no immediate follow-up is justified.
3. Update `ideas.md` with the high-level result.
4. Walk back to a parent branch or root-level idea.

Do not continue producing small variants after the branch summary says the family is plateaued.

## Holdout And Stress Interpretation

High validation with mediocre holdout can mean validation hillclimbing or split luck.

Mediocre validation with strong holdout/stress can mean a real broad direction that the current validation split undervalues. Record it as research signal, but do not promote unless the project's promotion bar allows it.

Stress improvements are especially useful for choosing future feature families, but stress should not become the everyday optimization target.
