#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path


def main() -> int:
    path = Path("results.tsv")
    if not path.exists():
        print("results.tsv not found")
        return 1
    rows = list(csv.DictReader(path.open(encoding="utf-8"), delimiter="\t"))
    rows = [row for row in rows if row.get("primary_score")]
    rows.sort(key=lambda row: float(row.get("primary_score") or 0), reverse=True)
    for row in rows[:20]:
        print("\t".join([row.get("primary_score", ""), row.get("status", ""), row.get("branch", ""), row.get("idea_id", ""), row.get("notes", "")]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
