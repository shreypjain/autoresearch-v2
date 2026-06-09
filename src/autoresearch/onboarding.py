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


def _selection_summary(values: list[str]) -> str:
    if not values:
        return "none selected"
    if len(values) == 1:
        return "1 selected"
    return f"{len(values)} selected"


def _answer_or_todo(value: str, prompt: str) -> str:
    cleaned = value.strip()
    return cleaned if cleaned else f"TODO: {prompt}"


def _slug(value: str) -> str:
    slug = "".join(character.lower() if character.isalnum() else "_" for character in value).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "custom_problem"


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
    console.print("[bold]Problem scope[/bold]")
    console.print("[dim]Answer in short phrases. Leave blank to create a TODO in problem.md.[/dim]")
    name = inquirer.text(message="Short problem name:", default="custom_classification_task").execute()
    problem = _answer_or_todo(
        inquirer.text(message="What should the model choose or predict?").execute(),
        "Describe what the model should choose or predict.",
    )
    goal = _answer_or_todo(
        inquirer.text(message="What metric should improve first?").execute(),
        "Define the first measurable metric to improve.",
    )
    application = _answer_or_todo(
        inquirer.text(message="Where will the winning model be used in production?").execute(),
        "Name the production placement, such as batch job, API endpoint, ranking step, or internal tool.",
    )
    baseline = _answer_or_todo(
        inquirer.text(message="What simple baseline should the first real experiment beat?").execute(),
        "Define the simple benchmark the first real experiment must beat, such as majority class, current heuristic, or previous model.",
    )
    inputs = _answer_or_todo(
        inquirer.text(message="What input columns or fields matter most?").execute(),
        "List the important input fields.",
    )
    output = _answer_or_todo(
        inquirer.text(message="What should one prediction contain?").execute(),
        "Describe the expected prediction fields.",
    )
    constraints = _answer_or_todo(
        inquirer.text(message="Any hard constraints?").execute(),
        "List runtime, dependency, interpretability, privacy, or deployment constraints.",
    )
    non_goals = _answer_or_todo(
        inquirer.text(message="What should the agent avoid?").execute(),
        "List non-goals or forbidden approaches.",
    )
    starting_ideas = _answer_or_todo(
        inquirer.text(message="Any starting experiment ideas?").execute(),
        "Seed a few initial ideas.",
    )
    problem_scope_id = f"{_slug(name)}-v1"
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

{problem}

## Goal

{goal}

## Eventual Application

{application}

## Baseline Goal

{baseline}

The baseline goal is the first simple benchmark the loop must beat. It is not the final product goal. Good examples are majority-class accuracy, a simple threshold rule, an existing heuristic, or the current production model.

## Inputs and Outputs

Inputs: {inputs}

Prediction output: {output}

Default normalized row shape is `id`, `text`, and `label`. Default prediction shape is `id`, `predicted_label`, and `confidence`. Update this section if your data or schema differs.

## Constraints

{constraints}

## Non-Goals

{non_goals}

## Useful Starting Ideas

{starting_ideas}
"""
    write_frontmatter(problem_path, frontmatter, body)
    console.print("[green]Wrote problem.md[/green]")
    if "TODO:" in body:
        console.print("[yellow]problem.md contains TODOs. Fill them in before starting the agent loop.[/yellow]")


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
    input_fields = inquirer.checkbox(
        message="Input/text fields:",
        choices=[column for column in columns if column != label_field],
        transformer=_selection_summary,
    ).execute()
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
        transformer=_selection_summary,
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
