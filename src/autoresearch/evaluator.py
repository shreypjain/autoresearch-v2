from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from jsonschema import Draft202012Validator

from .dataset_loader import load_manifest, load_split, strip_label, write_jsonl
from .paths import find_repo_root
from .scoring import balanced_accuracy, classification_accuracy, load_scoring_config, majority_baseline


def _load_candidate(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("candidate_module", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import candidate from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["candidate_module"] = module
    spec.loader.exec_module(module)
    if not hasattr(module, "predict"):
        raise ValueError("candidate.py must define predict(row)")
    return module


def _validate_predictions(
    predictions: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    schema: dict[str, Any],
    id_field: str,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    validator = Draft202012Validator(schema)
    expected_ids = [str(row[id_field]) for row in rows]
    expected_set = set(expected_ids)
    seen: set[str] = set()

    if len(predictions) != len(rows):
        issues.append({
            "path": "$",
            "message": f"expected {len(rows)} predictions, got {len(predictions)}",
        })

    for index, prediction in enumerate(predictions):
        row_id = prediction.get(id_field, f"prediction-{index}")
        for error in validator.iter_errors(prediction):
            issues.append({
                "row_id": row_id,
                "path": "$" + "".join(f".{part}" for part in error.path),
                "message": error.message,
            })
        if row_id in seen:
            issues.append({"row_id": row_id, "path": f"$.{id_field}", "message": "duplicate id"})
        seen.add(str(row_id))
        if str(row_id) not in expected_set:
            issues.append({"row_id": row_id, "path": f"$.{id_field}", "message": "id not present in evaluated split"})

    missing = expected_set - seen
    for row_id in sorted(missing):
        issues.append({"row_id": row_id, "path": f"$.{id_field}", "message": "missing prediction"})

    return issues


def _plot_score(run_dir: Path, metrics: dict[str, Any]) -> None:
    plots_dir = run_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    try:
        import matplotlib.pyplot as plt

        splits = list(metrics.get("splits", {}).keys())
        scores = [metrics["splits"][split].get("accuracy", 0.0) for split in splits]
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(splits, scores)
        ax.set_ylim(0, 1)
        ax.set_ylabel("accuracy")
        ax.set_title("Split accuracy")
        fig.tight_layout()
        fig.savefig(plots_dir / "score_curve.png")
        plt.close(fig)
    except Exception as exc:  # pragma: no cover - plotting is best-effort
        (plots_dir / "plot_error.txt").write_text(str(exc), encoding="utf-8")


def evaluate(args: argparse.Namespace) -> int:
    root = find_repo_root()
    load_dotenv(root / ".env")
    start = time.time()

    run_dir = (root / args.run_dir).resolve()
    candidate_path = (root / args.candidate).resolve() if args.candidate else run_dir / "candidate.py"
    manifest_path = (root / args.data_manifest).resolve()
    scoring_config_path = root / args.scoring_config
    metrics_path = run_dir / "metrics.json"
    predictions_path = run_dir / "predictions.jsonl"
    run_dir.mkdir(parents=True, exist_ok=True)

    scoring = load_scoring_config(scoring_config_path)
    manifest = load_manifest(manifest_path)
    id_field = str(scoring.get("id_field", manifest.get("id_field", "id")))
    label_field = str(scoring.get("label_field", manifest.get("label_field", "label")))
    seed = int(os.getenv("AUTORESEARCH_SEED", "42"))
    schema = scoring["prediction_schema"]

    metrics: dict[str, Any] = {
        "status": "running",
        "run_dir": str(run_dir.relative_to(root)),
        "seed": seed,
        "scorer_id": scoring.get("scorer_id"),
        "schema_version": scoring.get("schema_version"),
        "dataset_version": manifest.get("dataset_version", scoring.get("dataset_version")),
        "splits": {},
        "issues": [],
    }

    try:
        candidate = _load_candidate(candidate_path)
        train_rows = load_split(manifest_path, "train", root)
        if hasattr(candidate, "fit"):
            candidate.fit(train_rows)

        all_predictions: list[dict[str, Any]] = []
        for split in [part.strip() for part in args.splits.split(",") if part.strip()]:
            rows = load_split(manifest_path, split, root)
            predictions: list[dict[str, Any]] = []
            labels: list[str] = []
            for row in rows:
                labels.append(str(row.get(label_field, "")))
                prediction = candidate.predict(strip_label(row, label_field))
                predictions.append(prediction)
                all_predictions.append({"split": split, **prediction})

            issues = _validate_predictions(predictions, rows, schema, id_field)
            tolerance = 0.0
            if split != "holdout":
                tolerance = float(scoring.get("fault_tolerance", {}).get("validation_invalid_row_pct", 5.0))
            else:
                tolerance = float(scoring.get("fault_tolerance", {}).get("holdout_invalid_row_pct", 0.0))
            invalid_pct = (len(issues) / max(len(rows), 1)) * 100
            if issues and invalid_pct > tolerance:
                metrics["status"] = "schema_validation_failed"
                metrics["issues"].extend({"split": split, **issue} for issue in issues)
                continue

            by_id = {str(pred[id_field]): pred for pred in predictions if id_field in pred}
            ordered_predictions = [str(by_id[str(row[id_field])]["predicted_label"]) for row in rows if str(row[id_field]) in by_id]
            ordered_labels = [str(row[label_field]) for row in rows if str(row[id_field]) in by_id]
            accuracy = classification_accuracy(ordered_labels, ordered_predictions)
            metrics["splits"][split] = {
                "row_count": len(rows),
                "valid_prediction_count": len(ordered_predictions),
                "invalid_issue_count": len(issues),
                "invalid_pct": invalid_pct,
                "accuracy": accuracy,
                "balanced_accuracy": balanced_accuracy(ordered_labels, ordered_predictions),
                "majority_baseline": majority_baseline(labels),
            }

        write_jsonl(predictions_path, all_predictions)
        if metrics["status"] == "running":
            primary_split = "validation" if "validation" in metrics["splits"] else next(iter(metrics["splits"]), "")
            metrics["primary_score"] = metrics["splits"].get(primary_split, {}).get("accuracy", 0.0)
            metrics["status"] = "accepted" if metrics["primary_score"] >= 0 else "rejected"
        metrics["runtime_seconds"] = round(time.time() - start, 4)
        _plot_score(run_dir, metrics)
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0 if metrics["status"] != "schema_validation_failed" else 1
    except Exception as exc:
        metrics["status"] = "failed"
        metrics["issues"].append({"message": str(exc), "type": exc.__class__.__name__})
        metrics["runtime_seconds"] = round(time.time() - start, 4)
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run frozen evaluator against a candidate.")
    parser.add_argument("--candidate", default=None)
    parser.add_argument("--data-manifest", default="data/manifest.json")
    parser.add_argument("--scoring-config", default="scoring_config.yaml")
    parser.add_argument("--splits", default="train,validation")
    parser.add_argument("--run-dir", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    return evaluate(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
