---
name: demo_dataset
kind: dataset
status: active
dataset_version: dataset-v1
schema_version: 1
---

# Data

Replace these demo JSONL files with your own data.

Default row shape:

```json
{"id": "train-001", "text": "clear positive example", "label": "accept"}
```

Required split files:

- `train.jsonl`
- `validation.jsonl`

Optional split files:

- `holdout.jsonl`
- `stress.jsonl`

Do not put holdout label distributions or derived holdout analysis in this README.
