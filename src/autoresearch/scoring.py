from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml


def load_scoring_config(path: str | Path) -> dict[str, Any]:
    value = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a mapping")
    return value


def classification_accuracy(labels: list[str], predictions: list[str]) -> float:
    if not labels:
        return 0.0
    correct = sum(1 for label, prediction in zip(labels, predictions) if label == prediction)
    return correct / len(labels)


def balanced_accuracy(labels: list[str], predictions: list[str]) -> float:
    if not labels:
        return 0.0
    by_label: dict[str, list[int]] = {}
    for label, prediction in zip(labels, predictions):
        by_label.setdefault(label, []).append(1 if label == prediction else 0)
    return sum(sum(values) / len(values) for values in by_label.values()) / len(by_label)


def majority_baseline(labels: list[str]) -> float:
    if not labels:
        return 0.0
    count = Counter(labels).most_common(1)[0][1]
    return count / len(labels)
