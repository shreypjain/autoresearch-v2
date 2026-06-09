from __future__ import annotations

import json
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Static

from .paths import find_repo_root
from .readme_index import collect


class AutoresearchTUI(App):
    CSS = """
    Screen {
      layout: vertical;
    }
    #summary {
      height: 8;
      padding: 1 2;
    }
    DataTable {
      height: 1fr;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="summary")
        with Horizontal():
            yield DataTable(id="runs")
            yield DataTable(id="results")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Autoresearch"
        self.refresh_data()

    def action_refresh(self) -> None:
        self.refresh_data()

    def refresh_data(self) -> None:
        root = find_repo_root()
        summary = self.query_one("#summary", Static)
        problem = root / "problem.md"
        env = root / ".env"
        data_manifest = root / "data/manifest.json"
        summary.update(
            "\n".join(
                [
                    f"Repo: {root}",
                    f"problem.md: {'present' if problem.exists() else 'missing'}",
                    f".env: {'present' if env.exists() else 'missing'}",
                    f"data manifest: {'present' if data_manifest.exists() else 'missing'}",
                    "Keys: r refresh, q quit",
                ]
            )
        )

        runs = self.query_one("#runs", DataTable)
        runs.clear(columns=True)
        runs.add_columns("kind", "status", "name", "path")
        for row in collect(root):
            runs.add_row(str(row.get("kind", "")), str(row.get("status", "")), str(row.get("name", "")), str(row.get("path", "")))

        results = self.query_one("#results", DataTable)
        results.clear(columns=True)
        results.add_columns("run", "status", "score", "validation")
        for metrics_path in sorted(root.glob("runs/*/*/metrics.json")):
            try:
                metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            results.add_row(
                str(metrics_path.parent.relative_to(root)),
                str(metrics.get("status", "")),
                str(metrics.get("primary_score", "")),
                str(metrics.get("splits", {}).get("validation", {}).get("accuracy", "")),
            )


def run_tui() -> None:
    AutoresearchTUI().run()


if __name__ == "__main__":
    run_tui()
