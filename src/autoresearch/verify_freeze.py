from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .paths import find_repo_root

DEFAULT_FROZEN_PATHS = [
    "evaluator.py",
    "dataset_loader.py",
    "metrics.py",
    "scoring.py",
    "scoring_config.yaml",
    "data/manifest.json",
    "src/autoresearch/evaluator.py",
    "src/autoresearch/dataset_loader.py",
    "src/autoresearch/scoring.py",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_lock(root: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for rel_path in DEFAULT_FROZEN_PATHS:
        path = root / rel_path
        if path.exists():
            entries[rel_path] = sha256(path)
    return entries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify frozen harness hashes.")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    root = find_repo_root()
    lock_path = root / "frozen.lock"
    current = build_lock(root)
    if args.write or not lock_path.exists():
        lock_path.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {lock_path.relative_to(root)}")
        return 0
    expected = json.loads(lock_path.read_text(encoding="utf-8"))
    drift = {
        path: {"expected": expected.get(path), "actual": current.get(path)}
        for path in sorted(set(expected) | set(current))
        if expected.get(path) != current.get(path)
    }
    if drift:
        print(json.dumps({"status": "frozen_layer_modified", "drift": drift}, indent=2, sort_keys=True))
        return 1
    print("frozen layer verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
