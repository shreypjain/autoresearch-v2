from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .frontmatter import read_frontmatter


def collect(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("README.md")) + ([root / "problem.md"] if (root / "problem.md").exists() else []):
        data, _ = read_frontmatter(path)
        if not data:
            continue
        data = dict(data)
        data["path"] = str(path.relative_to(root))
        data["directory"] = str(path.parent.relative_to(root))
        rows.append(data)
    return rows


def _matches(row: dict[str, Any], args: argparse.Namespace) -> bool:
    if args.kind and row.get("kind") != args.kind:
        return False
    if args.status and row.get("status") != args.status:
        return False
    if args.parent and row.get("parent") != args.parent:
        return False
    if args.tag:
        tags = row.get("tags") or []
        if args.tag not in tags:
            return False
    return True


def _emit_table(rows: list[dict[str, Any]]) -> None:
    columns = ["kind", "status", "name", "best_score", "path", "summary"]
    print("\t".join(columns))
    for row in rows:
        print("\t".join(str(row.get(column, "")) for column in columns))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Index README YAML front matter.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--format", choices=["table", "json", "tsv"], default="table")
    parser.add_argument("--kind")
    parser.add_argument("--status")
    parser.add_argument("--tag")
    parser.add_argument("--parent")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    rows = [row for row in collect(root) if _matches(row, args)]
    rows.sort(key=lambda item: (str(item.get("kind", "")), str(item.get("status", "")), str(item.get("name", ""))))
    if args.format == "json":
        print(json.dumps(rows, indent=2, sort_keys=True))
    else:
        _emit_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
