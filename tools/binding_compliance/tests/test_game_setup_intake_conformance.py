"""Setup intake evidence must preserve explicit paths without writing settings."""

import copy
from pathlib import Path

from conformance.packs import load_and_validate_pack


def test_game_setup_intake_requires_read_only_observation() -> None:
    """Resolved paths cannot earn setup evidence after mutating the installation."""
    root = Path(__file__).resolve().parents[3]
    path = Path("tests/conformance/packs/game_setup_intake/v1.json")
    assert (root / path).is_file()
    from conformance.families.game_setup_intake import matches_intake

    observation = copy.deepcopy(
        load_and_validate_pack(root, path).document()["scenarios"][0]["expected"]
    )
    assert matches_intake(observation)
    observation["unchanged"] = False
    assert not matches_intake(observation)


def test_game_setup_proposal_requires_unpersisted_game_root_update() -> None:
    """A discovered path earns evidence only as a returned proposal with no write effect."""
    root = Path(__file__).resolve().parents[3]
    path = Path("tests/conformance/packs/game_setup_intake/v1.json")
    from conformance.families.game_setup_intake import matches_intake, matches_proposal

    scenarios = {
        scenario["id"]: scenario
        for scenario in load_and_validate_pack(root, path).document()["scenarios"]
    }
    observation = copy.deepcopy(scenarios["proposal"]["expected"])
    assert matches_proposal(observation)
    # The explicit-path fact cannot be satisfied by an observation that proposes an update,
    # and vice versa, so neither scenario can earn the other's credit.
    assert not matches_intake(observation)
    assert not matches_proposal(scenarios["explicit"]["expected"])

    persisted = copy.deepcopy(observation)
    persisted["unchanged"] = False
    assert not matches_proposal(persisted)

    dropped = copy.deepcopy(observation)
    dropped["pathUpdates"] = []
    dropped["pathUpdateCount"] = 0
    assert not matches_proposal(dropped)
