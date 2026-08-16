"""Tests for the diagnostic evidence migration ledger."""

from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path

import pytest
from migration_ledger import (
    LedgerValidationError,
    check_ledger_artifacts,
    discover_current_obligations,
    generate_ledger,
    render_ledger_markdown,
    validate_ledger_entries,
    write_ledger_artifacts,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _runtime_obligation(obligation_id: str) -> dict[str, object]:
    """Return one complete runtime-verifiable obligation for validator tests."""

    return {
        "id": obligation_id,
        "sourceKind": "parity_row",
        "source": {
            "artifact": "contract.json",
            "locator": obligation_id,
        },
        "participant": "node",
        "mappingOrigin": "canonical_rust",
        "classification": "runtime_verifiable",
        "target": {
            "familyId": "owner-module:scanlog",
            "scenarioId": "owner-module-runtime",
            "observationOrAssertion": obligation_id,
            "evidenceRole": "semantic_adapter",
        },
        "retainedAnalyzerIds": ["node-source-parity"],
        "migrationState": "shadow",
        "stateEvidence": ["The current Node parity gate remains blocking."],
    }


def _ledger(*obligations: dict[str, object]) -> dict[str, object]:
    """Wrap obligations in the tracked diagnostic ledger envelope."""

    return {
        "schemaVersion": 1,
        "diagnosticOnly": True,
        "analyzers": [
            {
                "id": "node-source-parity",
                "evidenceKind": "structural",
                "paths": ["tools/node_api_parity/check_parity_gate.py"],
                "blockingRequirementId": "node-parity-gate",
            }
        ],
        "policyExceptions": [],
        "obligations": [copy.deepcopy(obligation) for obligation in obligations],
    }


def test_new_obligation_is_rejected_until_the_ledger_classifies_it() -> None:
    """A newly discovered parity obligation cannot inherit compliance implicitly."""

    tracked = _runtime_obligation("parity:node:existing")
    discovered = (
        tracked,
        _runtime_obligation("parity:node:new-public-row"),
    )

    with pytest.raises(LedgerValidationError, match="missing obligations"):
        validate_ledger_entries(_ledger(tracked), discovered)


def test_unclassified_obligation_is_rejected() -> None:
    """The ledger cannot preserve a manual acknowledgement success bucket."""

    obligation = _runtime_obligation("parity:node:unclassified")
    ledger = _ledger(obligation)
    ledger["obligations"][0]["classification"] = "manual_acknowledgement"

    with pytest.raises(LedgerValidationError, match="unsupported classification"):
        validate_ledger_entries(ledger, (obligation,))


def test_discovery_freezes_every_current_evidence_source() -> None:
    """Discovery assigns one obligation to every Phase 0 evidence occurrence."""

    obligations = discover_current_obligations(REPO_ROOT)

    assert Counter(entry["sourceKind"] for entry in obligations) == {
        "parity_row": 2_776,
        "runtime_registry_claim": 67,
        "scan_run_contract_variant": 73,
        "scan_run_supported_adapter": 4,
        "scan_run_variant_acknowledgement": 292,
        "scan_run_source_marker": 124,
        "scan_run_required_participant": 28,
        "consumer_required_participant": 3,
        "consumer_audit": 6,
        "source_audit": 189,
        "rust_enum_inventory_audit": 15,
        "display_content_source_audit": 11,
        "display_content_consumer_audit": 3,
        "shared_runtime_source_audit": 1,
        "user_settings_source_audit": 4,
        "consumer_source_audit": 58,
        "policy_exception": 1,
    }
    assert len({entry["id"] for entry in obligations}) == len(obligations)
    consumer_cases = [
        entry for entry in obligations if entry["sourceKind"] == "consumer_source_audit"
    ]
    assert len(
        {
            (entry["source"]["artifact"], entry["source"]["locator"])
            for entry in consumer_cases
        }
    ) == len(consumer_cases)
    mixed_case = next(
        entry
        for entry in consumer_cases
        if "game_files_worker_forwards_game_version_to_setup_intake"
        in entry["source"]["locator"]
    )
    assert mixed_case["classification"] == "runtime_verifiable"
    assert mixed_case["retainedAnalyzerIds"]


def test_binding_only_rows_and_cxx_policy_exception_remain_explicit() -> None:
    """Discovery does not invent canonical mappings for known exceptional rows."""

    obligations = discover_current_obligations(REPO_ROOT)
    binding_only = [
        entry for entry in obligations if entry["mappingOrigin"] == "binding_only"
    ]
    cxx_rows = [
        entry
        for entry in obligations
        if entry["sourceKind"] == "parity_row" and entry["participant"] == "cxx"
    ]
    contract = json.loads(
        (
            REPO_ROOT
            / "docs/implementation/cxx_api_parity/baseline/parity_contract.json"
        ).read_text(encoding="utf-8")
    )
    contract_rows = {row["id"]: row for row in contract["entries"]}
    obligations_by_row_id = {
        entry["id"].removeprefix("parity:cxx:"): entry for entry in cxx_rows
    }
    resource_exception = next(
        entry
        for entry in obligations
        if entry["id"]
        == "policy-exception:cxx:cxx-classic-resource-core-transitive-access"
    )

    assert Counter(
        entry["participant"] for entry in binding_only if entry["participant"] != "cxx"
    ) == {
        "node": 7,
        "python": 1,
    }
    assert set(obligations_by_row_id) == set(contract_rows)
    for row_id, row in contract_rows.items():
        obligation = obligations_by_row_id[row_id]
        if "unmappedReason" not in row:
            assert obligation["mappingOrigin"] == "canonical_rust"
            assert obligation["classification"] == "runtime_verifiable"
            assert obligation["target"]["familyId"] == row["ownerModule"]
            continue

        assert obligation["mappingOrigin"] == "binding_only"
        declaration_only = row["kind"] != "function" or row["blockOrigin"] == "C++"
        expected_classification = (
            "structural_analyzer" if declaration_only else "runtime_verifiable"
        )
        assert obligation["classification"] == expected_classification
        if not declaration_only:
            assert obligation["target"]["familyId"] == (
                f"cxx-binding:{row['bridgeModule']}"
            )
    assert resource_exception["classification"] == "policy_exception"


def test_unreachable_reset_faults_remain_blocking_structural_obligations() -> None:
    """Private replacement faults cannot be mislabeled as public semantic receipts."""

    obligations = discover_current_obligations(REPO_ROOT)
    reset_faults = [
        entry
        for entry in obligations
        if entry["mappingOrigin"] == "retained_internal_fault_projection"
    ]

    assert {
        entry["participant"] for entry in reset_faults
    } == {"rust", "cxx", "node", "python"}
    assert all(entry["classification"] == "structural_analyzer" for entry in reset_faults)
    assert all(entry["migrationState"] == "blocking" for entry in reset_faults)
    assert all(
        entry["target"]["analyzerId"]
        == "scan-run-local-ignore-reset-internal-faults"
        for entry in reset_faults
    )
    variant_faults = [
        entry
        for entry in reset_faults
        if entry["sourceKind"] == "scan_run_variant_acknowledgement"
    ]
    marker_faults = [
        entry
        for entry in reset_faults
        if entry["sourceKind"] == "scan_run_source_marker"
    ]
    assert len(variant_faults) == 8
    assert len(marker_faults) == 17

    public_reset_variants = {
        entry["id"]: entry
        for entry in obligations
        if entry["sourceKind"] == "scan_run_variant_acknowledgement"
        and (
            entry["id"].endswith("local_ignore_reset_conflict")
            or entry["id"].endswith("local_ignore_reset_backup_failure")
        )
    }
    assert len(public_reset_variants) == 8
    assert all(
        entry["classification"] == "runtime_verifiable"
        for entry in public_reset_variants.values()
    )


def test_unreachable_structured_failures_remain_blocking_structural_obligations() -> None:
    """Injected and constructed failures cannot masquerade as public receipts."""

    obligations = discover_current_obligations(REPO_ROOT)
    retained_failures = [
        entry
        for entry in obligations
        if entry["mappingOrigin"] == "retained_internal_failure_projection"
    ]

    assert {
        entry["participant"] for entry in retained_failures
    } == {"rust", "cxx", "node", "python"}
    assert all(
        entry["classification"] == "structural_analyzer"
        for entry in retained_failures
    )
    assert all(entry["migrationState"] == "blocking" for entry in retained_failures)
    assert all(
        entry["target"]["analyzerId"]
        == "scan-run-structured-failure-internal-faults"
        for entry in retained_failures
    )
    assert all(
        entry["target"]["evidenceRole"] == "structural_analyzer"
        and entry["target"]["familyId"] is None
        and entry["target"]["scenarioId"] is None
        for entry in retained_failures
    )
    assert sum(
        entry["sourceKind"] == "scan_run_variant_acknowledgement"
        for entry in retained_failures
    ) == 16
    assert sum(
        entry["sourceKind"] == "scan_run_source_marker"
        for entry in retained_failures
    ) == 23

    public_variants = {
        entry["id"]: entry
        for entry in obligations
        if entry["sourceKind"] == "scan_run_variant_acknowledgement"
        and entry["id"].endswith(
            (
                "infrastructure_error_stage.request_validation",
                "infrastructure_error_stage.discovery",
                "infrastructure_error_stage.intake",
                "log_failure_stage.report_write",
                "log_failure_stage.unsolved_logs_finalization",
            )
        )
    }
    assert len(public_variants) == 20
    assert all(
        entry["classification"] == "runtime_verifiable"
        for entry in public_variants.values()
    )


def test_cxx_internal_failure_marker_cannot_be_relabelled_as_public_execution() -> None:
    """A tracked-ledger mutation cannot convert CXX structural proof to a receipt."""

    discovered = discover_current_obligations(REPO_ROOT)
    ledger = generate_ledger(REPO_ROOT)
    marker = next(
        entry
        for entry in ledger["obligations"]
        if entry["participant"] == "cxx"
        and entry["mappingOrigin"] == "retained_internal_failure_projection"
        and entry["sourceKind"] == "scan_run_source_marker"
        and "maps_every_core_enum_variant_to_a_typed_cxx_variant"
        in entry["source"]["locator"]
    )
    marker["classification"] = "runtime_verifiable"
    marker["migrationState"] = "shadow"
    marker["target"] = {
        "familyId": "crash-log-scan-run",
        "scenarioId": "fabricated-cxx-internal-failure",
        "observationOrAssertion": marker["source"]["locator"],
        "evidenceRole": "semantic_adapter",
    }

    with pytest.raises(LedgerValidationError, match="stale obligation entries"):
        validate_ledger_entries(ledger, discovered)


def test_preserved_id_with_stale_source_metadata_is_rejected() -> None:
    """An unchanged ID cannot hide that the underlying source locator drifted."""

    obligation = _runtime_obligation("parity:node:stable-id")
    stale = copy.deepcopy(obligation)
    stale["source"]["locator"] = "different-row"

    with pytest.raises(LedgerValidationError, match="stale obligation entries"):
        validate_ledger_entries(_ledger(stale), (obligation,))


def test_ledger_must_be_explicitly_diagnostic_only() -> None:
    """A ledger without the non-evidentiary marker cannot pass validation."""

    obligation = _runtime_obligation("parity:node:diagnostic-only")
    ledger = _ledger(obligation)
    ledger["diagnosticOnly"] = False

    with pytest.raises(LedgerValidationError, match="diagnosticOnly must be true"):
        validate_ledger_entries(ledger, (obligation,))


def test_structural_obligation_requires_a_named_analyzer() -> None:
    """A structural label cannot stand in for a catalogued analyzer."""

    obligation = _runtime_obligation("parity:node:erased-interface")
    obligation["classification"] = "structural_analyzer"
    obligation["target"] = {
        "familyId": None,
        "scenarioId": None,
        "observationOrAssertion": "erased-interface",
        "evidenceRole": "structural_analyzer",
        "analyzerId": "missing-analyzer",
    }
    obligation["retainedAnalyzerIds"] = ["missing-analyzer"]
    obligation["migrationState"] = "blocking"

    with pytest.raises(LedgerValidationError, match="unknown analyzer"):
        validate_ledger_entries(_ledger(obligation), (obligation,))


def test_duplicate_discovered_occurrence_is_rejected() -> None:
    """Set equality cannot collapse two live obligations with the same ID."""

    obligation = _runtime_obligation("parity:node:duplicate")

    with pytest.raises(LedgerValidationError, match="discovered duplicate obligations"):
        validate_ledger_entries(_ledger(obligation), (obligation, obligation))


def test_generated_ledger_is_deterministic_and_non_evidentiary() -> None:
    """Generation is stable and records no passing receipt or coverage result."""

    first = generate_ledger(REPO_ROOT)
    second = generate_ledger(REPO_ROOT)

    assert first == second
    assert first["diagnosticOnly"] is True
    assert first["sourceSummary"]["total"] == 3_655
    assert "coverage" not in first
    assert "receipts" not in first
    validate_ledger_entries(first, discover_current_obligations(REPO_ROOT))


def test_markdown_summary_warns_that_the_ledger_grants_no_compliance() -> None:
    """The human-readable artifact cannot be mistaken for a passing report."""

    markdown = render_ledger_markdown(generate_ledger(REPO_ROOT))

    assert "Diagnostic only" in markdown
    assert "does **not** grant compliance" in markdown
    assert "3,655" in markdown


def test_analyzer_must_resolve_to_a_blocking_owner_and_matching_kind() -> None:
    """A named file cannot masquerade as a blocking analyzer disposition."""

    obligation = _runtime_obligation("parity:node:structural")
    obligation["classification"] = "structural_analyzer"
    obligation["target"] = {
        "familyId": None,
        "scenarioId": None,
        "observationOrAssertion": "source-shape",
        "evidenceRole": "structural_analyzer",
        "analyzerId": "node-source-parity",
    }
    obligation["migrationState"] = "blocking"
    ledger = _ledger(obligation)
    ledger["analyzers"][0]["blockingRequirementId"] = "invented-gate"

    with pytest.raises(LedgerValidationError, match="unknown requirement"):
        validate_ledger_entries(ledger, (obligation,))

    ledger["analyzers"][0]["blockingRequirementId"] = "node-parity-gate"
    ledger["analyzers"][0]["evidenceKind"] = "negative"
    with pytest.raises(LedgerValidationError, match="negative analyzer"):
        validate_ledger_entries(ledger, (obligation,))


def test_coverage_granting_receipts_are_rejected() -> None:
    """Stale receipts or pass status cannot turn diagnostic state into evidence."""

    obligation = _runtime_obligation("parity:node:no-receipt")
    ledger = _ledger(obligation)
    ledger["receipts"] = [{"obligationId": obligation["id"], "passed": True}]

    with pytest.raises(LedgerValidationError, match="coverage-granting fields"):
        validate_ledger_entries(ledger, (obligation,))


def test_artifact_check_rejects_a_removed_obligation(tmp_path: Path) -> None:
    """The checked command fails when the tracked JSON loses a live occurrence."""

    ledger_path = tmp_path / "ledger.json"
    summary_path = tmp_path / "ledger.md"
    write_ledger_artifacts(REPO_ROOT, ledger_path, summary_path)
    check_ledger_artifacts(REPO_ROOT, ledger_path, summary_path)

    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["obligations"].pop()
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(LedgerValidationError, match="missing obligations"):
        check_ledger_artifacts(REPO_ROOT, ledger_path, summary_path)
