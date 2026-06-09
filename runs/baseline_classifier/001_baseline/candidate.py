from __future__ import annotations


LABEL = "accept"


def fit(train_rows: list[dict]) -> None:
    """Optional training hook. The evaluator passes labeled train rows here."""
    global LABEL
    counts: dict[str, int] = {}
    for row in train_rows:
        label = row.get("label")
        if isinstance(label, str):
            counts[label] = counts.get(label, 0) + 1
    if counts:
        LABEL = max(sorted(counts), key=lambda item: counts[item])


def predict(row: dict) -> dict:
    """Return one schema-valid prediction for one dataset row."""
    # Agent edits only this function.
    text = str(row.get("text", "")).lower()
    reject_words = ("reject", "deny", "invalid", "malformed", "broken", "incomplete")
    accept_words = ("accept", "approve", "valid", "complete", "clean")
    reject_hits = sum(word in text for word in reject_words)
    accept_hits = sum(word in text for word in accept_words)
    if reject_hits > accept_hits:
        label = "reject"
        confidence = 0.75
    elif accept_hits > reject_hits:
        label = "accept"
        confidence = 0.75
    else:
        label = LABEL
        confidence = 0.5
    return {
        "id": row["id"],
        "predicted_label": label,
        "confidence": confidence,
    }
