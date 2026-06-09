from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .frontmatter import write_frontmatter
from .paths import find_repo_root
from .scoring import load_scoring_config


def _prompt(value: str | None, label: str, default: str | None = None) -> str:
    if value:
        return value
    suffix = f" [{default}]" if default else ""
    response = input(f"{label}{suffix}: ").strip()
    if response:
        return response
    if default is not None:
        return default
    raise SystemExit(f"{label} is required")


def _next_run_name(branch_dir: Path, short_name: str) -> str:
    highest = 0
    for child in branch_dir.iterdir() if branch_dir.exists() else []:
        if child.is_dir():
            match = re.match(r"^(\d{3})_", child.name)
            if match:
                highest = max(highest, int(match.group(1)))
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", short_name.strip().lower()).strip("_")
    return f"{highest + 1:03d}_{slug}"


def _candidate_template() -> str:
    return '''from __future__ import annotations


def fit(train_rows: list[dict]) -> None:
    """Optional training hook. The evaluator passes labeled train rows here."""
    return None


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
        label = "accept"
        confidence = 0.5
    return {
        "id": row["id"],
        "predicted_label": label,
        "confidence": confidence,
    }
'''


def create_experiment(args: argparse.Namespace) -> Path:
    root = find_repo_root()
    scoring = load_scoring_config(root / "scoring_config.yaml")
    cwd = Path.cwd().resolve()
    runs_root = root / "runs"
    if not cwd.is_relative_to(runs_root):
        raise SystemExit("new-experiment must be run from inside runs/<branch>")
    if cwd == runs_root:
        raise SystemExit("new-experiment must be run from a specific runs/<branch> directory")

    short_name = _prompt(args.short_name, "short name")
    idea_id = _prompt(args.idea_id, "idea id", "IDEA-000")
    parent = args.parent
    existing_runs = sorted(child for child in cwd.iterdir() if child.is_dir() and re.match(r"^\d{3}_", child.name))
    if not existing_runs and not args.root:
        raise SystemExit("No previous run exists. Pass --root for a root experiment branch.")
    if parent is None:
        parent = "root" if not existing_runs else str(existing_runs[-1].relative_to(root))

    run_name = _next_run_name(cwd, short_name)
    run_dir = cwd / run_name
    run_dir.mkdir(mode=0o755, parents=False, exist_ok=False)
    (run_dir / "plots").mkdir()

    branch = str(cwd.relative_to(runs_root))
    problem_scope_id = args.problem_scope_id or "example_classification_task-v1"
    seed = int(args.seed)
    config = {
        "idea_id": idea_id,
        "problem_scope_id": problem_scope_id,
        "branch": branch,
        "run_name": run_name,
        "parent": parent,
        "created_from_directory": str(cwd.relative_to(root)),
        "scoring_config": "scoring_config.yaml",
        "primary_scorer": scoring.get("primary_scorer", "accuracy"),
        "scorer_id": scoring.get("scorer_id", "accuracy-v1"),
        "schema_version": scoring.get("schema_version", 1),
        "dataset_version": scoring.get("dataset_version", "dataset-v1"),
        "seed": seed,
        "prediction_schema": "scoring_config.yaml:prediction_schema",
        "splits": ["train", "validation"],
    }
    (run_dir / "config.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (run_dir / "candidate.py").write_text(_candidate_template(), encoding="utf-8")
    (run_dir / "run.log").write_text("", encoding="utf-8")
    (run_dir / "metrics.json").write_text("{}\n", encoding="utf-8")
    readme_frontmatter = {
        "name": run_name,
        "kind": "experiment_run",
        "status": "created",
        "parent": parent,
        "idea_id": idea_id,
        "problem_scope_id": problem_scope_id,
        "primary_scorer": config["primary_scorer"],
        "scorer_id": config["scorer_id"],
        "schema_version": config["schema_version"],
        "dataset_version": config["dataset_version"],
        "seed": seed,
        "prediction_schema": "scoring_config.yaml:prediction_schema",
        "tags": [branch],
        "summary": f"Created from {idea_id}. Awaiting first verification run.",
        "next": [f"Edit only predict(row) in candidate.py.", f"Run scripts/verify.sh {run_dir.relative_to(root)}."],
    }
    write_frontmatter(run_dir / "README.md", readme_frontmatter, f"# {run_name}\n\nGenerated experiment.\n")
    return run_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create the next numbered experiment in runs/<branch>.")
    parser.add_argument("short_name", nargs="?")
    parser.add_argument("--idea-id")
    parser.add_argument("--parent")
    parser.add_argument("--problem-scope-id")
    parser.add_argument("--seed", default="42")
    parser.add_argument("--root", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    run_dir = create_experiment(build_parser().parse_args(argv))
    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
