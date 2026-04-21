"""Helpers for reading Python binding runtime coverage registry data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REGISTRY_PATH = Path(__file__).with_name("runtime_coverage_registry.json")


def load_runtime_coverage_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def get_runtime_coverage_case_ids(test_suite: str) -> list[str]:
    registry = load_runtime_coverage_registry()
    return [
        entry["testCaseId"]
        for entry in registry.get("entries", [])
        if entry.get("testSuite") == test_suite
    ]
