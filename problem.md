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

Classify each input row into one of the labels defined by `scoring_config.yaml`.

## Goal

Improve validation accuracy over the baseline while preserving schema validity, runtime limits, and holdout discipline.

## Eventual Application

Offline batch scoring for a human decision-support workflow.

## Baseline Goal

Beat the majority-class baseline on validation.

## Inputs and Outputs

Rows live in `data/*.jsonl`. The default row shape is:

```json
{"id": "row-1", "text": "example input", "label": "accept"}
```

Candidates emit:

```json
{"id": "row-1", "predicted_label": "accept", "confidence": 0.5}
```

## Constraints

- Use dependencies already declared in `pyproject.toml`.
- Keep runs reproducible with `AUTORESEARCH_SEED`.
- Do not read holdout rows or labels directly.
- Keep candidate changes inside generated `predict(row)` unless a human changes scope.

## Non-Goals

- Do not change evaluator, scoring, schema, or dataset construction from candidate runs.
- Do not add remote services or network calls from candidates.

## Useful Starting Ideas

- Majority-class baseline.
- Keyword-based baseline.
- Threshold tuning.
- Simple linear or tree model after the baseline is verified.
