from __future__ import annotations


class BaselineModel:
    def predict(self, row: dict) -> str:
        return "accept"
