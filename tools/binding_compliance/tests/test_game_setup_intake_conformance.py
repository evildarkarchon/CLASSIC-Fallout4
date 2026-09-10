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
