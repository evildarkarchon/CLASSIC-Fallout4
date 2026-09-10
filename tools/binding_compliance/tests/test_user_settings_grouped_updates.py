"""Grouped settings update observations cannot omit individual members."""

import copy
from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
from conformance.families.user_settings import USER_SETTINGS_COVERAGE_POLICY
from conformance.packs import load_and_validate_pack


def test_legacy_import_restore_requires_verified_original_bytes() -> None:
    """An import restoration cannot claim success without a verified base revision."""
    root = Path(__file__).resolve().parents[3]
    document = load_and_validate_pack(
        root, Path("tests/conformance/packs/user_settings/v1.json")
    ).document()
    scenario = next(
        (
            item
            for item in document["scenarios"]
            if item["id"] == "legacy-tui-import-restore"
        ),
        None,
    )
    assert scenario is not None
    observation = copy.deepcopy(scenario["expected"])
    fact = "user-settings.legacy-import-restored"
    assert fact in derive_observed_fact_ids(
        document, scenario, observation, USER_SETTINGS_COVERAGE_POLICY
    )
    observation["restore"]["revisionMatches"] = False
    assert fact not in derive_observed_fact_ids(
        document, scenario, observation, USER_SETTINGS_COVERAGE_POLICY
    )


def test_geometry_commit_authenticates_published_revision() -> None:
    """A claimed geometry commit cannot borrow an unverified published revision."""
    root = Path(__file__).resolve().parents[3]
    document = load_and_validate_pack(
        root, Path("tests/conformance/packs/user_settings/v1.json")
    ).document()
    scenario = next(
        (item for item in document["scenarios"] if item["id"] == "geometry-commit"),
        None,
    )
    assert scenario is not None
    observation = copy.deepcopy(scenario["expected"])
    fact = "user-settings.geometry-committed"
    assert fact in derive_observed_fact_ids(
        document, scenario, observation, USER_SETTINGS_COVERAGE_POLICY
    )
    observation["transition"]["revisionMatches"] = False
    assert fact not in derive_observed_fact_ids(
        document, scenario, observation, USER_SETTINGS_COVERAGE_POLICY
    )


def test_geometry_setter_requires_all_three_dimensions() -> None:
    """Partial geometry cannot cover the grouped window transition setter."""
    root = Path(__file__).resolve().parents[3]
    document = load_and_validate_pack(
        root, Path("tests/conformance/packs/user_settings/v1.json")
    ).document()
    scenario = next(
        item
        for item in document["scenarios"]
        if item["id"] == "preview-all-typed-fields"
    )
    observation = copy.deepcopy(scenario["expected"])
    fact = "user-settings.setter.window-geometry"
    assert fact in derive_observed_fact_ids(
        document, scenario, observation, USER_SETTINGS_COVERAGE_POLICY
    )
    observation["preview"]["acceptedFields"] = [
        field
        for field in observation["preview"]["acceptedFields"]
        if field["fieldPath"] != "/UI/window_geometry/main_tab/width"
    ]
    assert fact not in derive_observed_fact_ids(
        document, scenario, observation, USER_SETTINGS_COVERAGE_POLICY
    )
