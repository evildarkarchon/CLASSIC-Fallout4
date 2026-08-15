"""Behavior tests for current conformance receipts and exact observations."""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from conformance import (
    CoveragePredicate,
    FamilyCoveragePolicy,
    load_and_validate_pack,
    materialize_run_plan,
    validate_prepared_run,
)


def _valid_pack() -> dict[str, Any]:
    """Return one complete pack with an independently authored observation."""

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
                "expected": {
                    "status": "completed",
                    "durableEffects": [
                        {
                            "path": "reports/result.md",
                            "byteLength": 7,
                            "sha256": "sha256:" + "a" * 64,
                        }
                    ],
                },
                "normalization": {
                    "rootRelativePaths": True,
                    "unorderedPaths": [],
                    "excludedPaths": [],
                },
            }
        ],
        "consumerObligations": [],
    }


def _prepare_run(
    tmp_path: Path,
    policy_exceptions: list[dict[str, Any]] | None = None,
    pack_document: dict[str, Any] | None = None,
) -> tuple[Any, Any]:
    """Create a committed pack and one fresh prepared adapter invocation."""

    fixture_root = tmp_path / "tests" / "fixtures" / "example-family"
    fixture_root.mkdir(parents=True)
    (fixture_root / "primary.txt").write_text("input bytes\n", encoding="utf-8")
    pack_path = tmp_path / "tests" / "conformance" / "packs" / "example.json"
    pack_path.parent.mkdir(parents=True)
    pack_path.write_text(json.dumps(pack_document or _valid_pack()), encoding="utf-8")
    runner_path = tmp_path / "runner.py"
    runner_path.write_text("RUNNER_VERSION = 1\n", encoding="utf-8")
    policy_page = tmp_path / "docs" / "api" / "binding-parity-policy.md"
    policy_page.parent.mkdir(parents=True)
    policy_page.write_text("# Binding Parity Policy\n", encoding="utf-8")
    policy_path = tmp_path / "tests" / "conformance" / "policy_exceptions.json"
    policy_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "exceptions": policy_exceptions or [],
            }
        ),
        encoding="utf-8",
    )
    for arguments in (
        ("init",),
        ("config", "user.email", "conformance-tests@example.invalid"),
        ("config", "user.name", "Conformance Tests"),
        ("add", "."),
        ("commit", "-m", "fixture"),
    ):
        subprocess.run(
            ["git", "-C", str(tmp_path), *arguments],
            check=True,
            capture_output=True,
        )
    pack = load_and_validate_pack(tmp_path, pack_path)
    run = materialize_run_plan(
        pack,
        participant_id="node",
        participant_role="semantic-adapter",
        execution_instance_id="windows-node",
        source_paths=(runner_path,),
    )
    return pack, run


def _completed_receipt(
    run: Any, observation: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build a completed receipt bound exactly to the prepared invocation."""

    plan = run.document()
    return {
        "schemaVersion": 1,
        "familyId": plan["familyId"],
        "familyVersion": plan["familyVersion"],
        "expectationDigest": plan["expectationDigest"],
        "invocation": plan["invocation"],
        "participant": plan["participant"],
        "runner": {
            "id": "classic-node-conformance",
            "version": 1,
            "platform": "windows",
            "toolchain": "node",
        },
        "scenarios": [
            {
                "id": "base-case",
                "executionStatus": "completed",
                "capabilityIds": ["example.execute"],
                "observation": observation
                if observation is not None
                else _valid_pack()["scenarios"][0]["expected"],
                "failure": None,
            }
        ],
    }


def _not_applicable_receipt(run: Any, exception_id: str) -> dict[str, Any]:
    """Build a receipt that requests one reviewed applicability exception."""

    receipt = _completed_receipt(run)
    scenario = receipt["scenarios"][0]
    scenario["executionStatus"] = "not_applicable"
    scenario["observation"] = None
    scenario["failure"] = None
    scenario["policyExceptionId"] = exception_id
    return receipt


def test_current_completed_receipt_matches_the_independent_expectation(
    tmp_path: Path,
) -> None:
    """A current completed receipt passes only with the exact scenario oracle."""

    pack, run = _prepare_run(tmp_path)
    run.receipt_path.write_text(json.dumps(_completed_receipt(run)), encoding="utf-8")

    report = validate_prepared_run(pack, run)

    assert report.document()["result"] == "pass"
    assert report.document()["failures"] == []
    assert report.document()["scenarios"] == [
        {
            "id": "base-case",
            "executionStatus": "completed",
            "result": "pass",
            "failureKinds": [],
        }
    ]


def test_duplicate_receipts_fail_as_malformed_execution_evidence(
    tmp_path: Path,
) -> None:
    """Two receipts cannot compete to satisfy one prepared invocation."""

    pack, run = _prepare_run(tmp_path)
    receipt = _completed_receipt(run)
    run.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    duplicate_path = run.artifact_dir / "duplicate-receipt.json"
    duplicate_path.write_text(json.dumps(receipt), encoding="utf-8")

    report = validate_prepared_run(
        pack, run, receipt_paths=(run.receipt_path, duplicate_path)
    )

    assert [failure["kind"] for failure in report.document()["failures"]] == [
        "malformed_execution_receipt"
    ]


@pytest.mark.parametrize(
    "identity",
    [
        "schema-version",
        "family",
        "family-version",
        "expectation-digest",
        "invocation",
        "run-plan-digest",
        "source-identity",
    ],
)
def test_receipt_identity_must_match_the_current_prepared_invocation(
    tmp_path: Path, identity: str
) -> None:
    """Earlier schema, pack, plan, invocation, or source evidence is stale."""

    pack, run = _prepare_run(tmp_path)
    receipt = _completed_receipt(run)
    if identity == "schema-version":
        receipt["schemaVersion"] = 2
    elif identity == "family":
        receipt["familyId"] = "other-family"
    elif identity == "family-version":
        receipt["familyVersion"] = 2
    elif identity == "expectation-digest":
        receipt["expectationDigest"] = "sha256:" + "b" * 64
    elif identity == "invocation":
        receipt["invocation"]["id"] = "00000000-0000-4000-8000-000000000000"
    elif identity == "run-plan-digest":
        receipt["invocation"]["runPlanDigest"] = "sha256:" + "b" * 64
    else:
        receipt["invocation"]["sourceIdentity"] = (
            "git:" + "b" * 40 + ":sha256:" + "b" * 64
        )
    run.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    report = validate_prepared_run(pack, run)

    assert [failure["kind"] for failure in report.document()["failures"]] == [
        "stale_execution_receipt"
    ]


@pytest.mark.parametrize("current_input", ["pack", "fixture", "run-plan"])
def test_validation_rejects_receipts_after_prepared_inputs_change(
    tmp_path: Path, current_input: str
) -> None:
    """A valid old receipt cannot satisfy changed tracked or prepared inputs."""

    pack, run = _prepare_run(tmp_path)
    run.receipt_path.write_text(json.dumps(_completed_receipt(run)), encoding="utf-8")
    if current_input == "pack":
        document = pack.document()
        document["scenarios"][0]["expected"]["status"] = "changed"
        pack.pack_path.write_text(json.dumps(document), encoding="utf-8")
    elif current_input == "fixture":
        pack.fixtures[0].resolved_path.write_text("changed bytes\n", encoding="utf-8")
    else:
        run.run_plan_path.write_text("{}", encoding="utf-8")

    report = validate_prepared_run(pack, run)

    assert [failure["kind"] for failure in report.document()["failures"]] == [
        "stale_execution_receipt"
    ]


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate-json-key",
        "duplicate-scenario",
        "unexpected-scenario",
        "unexpected-participant",
        "unexpected-role",
        "unexpected-instance",
        "unexpected-capability",
        "unexpected-envelope-field",
        "invalid-runner-id",
        "floating-observation",
        "nonstring-execution-status",
        "nonstring-participant-role",
    ],
)
def test_ambiguous_or_unexpected_receipt_evidence_is_malformed(
    tmp_path: Path, mutation: str
) -> None:
    """Receipt-controlled identities cannot broaden one prepared run's scope."""

    pack, run = _prepare_run(tmp_path)
    receipt = _completed_receipt(run)
    if mutation == "duplicate-scenario":
        receipt["scenarios"].append(copy.deepcopy(receipt["scenarios"][0]))
    elif mutation == "unexpected-scenario":
        receipt["scenarios"].append(
            {
                **copy.deepcopy(receipt["scenarios"][0]),
                "id": "unexpected-case",
            }
        )
    elif mutation == "unexpected-participant":
        receipt["participant"]["id"] = "python"
    elif mutation == "unexpected-role":
        receipt["participant"]["role"] = "consumer"
    elif mutation == "unexpected-instance":
        receipt["participant"]["executionInstanceId"] = "linux-node"
    elif mutation == "unexpected-capability":
        receipt["scenarios"][0]["capabilityIds"] = ["example.other"]
    elif mutation == "unexpected-envelope-field":
        receipt["passed"] = True
    elif mutation == "invalid-runner-id":
        receipt["runner"]["id"] = "Classic Node Conformance"
    elif mutation == "floating-observation":
        receipt["scenarios"][0]["observation"]["durableEffects"][0]["byteLength"] = 7.0
    elif mutation == "nonstring-execution-status":
        receipt["scenarios"][0]["executionStatus"] = []
    elif mutation == "nonstring-participant-role":
        receipt["participant"]["role"] = []

    receipt_text = json.dumps(receipt)
    if mutation == "duplicate-json-key":
        receipt_text = '{"schemaVersion":1,' + receipt_text[1:]
    run.receipt_path.write_text(receipt_text, encoding="utf-8")

    report = validate_prepared_run(pack, run)

    assert [failure["kind"] for failure in report.document()["failures"]] == [
        "malformed_execution_receipt"
    ]


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("familyVersion", "1"),
        ("expectationDigest", []),
    ],
)
def test_invalid_receipt_identity_types_are_malformed_not_stale(
    tmp_path: Path, field: str, invalid_value: object
) -> None:
    """Invalid identity types cannot masquerade as an older valid launch."""

    pack, run = _prepare_run(tmp_path)
    receipt = _completed_receipt(run)
    receipt[field] = invalid_value
    run.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    report = validate_prepared_run(pack, run)

    assert [failure["kind"] for failure in report.document()["failures"]] == [
        "malformed_execution_receipt"
    ]


def test_missing_planned_scenario_fails_as_missing_execution_evidence(
    tmp_path: Path,
) -> None:
    """A well-formed envelope cannot omit every required scenario result."""

    pack, run = _prepare_run(tmp_path)
    receipt = _completed_receipt(run)
    receipt["scenarios"] = []
    run.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    report = validate_prepared_run(pack, run)

    assert [failure["kind"] for failure in report.document()["failures"]] == [
        "missing_execution_receipt"
    ]
    assert report.document()["failures"][0]["scenarioId"] == "base-case"


@pytest.mark.parametrize("execution_status", ["skipped", "unsupported"])
def test_skipped_or_unsupported_execution_is_an_applicability_violation(
    tmp_path: Path, execution_status: str
) -> None:
    """A required adapter cannot weaken applicability in its own receipt."""

    pack, run = _prepare_run(tmp_path)
    receipt = _completed_receipt(run)
    receipt["scenarios"][0]["executionStatus"] = execution_status
    run.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    report = validate_prepared_run(pack, run)

    assert [failure["kind"] for failure in report.document()["failures"]] == [
        "applicability_violation"
    ]


def test_adapter_execution_failure_remains_distinct_from_semantic_mismatch(
    tmp_path: Path,
) -> None:
    """A runner failure is execution evidence, not a domain observation result."""

    pack, run = _prepare_run(tmp_path)
    receipt = _completed_receipt(run)
    scenario = receipt["scenarios"][0]
    scenario["executionStatus"] = "failed"
    scenario["observation"] = {}
    scenario["failure"] = {
        "kind": "runner-failed",
        "message": "adapter process exited before completing the scenario",
    }
    run.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    report = validate_prepared_run(pack, run)

    assert [failure["kind"] for failure in report.document()["failures"]] == [
        "adapter_command_failure"
    ]


def test_not_applicable_without_a_matching_reviewed_exception_fails(
    tmp_path: Path,
) -> None:
    """Free-form adapter inapplicability cannot weaken a required scenario."""

    pack, run = _prepare_run(tmp_path)
    run.receipt_path.write_text(
        json.dumps(_not_applicable_receipt(run, "missing-exception")),
        encoding="utf-8",
    )

    report = validate_prepared_run(pack, run)

    assert [failure["kind"] for failure in report.document()["failures"]] == [
        "applicability_violation"
    ]


def test_matching_reviewed_exception_accepts_not_applicable_execution(
    tmp_path: Path,
) -> None:
    """A narrow repository-owned exception may satisfy one exact obligation."""

    exception = {
        "id": "node-example-exception",
        "capabilityId": "example.execute",
        "participantId": "node",
        "rationale": "The example capability is intentionally absent on Node.",
        "policyPage": "docs/api/binding-parity-policy.md",
    }
    pack, run = _prepare_run(tmp_path, [exception])
    run.receipt_path.write_text(
        json.dumps(_not_applicable_receipt(run, exception["id"])),
        encoding="utf-8",
    )

    report = validate_prepared_run(pack, run)

    assert report.document()["result"] == "pass"
    assert report.document()["scenarios"] == [
        {
            "id": "base-case",
            "executionStatus": "not_applicable",
            "result": "pass",
            "failureKinds": [],
        }
    ]


@pytest.mark.parametrize(
    "mismatch",
    [
        "participant",
        "capability",
        "rationale",
        "policy-page",
        "duplicate-id",
    ],
)
def test_not_applicable_rejects_nonmatching_or_unreviewable_exceptions(
    tmp_path: Path, mismatch: str
) -> None:
    """Exception identity alone cannot authorize a broader applicability gap."""

    exception = {
        "id": "node-example-exception",
        "capabilityId": "example.execute",
        "participantId": "node",
        "rationale": "The example capability is intentionally absent on Node.",
        "policyPage": "docs/api/binding-parity-policy.md",
    }
    if mismatch == "participant":
        exception["participantId"] = "python"
    elif mismatch == "capability":
        exception["capabilityId"] = "example.other"
    elif mismatch == "rationale":
        exception["rationale"] = ""
    elif mismatch == "policy-page":
        exception["policyPage"] = "docs/api/missing-policy.md"
    exceptions = [exception]
    if mismatch == "duplicate-id":
        exceptions.append(copy.deepcopy(exception))
    pack, run = _prepare_run(tmp_path, exceptions)
    run.receipt_path.write_text(
        json.dumps(_not_applicable_receipt(run, exception["id"])),
        encoding="utf-8",
    )

    report = validate_prepared_run(pack, run)

    assert [failure["kind"] for failure in report.document()["failures"]] == [
        "applicability_violation"
    ]


def test_comparison_applies_only_declared_exclusions_and_unordered_paths(
    tmp_path: Path,
) -> None:
    """Exact path declarations permit only their named normalization work."""

    pack_document = _valid_pack()
    expected = pack_document["scenarios"][0]["expected"]
    expected["unorderedFacts"] = [{"id": "alpha"}, {"id": "beta"}]
    expected["volatileDiagnostic"] = "oracle value"
    pack_document["scenarios"][0]["normalization"] = {
        "rootRelativePaths": True,
        "unorderedPaths": ["$.unorderedFacts"],
        "excludedPaths": [
            {
                "path": "$.volatileDiagnostic",
                "rationale": "The adapter diagnostic text is intentionally non-contractual.",
            }
        ],
    }
    pack, run = _prepare_run(tmp_path, pack_document=pack_document)
    actual = copy.deepcopy(expected)
    actual["unorderedFacts"].reverse()
    actual["volatileDiagnostic"] = "adapter-specific value"
    run.receipt_path.write_text(
        json.dumps(_completed_receipt(run, actual)), encoding="utf-8"
    )

    report = validate_prepared_run(pack, run)

    assert report.document()["result"] == "pass"


@pytest.mark.parametrize("path_form", ["absolute", "windows-relative"])
def test_declared_fixture_paths_are_normalized_relative_to_the_fixture_root(
    tmp_path: Path, path_form: str
) -> None:
    """Declared path normalization removes only the prepared fixture root."""

    pack, run = _prepare_run(tmp_path)
    expected = pack.document()["scenarios"][0]["expected"]
    actual = copy.deepcopy(expected)
    relative_path = expected["durableEffects"][0]["path"]
    if path_form == "absolute":
        actual["durableEffects"][0]["path"] = str(pack.fixture_root / relative_path)
    else:
        actual["durableEffects"][0]["path"] = relative_path.replace("/", "\\")
    run.receipt_path.write_text(
        json.dumps(_completed_receipt(run, actual)), encoding="utf-8"
    )

    report = validate_prepared_run(pack, run)

    assert report.document()["result"] == "pass"


def test_fixture_path_normalization_is_not_applied_when_undeclared(
    tmp_path: Path,
) -> None:
    """Separator changes remain semantic when root-relative projection is disabled."""

    pack_document = _valid_pack()
    pack_document["scenarios"][0]["normalization"]["rootRelativePaths"] = False
    pack, run = _prepare_run(tmp_path, pack_document=pack_document)
    actual = copy.deepcopy(pack_document["scenarios"][0]["expected"])
    actual["durableEffects"][0]["path"] = "reports\\output.md"
    run.receipt_path.write_text(
        json.dumps(_completed_receipt(run, actual)), encoding="utf-8"
    )

    report = validate_prepared_run(pack, run)

    assert {failure["kind"] for failure in report.document()["failures"]} == {
        "semantic_conformance_mismatch"
    }


@pytest.mark.parametrize(
    ("expected_value", "actual_value"),
    [
        ("https://example.test/a//b", "https://example.test/a/b"),
        ("domain/value", "domain\\value"),
    ],
)
def test_root_relative_normalization_does_not_rewrite_non_path_strings(
    tmp_path: Path, expected_value: str, actual_value: str
) -> None:
    """The path flag cannot make distinct slash-bearing domain values equal."""

    pack_document = _valid_pack()
    pack_document["scenarios"][0]["expected"]["domainValue"] = expected_value
    pack, run = _prepare_run(tmp_path, pack_document=pack_document)
    actual = copy.deepcopy(pack_document["scenarios"][0]["expected"])
    actual["domainValue"] = actual_value
    run.receipt_path.write_text(
        json.dumps(_completed_receipt(run, actual)), encoding="utf-8"
    )

    report = validate_prepared_run(pack, run)

    assert {failure["kind"] for failure in report.document()["failures"]} == {
        "semantic_conformance_mismatch"
    }


def test_declared_absolute_path_outside_fixture_root_fails_normalization(
    tmp_path: Path,
) -> None:
    """Root projection cannot legitimize a machine path outside the fixture root."""

    pack, run = _prepare_run(tmp_path)
    actual = copy.deepcopy(pack.document()["scenarios"][0]["expected"])
    actual["durableEffects"][0]["path"] = str(tmp_path / "outside.md")
    run.receipt_path.write_text(
        json.dumps(_completed_receipt(run, actual)), encoding="utf-8"
    )

    report = validate_prepared_run(pack, run)

    assert [failure["kind"] for failure in report.document()["failures"]] == [
        "normalization_failure"
    ]


@pytest.mark.parametrize(
    "mutation",
    [
        "extra-field",
        "missing-field",
        "type-change",
        "undeclared-reordering",
        "changed-durable-path",
        "changed-durable-length",
        "changed-durable-digest",
        "extra-durable-effect",
    ],
)
def test_exact_comparison_rejects_every_undeclared_semantic_change(
    tmp_path: Path, mutation: str
) -> None:
    """Missing, extra, reordered, retyped, and changed durable facts all fail."""

    pack_document = _valid_pack()
    expected = pack_document["scenarios"][0]["expected"]
    expected["orderedFacts"] = [{"id": "alpha"}, {"id": "beta"}]
    pack, run = _prepare_run(tmp_path, pack_document=pack_document)
    actual = copy.deepcopy(expected)
    if mutation == "extra-field":
        actual["adapterOnly"] = True
    elif mutation == "missing-field":
        del actual["status"]
    elif mutation == "type-change":
        actual["durableEffects"][0]["byteLength"] = True
    elif mutation == "undeclared-reordering":
        actual["orderedFacts"].reverse()
    elif mutation == "changed-durable-path":
        actual["durableEffects"][0]["path"] = "reports/other.md"
    elif mutation == "changed-durable-length":
        actual["durableEffects"][0]["byteLength"] = 8
    elif mutation == "changed-durable-digest":
        actual["durableEffects"][0]["sha256"] = "sha256:" + "b" * 64
    else:
        actual["durableEffects"].append(
            {
                "path": "reports/extra.md",
                "byteLength": 1,
                "sha256": "sha256:" + "b" * 64,
            }
        )
    run.receipt_path.write_text(
        json.dumps(_completed_receipt(run, actual)), encoding="utf-8"
    )

    report = validate_prepared_run(pack, run)

    failures = report.document()["failures"]
    assert failures
    assert {failure["kind"] for failure in failures} == {
        "semantic_conformance_mismatch"
    }


@pytest.mark.parametrize("declaration", ["unordered-non-array", "invalid-traversal"])
def test_unperformable_declared_normalization_has_its_own_failure_kind(
    tmp_path: Path, declaration: str
) -> None:
    """The engine never invents a projection when an exact path cannot apply."""

    pack_document = _valid_pack()
    expected = pack_document["scenarios"][0]["expected"]
    actual = copy.deepcopy(expected)
    if declaration == "unordered-non-array":
        expected["facts"] = [{"id": "alpha"}]
        actual["facts"] = {"id": "alpha"}
        pack_document["scenarios"][0]["normalization"]["unorderedPaths"] = ["$.facts"]
    else:
        expected["diagnostic"] = {"message": "expected"}
        actual["diagnostic"] = "adapter text"
        pack_document["scenarios"][0]["normalization"]["excludedPaths"] = [
            {
                "path": "$.diagnostic.message",
                "rationale": "The diagnostic prose is intentionally excluded.",
            }
        ]
    pack, run = _prepare_run(tmp_path, pack_document=pack_document)
    run.receipt_path.write_text(
        json.dumps(_completed_receipt(run, actual)), encoding="utf-8"
    )

    report = validate_prepared_run(pack, run)

    assert [failure["kind"] for failure in report.document()["failures"]] == [
        "normalization_failure"
    ]


@pytest.mark.parametrize(
    "carrier_mutation",
    [
        "missing-field",
        "extra-field",
        "boolean-count",
        "invalid-kind",
        "nonstring-kind",
        "populated-unused-field",
        "invalid-severity",
        "nonstring-severity",
        "absolute-path",
    ],
)
def test_malformed_display_content_carrier_is_a_normalization_failure(
    tmp_path: Path, carrier_mutation: str
) -> None:
    """A flattened display segment must preserve every frozen payload field."""

    pack_document = _valid_pack()
    pack_document["capabilities"][0]["observationFamilies"].append("display-content")
    expected = pack_document["scenarios"][0]["expected"]
    expected["displayContent"] = [
        {
            "severity": "info",
            "segments": [
                {
                    "kind": "text",
                    "text": "completed",
                    "path": "",
                    "count": 0,
                }
            ],
        }
    ]
    pack, run = _prepare_run(tmp_path, pack_document=pack_document)
    actual = copy.deepcopy(expected)
    line = actual["displayContent"][0]
    segment = line["segments"][0]
    if carrier_mutation == "missing-field":
        del segment["path"]
    elif carrier_mutation == "extra-field":
        segment["adapterOnly"] = "value"
    elif carrier_mutation == "boolean-count":
        segment["count"] = False
    elif carrier_mutation == "invalid-kind":
        segment["kind"] = "html"
    elif carrier_mutation == "nonstring-kind":
        segment["kind"] = []
    elif carrier_mutation == "populated-unused-field":
        segment["path"] = "logs/crash.log"
    elif carrier_mutation == "invalid-severity":
        line["severity"] = "debug"
    elif carrier_mutation == "nonstring-severity":
        line["severity"] = {}
    else:
        segment.update(
            {
                "kind": "path",
                "text": "",
                "path": "C:/logs/crash.log",
                "count": 0,
            }
        )
    run.receipt_path.write_text(
        json.dumps(_completed_receipt(run, actual)), encoding="utf-8"
    )

    report = validate_prepared_run(pack, run)

    assert [failure["kind"] for failure in report.document()["failures"]] == [
        "normalization_failure"
    ]


@pytest.mark.parametrize(
    "line_mutation", ["missing-severity", "missing-segments", "extra-field"]
)
def test_matching_malformed_display_lines_cannot_evade_carrier_validation(
    tmp_path: Path, line_mutation: str
) -> None:
    """Exact equality does not legitimize a malformed schema-owned display line."""

    pack_document = _valid_pack()
    pack_document["capabilities"][0]["observationFamilies"].append("display-content")
    line = {
        "severity": "info",
        "segments": [
            {
                "kind": "text",
                "text": "completed",
                "path": "",
                "count": 0,
            }
        ],
    }
    if line_mutation == "missing-severity":
        del line["severity"]
    elif line_mutation == "missing-segments":
        del line["segments"]
    else:
        line["frontendStyle"] = "accent"
    pack_document["scenarios"][0]["expected"]["displayContent"] = [line]
    pack, run = _prepare_run(tmp_path, pack_document=pack_document)
    run.receipt_path.write_text(
        json.dumps(
            _completed_receipt(run, pack.document()["scenarios"][0]["expected"])
        ),
        encoding="utf-8",
    )

    report = validate_prepared_run(pack, run)

    assert [failure["kind"] for failure in report.document()["failures"]] == [
        "normalization_failure"
    ]


@pytest.mark.parametrize("line", ["not-a-line", None])
def test_non_object_display_entries_cannot_evade_carrier_validation(
    tmp_path: Path, line: object
) -> None:
    """Every explicit Display Content entry must use the frozen line object."""

    pack_document = _valid_pack()
    pack_document["capabilities"][0]["observationFamilies"].append("display-content")
    pack_document["scenarios"][0]["expected"]["displayContent"] = [line]
    pack, run = _prepare_run(tmp_path, pack_document=pack_document)
    run.receipt_path.write_text(
        json.dumps(
            _completed_receipt(run, pack.document()["scenarios"][0]["expected"])
        ),
        encoding="utf-8",
    )

    report = validate_prepared_run(pack, run)

    assert [failure["kind"] for failure in report.document()["failures"]] == [
        "normalization_failure"
    ]


def test_display_validation_does_not_reinterpret_unrelated_severity_records(
    tmp_path: Path,
) -> None:
    """A domain diagnostic may use severity without becoming a display carrier."""

    pack_document = _valid_pack()
    pack_document["capabilities"][0]["observationFamilies"].append("display-content")
    expected = pack_document["scenarios"][0]["expected"]
    expected["diagnostic"] = {"severity": "warning", "message": "stable-token"}
    expected["displayContent"] = [
        {
            "severity": "info",
            "segments": [
                {
                    "kind": "text",
                    "text": "completed",
                    "path": "",
                    "count": 0,
                }
            ],
        }
    ]
    pack, run = _prepare_run(tmp_path, pack_document=pack_document)
    run.receipt_path.write_text(
        json.dumps(_completed_receipt(run, copy.deepcopy(expected))),
        encoding="utf-8",
    )

    report = validate_prepared_run(pack, run)

    assert report.document()["result"] == "pass"


def test_report_output_is_deterministic_in_tracked_scenario_order(
    tmp_path: Path,
) -> None:
    """Receipt ordering cannot make machine-readable report bytes unstable."""

    pack_document = _valid_pack()
    second_scenario = copy.deepcopy(pack_document["scenarios"][0])
    second_scenario["id"] = "second-case"
    second_scenario["expected"]["status"] = "second"
    pack_document["scenarios"].append(second_scenario)
    pack, run = _prepare_run(tmp_path, pack_document=pack_document)
    receipt = _completed_receipt(
        run, copy.deepcopy(pack_document["scenarios"][0]["expected"])
    )
    second_receipt = copy.deepcopy(receipt["scenarios"][0])
    second_receipt["id"] = "second-case"
    second_receipt["observation"] = copy.deepcopy(second_scenario["expected"])
    receipt["scenarios"] = [second_receipt, receipt["scenarios"][0]]
    run.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    first_report = validate_prepared_run(pack, run)
    second_report = validate_prepared_run(pack, run)

    assert [scenario["id"] for scenario in first_report.document()["scenarios"]] == [
        "base-case",
        "second-case",
    ]
    assert first_report.json_text() == second_report.json_text()


def test_matching_receipt_derives_facts_from_family_owned_predicates(
    tmp_path: Path,
) -> None:
    """Coverage facts come from the trusted action and normalized observation."""

    pack, run = _prepare_run(tmp_path)
    receipt = _completed_receipt(run)
    run.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    policy = FamilyCoveragePolicy(
        family_id="example-family",
        predicates=(
            CoveragePredicate(
                id="example.completed",
                capability_id="example.execute",
                action="example.execute",
                observation_family="result",
                rust_symbols=("Request", "execute"),
                matches=lambda observation: observation.get("status") == "completed",
            ),
        ),
    )

    report = validate_prepared_run(pack, run, coverage_policy=policy)

    assert report.document()["scenarios"] == [
        {
            "id": "base-case",
            "executionStatus": "completed",
            "result": "pass",
            "failureKinds": [],
            "observedFactIds": ["example.completed"],
        }
    ]


def test_valid_runner_metadata_cannot_change_derived_facts(tmp_path: Path) -> None:
    """Runner identity remains diagnostic and outside family predicate inputs."""

    pack, run = _prepare_run(tmp_path)
    policy = FamilyCoveragePolicy(
        family_id="example-family",
        predicates=(
            CoveragePredicate(
                id="example.completed",
                capability_id="example.execute",
                action="example.execute",
                observation_family="result",
                rust_symbols=("execute",),
                matches=lambda observation: observation.get("status") == "completed",
            ),
        ),
    )
    receipt = _completed_receipt(run)
    receipt["runner"] = {
        "id": "renamed-runner",
        "version": 99,
        "platform": "diagnostic-platform",
        "toolchain": "diagnostic-toolchain",
    }
    run.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    report = validate_prepared_run(pack, run, coverage_policy=policy)

    assert report.document()["scenarios"][0]["observedFactIds"] == ["example.completed"]


@pytest.mark.parametrize(
    ("container", "field"),
    [
        ("runner", "coverage"),
        ("runner", "testName"),
        ("runner", "selectorHash"),
        ("scenario", "factIds"),
        ("scenario", "migrationLedgerState"),
    ],
)
def test_runner_authored_coverage_claim_fields_are_malformed(
    tmp_path: Path, container: str, field: str
) -> None:
    """Receipts cannot smuggle acknowledgements into central coverage reports."""

    pack, run = _prepare_run(tmp_path)
    receipt = _completed_receipt(run)
    target = receipt["runner"] if container == "runner" else receipt["scenarios"][0]
    target[field] = "runner-authored-claim"
    run.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    report = validate_prepared_run(pack, run)

    assert [failure["kind"] for failure in report.document()["failures"]] == [
        "malformed_execution_receipt"
    ]
