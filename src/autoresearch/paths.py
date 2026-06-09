from __future__ import annotations

from pathlib import Path


def find_repo_root(start: str | Path | None = None) -> Path:
    current = Path(start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent
    for path in [current, *current.parents]:
        if (path / "architecture.md").exists() and (path / "pyproject.toml").exists():
            return path
    raise RuntimeError(f"Could not find repo root from {current}")


def repo_path(path: str | Path, root: str | Path | None = None) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return find_repo_root(root) / candidate
