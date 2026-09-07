"""Compare public Python auxiliary transports with independently authored cases."""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "family", ["web-operations", "resource-operations", "version-operations"]
)
def test_auxiliary_public_operations_match_authored_cases(
    family: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Call native public APIs and compare complete values, errors and file results."""
    monkeypatch.syspath_prepend(str(Path(__file__).parent))
    observe_aux_operations = import_module(
        "aux_operations_conformance"
    ).observe_aux_operations
    pack = json.loads(
        (
            ROOT / "tests/conformance/packs" / family.replace("-", "_") / "v1.json"
        ).read_text(encoding="utf-8")
    )
    for scenario in pack["scenarios"]:
        fixture = json.loads(
            (
                ROOT
                / pack["fixtureRoot"]
                / pack["fixtures"][scenario["input"]["fixtureRef"]]
            ).read_text(encoding="utf-8")
        )
        assert observe_aux_operations(family, fixture) == scenario["expected"], (
            scenario["id"]
        )
