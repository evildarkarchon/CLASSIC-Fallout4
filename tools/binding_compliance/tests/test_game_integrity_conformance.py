"""Game integrity evidence retains independent version/location check identities."""

import copy
from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
from conformance.packs import load_and_validate_pack


def test_integrity_check_identity_cannot_be_substituted() -> None:
    """A successful location check cannot substitute for executable-version evidence."""
    root = Path(__file__).resolve().parents[3]
    path = Path("tests/conformance/packs/game_integrity/v1.json")
    assert (root / path).is_file()
    from conformance.families.game_integrity import GAME_INTEGRITY_COVERAGE_POLICY

    document = load_and_validate_pack(root, path).document()
    scenario = document["scenarios"][0]
    observation = copy.deepcopy(scenario["expected"])
    assert derive_observed_fact_ids(
        document, scenario, observation, GAME_INTEGRITY_COVERAGE_POLICY
    )
    observation["checks"][0]["checkType"] = "InstallationLocation"
    assert not derive_observed_fact_ids(
        document, scenario, observation, GAME_INTEGRITY_COVERAGE_POLICY
    )
