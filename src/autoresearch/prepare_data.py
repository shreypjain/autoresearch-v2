from __future__ import annotations

import argparse
import json
from pathlib import Path

from .dataset_loader import read_jsonl, write_jsonl
from .paths import find_repo_root


DEMO_ROWS = {
    "train": [
        {"id": "train-001", "text": "approve the simple valid request", "label": "accept"},
        {"id": "train-002", "text": "reject the malformed request", "label": "reject"},
    ],
    "validation": [
        {"id": "validation-001", "text": "accept this clean request", "label": "accept"},
        {"id": "validation-002", "text": "reject this broken request", "label": "reject"},
    ],
    "holdout": [
        {"id": "holdout-001", "text": "accept the valid held out request", "label": "accept"},
        {"id": "holdout-002", "text": "reject the invalid held out request", "label": "reject"},
    ],
    "stress": [
        {"id": "stress-001", "text": "", "label": "reject"},
        {"id": "stress-002", "text": "ACCEPT valid complete", "label": "accept"},
    ],
}


def write_demo(root: Path) -> None:
    data_dir = root / "data"
    data_dir.mkdir(exist_ok=True)
    for split, rows in DEMO_ROWS.items():
        write_jsonl(data_dir / f"{split}.jsonl", rows)
    manifest = {
        "dataset_version": "dataset-v1",
        "schema_version": 1,
        "id_field": "id",
        "label_field": "label",
        "splits": {split: f"data/{split}.jsonl" for split in DEMO_ROWS},
    }
    (data_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def validate_data(root: Path) -> None:
    manifest = json.loads((root / "data/manifest.json").read_text(encoding="utf-8"))
    id_field = manifest.get("id_field", "id")
    label_field = manifest.get("label_field", "label")
    for split, rel_path in manifest.get("splits", {}).items():
        rows = read_jsonl(root / rel_path)
        ids = [row.get(id_field) for row in rows]
        if len(ids) != len(set(ids)):
            raise SystemExit(f"{split}: duplicate ids found")
        missing = [row for row in rows if id_field not in row or label_field not in row]
        if missing:
            raise SystemExit(f"{split}: {len(missing)} rows missing {id_field!r} or {label_field!r}")
        print(f"{split}: {len(rows)} rows")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare or validate JSONL data.")
    parser.add_argument("--write-demo", action="store_true")
    args = parser.parse_args(argv)
    root = find_repo_root()
    if args.write_demo:
        write_demo(root)
    validate_data(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
