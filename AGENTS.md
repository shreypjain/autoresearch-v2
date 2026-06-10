---
name: autoresearch-agent-guide
kind: agent_instructions
status: active
---

# Agent Guide

This repo is an evaluator-driven experiment harness. The agent proposes candidate implementations; the frozen harness validates, scores, and decides what worked.

## Start Here

1. Read [.agents/skills/autoresearch/SKILL.md](.agents/skills/autoresearch/SKILL.md).
2. Read [problem.md](problem.md) for the current problem scope.
3. Run `autoresearch index --status active`.
4. Inspect [results.tsv](results.tsv), [ideas.md](ideas.md), [best/README.md](best/README.md), and the active run tree under [runs/](runs).
5. Continue unfinished verification, logging, or README cleanup before creating a new experiment.

## Commands

Use the installed CLI after activating the virtualenv:

```bash
source .venv/bin/activate
autoresearch monitor
autoresearch index --status active
autoresearch new-experiment <short_name> --idea-id IDEA-001
autoresearch verify runs/<branch>/<NNN_name>
```

`scripts/verify.sh runs/<branch>/<NNN_name>` is also valid and is the canonical shell entrypoint used by the loop.

## Edit Boundary

Editable during normal experiments:

- `runs/<branch>/<NNN_name>/candidate.py`
- run and branch `README.md` files
- [ideas.md](ideas.md)
- [results.tsv](results.tsv), append-only

Frozen during normal experiments:

- [src/autoresearch/evaluator.py](src/autoresearch/evaluator.py)
- [src/autoresearch/dataset_loader.py](src/autoresearch/dataset_loader.py)
- [src/autoresearch/scoring.py](src/autoresearch/scoring.py)
- [scoring_config.yaml](scoring_config.yaml)
- [data/](data)
- existing rows in [results.tsv](results.tsv)

If the frozen layer looks wrong, write the issue to [evaluator_issues.md](evaluator_issues.md) instead of patching the evaluator from inside an experiment.

## Working Standard

Prefer simple, train-fitted, reproducible candidates before heavier models. Validation is for accept/reject, not for selecting narrow clauses after inspecting outcomes. Use holdout and stress results as robustness checks, not as the everyday optimization target.

Every completed run should leave enough evidence for the next agent: `candidate.py`, `config.json`, `metrics.json`, `run.log`, plots when generated, and a README with hypothesis, result, risk, and next action.
