from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

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


def read_tabular(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return read_jsonl(path)
    if suffix == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
        raise ValueError("JSON input must be a list of objects")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def write_dataset_from_rows(
    root: Path,
    rows: list[dict[str, Any]],
    *,
    id_field: str,
    input_fields: list[str],
    label_field: str,
    validation_pct: float,
    holdout_pct: float,
    dataset_version: str,
) -> None:
    if not rows:
        raise ValueError("No rows found in input data")
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(rows, 1):
        row_id = str(row.get(id_field) or f"row-{index:06d}")
        text = " ".join(str(row.get(field, "")).strip() for field in input_fields if str(row.get(field, "")).strip())
        label = str(row.get(label_field, "")).strip()
        normalized.append({"id": row_id, "text": text, "label": label})

    validation_count = max(1, int(len(normalized) * validation_pct))
    holdout_count = max(0, int(len(normalized) * holdout_pct))
    train_count = max(1, len(normalized) - validation_count - holdout_count)
    train_rows = normalized[:train_count]
    validation_rows = normalized[train_count : train_count + validation_count]
    holdout_rows = normalized[train_count + validation_count : train_count + validation_count + holdout_count]
    stress_rows = [
        {"id": "stress-empty", "text": "", "label": normalized[0]["label"]},
        {"id": "stress-long", "text": " ".join([normalized[0]["text"]] * 5), "label": normalized[0]["label"]},
    ]

    data_dir = root / "data"
    data_dir.mkdir(exist_ok=True)
    write_jsonl(data_dir / "train.jsonl", train_rows)
    write_jsonl(data_dir / "validation.jsonl", validation_rows)
    write_jsonl(data_dir / "holdout.jsonl", holdout_rows)
    write_jsonl(data_dir / "stress.jsonl", stress_rows)
    manifest = {
        "dataset_version": dataset_version,
        "schema_version": 1,
        "id_field": "id",
        "label_field": "label",
        "source": str(Path.cwd()),
        "splits": {
            "train": "data/train.jsonl",
            "validation": "data/validation.jsonl",
            "holdout": "data/holdout.jsonl",
            "stress": "data/stress.jsonl",
        },
    }
    (data_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare or validate JSONL data.")
    parser.add_argument("--write-demo", action="store_true")
    parser.add_argument("--input")
    parser.add_argument("--id-field")
    parser.add_argument("--input-fields", nargs="*")
    parser.add_argument("--label-field")
    parser.add_argument("--validation-pct", type=float, default=0.2)
    parser.add_argument("--holdout-pct", type=float, default=0.1)
    parser.add_argument("--dataset-version", default="dataset-v1")
    args = parser.parse_args(argv)
    root = find_repo_root()
    if args.write_demo:
        write_demo(root)
    if args.input:
        rows = read_tabular(Path(args.input))
        if not args.id_field or not args.input_fields or not args.label_field:
            raise SystemExit("--id-field, --input-fields, and --label-field are required with --input")
        write_dataset_from_rows(
            root,
            rows,
            id_field=args.id_field,
            input_fields=args.input_fields,
            label_field=args.label_field,
            validation_pct=args.validation_pct,
            holdout_pct=args.holdout_pct,
            dataset_version=args.dataset_version,
        )
    validate_data(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
