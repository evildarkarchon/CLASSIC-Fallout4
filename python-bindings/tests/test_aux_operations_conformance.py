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
    monkeypatch.syspath_prepend(str(ROOT / "tools/binding_compliance"))
    from conformance.applicability import derive_applicability
    from conformance.coverage import load_source_parity_rows
    from conformance.packs import load_and_validate_pack

    observe_aux_operations = import_module(
        "aux_operations_conformance"
    ).observe_aux_operations
    pack = load_and_validate_pack(
        ROOT, Path("tests/conformance/packs") / family.replace("-", "_") / "v1.json"
    ).document()
    matrix = derive_applicability(pack, load_source_parity_rows(ROOT))
    selected = next(
        participant.scenario_ids
        for participant in matrix.participants
        if participant.id == "python"
    )
    assert selected
    for scenario in pack["scenarios"]:
        if scenario["id"] not in selected:
            continue
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
