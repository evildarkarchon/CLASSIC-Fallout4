"""Public pack and receipt boundary checks for User Settings shadow conformance."""

from __future__ import annotations

import hashlib
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


def test_user_settings_pack_covers_authored_update_and_bootstrap_operations() -> None:
    """Operation scenarios are compiled from the existing independent corpus."""

    pack = load_and_validate_pack(REPO_ROOT, PACK_PATH)
    scenarios = {scenario["id"]: scenario for scenario in pack.document()["scenarios"]}
    assert scenarios["preview-multi-field-update"]["expected"]["preview"][
        "acceptedFields"
    ] == [
        {"fieldPath": "/CLASSIC_Settings/Update Check", "value": False},
        {"fieldPath": "/CLASSIC_Settings/Max Concurrent Scans", "value": 4},
    ]
    assert (
        scenarios["bootstrap-missing-defaults"]["expected"]["commit"]["status"]
        == "committed"
    )
    assert (
        scenarios["refuse-stale-revision"]["expected"]["commit"]["status"] == "conflict"
    )
    assert all(
        "after_update" not in path and "bootstrap_defaults" not in path
        for path in pack.document()["fixtures"].values()
    )


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


def _prepared_copy(tmp_path: Path, fixture_updates: dict[str, bytes] | None = None):
    """Prepare an isolated committed copy through the public pack boundary."""

    fixture_root = tmp_path / "tests/fixtures/user_settings_compatibility"
    shutil.copytree(
        REPO_ROOT / "tests/fixtures/user_settings_compatibility", fixture_root
    )
    for name, content in (fixture_updates or {}).items():
        (fixture_root / name).write_bytes(content)
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
    receipt = {
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
    oracle_root = pack.fixture_root
    oracle = json.loads((oracle_root / "expectations.json").read_text(encoding="utf-8"))
    operations = {
        operation["id"].replace("_", "-"): operation
        for operation in oracle["operation_scenarios"]
    }
    for scenario in receipt["scenarios"]:
        observation = scenario["observation"]
        if observation.get("commit", {}).get("status") == "committed":
            content = (
                oracle_root / operations[scenario["id"]]["expected_document"]
            ).read_bytes()
            document = observation["finalTree"][1]
            del document["yamlNodes"]
            document["bytesHex"] = content.hex()
            observation["commit"]["revision"] = (
                "sha256:" + hashlib.sha256(content).hexdigest()
            )
    return receipt


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
    "changed_file",
    ["expectations.json", "canonical_current_nested.yaml", "bootstrap_defaults.yaml"],
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
    descriptor["scenarios"] = [
        scenario
        for scenario in descriptor["scenarios"]
        if scenario["id"] != "canonical-current-nested"
    ]
    path.write_text(json.dumps(descriptor), encoding="utf-8")
    with pytest.raises(PackValidationError):
        load_and_validate_pack(tmp_path, PACK_PATH)


@pytest.mark.parametrize(
    "case,mutation",
    [
        ("preview-multi-field-update", "accepted-value"),
        ("preview-multi-field-update", "accepted-type"),
        ("preview-multi-field-update", "accepted-extra"),
        ("preview-multi-field-update", "base-revision"),
        ("reject-invalid-update-as-one-unit", "diagnostic-field"),
        ("reject-invalid-update-as-one-unit", "diagnostic-code"),
        ("reject-invalid-update-as-one-unit", "diagnostic-message"),
        ("reject-invalid-update-as-one-unit", "partial-write"),
        ("bootstrap-missing-declined", "created-root"),
        ("bootstrap-missing-defaults", "published-revision"),
        ("bootstrap-missing-defaults", "default-value"),
        ("bootstrap-missing-defaults", "pre-normalized"),
        ("bootstrap-missing-defaults", "malformed-tree"),
        ("bootstrap-missing-defaults", "malformed-yaml"),
        ("bootstrap-missing-defaults", "extra-file"),
        ("commit-one-canonical-field-without-losing-unknowns", "unknown-type"),
        ("commit-preserves-alias-only", "dropped-alias"),
        ("commit-preserves-invalid-known-values", "repaired-invalid"),
        ("refuse-stale-revision", "conflict-expected"),
        ("refuse-stale-revision", "conflict-actual"),
        ("refuse-stale-revision", "external-overwritten"),
        ("bootstrap-concurrent-creation", "extra-lock"),
    ],
)
def test_operation_receipts_reject_changed_semantics_or_durable_effects(
    tmp_path: Path, case: str, mutation: str
) -> None:
    """Actual receipt values and both disk checkpoints must match the authored contract."""

    pack, run = _prepared_copy(tmp_path)
    receipt = _receipt(pack, run)
    run.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert not validate_prepared_run(
        pack, run, coverage_policy=USER_SETTINGS_COVERAGE_POLICY
    ).failures
    scenario = next(item for item in receipt["scenarios"] if item["id"] == case)
    observation = scenario["observation"]
    preview = observation["preview"]
    if mutation == "accepted-value":
        preview["acceptedFields"][0]["value"] = True
    elif mutation == "accepted-type":
        preview["acceptedFields"][0]["value"] = 0
    elif mutation == "accepted-extra":
        preview["acceptedFields"].append(
            {"fieldPath": "/CLASSIC_Settings/Game Version", "value": "auto"}
        )
    elif mutation == "base-revision":
        preview["baseRevision"] = "sha256:" + "0" * 64
    elif mutation.startswith("diagnostic-"):
        field = {
            "diagnostic-field": "fieldPath",
            "diagnostic-code": "code",
            "diagnostic-message": "message",
        }[mutation]
        preview["diagnostics"][0][field] = "incorrect"
    elif mutation == "partial-write":
        observation["finalTree"][1]["bytesHex"] = b"partial write".hex()
    elif mutation == "created-root":
        observation["afterPreviewTree"].append(
            {"path": {"path": "."}, "kind": "directory"}
        )
    elif mutation == "published-revision":
        observation["commit"]["revision"] = "sha256:" + "0" * 64
    elif mutation == "pre-normalized":
        expected_case = next(
            item for item in pack.document()["scenarios"] if item["id"] == case
        )
        observation["finalTree"][1] = expected_case["expected"]["finalTree"][1]
    elif mutation == "malformed-tree":
        observation["finalTree"] = [None]
    elif mutation in {"extra-file", "extra-lock"}:
        name = (
            "unexpected.tmp"
            if mutation == "extra-file"
            else "CLASSIC Settings.yaml.commit.lock"
        )
        observation["finalTree"].append(
            {"path": {"path": name}, "kind": "file", "bytesHex": ""}
        )
    elif mutation in {"conflict-expected", "conflict-actual"}:
        field = (
            "expectedRevision" if mutation == "conflict-expected" else "actualRevision"
        )
        observation["commit"][field] = "sha256:" + "0" * 64
    elif mutation == "external-overwritten":
        observation["finalTree"][1]["bytesHex"] = b"overwritten concurrent edit".hex()
    else:
        document = observation["finalTree"][1]
        content = bytes.fromhex(document["bytesHex"])
        replacements = {
            "default-value": (b'"Update Source": "GitHub"', b'"Update Source": "Both"'),
            "unknown-type": (b'string_number: "3"', b"string_number: 3"),
            "dropped-alias": (
                b"  Custom Scan Folder: E:/Alias Crash Logs",
                b"  unrelated: removed",
            ),
            "repaired-invalid": (b"  Game Version: Future", b"  Game Version: auto"),
        }
        if mutation == "malformed-yaml":
            content = b"broken: ["
        else:
            original, changed = replacements[mutation]
            assert original in content
            content = content.replace(original, changed)
        document["bytesHex"] = content.hex()
        # Keep the revision truthful so the semantic comparison, rather than the
        # byte-authentication check, detects dropped or mistyped document nodes.
        observation["commit"]["revision"] = (
            "sha256:" + hashlib.sha256(content).hexdigest()
        )
    run.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    report = validate_prepared_run(
        pack, run, coverage_policy=USER_SETTINGS_COVERAGE_POLICY
    )
    assert any(failure.scenario_id == case for failure in report.failures)
    result = next(item for item in report.scenarios if item.id == case)
    assert result.result == "fail"
    assert not result.observed_fact_ids


def test_committed_yaml_preserves_unknown_real_precision(tmp_path: Path) -> None:
    """Distinct real scalars cannot collapse through binary floating-point normalization."""

    name = "unknown_entries_after_update.yaml"
    original = (
        REPO_ROOT / "tests/fixtures/user_settings_compatibility" / name
    ).read_bytes()
    authored = original.replace(
        b"threshold: 1.25", b"threshold: 1.25000000000000000000001"
    )
    pack, run = _prepared_copy(tmp_path, {name: authored})
    receipt = _receipt(pack, run)
    run.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert not validate_prepared_run(pack, run).failures
    case = next(
        item
        for item in receipt["scenarios"]
        if item["id"] == "commit-one-canonical-field-without-losing-unknowns"
    )
    content = authored.replace(
        b"1.25000000000000000000001", b"1.25000000000000000000002"
    )
    case["observation"]["finalTree"][1]["bytesHex"] = content.hex()
    case["observation"]["commit"]["revision"] = (
        "sha256:" + hashlib.sha256(content).hexdigest()
    )
    run.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert validate_prepared_run(pack, run).failures


def test_bootstrap_expected_documents_are_authenticated_but_never_materialized(
    tmp_path: Path,
) -> None:
    """The complete default oracle participates in freshness without reaching adapters."""

    pack, run = _prepared_copy(tmp_path)
    dependency_names = {path.name for path in pack.oracle_paths}
    assert {
        "bootstrap_defaults.yaml",
        "bootstrap_overrides.yaml",
        "alias_only_after_update.yaml",
    } <= dependency_names
    planned_fixtures = run.document()["fixtures"]
    assert not any(name in json.dumps(planned_fixtures) for name in dependency_names)
    inputs = run.run_plan_path.read_text(encoding="utf-8")
    assert '"expected"' not in inputs
    assert "preview_diagnostics" not in inputs


def test_dropped_operation_cannot_shrink_authored_coverage(tmp_path: Path) -> None:
    """All independently authored operations remain mandatory in the executable pack."""

    _prepared_copy(tmp_path)
    path = tmp_path / PACK_PATH
    descriptor = json.loads(path.read_text(encoding="utf-8"))
    descriptor["scenarios"] = [
        scenario
        for scenario in descriptor["scenarios"]
        if scenario["id"] != "bootstrap-missing-defaults"
    ]
    path.write_text(json.dumps(descriptor), encoding="utf-8")
    with pytest.raises(PackValidationError):
        load_and_validate_pack(tmp_path, PACK_PATH)
