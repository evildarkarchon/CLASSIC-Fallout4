"""Published defaults require complete public projection observations."""

import copy
from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
from conformance.families.user_settings import USER_SETTINGS_COVERAGE_POLICY
from conformance.packs import load_and_validate_pack


def test_published_defaults_require_all_projection_fields() -> None:
    """Missing provenance cannot grant full default projection coverage."""
    root = Path(__file__).resolve().parents[3]
    document = load_and_validate_pack(
        root, Path("tests/conformance/packs/user_settings/v1.json")
    ).document()
    scenario = next(
        (
            item
            for item in document["scenarios"]
            if item["action"] == "user-settings.defaults"
        ),
        None,
    )
    assert scenario is not None
    expected = scenario["expected"]
    assert "user-settings.defaults" in derive_observed_fact_ids(
        document, scenario, expected, USER_SETTINGS_COVERAGE_POLICY
    )
    for key in expected["projection"]:
        incomplete = copy.deepcopy(expected)
        del incomplete["projection"][key]
        assert "user-settings.defaults" not in derive_observed_fact_ids(
            document, scenario, incomplete, USER_SETTINGS_COVERAGE_POLICY
        )


def test_update_setters_require_their_own_accepted_field() -> None:
    """An unrelated accepted preview cannot cover a setter that was not requested."""
    root = Path(__file__).resolve().parents[3]
    document = load_and_validate_pack(
        root, Path("tests/conformance/packs/user_settings/v1.json")
    ).document()
    scenario = next(
        (
            item
            for item in document["scenarios"]
            if item["id"] == "preview-all-typed-fields"
        ),
        None,
    )
    assert scenario is not None
    observation = copy.deepcopy(scenario["expected"])
    fact = "user-settings.setter.game-root"
    assert fact in derive_observed_fact_ids(
        document, scenario, observation, USER_SETTINGS_COVERAGE_POLICY
    )
    observation["preview"]["acceptedFields"] = [
        field
        for field in observation["preview"]["acceptedFields"]
        if field["fieldPath"] != "/CLASSIC_Settings/Game Folder Path"
    ]
    assert fact not in derive_observed_fact_ids(
        document, scenario, observation, USER_SETTINGS_COVERAGE_POLICY
    )
