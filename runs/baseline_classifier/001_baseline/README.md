---
name: 001_baseline
kind: experiment_run
status: created
parent: root
idea_id: IDEA-000
problem_scope_id: example_classification_task-v1
primary_scorer: accuracy
scorer_id: accuracy-v1
schema_version: 1
dataset_version: dataset-v1
seed: 42
prediction_schema: scoring_config.yaml:prediction_schema
tags:
  - baseline
summary: Created baseline candidate for smoke testing the harness.
next:
  - Run scripts/verify.sh runs/baseline_classifier/001_baseline.
---

# 001 Baseline

Initial schema-valid baseline run.
