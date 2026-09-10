"""Behavior tests for source-owned consumer conformance obligations."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from conformance.applicability import derive_applicability
from conformance.consumers import (
    derive_consumer_coverage,
    load_consumer_obligations,
    prepare_consumer_run,
)
from conformance.packs import (
    MaterializationError,
    _run_plan_digest,
    _source_identity,
    load_and_validate_pack,
    load_prepared_run,
)
from conformance.receipts import (
    ObligationValidationResult,
    PreparedRunReport,
    validate_prepared_run,
)
from conformance.reports import build_scoped_report


def _catalog() -> dict[str, object]:
    """Return one minimal source-owned consumer obligation catalog."""

    return {
        "schemaVersion": 1,
        "families": [
            {
                "familyId": "example-family",
                "consumers": [
                    {
                        "id": "cli",
                        "executionInstanceIds": ["windows-msvc"],
                        "sourcePaths": ["classic-cli/src/main.cpp"],
                        "obligations": [
                            {
                                "id": "cli.stream-selection",
                                "scenarioIds": ["base-case"],
                                "expected": {"stdout": True, "stderr": False},
                            }
                        ],
                    }
                ],
            }
        ],
    }


def _prepare_example_consumer(tmp_path: Path):
    """Create one committed pack, catalog, and input-only consumer run."""

    source = tmp_path / "classic-cli" / "src" / "main.cpp"
    source.parent.mkdir(parents=True)
    source.write_text("int main() {}\n", encoding="utf-8")
    catalog_path = tmp_path / "tests" / "conformance" / "consumer-obligations.json"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text(json.dumps(_catalog()), encoding="utf-8")
    fixture_root = tmp_path / "tests" / "fixtures" / "example-family"
    fixture_root.mkdir(parents=True)
    (fixture_root / "primary.txt").write_text("input\n", encoding="utf-8")
    pack = {
        "schemaVersion": 1,
        "familyId": "example-family",
        "familyVersion": 1,
        "domainOwner": {"rustCrate": "classic-example-core"},
        "fixtureRoot": "tests/fixtures/example-family",
        "fixtures": {"primaryInput": "primary.txt"},
        "capabilities": [
            {
                "id": "example.execute",
                "rustSymbols": ["execute"],
                "observationFamilies": ["result"],
            }
        ],
        "scenarios": [
            {
                "id": "base-case",
                "action": "example.execute",
                "capabilityIds": ["example.execute"],
                "fixtureRefs": ["primaryInput"],
                "input": {},
                "expected": {"status": "completed"},
                "normalization": {
                    "rootRelativePaths": True,
                    "unorderedPaths": [],
                    "excludedPaths": [],
                },
            }
        ],
        "consumerObligations": [{"id": "cli.stream-selection"}],
    }
    pack_path = tmp_path / "tests" / "conformance" / "packs" / "example.json"
    pack_path.parent.mkdir(parents=True)
    pack_path.write_text(json.dumps(pack), encoding="utf-8")
    for arguments in (
        ("init",),
        ("config", "user.email", "consumer@example.invalid"),
        ("config", "user.name", "Consumer Test"),
        ("add", "."),
        ("commit", "-m", "fixture"),
    ):
        subprocess.run(
            ["git", "-C", str(tmp_path), *arguments],
            check=True,
            capture_output=True,
        )
    validated = load_and_validate_pack(tmp_path, pack_path)
    catalog = load_consumer_obligations(tmp_path, catalog_path)
    run = prepare_consumer_run(
        validated,
        participant_id="cli",
        execution_instance_id="windows-msvc",
        artifact_root=tmp_path / "artifacts",
        catalog=catalog,
    )
    return validated, catalog, run


def test_catalog_loads_repository_owned_consumer_expectations(tmp_path: Path) -> None:
    """The central loader owns participant, source, scope, and expected payload."""

    source = tmp_path / "classic-cli" / "src" / "main.cpp"
    source.parent.mkdir(parents=True)
    source.write_text("int main() {}\n", encoding="utf-8")
    path = tmp_path / "tests" / "conformance" / "consumer-obligations.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_catalog()), encoding="utf-8")

    catalog = load_consumer_obligations(tmp_path, path)

    participant = catalog.participant("example-family", "cli")
    assert participant.execution_instance_ids == ("windows-msvc",)
    assert participant.source_paths == (Path("classic-cli/src/main.cpp"),)
    assert participant.obligations[0].document() == {
        "id": "cli.stream-selection",
        "scenarioIds": ["base-case"],
        "expected": {"stdout": True, "stderr": False},
    }
    assert catalog.has_trusted_provenance

    detached = participant.obligations[0].expected
    detached["stdout"] = False
    assert participant.obligations[0].expected["stdout"] is True


def test_applicability_adds_only_catalog_owned_pack_obligations(tmp_path: Path) -> None:
    """Pack IDs select profiles, while the source catalog owns their consumers."""

    source = tmp_path / "classic-cli" / "src" / "main.cpp"
    source.parent.mkdir(parents=True)
    source.write_text("int main() {}\n", encoding="utf-8")
    path = tmp_path / "tests" / "conformance" / "consumer-obligations.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_catalog()), encoding="utf-8")
    catalog = load_consumer_obligations(tmp_path, path)
    pack = {
        "familyId": "example-family",
        "domainOwner": {"rustCrate": "classic-example-core"},
        "capabilities": [{"id": "example.execute", "rustSymbols": ["execute"]}],
        "scenarios": [{"id": "base-case", "action": "example.execute"}],
        "consumerObligations": [{"id": "cli.stream-selection"}],
    }

    applicability = derive_applicability(pack, (), consumer_catalog=catalog)

    consumer = next(item for item in applicability.participants if item.id == "cli")
    assert consumer.document() == {
        "id": "cli",
        "role": "consumer",
        "executionInstanceIds": ["windows-msvc"],
        "capabilityIds": [],
        "scenarioIds": ["base-case"],
        "obligationIds": ["cli.stream-selection"],
    }


def test_consumer_preparation_withholds_expected_observations(tmp_path: Path) -> None:
    """A launcher receives only centrally selected obligation and scenario IDs."""

    _validated, _catalog_value, run = _prepare_example_consumer(tmp_path)

    plan = run.document()
    assert "scenarios" not in plan
    assert plan["obligations"] == [
        {"id": "cli.stream-selection", "scenarioIds": ["base-case"]}
    ]
    assert "expected" not in run.run_plan_path.read_text(encoding="utf-8")
    assert plan["sourcePaths"] == [
        "classic-cli/src/main.cpp",
        "tests/conformance/consumer-obligations.json",
    ]


def test_consumer_reload_rejects_rehashed_source_path_narrowing(tmp_path: Path) -> None:
    """A plan cannot replace the catalog-owned source denominator and rehash it."""

    pack, catalog, run = _prepare_example_consumer(tmp_path)
    plan = run.document()
    narrowed_paths = ["classic-cli/src/main.cpp"]
    plan["sourcePaths"] = narrowed_paths
    plan["invocation"]["sourceIdentity"] = _source_identity(
        pack, tuple(Path(path) for path in narrowed_paths)
    )
    plan_without_digest = dict(plan)
    invocation_without_digest = dict(plan["invocation"])
    invocation_without_digest.pop("runPlanDigest")
    plan_without_digest["invocation"] = invocation_without_digest
    plan["invocation"]["runPlanDigest"] = _run_plan_digest(plan_without_digest)
    run.run_plan_path.write_text(
        json.dumps(plan, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )

    with pytest.raises(MaterializationError, match="sourcePaths"):
        load_prepared_run(pack, run.run_plan_path, consumer_catalog=catalog)


def test_consumer_receipt_compares_only_named_obligation_observations(
    tmp_path: Path,
) -> None:
    """Consumer success grants its profile without producing semantic facts."""

    pack, catalog, run = _prepare_example_consumer(tmp_path)
    plan = run.document()
    receipt = {
        "schemaVersion": 1,
        "familyId": plan["familyId"],
        "familyVersion": plan["familyVersion"],
        "expectationDigest": plan["expectationDigest"],
        "invocation": plan["invocation"],
        "participant": plan["participant"],
        "runner": {
            "id": "example-consumer",
            "version": 1,
            "platform": "windows",
            "toolchain": "msvc",
        },
        "obligations": [
            {
                "id": "cli.stream-selection",
                "executionStatus": "completed",
                "observation": {"stdout": True, "stderr": False},
                "failure": None,
            }
        ],
    }
    run.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    report = validate_prepared_run(pack, run, consumer_catalog=catalog)

    assert report.failures == ()
    assert report.scenarios == ()
    assert [item.id for item in report.obligations] == ["cli.stream-selection"]
    assert report.obligations[0].result == "pass"

    coverage = derive_consumer_coverage(
        pack.document(),
        catalog,
        (report,),
        scope_participant_id="cli",
        scope_execution_instance_id="windows-msvc",
    )
    assert coverage.document()["obligations"] == [
        {
            "obligationId": "cli.stream-selection",
            "participantId": "cli",
            "evidenceIds": ["base-case"],
        }
    ]
    assert coverage.document()["result"] == "pass"

    applicability = derive_applicability(pack.document(), (), consumer_catalog=catalog)
    scoped = build_scoped_report(
        family_id="example-family",
        profile="conformance",
        applicability=applicability,
        prepared_reports=(report,),
        participant_id="cli",
        execution_instance_id="windows-msvc",
        consumer_coverage=coverage,
    )
    assert scoped.document()["result"] == "pass"
    assert scoped.document()["coverage"] is None
    assert scoped.document()["consumerCoverage"]["result"] == "pass"


def test_participant_coverage_ignores_other_registered_consumers(
    tmp_path: Path,
) -> None:
    """A CLI slice denominates CLI obligations without claiming GUI evidence."""

    for relative_path in ("classic-cli/main.cpp", "classic-gui/main.cpp"):
        source = tmp_path / relative_path
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("source\n", encoding="utf-8")
    document = {
        "schemaVersion": 1,
        "families": [
            {
                "familyId": "example-family",
                "consumers": [
                    {
                        "id": "cli",
                        "executionInstanceIds": ["windows-msvc"],
                        "sourcePaths": ["classic-cli/main.cpp"],
                        "obligations": [
                            {
                                "id": "cli.stream-selection",
                                "scenarioIds": ["base-case"],
                                "expected": {"stdout": True},
                            }
                        ],
                    },
                    {
                        "id": "gui",
                        "executionInstanceIds": ["windows-msvc"],
                        "sourcePaths": ["classic-gui/main.cpp"],
                        "obligations": [
                            {
                                "id": "gui.path-links",
                                "scenarioIds": ["base-case"],
                                "expected": {"linked": True},
                            }
                        ],
                    },
                ],
            }
        ],
    }
    path = tmp_path / "tests/conformance/consumer-obligations.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(document), encoding="utf-8")
    catalog = load_consumer_obligations(tmp_path, path)
    plan = {
        "familyId": "example-family",
        "familyVersion": 1,
        "expectationDigest": "sha256:" + "a" * 64,
        "invocation": {"sourceIdentity": "git:" + "b" * 40 + ":sha256:" + "c" * 64},
        "participant": {
            "id": "cli",
            "role": "consumer",
            "executionInstanceId": "windows-msvc",
        },
    }
    report = PreparedRunReport._from_plan(
        plan,
        obligations=(
            ObligationValidationResult("cli.stream-selection", "completed", "pass"),
        ),
    )
    pack = {
        "familyId": "example-family",
        "consumerObligations": [
            {"id": "cli.stream-selection"},
            {"id": "gui.path-links"},
        ],
    }

    coverage = derive_consumer_coverage(
        pack,
        catalog,
        (report,),
        scope_participant_id="cli",
        scope_execution_instance_id="windows-msvc",
    )

    assert coverage.document()["result"] == "pass"
    assert [item["obligationId"] for item in coverage.document()["obligations"]] == [
        "cli.stream-selection"
    ]

    pack["consumerObligations"].append({"id": "cli.unregistered"})
    unknown_coverage = derive_consumer_coverage(
        pack,
        catalog,
        (report,),
        scope_participant_id="cli",
        scope_execution_instance_id="windows-msvc",
    )
    assert unknown_coverage.document()["failures"] == [
        {
            "kind": "coverage_mapping_gap",
            "obligationId": "cli.unregistered",
            "blocking": True,
            "message": "pack consumer obligation has no source-owned coverage registration",
        }
    ]
