from __future__ import annotations


def predict(row: dict) -> dict:
    """Baseline editable candidate surface."""
    return {"id": row["id"], "predicted_label": "accept", "confidence": 0.5}
