"""Public pack and receipt boundary checks for User Settings shadow conformance."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from conformance.families.user_settings import USER_SETTINGS_COVERAGE_POLICY
from conformance.packs import (
    MaterializationError,
    PackValidationError,
    discover_pack_paths,
    load_and_validate_pack,
    load_prepared_run,
    materialize_run_plan,
)
from conformance.receipts import validate_prepared_run

REPO_ROOT = Path(__file__).resolve().parents[3]
PACK_PATH = Path("tests/conformance/packs/user_settings/v1.json")


def test_user_settings_pack_resolves_the_existing_independent_oracle() -> None:
    """The second family references one oracle while exposing exact observations."""

    assert REPO_ROOT / PACK_PATH in discover_pack_paths(REPO_ROOT)
    tracked = json.loads((REPO_ROOT / PACK_PATH).read_text(encoding="utf-8"))
    assert tracked["scenarios"][0]["expected"] == {
        "compatibilityCase": "canonical_current_nested"
    }
    pack = load_and_validate_pack(REPO_ROOT, PACK_PATH)
    first = pack.document()["scenarios"][0]
    assert first["expected"]["view"]["update_check"] is True
    assert first["expected"]["source"] == {
        "location": "canonical",
        "path": {"path": "CLASSIC Settings.yaml"},
        "classification": "current",
    }
    assert "expectations.json" not in pack.document()["fixtures"].values()


def _prepared_copy(tmp_path: Path):
    """Prepare an isolated committed copy through the public pack boundary."""

    fixture_root = tmp_path / "tests/fixtures/user_settings_compatibility"
    shutil.copytree(
        REPO_ROOT / "tests/fixtures/user_settings_compatibility", fixture_root
    )
    pack_path = tmp_path / PACK_PATH
    pack_path.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / PACK_PATH, pack_path)
    (tmp_path / "tests/conformance/policy_exceptions.json").write_text(
        '{"schemaVersion":1,"exceptions":[]}', encoding="utf-8"
    )
    for arguments in (
        ("init",),
        ("config", "user.email", "conformance@example.invalid"),
        ("config", "user.name", "Conformance Tests"),
        ("add", "."),
        ("commit", "-m", "fixture"),
    ):
        subprocess.run(
            ["git", "-C", str(tmp_path), *arguments], check=True, capture_output=True
        )
    pack = load_and_validate_pack(tmp_path, PACK_PATH)
    run = materialize_run_plan(
        pack,
        participant_id="rust",
        participant_role="semantic-adapter",
        execution_instance_id="rust",
        source_paths=(PACK_PATH,),
    )
    return pack, run


def _receipt(pack, run) -> dict:
    """Supply exact reference evidence to exercise central comparison mutations."""

    plan = run.document()
    return {
        **{
            key: plan[key]
            for key in (
                "schemaVersion",
                "familyId",
                "familyVersion",
                "expectationDigest",
                "invocation",
                "participant",
            )
        },
        "runner": {
            "id": "user-settings-test",
            "version": 1,
            "platform": "windows",
            "toolchain": "rust",
        },
        "scenarios": [
            {
                "id": scenario["id"],
                "executionStatus": "completed",
                "capabilityIds": scenario["capabilityIds"],
                "observation": scenario["expected"],
                "failure": None,
            }
            for scenario in pack.document()["scenarios"]
        ],
    }


@pytest.mark.parametrize(
    "mutation",
    [
        "extra-field",
        "wrong-type",
        "wrong-value",
        "changed-tree",
        "missing-scenario",
        "wrong-participant",
        "reordered-diagnostics",
    ],
)
def test_central_comparison_rejects_incomplete_or_changed_observations(
    tmp_path: Path, mutation: str
) -> None:
    """Completed adapter status cannot hide a semantic or envelope mismatch."""

    pack, run = _prepared_copy(tmp_path)
    plan_text = run.run_plan_path.read_text(encoding="utf-8")
    assert "compatibilityCase" not in plan_text
    assert "expectations.json" not in json.dumps(run.document()["fixtures"])
    assert all("expected" not in scenario for scenario in run.document()["scenarios"])
    receipt = _receipt(pack, run)
    run.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert not validate_prepared_run(
        pack, run, coverage_policy=USER_SETTINGS_COVERAGE_POLICY
    ).failures
    observation = receipt["scenarios"][0]["observation"]
    if mutation == "extra-field":
        observation["view"]["unexpected"] = True
    elif mutation == "wrong-type":
        observation["view"]["update_check"] = 1
    elif mutation == "wrong-value":
        observation["view"]["update_check"] = False
    elif mutation == "changed-tree":
        observation["durableEffects"]["treeUnchanged"] = False
    elif mutation == "missing-scenario":
        receipt["scenarios"].pop()
    elif mutation == "reordered-diagnostics":
        invalid = next(
            scenario
            for scenario in receipt["scenarios"]
            if scenario["id"] == "invalid-known-values"
        )
        invalid["observation"]["diagnostics"].reverse()
    else:
        receipt["participant"]["id"] = "node"
    run.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert validate_prepared_run(
        pack, run, coverage_policy=USER_SETTINGS_COVERAGE_POLICY
    ).failures


@pytest.mark.parametrize(
    "changed_file", ["expectations.json", "canonical_current_nested.yaml"]
)
def test_existing_preparation_rejects_changed_oracle_or_fixture(
    tmp_path: Path, changed_file: str
) -> None:
    """Both oracle and fixture bytes participate in freshness authentication."""

    pack, run = _prepared_copy(tmp_path)
    path = tmp_path / "tests/fixtures/user_settings_compatibility" / changed_file
    path.write_bytes(path.read_bytes() + b"\n")
    current = load_and_validate_pack(tmp_path, PACK_PATH)
    assert current.expectation_digest != pack.expectation_digest
    with pytest.raises(MaterializationError):
        materialize_run_plan(
            pack,
            participant_id="rust",
            participant_role="semantic-adapter",
            execution_instance_id="rust",
            source_paths=(PACK_PATH,),
        )
    with pytest.raises(MaterializationError):
        load_prepared_run(current, run.run_plan_path)


def test_unknown_oracle_classification_fails_closed(tmp_path: Path) -> None:
    """A new corpus classification requires an explicit central contract mapping."""

    _prepared_copy(tmp_path)
    path = tmp_path / "tests/fixtures/user_settings_compatibility/expectations.json"
    oracle = json.loads(path.read_text(encoding="utf-8"))
    oracle["cases"][0]["source"]["classification"] = "unrecognized_future_contract"
    path.write_text(json.dumps(oracle), encoding="utf-8")
    with pytest.raises(PackValidationError):
        load_and_validate_pack(tmp_path, PACK_PATH)


def test_removing_an_ordinary_open_case_cannot_shrink_the_pack(tmp_path: Path) -> None:
    """The compatibility corpus, rather than edited scenario count, owns scope."""

    _prepared_copy(tmp_path)
    path = tmp_path / PACK_PATH
    descriptor = json.loads(path.read_text(encoding="utf-8"))
    descriptor["scenarios"].pop()
    path.write_text(json.dumps(descriptor), encoding="utf-8")
    with pytest.raises(PackValidationError):
        load_and_validate_pack(tmp_path, PACK_PATH)
