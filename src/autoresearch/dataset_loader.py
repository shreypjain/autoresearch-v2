from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    file_path = Path(path)
    if not file_path.exists():
        return rows
    with file_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped:
                continue
            value = json.loads(stripped)
            if not isinstance(value, dict):
                raise ValueError(f"{file_path}:{line_number} is not a JSON object")
            rows.append(value)
    return rows


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def load_manifest(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_split(manifest_path: str | Path, split: str, root: str | Path) -> list[dict[str, Any]]:
    manifest = load_manifest(manifest_path)
    split_path = manifest.get("splits", {}).get(split)
    if not split_path:
        raise ValueError(f"Split {split!r} is not defined in {manifest_path}")
    path = Path(root) / split_path
    return read_jsonl(path)


def strip_label(row: dict[str, Any], label_field: str) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != label_field}
