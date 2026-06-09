from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml
from InquirerPy import inquirer
from rich.console import Console

from .frontmatter import write_frontmatter
from .paths import find_repo_root
from .prepare_data import read_tabular, validate_data, write_dataset_from_rows
from .scoring import load_scoring_config

console = Console()


def _write_env(root: Path) -> None:
    env_path = root / ".env"
    template = (root / ".env.example").read_text(encoding="utf-8")
    if env_path.exists():
        overwrite = inquirer.confirm(message=".env already exists. Update it?", default=False).execute()
        if not overwrite:
            return
    api_key = inquirer.secret(message="OpenAI API key (leave blank for placeholder):", mandatory=False).execute()
    if api_key:
        template = template.replace("OPENAI_API_KEY=placeholder", f"OPENAI_API_KEY={api_key}")
    seed = inquirer.text(message="Default random seed:", default="42").execute()
    template = template.replace("AUTORESEARCH_SEED=42", f"AUTORESEARCH_SEED={seed}")
    env_path.write_text(template, encoding="utf-8")
    console.print("[green]Wrote .env[/green]")


def _write_problem(root: Path) -> None:
    problem_path = root / "problem.md"
    overwrite = True
    if problem_path.exists():
        overwrite = inquirer.confirm(message="problem.md exists. Replace scope?", default=False).execute()
    if not overwrite:
        return
    name = inquirer.text(message="Problem name:", default="custom_classification_task").execute()
    goal = inquirer.text(message="Measurable goal:", default="Improve validation accuracy over the baseline.").execute()
    application = inquirer.select(
        message="Eventual application:",
        choices=[
            "offline batch scoring",
            "online prediction endpoint",
            "ranking pipeline",
            "forecasting job",
            "optimization routine",
            "human decision-support workflow",
        ],
        default="offline batch scoring",
    ).execute()
    baseline = inquirer.text(message="Baseline goal:", default="beat_majority_class_baseline").execute()
    problem_scope_id = f"{name.replace(' ', '_').lower()}-v1"
    frontmatter = {
        "name": name,
        "kind": "problem_scope",
        "status": "active",
        "primary_metric": "validation_accuracy",
        "baseline_goal": baseline,
        "target_application": application,
        "problem_scope_id": problem_scope_id,
        "owner": "human",
    }
    body = f"""# Problem

{name}

## Goal

{goal}

## Eventual Application

{application}

## Baseline Goal

{baseline}

## Inputs and Outputs

Rows are normalized into `id`, `text`, and `label`. Candidates emit `id`, `predicted_label`, and `confidence`.

## Constraints

- Use dependencies already declared in `pyproject.toml`.
- Keep runs reproducible with `AUTORESEARCH_SEED`.
- Do not read holdout rows or labels directly.

## Non-Goals

- Do not change evaluator, scoring, schema, or dataset construction from candidate runs.

## Useful Starting Ideas

- Majority-class baseline.
- Keyword or threshold baseline.
- Simple linear or tree model after the baseline is verified.
"""
    write_frontmatter(problem_path, frontmatter, body)
    console.print("[green]Wrote problem.md[/green]")


def _configure_labels(root: Path, labels: list[str]) -> None:
    config_path = root / "scoring_config.yaml"
    config = load_scoring_config(config_path)
    config["allowed_labels"] = sorted(labels)
    schema = config.setdefault("prediction_schema", {})
    properties = schema.setdefault("properties", {})
    predicted_label = properties.setdefault("predicted_label", {})
    predicted_label["enum"] = sorted(labels)
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    console.print("[green]Updated scoring_config.yaml labels[/green]")


def _import_data(root: Path) -> None:
    path_value = inquirer.filepath(message="CSV/JSON/JSONL data file:", validate=lambda p: Path(p).exists()).execute()
    path = Path(path_value).expanduser().resolve()
    rows = read_tabular(path)
    if not rows:
        raise SystemExit("No rows found")
    columns = list(rows[0].keys())
    id_field = inquirer.select(message="ID field:", choices=columns).execute()
    label_field = inquirer.select(message="Label field:", choices=columns).execute()
    input_fields = inquirer.checkbox(message="Input/text fields:", choices=[column for column in columns if column != label_field]).execute()
    validation_pct = float(inquirer.text(message="Validation split fraction:", default="0.2").execute())
    holdout_pct = float(inquirer.text(message="Holdout split fraction:", default="0.1").execute())
    dataset_version = inquirer.text(message="Dataset version:", default="dataset-v1").execute()
    write_dataset_from_rows(
        root,
        rows,
        id_field=id_field,
        input_fields=input_fields,
        label_field=label_field,
        validation_pct=validation_pct,
        holdout_pct=holdout_pct,
        dataset_version=dataset_version,
    )
    labels = sorted({str(row.get(label_field, "")).strip() for row in rows if str(row.get(label_field, "")).strip()})
    _configure_labels(root, labels)
    validate_data(root)
    console.print("[green]Imported data into data/*.jsonl[/green]")


def _run(root: Path, command: list[str]) -> None:
    console.print(f"[dim]$ {' '.join(command)}[/dim]")
    subprocess.run(command, cwd=root, check=True)


def run_onboarding() -> int:
    root = find_repo_root()
    console.rule("[bold]Autoresearch Onboarding[/bold]")
    actions = inquirer.checkbox(
        message="What do you want to set up?",
        choices=[
            {"name": "API key / .env", "value": "env", "enabled": True},
            {"name": "problem.md", "value": "problem", "enabled": True},
            {"name": "Import CSV/JSONL data", "value": "data", "enabled": True},
            {"name": "Verify baseline run", "value": "verify", "enabled": True},
            {"name": "Open TUI dashboard", "value": "tui", "enabled": False},
        ],
    ).execute()
    if "env" in actions:
        _write_env(root)
    if "problem" in actions:
        _write_problem(root)
    if "data" in actions:
        _import_data(root)
    if "verify" in actions:
        _run(root, ["scripts/verify.sh", "runs/baseline_classifier/001_baseline"])
    if "tui" in actions:
        from .tui import run_tui

        run_tui()
    console.print("[green]Onboarding complete[/green]")
    return 0

