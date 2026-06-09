from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .paths import find_repo_root
from .prepare_data import validate_data, write_demo


def _copy_env(root: Path) -> None:
    env_path = root / ".env"
    if env_path.exists():
        return
    template = (root / ".env.example").read_text(encoding="utf-8")
    api_key = input("OpenAI API key (blank keeps placeholder): ").strip()
    if api_key:
        template = template.replace("OPENAI_API_KEY=placeholder", f"OPENAI_API_KEY={api_key}")
    env_path.write_text(template, encoding="utf-8")
    print("created .env")


def _ensure_demo_data(root: Path) -> None:
    required = [root / "data/train.jsonl", root / "data/validation.jsonl", root / "data/manifest.json"]
    if all(path.exists() for path in required):
        validate_data(root)
        return
    print("data files missing; writing demo data")
    write_demo(root)


def _run(root: Path, command: list[str]) -> None:
    subprocess.run(command, cwd=root, check=True)


def main() -> int:
    root = find_repo_root()
    _copy_env(root)
    _ensure_demo_data(root)
    (root / "runs/baseline_classifier/001_baseline/plots").mkdir(parents=True, exist_ok=True)
    _run(root, [sys.executable, "-m", "autoresearch.verify_freeze", "--write"])
    _run(root, ["scripts/verify.sh", "runs/baseline_classifier/001_baseline"])
    print("\nReady. Replace data/*.jsonl with your data, then run:")
    print("  source .venv/bin/activate")
    print("  make clean-data")
    print("  make index")
    print("  make loop")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
