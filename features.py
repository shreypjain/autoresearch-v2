from __future__ import annotations


def text_length(row: dict) -> int:
    return len(str(row.get("text", "")))
