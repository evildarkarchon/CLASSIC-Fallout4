"""Behavior tests for validated conformance packs and input-only run plans."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from conformance.packs import (
    MaterializationError,
    PackValidationError,
    discover_pack_paths,
    load_and_validate_pack,
    load_prepared_run,
    materialize_run_plan,
)


def _valid_pack() -> dict[str, Any]:
    """Return the smallest complete generic scenario pack used by these tests."""

    return {
        "schemaVersion": 1,
        "familyId": "example-family",
        "familyVersion": 1,
        "domainOwner": {"rustCrate": "classic-example-core"},
        "fixtureRoot": "tests/fixtures/example-family",
        "fixtures": {"primaryInput": "primary.txt"},
        "capabilities": [
            {
                "id": "example.execute",
                "rustSymbols": ["Request", "execute"],
                "observationFamilies": ["result"],
            }
        ],
        "scenarios": [
            {
                "id": "base-case",
                "action": "example.execute",
                "capabilityIds": ["example.execute"],
                "fixtureRefs": ["primaryInput"],
                "input": {"enabled": True},
                "expected": {"status": "completed"},
                "normalization": {
                    "rootRelativePaths": True,
                    "unorderedPaths": [],
                    "excludedPaths": [],
                },
            }
        ],
        "consumerObligations": [{"id": "example-rendering"}],
    }


def _write_pack(repo_root: Path, pack: dict[str, Any]) -> Path:
    """Write a pack and its declared input fixture beneath a temporary repo root."""

    fixture_root = repo_root / "tests" / "fixtures" / "example-family"
    fixture_root.mkdir(parents=True)
    (fixture_root / "primary.txt").write_text("input bytes\n", encoding="utf-8")
    pack_path = repo_root / "tests" / "conformance" / "packs" / "example.json"
    pack_path.parent.mkdir(parents=True)
    pack_path.write_text(json.dumps(pack), encoding="utf-8")
    return pack_path


def _commit_repository(repo_root: Path) -> None:
    """Create one self-contained Git revision for source-identity behavior tests."""

    commands = (
        ("init",),
        ("config", "user.email", "conformance-tests@example.invalid"),
        ("config", "user.name", "Conformance Tests"),
        ("add", "."),
        ("commit", "-m", "fixture"),
    )
    for arguments in commands:
        subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            check=True,
            capture_output=True,
        )


@pytest.mark.parametrize(
    ("field", "invalid_identity"),
    [
        ("family", "Example-Family"),
        ("owner", "Classic_Example_Core"),
        ("capability", "example/execute"),
        ("observation", "result value"),
        ("scenario", "base case"),
        ("action", "Example.execute"),
        ("consumer", "example_rendering"),
    ],
)
def test_pack_validation_rejects_invalid_machine_identities(
    tmp_path: Path, field: str, invalid_identity: str
) -> None:
    """Every schema-owned identity uses the stable lowercase token grammar."""

    pack = _valid_pack()
    if field == "family":
        pack["familyId"] = invalid_identity
    elif field == "owner":
        pack["domainOwner"]["rustCrate"] = invalid_identity
    elif field == "capability":
        pack["capabilities"][0]["id"] = invalid_identity
    elif field == "observation":
        pack["capabilities"][0]["observationFamilies"][0] = invalid_identity
    elif field == "scenario":
        pack["scenarios"][0]["id"] = invalid_identity
    elif field == "action":
        pack["scenarios"][0]["action"] = invalid_identity
    else:
        pack["consumerObligations"][0]["id"] = invalid_identity
    pack_path = _write_pack(tmp_path, pack)

    with pytest.raises(PackValidationError, match="stable machine identifier"):
        load_and_validate_pack(tmp_path, pack_path)


def test_pack_validation_rejects_floating_point_common_observations(
    tmp_path: Path,
) -> None:
    """Common observations cannot depend on cross-language float encoding."""

    pack = _valid_pack()
    pack["scenarios"][0]["expected"]["durationSeconds"] = 0.1
    pack_path = _write_pack(tmp_path, pack)

    with pytest.raises(PackValidationError, match="floating-point"):
        load_and_validate_pack(tmp_path, pack_path)


@pytest.mark.parametrize(
    "failure_kind", ["undeclared", "parent", "absolute", "missing"]
)
def test_pack_validation_rejects_undeclared_or_escaping_fixtures(
    tmp_path: Path, failure_kind: str
) -> None:
    """Adapters can receive only declared files contained by the fixture root."""

    pack = _valid_pack()
    if failure_kind == "undeclared":
        pack["scenarios"][0]["fixtureRefs"] = ["missingInput"]
    elif failure_kind == "parent":
        pack["fixtures"]["primaryInput"] = "../outside.txt"
    elif failure_kind == "absolute":
        pack["fixtures"]["primaryInput"] = (tmp_path / "outside.txt").as_posix()
        (tmp_path / "outside.txt").write_text("outside\n", encoding="utf-8")
    else:
        pack["fixtures"]["primaryInput"] = "missing.txt"
    pack_path = _write_pack(tmp_path, pack)
    if failure_kind == "parent":
        (tmp_path / "tests" / "fixtures" / "outside.txt").write_text(
            "outside\n", encoding="utf-8"
        )

    with pytest.raises(PackValidationError, match="fixture"):
        load_and_validate_pack(tmp_path, pack_path)


def test_pack_validation_rejects_a_fixture_symlink_that_escapes_its_root(
    tmp_path: Path,
) -> None:
    """Resolved fixture containment cannot be bypassed through a symlink."""

    pack = _valid_pack()
    pack["fixtures"]["primaryInput"] = "escape.txt"
    pack_path = _write_pack(tmp_path, pack)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    fixture_link = tmp_path / "tests" / "fixtures" / "example-family" / "escape.txt"
    try:
        fixture_link.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"fixture symlinks are unavailable on this host: {error}")

    with pytest.raises(PackValidationError, match="fixture"):
        load_and_validate_pack(tmp_path, pack_path)


@pytest.mark.parametrize(
    "excluded_paths",
    [
        [{"path": "$.events[*]", "rationale": "Events are concurrent."}],
        [{"path": "$..elapsedMs", "rationale": "Wall-clock timing varies."}],
        [{"path": "$", "rationale": "Ignore the entire observation."}],
        [{"path": "$.elapsedMs", "rationale": ""}],
        [{"path": "$.elapsedMs"}],
    ],
)
def test_pack_validation_rejects_over_broad_normalization(
    tmp_path: Path, excluded_paths: list[dict[str, str]]
) -> None:
    """Exclusions name one exact path and carry a non-empty rationale."""

    pack = _valid_pack()
    pack["scenarios"][0]["normalization"]["excludedPaths"] = excluded_paths
    pack_path = _write_pack(tmp_path, pack)

    with pytest.raises(PackValidationError, match="normalization"):
        load_and_validate_pack(tmp_path, pack_path)


@pytest.mark.parametrize(
    "failure_kind",
    [
        "duplicate-capability",
        "duplicate-scenario",
        "duplicate-observation",
        "duplicate-consumer",
        "unknown-capability",
        "action-not-declared",
    ],
)
def test_pack_validation_rejects_duplicate_or_dangling_identities(
    tmp_path: Path, failure_kind: str
) -> None:
    """Stable IDs stay unique and every scenario reference resolves centrally."""

    pack = _valid_pack()
    if failure_kind == "duplicate-capability":
        pack["capabilities"].append(dict(pack["capabilities"][0]))
    elif failure_kind == "duplicate-scenario":
        pack["scenarios"].append(dict(pack["scenarios"][0]))
    elif failure_kind == "duplicate-observation":
        pack["capabilities"][0]["observationFamilies"].append("result")
    elif failure_kind == "duplicate-consumer":
        pack["consumerObligations"].append({"id": "example-rendering"})
    elif failure_kind == "unknown-capability":
        pack["scenarios"][0]["capabilityIds"] = ["example.missing"]
        pack["scenarios"][0]["action"] = "example.missing"
    else:
        pack["scenarios"][0]["action"] = "example.prepare"
    pack_path = _write_pack(tmp_path, pack)

    with pytest.raises(PackValidationError, match="identit|capabilit|action"):
        load_and_validate_pack(tmp_path, pack_path)


@pytest.mark.parametrize(
    "failure_kind",
    [
        "schema-version",
        "family-version",
        "top-level-participant",
        "participant-expectation",
        "missing-expected",
        "missing-rust-symbol",
        "duplicate-rust-symbol",
        "free-form-consumer",
    ],
)
def test_pack_schema_rejects_unknown_fields_and_incomplete_common_shapes(
    tmp_path: Path, failure_kind: str
) -> None:
    """The common schema fails closed instead of accepting adapter escape hatches."""

    pack = _valid_pack()
    if failure_kind == "schema-version":
        pack["schemaVersion"] = 2
    elif failure_kind == "family-version":
        pack["familyVersion"] = 0
    elif failure_kind == "top-level-participant":
        pack["participants"] = [{"id": "node", "required": False}]
    elif failure_kind == "participant-expectation":
        pack["scenarios"][0]["nodeExpected"] = {"status": "different"}
    elif failure_kind == "missing-expected":
        del pack["scenarios"][0]["expected"]
    elif failure_kind == "missing-rust-symbol":
        pack["capabilities"][0]["rustSymbols"] = []
    elif failure_kind == "duplicate-rust-symbol":
        pack["capabilities"][0]["rustSymbols"] = ["execute", "execute"]
    else:
        pack["consumerObligations"][0]["expected"] = {"text": "copied"}
    pack_path = _write_pack(tmp_path, pack)

    with pytest.raises(PackValidationError, match="schema"):
        load_and_validate_pack(tmp_path, pack_path)


def test_pack_validation_rejects_duplicate_json_object_keys(tmp_path: Path) -> None:
    """JSON parsing cannot silently collapse two declarations into one value."""

    pack_path = _write_pack(tmp_path, _valid_pack())
    source = pack_path.read_text(encoding="utf-8")
    source = source.replace(
        '"familyId": "example-family"',
        '"familyId": "example-family", "familyId": "other-family"',
        1,
    )
    pack_path.write_text(source, encoding="utf-8")

    with pytest.raises(PackValidationError, match="duplicate JSON object key"):
        load_and_validate_pack(tmp_path, pack_path)


def test_expectation_digest_covers_canonical_pack_and_every_declared_fixture(
    tmp_path: Path,
) -> None:
    """Formatting is irrelevant while any pack fact or declared byte is covered."""

    pack = _valid_pack()
    pack["fixtures"]["unusedInput"] = "unused.bin"
    pack["scenarios"][0]["expected"]["message"] = "café 🚀"
    pack_path = _write_pack(tmp_path, pack)
    unused_path = tmp_path / "tests" / "fixtures" / "example-family" / "unused.bin"
    unused_path.write_bytes(b"unused fixture v1\x00")

    first = load_and_validate_pack(tmp_path, pack_path)
    pack_path.write_text(
        json.dumps(pack, indent=4, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    reformatted = load_and_validate_pack(tmp_path, pack_path)
    assert first.expectation_digest == reformatted.expectation_digest
    assert first.expectation_digest.startswith("sha256:")

    unused_path.write_bytes(b"unused fixture v2\x00")
    changed_fixture = load_and_validate_pack(tmp_path, pack_path)
    assert changed_fixture.expectation_digest != first.expectation_digest

    unused_path.write_bytes(b"unused fixture v1\x00")
    pack["scenarios"][0]["expected"]["message"] = "different oracle"
    pack_path.write_text(json.dumps(pack), encoding="utf-8")
    changed_pack = load_and_validate_pack(tmp_path, pack_path)
    assert changed_pack.expectation_digest != first.expectation_digest


def test_pack_discovery_is_recursive_and_deterministic(tmp_path: Path) -> None:
    """Contributors get one stable repository-relative order for tracked packs."""

    packs_root = tmp_path / "tests" / "conformance" / "packs"
    (packs_root / "zeta").mkdir(parents=True)
    (packs_root / "alpha").mkdir(parents=True)
    (packs_root / "zeta" / "second.json").write_text("{}", encoding="utf-8")
    (packs_root / "alpha" / "first.json").write_text("{}", encoding="utf-8")
    (packs_root / "README.md").write_text("not a pack\n", encoding="utf-8")

    discovered = discover_pack_paths(tmp_path)

    assert [path.relative_to(tmp_path).as_posix() for path in discovered] == [
        "tests/conformance/packs/alpha/first.json",
        "tests/conformance/packs/zeta/second.json",
    ]


def test_each_materialization_is_fresh_and_never_exposes_the_oracle(
    tmp_path: Path,
) -> None:
    """Adapters receive fresh plans containing inputs but no expected observation."""

    pack = _valid_pack()
    oracle_sentinel = "ORACLE-ONLY-7e80f853"
    pack["scenarios"][0]["input"]["expected"] = "legitimate-input-field"
    pack["scenarios"][0]["expected"] = {
        "status": "completed",
        "secret": {"sentinel": oracle_sentinel},
    }
    pack["scenarios"][0]["normalization"] = {
        "rootRelativePaths": True,
        "unorderedPaths": ["$.events"],
        "excludedPaths": [
            {
                "path": "$.diagnostics.elapsedMs",
                "rationale": "Wall-clock timing is not a semantic observation.",
            }
        ],
    }
    pack_path = _write_pack(tmp_path, pack)
    runner_path = tmp_path / "runner.py"
    runner_path.write_text("# adapter runner input\n", encoding="utf-8")
    _commit_repository(tmp_path)
    validated = load_and_validate_pack(tmp_path, pack_path)
    artifact_root = tmp_path / "tools" / "binding_compliance" / "artifacts"

    first = materialize_run_plan(
        validated,
        participant_id="node",
        participant_role="semantic-adapter",
        execution_instance_id="windows-node",
        source_paths=(runner_path,),
        artifact_root=artifact_root,
    )
    second = materialize_run_plan(
        validated,
        participant_id="node",
        participant_role="semantic-adapter",
        execution_instance_id="windows-node",
        source_paths=(runner_path,),
        artifact_root=artifact_root,
    )

    first_plan = first.document()
    second_plan = second.document()
    assert first_plan["invocation"]["id"] != second_plan["invocation"]["id"]
    assert (
        first_plan["invocation"]["runPlanDigest"]
        != second_plan["invocation"]["runPlanDigest"]
    )
    assert (
        first_plan["invocation"]["sourceIdentity"]
        == second_plan["invocation"]["sourceIdentity"]
    )
    assert first.artifact_dir != second.artifact_dir
    assert first.run_plan_path.is_file()
    assert not first.receipt_path.exists()
    assert list(first.artifact_dir.iterdir()) == [first.run_plan_path]
    assert first_plan["participant"] == {
        "id": "node",
        "role": "semantic-adapter",
        "executionInstanceId": "windows-node",
    }
    assert Path(first_plan["fixtureRoot"]).is_absolute()
    assert all(Path(path).is_absolute() for path in first_plan["fixtures"].values())
    assert first_plan["sourcePaths"] == ["runner.py"]
    assert first_plan["scenarios"][0]["input"]["expected"] == "legitimate-input-field"
    assert "expected" not in first_plan["scenarios"][0]
    assert oracle_sentinel not in first.run_plan_path.read_text(encoding="utf-8")


def test_materialized_run_can_be_authenticated_by_a_later_cli_process(
    tmp_path: Path,
) -> None:
    """Receipt-only validation reloads the exact current immutable plan."""

    pack_path = _write_pack(tmp_path, _valid_pack())
    runner_path = tmp_path / "runner.py"
    runner_path.write_text("# native launcher\n", encoding="utf-8")
    _commit_repository(tmp_path)
    pack = load_and_validate_pack(tmp_path, pack_path)
    run = materialize_run_plan(
        pack,
        participant_id="node",
        participant_role="semantic-adapter",
        execution_instance_id="node",
        source_paths=(runner_path,),
        artifact_root=tmp_path / "tools" / "binding_compliance" / "artifacts",
    )

    reloaded = load_prepared_run(pack, run.run_plan_path, receipt_path=run.receipt_path)

    assert reloaded.has_trusted_provenance
    assert reloaded.canonical_json == run.canonical_json
    assert reloaded.receipt_path == run.receipt_path

    runner_path.write_text("# changed native launcher\n", encoding="utf-8")
    with pytest.raises(MaterializationError, match="source identity"):
        load_prepared_run(pack, run.run_plan_path, receipt_path=run.receipt_path)


def test_source_identity_tracks_only_declared_current_runner_inputs(
    tmp_path: Path,
) -> None:
    """Current source identity changes with relevant, not unrelated, worktree bytes."""

    pack_path = _write_pack(tmp_path, _valid_pack())
    runner_path = tmp_path / "runner.py"
    runner_path.write_text("version = 1\n", encoding="utf-8")
    unrelated_path = tmp_path / "notes.txt"
    unrelated_path.write_text("version = 1\n", encoding="utf-8")
    _commit_repository(tmp_path)
    validated = load_and_validate_pack(tmp_path, pack_path)
    artifact_root = tmp_path / "tools" / "binding_compliance" / "artifacts"

    first = materialize_run_plan(
        validated,
        participant_id="python",
        participant_role="semantic-adapter",
        execution_instance_id="windows-python",
        source_paths=(runner_path,),
        artifact_root=artifact_root,
    )
    unrelated_path.write_text("version = 2\n", encoding="utf-8")
    unrelated = materialize_run_plan(
        validated,
        participant_id="python",
        participant_role="semantic-adapter",
        execution_instance_id="windows-python",
        source_paths=(runner_path,),
        artifact_root=artifact_root,
    )
    runner_path.write_text("version = 2\n", encoding="utf-8")
    relevant = materialize_run_plan(
        validated,
        participant_id="python",
        participant_role="semantic-adapter",
        execution_instance_id="windows-python",
        source_paths=(runner_path,),
        artifact_root=artifact_root,
    )

    first_identity = first.document()["invocation"]["sourceIdentity"]
    assert unrelated.document()["invocation"]["sourceIdentity"] == first_identity
    assert relevant.document()["invocation"]["sourceIdentity"] != first_identity


def test_source_identity_covers_declared_paths_even_when_git_ignores_them(
    tmp_path: Path,
) -> None:
    """Declared path identity and bytes never disappear behind Git ignore state."""

    pack_path = _write_pack(tmp_path, _valid_pack())
    first_runner = tmp_path / "first_runner.py"
    second_runner = tmp_path / "second_runner.py"
    first_runner.write_text("same bytes\n", encoding="utf-8")
    second_runner.write_text("same bytes\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("ignored-runner.bin\n", encoding="utf-8")
    ignored_runner = tmp_path / "ignored-runner.bin"
    ignored_runner.write_bytes(b"ignored v1\x00")
    _commit_repository(tmp_path)
    validated = load_and_validate_pack(tmp_path, pack_path)
    artifact_root = tmp_path / "tools" / "binding_compliance" / "artifacts"

    first_path = materialize_run_plan(
        validated,
        participant_id="rust",
        participant_role="semantic-adapter",
        execution_instance_id="windows-rust",
        source_paths=(first_runner,),
        artifact_root=artifact_root,
    )
    second_path = materialize_run_plan(
        validated,
        participant_id="rust",
        participant_role="semantic-adapter",
        execution_instance_id="windows-rust",
        source_paths=(second_runner,),
        artifact_root=artifact_root,
    )
    ignored_first = materialize_run_plan(
        validated,
        participant_id="rust",
        participant_role="semantic-adapter",
        execution_instance_id="windows-rust",
        source_paths=(ignored_runner,),
        artifact_root=artifact_root,
    )
    ignored_runner.write_bytes(b"ignored v2\x00")
    ignored_second = materialize_run_plan(
        validated,
        participant_id="rust",
        participant_role="semantic-adapter",
        execution_instance_id="windows-rust",
        source_paths=(ignored_runner,),
        artifact_root=artifact_root,
    )

    assert (
        first_path.document()["invocation"]["sourceIdentity"]
        != second_path.document()["invocation"]["sourceIdentity"]
    )
    assert (
        ignored_first.document()["invocation"]["sourceIdentity"]
        != ignored_second.document()["invocation"]["sourceIdentity"]
    )


def test_materialization_rejects_an_artifact_component_symlink_escape(
    tmp_path: Path,
) -> None:
    """A participant directory cannot redirect a fresh launch outside artifacts."""

    pack_path = _write_pack(tmp_path, _valid_pack())
    runner_path = tmp_path / "runner.py"
    runner_path.write_text("version = 1\n", encoding="utf-8")
    _commit_repository(tmp_path)
    validated = load_and_validate_pack(tmp_path, pack_path)
    artifact_root = tmp_path / "tools" / "binding_compliance" / "artifacts"
    artifact_root.mkdir(parents=True)
    outside = tmp_path / "outside-artifacts"
    outside.mkdir()
    try:
        (artifact_root / "node").symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlinks are unavailable on this host: {error}")

    with pytest.raises(MaterializationError, match="artifact"):
        materialize_run_plan(
            validated,
            participant_id="node",
            participant_role="semantic-adapter",
            execution_instance_id="windows-node",
            source_paths=(runner_path,),
            artifact_root=artifact_root,
        )
    assert list(outside.iterdir()) == []


def test_materialization_rejects_an_in_root_artifact_component_symlink(
    tmp_path: Path,
) -> None:
    """Participant identity cannot alias another participant's artifact subtree."""

    pack_path = _write_pack(tmp_path, _valid_pack())
    runner_path = tmp_path / "runner.py"
    runner_path.write_text("version = 1\n", encoding="utf-8")
    _commit_repository(tmp_path)
    validated = load_and_validate_pack(tmp_path, pack_path)
    artifact_root = tmp_path / "tools" / "binding_compliance" / "artifacts"
    other_participant = artifact_root / "python"
    other_participant.mkdir(parents=True)
    try:
        (artifact_root / "node").symlink_to(other_participant, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlinks are unavailable on this host: {error}")

    with pytest.raises(MaterializationError, match="artifact"):
        materialize_run_plan(
            validated,
            participant_id="node",
            participant_role="semantic-adapter",
            execution_instance_id="windows-node",
            source_paths=(runner_path,),
            artifact_root=artifact_root,
        )

    assert list(other_participant.iterdir()) == []
