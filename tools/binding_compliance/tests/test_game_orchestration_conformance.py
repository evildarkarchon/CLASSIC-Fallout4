"""Concurrent game checks retain complete job and report-assembly evidence."""

import copy
from pathlib import Path

from conformance.packs import load_and_validate_pack


def test_orchestration_requires_report_assembly_evidence() -> None:
    """A returned check list cannot cover report assembly when the raw report disagrees."""
    root = Path(__file__).resolve().parents[3]
    path = Path("tests/conformance/packs/game_orchestration/v1.json")
    assert (root / path).is_file()
    from conformance.families.game_orchestration import matches_orchestration

    observation = copy.deepcopy(
        load_and_validate_pack(root, path).document()["scenarios"][0]["expected"]
    )
    assert matches_orchestration(observation)
    observation["game"]["reportMatchesChecks"] = False
    assert not matches_orchestration(observation)
