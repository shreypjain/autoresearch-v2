---
name: autoresearch
description: Run schema-safe, evaluator-driven ML experiments in this repo.
tags:
  - ml
  - experiments
  - evaluation
---

# Autoresearch Skill

Read `problem.md` first. It defines the problem, baseline goal, target application, and constraints.

Then:

1. Run `python scripts/readme_index.py --root . --status active`.
2. Inspect `results.tsv`, `ideas.md`, and the current `runs/` tree.
3. Pick one candidate idea.
4. `cd runs/<branch>` and run `new-experiment <short_name> --idea-id <idea_id>` if the venv is active, or `../../scripts/new-experiment <short_name> --idea-id <idea_id>` otherwise.
5. Edit only `predict(row)` in the generated `candidate.py`.
6. Run `scripts/verify.sh runs/<branch>/<NNN_name>`.
7. Read `metrics.json`, `run.log`, generated plots, and the run README.
8. Append a row to `results.tsv`.
9. Update README front matter and `ideas.md`.
10. Continue until blocked or plateaued.

Do not edit frozen files:

- `evaluator.py`
- `dataset_loader.py`
- `metrics.py`
- `scoring.py`
- `scoring_config.yaml`
- `data/`
- `scripts/compare_results.py`

If schema validation fails, fix candidate output shape and rerun the same experiment. Do not score schema failures as rejected experiments.
