from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def read_frontmatter(path: str | Path) -> tuple[dict[str, Any], str]:
    text = Path(path).read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        return {}, body
    return data, body


def write_frontmatter(path: str | Path, data: dict[str, Any], body: str) -> None:
    rendered = yaml.safe_dump(data, sort_keys=False).strip()
    Path(path).write_text(f"---\n{rendered}\n---\n\n{body.lstrip()}", encoding="utf-8")
