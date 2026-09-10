"""YAML update receipt facts must authenticate consent and rollback byte effects."""

import copy
from pathlib import Path

from conformance.packs import load_and_validate_pack


def test_yaml_rollback_rejects_non_byte_identity_strings() -> None:
    """Equal arbitrary strings cannot stand in for the prior and restored file bytes."""
    from conformance.families.yaml_update_operations import matches_rollback

    root = Path(__file__).resolve().parents[3]
    document = load_and_validate_pack(
        root, Path("tests/conformance/packs/yaml_update_operations/v1.json")
    ).document()
    observation = copy.deepcopy(
        next(
            item
            for item in document["scenarios"]
            if item["id"] == "rollback-generations"
        )["expected"]
    )
    for item in observation["beforeFiles"]:
        if item["path"] == "cache/CLASSIC/yaml-cache/fixture.yaml.prev":
            item["hex"] = "not byte data"
    for item in observation["files"]:
        if item["path"] == "cache/CLASSIC/yaml-cache/fixture.yaml":
            item["hex"] = "not byte data"
    assert not matches_rollback("yaml_rollback_update", observation)


def test_each_yaml_update_case_requires_both_file_checkpoints() -> None:
    """No YAML update operation earns evidence after either durable checkpoint disappears."""
    from conformance.coverage import derive_observed_fact_ids
    from conformance.families.yaml_update_operations import (
        YAML_UPDATE_OPERATIONS_COVERAGE_POLICY,
    )

    root = Path(__file__).resolve().parents[3]
    document = load_and_validate_pack(
        root, Path("tests/conformance/packs/yaml_update_operations/v1.json")
    ).document()
    for scenario in document["scenarios"]:
        observation = copy.deepcopy(scenario["expected"])
        assert derive_observed_fact_ids(
            document, scenario, observation, YAML_UPDATE_OPERATIONS_COVERAGE_POLICY
        )
        del observation["beforeFiles"]
        assert not derive_observed_fact_ids(
            document, scenario, observation, YAML_UPDATE_OPERATIONS_COVERAGE_POLICY
        )


def test_yaml_rollback_requires_the_previous_generation_bytes() -> None:
    """A rolled-back flag alone cannot replace proof that the previous bytes became current."""
    root = Path(__file__).resolve().parents[3]
    path = Path("tests/conformance/packs/yaml_update_operations/v1.json")
    assert (root / path).is_file()
    from conformance.families.yaml_update_operations import matches_rollback

    document = load_and_validate_pack(root, path).document()
    scenario = next(
        item for item in document["scenarios"] if item["id"] == "rollback-generations"
    )
    observation = copy.deepcopy(scenario["expected"])
    assert matches_rollback("yaml_rollback_update", observation)
    for item in observation["files"]:
        if item["path"] == "cache/CLASSIC/yaml-cache/fixture.yaml":
            item["hex"] = b"wrong generation".hex()
    assert not matches_rollback("yaml_rollback_update", observation)
