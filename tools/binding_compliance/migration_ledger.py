#!/usr/bin/env python3
"""Generate and validate the diagnostic binding-evidence migration ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

# Support both package imports in tests and direct execution from this directory.
try:
    from .catalog import REQUIREMENTS
except ImportError:
    from catalog import REQUIREMENTS  # type: ignore[no-redef]

VALID_CLASSIFICATIONS = frozenset(
    {
        "runtime_verifiable",
        "structural_analyzer",
        "negative_analyzer",
        "policy_exception",
    }
)

PARITY_CONTRACTS = {
    "cxx": Path("docs/implementation/cxx_api_parity/baseline/parity_contract.json"),
    "node": Path("docs/implementation/node_api_parity/baseline/parity_contract.json"),
    "python": Path(
        "docs/implementation/python_api_parity/baseline/parity_contract.json"
    ),
}
RUNTIME_REGISTRIES = {
    "node": Path(
        "node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json"
    ),
    "python": Path("python-bindings/tests/fixtures/runtime_coverage_registry.json"),
}
SCAN_RUN_MANIFEST = Path("tests/fixtures/crash_log_scan_run/manifest.json")
RESOURCE_EXCEPTION_POLICY = Path("docs/api/binding-parity-policy.md")
RESOURCE_EXCEPTION_ID = "cxx-classic-resource-core-transitive-access"
DEFAULT_LEDGER_PATH = Path(
    "docs/implementation/binding_compliance/evidence_migration_ledger.json"
)
DEFAULT_SUMMARY_PATH = Path(
    "docs/implementation/binding_compliance/evidence_migration_ledger.md"
)
BLOCKING_REQUIREMENT_IDS = frozenset(
    requirement.id for requirement in REQUIREMENTS if requirement.blocking
)

WORKFLOW_BLOCKING_OWNERS: dict[str, dict[str, str]] = {
    "cli": {
        "path": ".github/workflows/ci-cpp.yml",
        "commandMarker": "classic-cli/build_cli.ps1 -Test",
    },
    "gui": {
        "path": ".github/workflows/ci-cpp.yml",
        "commandMarker": "classic-gui/build_gui.ps1",
    },
    "node": {
        "path": ".github/workflows/ci-typescript.yml",
        "commandMarker": "bun run test:bun",
    },
    "python-cli": {
        "path": ".github/workflows/ci-python-bindings.yml",
        "commandMarker": "python -m pytest python-bindings/tests -q",
    },
    "tui": {
        "path": ".github/workflows/ci-rust.yml",
        "commandMarker": "cargo test --workspace --release",
    },
}

ANALYZER_IDS = {
    "cxx": "cxx-source-parity",
    "node": "node-source-and-declaration-parity",
    "python": "python-source-and-stub-parity",
}

SCAN_RUN_INTERNAL_RESET_VARIANTS = frozenset(
    {
        "resume_error_kind.local_ignore_reset_replacement_failure",
        "resume_error_kind.local_ignore_reset_durability_unknown",
    }
)
"""Reset outcomes that cannot be triggered safely through every public adapter seam."""

SCAN_RUN_INTERNAL_RESET_MARKERS = frozenset(
    {
        "local_ignore_reset_types_durability_unknown_after_canonical_replacement",
        "reset_replacement_publication_failure_projects_stable_typed_details",
        "reset_replacement_durability_unknown_projects_recoverable_receipt",
        "cxx_resume_operational_errors_preserve_every_stable_reset_outcome_field",
        "cxx_resume_durability_unknown_preserves_recovery_receipt",
        "replacement_failure_projects_shared_node_rejection_metadata",
        "durability_unknown_projects_shared_node_recovery_receipt",
        "replacement_failure_maps_shared_outcome_to_typed_python_exception",
        "durability_unknown_maps_shared_outcome_to_typed_python_exception",
    }
)
"""Blocking internal tests that preserve unreachable reset-fault projection coverage."""

DISPLAY_AUDIT_SPECS: tuple[
    tuple[str, Path, tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]], ...
] = (
    (
        "cli",
        Path("classic-cli/tests/test_display_label_audit.cpp"),
        (
            ("no-local-display-label", "No CLI source turns an audited enum"),
            (
                "no-local-display-content",
                "No CLI source writes a sentence the presentation crate owns",
            ),
        ),
        (
            (
                "display-segment-routing",
                "Every CLI Display Label arrives inside a rendered display line",
            ),
        ),
    ),
    (
        "gui",
        Path("classic-gui/tests/test_display_label_audit.cpp"),
        (
            (
                "no-local-display-label",
                "no_gui_source_turns_an_audited_enum_into_a_string_literal",
            ),
            (
                "no-local-display-content",
                "no_gui_source_writes_a_sentence_the_presentation_crate_owns",
            ),
        ),
        (
            (
                "display-segment-routing",
                "every_rendered_gui_display_label_comes_from_a_bridge_accessor",
            ),
        ),
    ),
    (
        "node",
        Path("node-bindings/classic-node/__test__/display_label_audit.spec.ts"),
        (
            (
                "no-local-display-content",
                "no CLI source writes a sentence the presentation crate owns",
            ),
        ),
        (),
    ),
    (
        "python-cli",
        Path("python-bindings/tests/test_classic_py_cli_display_label_audit.py"),
        (
            (
                "no-token-in-prose",
                "test_no_source_interpolates_a_vocabulary_token_into_prose",
            ),
            (
                "no-local-display-content",
                "test_no_source_writes_a_sentence_the_presentation_crate_owns",
            ),
            (
                "no-local-display-label",
                "test_no_source_resolves_a_display_label_for_itself",
            ),
            (
                "no-plural-rederivation",
                "test_no_source_re_derives_a_plural_noun",
            ),
        ),
        (
            (
                "display-segment-routing",
                "test_the_renderer_reads_every_segment_kind",
            ),
        ),
    ),
    (
        "tui",
        Path("ui-applications/classic-tui/tests/shared_runtime_audit.rs"),
        (
            (
                "no-local-display-label",
                "no_tui_source_turns_an_audited_enum_into_a_string_literal",
            ),
            (
                "no-local-display-content",
                "no_tui_source_writes_a_sentence_the_presentation_crate_owns",
            ),
        ),
        (),
    ),
)

TUI_SHARED_RUNTIME_SELECTORS = (
    "the_tui_never_constructs_its_own_async_runtime",
    "every_tui_spawn_targets_the_shared_runtime",
    "the_audit_covers_every_declared_workflow_module",
    "local_ignore_recovery_resume_is_dispatched_like_every_other_workflow",
)

CONSUMER_SOURCE_AUDIT_SUITES: tuple[tuple[str, Path, str], ...] = (
    (
        "cli",
        Path("classic-cli/tests/test_app_update_wiring.cpp"),
        "app-update",
    ),
    (
        "gui",
        Path("classic-gui/tests/test_mainwindow_geometry.cpp"),
        "gui-layout-and-navigation",
    ),
    (
        "gui",
        Path("classic-gui/tests/test_scan_settings_wiring.cpp"),
        "crash-log-scan-run",
    ),
    (
        "gui",
        Path("classic-gui/tests/test_yaml_update_wiring.cpp"),
        "yaml-data-update",
    ),
)

STRUCTURAL_CONSUMER_CASES = frozenset(
    {
        "gui_production_has_no_raw_user_settings_geometry_paths",
        "mainwindow_does_not_use_deprecated_vr_mode_setting",
        "yaml_update_worker_reuses_incompatible_file_population",
        "native_yaml_update_callers_use_first_party_bridge_helpers",
    }
)

# These inventories intentionally overlap. A mixed source-inspection case gets
# one planned runtime disposition and records its ownership/absence analyzer as
# companion evidence. Pure source-only cases instead target that analyzer. The
# negative subset selects absence analyzers; the remaining cases select shape
# analyzers. This keeps one disposition per test without discarding either claim.
MIXED_CONSUMER_CASES = frozenset(
    {
        "first_run_bootstraps_and_updates_local_yaml",
        "mainwindow_sources_initial_policy_from_rust_defaults",
        "game_files_worker_forwards_game_version_to_setup_intake",
        "mainwindow_preserves_legacy_settings_on_failed_migration",
        "scan_controller_delegates_xse_folder_resolution_to_core",
        "settings_dialog_check_slot_calls_first_party_bridge_helper",
    }
)

NEGATIVE_CONSUMER_CASES = frozenset(
    {
        "gui_production_has_no_raw_user_settings_geometry_paths",
        "mainwindow_does_not_use_deprecated_vr_mode_setting",
        "native_yaml_update_callers_use_first_party_bridge_helpers",
        "first_run_bootstraps_and_updates_local_yaml",
        "game_files_worker_forwards_game_version_to_setup_intake",
        "mainwindow_preserves_legacy_settings_on_failed_migration",
        "settings_dialog_check_slot_calls_first_party_bridge_helper",
    }
)

BASE_ANALYZER_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "id": "cxx-source-parity",
        "evidenceKind": "structural",
        "paths": [
            "tools/cxx_api_parity/check_parity_gate.py",
            "docs/implementation/cxx_api_parity/baseline/parity_contract.json",
        ],
        "blockingRequirementId": "cxx-parity-gate",
    },
    {
        "id": "node-source-and-declaration-parity",
        "evidenceKind": "structural",
        "paths": [
            "tools/node_api_parity/check_parity_gate.py",
            "tools/node_api_parity/check_dts_freshness.py",
            "docs/implementation/node_api_parity/baseline/parity_contract.json",
        ],
        "blockingRequirementId": "node-parity-gate",
    },
    {
        "id": "python-source-and-stub-parity",
        "evidenceKind": "structural",
        "paths": [
            "tools/python_api_parity/check_parity_gate.py",
            "validate_stubs.py",
            "docs/implementation/python_api_parity/baseline/parity_contract.json",
        ],
        "blockingRequirementId": "python-parity-gate",
    },
    {
        "id": "scan-run-contract-validator",
        "evidenceKind": "structural",
        "paths": [
            "tools/binding_compliance/scan_run_contract.py",
            "tests/fixtures/crash_log_scan_run/manifest.json",
        ],
        "blockingRequirementId": "scan-run-contract-variants",
    },
    {
        "id": "scan-run-forbidden-export-audit",
        "evidenceKind": "negative",
        "paths": ["tools/binding_compliance/scan_run_contract.py"],
        "blockingRequirementId": "scan-run-contract-variants",
    },
    {
        "id": "scan-run-rust-enum-inventory",
        "evidenceKind": "structural",
        "paths": ["tools/binding_compliance/scan_run_contract.py"],
        "blockingRequirementId": "scan-run-contract-variants",
    },
    {
        "id": "scan-run-local-ignore-reset-internal-faults",
        "evidenceKind": "structural",
        "paths": [
            "tools/binding_compliance/scan_run_contract.py",
            "tests/fixtures/crash_log_scan_run/manifest.json",
            "business-logic/classic-durable-publication/src/publication_fault.rs",
            "business-logic/classic-config-core/src/installed_yaml_data_reset_fault.rs",
            "business-logic/classic-config-core/src/installed_yaml_data_tests.rs",
            "business-logic/classic-scanlog-core/src/scan_run/contract_tests.rs",
            "cpp-bindings/classic-cpp-bridge/src/scanner/contract_tests.rs",
            "node-bindings/classic-node/src/scan_run_tests.rs",
            "python-bindings/classic-scanlog-py/src/scan_run_tests.rs",
        ],
        "blockingRequirementId": "scan-run-contract-variants",
    },
    {
        "id": "tui-shared-runtime-ownership",
        "evidenceKind": "structural",
        "paths": ["ui-applications/classic-tui/tests/shared_runtime_audit.rs"],
        "blockingWorkflow": WORKFLOW_BLOCKING_OWNERS["tui"],
    },
    {
        "id": "user-settings-exclusive-ownership",
        "evidenceKind": "negative",
        "paths": ["tools/user_settings_ownership/check.py"],
        "blockingRequirementId": "user-settings-exclusive-ownership",
    },
)


class LedgerValidationError(ValueError):
    """Raised when the diagnostic ledger does not cover the live obligations."""


def _catalog_ids(ledger: Mapping[str, Any], key: str) -> set[str]:
    """Validate a named ledger catalog and return its unique stable IDs."""

    catalog = ledger.get(key)
    if not isinstance(catalog, list):
        raise LedgerValidationError(f"ledger {key} must be a list")
    ids: list[str] = []
    for index, item in enumerate(catalog):
        if not isinstance(item, Mapping):
            raise LedgerValidationError(f"ledger {key}[{index}] must be an object")
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id:
            raise LedgerValidationError(f"ledger {key}[{index}] has no stable id")
        ids.append(item_id)
    duplicates = sorted(item_id for item_id, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise LedgerValidationError(
            f"ledger {key} contains duplicate IDs: {', '.join(duplicates)}"
        )
    return set(ids)


def _analyzer_kinds(ledger: Mapping[str, Any]) -> dict[str, str]:
    """Validate analyzer ownership and return each analyzer's evidence kind.

    Returns a stable-ID lookup whose values are ``structural`` or ``negative``.
    Raises ``LedgerValidationError`` when an analyzer is not tied to either a
    blocking compliance requirement or a checked blocking workflow command.
    """

    analyzer_ids = _catalog_ids(ledger, "analyzers")
    analyzers = ledger["analyzers"]
    kinds: dict[str, str] = {}
    for analyzer in analyzers:
        analyzer_id = analyzer["id"]
        evidence_kind = analyzer.get("evidenceKind")
        if evidence_kind not in {"structural", "negative"}:
            raise LedgerValidationError(
                f"analyzer {analyzer_id!r} has unsupported evidenceKind"
            )
        requirement_id = analyzer.get("blockingRequirementId")
        workflow = analyzer.get("blockingWorkflow")
        if (requirement_id is None) == (workflow is None):
            raise LedgerValidationError(
                f"analyzer {analyzer_id!r} needs exactly one blocking owner"
            )
        if requirement_id is not None:
            if requirement_id not in BLOCKING_REQUIREMENT_IDS:
                raise LedgerValidationError(
                    f"analyzer {analyzer_id!r} references nonblocking or unknown "
                    f"requirement {requirement_id!r}"
                )
        elif not isinstance(workflow, Mapping) or not all(
            isinstance(workflow.get(key), str) and workflow[key]
            for key in ("path", "commandMarker")
        ):
            raise LedgerValidationError(
                f"analyzer {analyzer_id!r} has invalid blockingWorkflow"
            )
        kinds[analyzer_id] = evidence_kind
    if set(kinds) != analyzer_ids:
        raise LedgerValidationError("analyzer catalog IDs could not be validated")
    return kinds


def _validate_obligation_entry(
    entry: Mapping[str, Any],
    *,
    index: int,
    analyzer_kinds: Mapping[str, str],
    policy_exception_ids: set[str],
) -> None:
    """Validate one ledger row's discriminated disposition and state evidence."""

    obligation_id = entry.get("id")
    if not isinstance(obligation_id, str) or not obligation_id:
        raise LedgerValidationError(f"ledger obligation {index} has no stable id")
    for key in ("sourceKind", "participant", "mappingOrigin"):
        if not isinstance(entry.get(key), str) or not entry[key]:
            raise LedgerValidationError(
                f"ledger obligation {obligation_id} has invalid {key}"
            )
    source = entry.get("source")
    if not isinstance(source, Mapping) or not all(
        isinstance(source.get(key), str) and source[key]
        for key in ("artifact", "locator")
    ):
        raise LedgerValidationError(
            f"ledger obligation {obligation_id} has invalid source identity"
        )

    classification = entry.get("classification")
    if classification not in VALID_CLASSIFICATIONS:
        raise LedgerValidationError(
            f"ledger obligation {index} has unsupported classification: "
            f"{classification!r}"
        )
    target = entry.get("target")
    if not isinstance(target, Mapping):
        raise LedgerValidationError(
            f"ledger obligation {obligation_id} must have a target object"
        )
    migration_state = entry.get("migrationState")
    if migration_state not in {"shadow", "equivalent", "blocking", "retired"}:
        raise LedgerValidationError(
            f"ledger obligation {obligation_id} has invalid migrationState"
        )
    state_evidence = entry.get("stateEvidence")
    if (
        not isinstance(state_evidence, list)
        or not state_evidence
        or not all(isinstance(item, str) and item for item in state_evidence)
    ):
        raise LedgerValidationError(
            f"ledger obligation {obligation_id} needs objective stateEvidence"
        )

    retained = entry.get("retainedAnalyzerIds")
    if not isinstance(retained, list) or not all(
        isinstance(item, str) and item for item in retained
    ):
        raise LedgerValidationError(
            f"ledger obligation {obligation_id} has invalid retainedAnalyzerIds"
        )
    unknown_retained = sorted(set(retained) - analyzer_kinds.keys())
    if unknown_retained:
        raise LedgerValidationError(
            f"ledger obligation {obligation_id} references unknown analyzer(s): "
            f"{', '.join(unknown_retained)}"
        )

    evidence_role = target.get("evidenceRole")
    if classification == "runtime_verifiable":
        if evidence_role not in {"semantic_adapter", "consumer"}:
            raise LedgerValidationError(
                f"runtime obligation {obligation_id} has invalid evidenceRole"
            )
        if not isinstance(target.get("familyId"), str) or not target["familyId"]:
            raise LedgerValidationError(
                f"runtime obligation {obligation_id} needs a planned familyId"
            )
        # Shadow entries may name only a family hint. Later ratchet states must
        # cite concrete scenario and observation IDs backed by dual-run evidence.
        if migration_state != "shadow" and not all(
            isinstance(target.get(key), str) and target[key]
            for key in ("scenarioId", "observationOrAssertion")
        ):
            raise LedgerValidationError(
                f"runtime obligation {obligation_id} needs concrete target IDs "
                f"before {migration_state}"
            )
        return

    if classification in {"structural_analyzer", "negative_analyzer"}:
        expected_role = classification
        if evidence_role != expected_role:
            raise LedgerValidationError(
                f"{classification} obligation {obligation_id} has invalid evidenceRole"
            )
        analyzer_id = target.get("analyzerId")
        if not isinstance(analyzer_id, str) or analyzer_id not in analyzer_kinds:
            raise LedgerValidationError(
                f"ledger obligation {obligation_id} references unknown analyzer: "
                f"{analyzer_id!r}"
            )
        expected_kind = (
            "structural" if classification == "structural_analyzer" else "negative"
        )
        if analyzer_kinds[analyzer_id] != expected_kind:
            raise LedgerValidationError(
                f"{classification} obligation {obligation_id} references "
                f"{analyzer_kinds[analyzer_id]} analyzer {analyzer_id!r}"
            )
        assertion = target.get("observationOrAssertion")
        if not isinstance(assertion, str) or not assertion:
            raise LedgerValidationError(
                f"{classification} obligation {obligation_id} needs an assertion ID"
            )
        return

    if evidence_role != "policy_exception":
        raise LedgerValidationError(
            f"policy exception obligation {obligation_id} has invalid evidenceRole"
        )
    policy_exception_id = target.get("policyExceptionId")
    if policy_exception_id not in policy_exception_ids:
        raise LedgerValidationError(
            f"ledger obligation {obligation_id} references unknown policy exception: "
            f"{policy_exception_id!r}"
        )


def _read_json(repo_root: Path, relative_path: Path) -> dict[str, Any]:
    """Read one required repository JSON object with a useful ledger diagnostic."""

    path = repo_root / relative_path
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LedgerValidationError(f"cannot read {relative_path}: {error}") from error
    if not isinstance(value, dict):
        raise LedgerValidationError(f"{relative_path} must contain a JSON object")
    return value


def _read_text(repo_root: Path, relative_path: Path) -> str:
    """Read one required repository text file for source-audit discovery."""

    try:
        return (repo_root / relative_path).read_text(encoding="utf-8")
    except OSError as error:
        raise LedgerValidationError(f"cannot read {relative_path}: {error}") from error


def _stable_digest(*parts: object) -> str:
    """Return a short stable identity suffix for verbose marker occurrences."""

    encoded = "\0".join(str(part) for part in parts).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _require_list(value: object, label: str) -> list[Any]:
    """Return a JSON list or raise a source-specific validation error."""

    if not isinstance(value, list):
        raise LedgerValidationError(f"{label} must be a list")
    return value


def _require_object(value: object, label: str) -> dict[str, Any]:
    """Return a JSON object or raise a source-specific validation error."""

    if not isinstance(value, dict):
        raise LedgerValidationError(f"{label} must be an object")
    return value


def _planned_runtime_obligation(
    *,
    obligation_id: str,
    source_kind: str,
    artifact: Path,
    locator: str,
    participant: str,
    mapping_origin: str,
    family_id: str,
    evidence_role: str = "semantic_adapter",
    retained_analyzer_ids: Sequence[str] = (),
    planned_scenario_id: str | None = None,
) -> dict[str, Any]:
    """Build one diagnostic-only runtime target that grants no executed coverage."""

    return {
        "id": obligation_id,
        "sourceKind": source_kind,
        "source": {"artifact": artifact.as_posix(), "locator": locator},
        "participant": participant,
        "mappingOrigin": mapping_origin,
        "classification": "runtime_verifiable",
        "target": {
            "familyId": family_id,
            "scenarioId": planned_scenario_id,
            "observationOrAssertion": None,
            "evidenceRole": evidence_role,
        },
        "retainedAnalyzerIds": list(retained_analyzer_ids),
        "migrationState": "shadow",
        "stateEvidence": [
            "Phase 0 records the target disposition only; no executable receipt exists."
        ],
    }


def _analyzer_obligation(
    *,
    obligation_id: str,
    source_kind: str,
    artifact: Path,
    locator: str,
    participant: str,
    mapping_origin: str,
    classification: str,
    analyzer_id: str,
) -> dict[str, Any]:
    """Build one obligation permanently owned by a named retained analyzer."""

    evidence_role = (
        "structural_analyzer"
        if classification == "structural_analyzer"
        else "negative_analyzer"
    )
    return {
        "id": obligation_id,
        "sourceKind": source_kind,
        "source": {"artifact": artifact.as_posix(), "locator": locator},
        "participant": participant,
        "mappingOrigin": mapping_origin,
        "classification": classification,
        "target": {
            "familyId": None,
            "scenarioId": None,
            "observationOrAssertion": locator,
            "evidenceRole": evidence_role,
            "analyzerId": analyzer_id,
        },
        "retainedAnalyzerIds": [analyzer_id],
        "migrationState": "blocking",
        "stateEvidence": [
            f"The retained {analyzer_id} analyzer already fails its blocking workflow."
        ],
    }


def _policy_exception_obligation(repo_root: Path) -> dict[str, Any]:
    """Record the sole documented CXX Resource binding exception."""

    policy_path = repo_root / RESOURCE_EXCEPTION_POLICY
    try:
        policy = policy_path.read_text(encoding="utf-8")
    except OSError as error:
        raise LedgerValidationError(
            f"cannot read {RESOURCE_EXCEPTION_POLICY}: {error}"
        ) from error
    required_text = (
        "The only current exception is `classic-resource-core`, which has no "
        "dedicated C++ bridge module"
    )
    if required_text not in policy:
        raise LedgerValidationError(
            f"{RESOURCE_EXCEPTION_POLICY} no longer documents the CXX Resource exception"
        )
    return {
        "id": f"policy-exception:cxx:{RESOURCE_EXCEPTION_ID}",
        "sourceKind": "policy_exception",
        "source": {
            "artifact": RESOURCE_EXCEPTION_POLICY.as_posix(),
            "locator": RESOURCE_EXCEPTION_ID,
        },
        "participant": "cxx",
        "mappingOrigin": "documented_exception",
        "classification": "policy_exception",
        "target": {
            "familyId": None,
            "scenarioId": None,
            "observationOrAssertion": None,
            "evidenceRole": "policy_exception",
            "policyExceptionId": RESOURCE_EXCEPTION_ID,
        },
        "retainedAnalyzerIds": [],
        "migrationState": "blocking",
        "stateEvidence": [
            f"The one-tier binding policy documents {RESOURCE_EXCEPTION_ID}."
        ],
    }


def _parity_obligations(repo_root: Path) -> list[dict[str, Any]]:
    """Discover and classify every tracked CXX, Node, and Python parity row."""

    obligations: list[dict[str, Any]] = []
    for participant, artifact in PARITY_CONTRACTS.items():
        contract = _read_json(repo_root, artifact)
        row_key = "entries" if participant == "cxx" else "tier1Mappings"
        rows = _require_list(contract.get(row_key), f"{artifact}:{row_key}")
        raw_ids = [row.get("id") if isinstance(row, dict) else None for row in rows]
        id_totals = Counter(raw_ids)
        id_occurrences: Counter[object] = Counter()
        for index, raw_row in enumerate(rows):
            row = _require_object(raw_row, f"{artifact}:{row_key}[{index}]")
            row_id = row.get("id")
            if not isinstance(row_id, str) or not row_id:
                raise LedgerValidationError(
                    f"{artifact}:{row_key}[{index}] has no stable id"
                )
            id_occurrences[row_id] += 1
            occurrence_suffix = (
                f":occurrence:{id_occurrences[row_id]}" if id_totals[row_id] > 1 else ""
            )
            # The Node baseline intentionally contains repeated Rust-side rows;
            # the suffix preserves each occurrence instead of treating IDs as a set.
            obligation_id = f"parity:{participant}:{row_id}{occurrence_suffix}"
            locator = f"/{row_key}/{index}#id={row_id}"
            analyzer_id = ANALYZER_IDS[participant]

            if participant == "cxx":
                binding_only = isinstance(row.get("unmappedReason"), str)
                if binding_only:
                    declaration_only = (
                        row.get("kind") != "function" or row.get("blockOrigin") == "C++"
                    )
                    if declaration_only:
                        # Opaque transports and foreign C++ callbacks expose only
                        # declaration shape; the retained source analyzer owns that
                        # irreducibly structural evidence.
                        obligations.append(
                            _analyzer_obligation(
                                obligation_id=obligation_id,
                                source_kind="parity_row",
                                artifact=artifact,
                                locator=locator,
                                participant=participant,
                                mapping_origin="binding_only",
                                classification="structural_analyzer",
                                analyzer_id=analyzer_id,
                            )
                        )
                        continue

                    bridge_module = row.get("bridgeModule")
                    if not isinstance(bridge_module, str) or not bridge_module:
                        raise LedgerValidationError(
                            f"{artifact}:{row_key}[{index}] has no CXX bridge module"
                        )
                    # Binding-owned public operations still require executed
                    # evidence even though no canonical Rust symbol owns them.
                    obligations.append(
                        _planned_runtime_obligation(
                            obligation_id=obligation_id,
                            source_kind="parity_row",
                            artifact=artifact,
                            locator=locator,
                            participant=participant,
                            mapping_origin="binding_only",
                            family_id=f"cxx-binding:{bridge_module}",
                            retained_analyzer_ids=(analyzer_id,),
                        )
                    )
                    continue

                canonical_fields = ("ownerModule", "rustCrate", "coreRustSymbol")
                if not all(
                    isinstance(row.get(field), str) and row[field]
                    for field in canonical_fields
                ):
                    raise LedgerValidationError(
                        f"{artifact}:{row_key}[{index}] has no canonical CXX mapping"
                    )
                obligations.append(
                    _planned_runtime_obligation(
                        obligation_id=obligation_id,
                        source_kind="parity_row",
                        artifact=artifact,
                        locator=locator,
                        participant=participant,
                        mapping_origin="canonical_rust",
                        family_id=str(row["ownerModule"]),
                        retained_analyzer_ids=(analyzer_id,),
                    )
                )
                continue

            binding_only = isinstance(row.get("unmappedReason"), str)
            if participant == "node":
                binding_kind = row.get("nodeKind")
                mapping_origin = (
                    "binding_only"
                    if binding_only
                    else "canonical_rust"
                    if row.get("nodeExport")
                    else "rust_only"
                )
                # Interfaces and const enums are erased by TypeScript, so runtime
                # execution cannot replace declaration/source analysis for the row.
                if binding_kind in {"interface", "type", "const_enum"}:
                    obligations.append(
                        _analyzer_obligation(
                            obligation_id=obligation_id,
                            source_kind="parity_row",
                            artifact=artifact,
                            locator=locator,
                            participant=participant,
                            mapping_origin=mapping_origin,
                            classification="structural_analyzer",
                            analyzer_id=analyzer_id,
                        )
                    )
                    continue
            else:
                mapping_origin = "binding_only" if binding_only else "canonical_rust"

            obligations.append(
                _planned_runtime_obligation(
                    obligation_id=obligation_id,
                    source_kind="parity_row",
                    artifact=artifact,
                    locator=locator,
                    participant=participant,
                    mapping_origin=mapping_origin,
                    family_id=str(row.get("ownerModule") or "unowned"),
                    retained_analyzer_ids=(analyzer_id,),
                )
            )
    return obligations


def _runtime_registry_obligations(repo_root: Path) -> list[dict[str, Any]]:
    """Discover legacy Node and Python runtime-registry claims."""

    obligations: list[dict[str, Any]] = []
    for participant, artifact in RUNTIME_REGISTRIES.items():
        registry = _read_json(repo_root, artifact)
        entries = _require_list(registry.get("entries"), f"{artifact}:entries")
        for index, raw_entry in enumerate(entries):
            entry = _require_object(raw_entry, f"{artifact}:entries[{index}]")
            coverage_id = entry.get("coverageId")
            if not isinstance(coverage_id, str) or not coverage_id:
                raise LedgerValidationError(
                    f"{artifact}:entries[{index}] has no coverageId"
                )
            obligations.append(
                _planned_runtime_obligation(
                    obligation_id=f"runtime-claim:{participant}:{coverage_id}",
                    source_kind="runtime_registry_claim",
                    artifact=artifact,
                    locator=f"/entries/{index}#coverageId={coverage_id}",
                    participant=participant,
                    mapping_origin="legacy_registry_claim",
                    family_id=str(entry.get("ownerModule") or "unowned"),
                    retained_analyzer_ids=(ANALYZER_IDS[participant],),
                )
            )
    return obligations


def _evidence_markers(
    *,
    artifact: Path,
    entries: object,
    scope: str,
    participant: str,
    source_kind: str,
    evidence_role: str,
    planned_scenario_id: str | None,
) -> list[dict[str, Any]]:
    """Expand every positive source-marker occurrence into one obligation."""

    obligations: list[dict[str, Any]] = []
    for entry_index, raw_entry in enumerate(_require_list(entries, scope)):
        entry = _require_object(raw_entry, f"{scope}[{entry_index}]")
        path = entry.get("path")
        if not isinstance(path, str) or not path:
            raise LedgerValidationError(f"{scope}[{entry_index}] has no path")
        markers = _require_list(
            entry.get("contains"), f"{scope}[{entry_index}].contains"
        )
        for marker_index, marker in enumerate(markers):
            if not isinstance(marker, str) or not marker:
                raise LedgerValidationError(
                    f"{scope}[{entry_index}].contains[{marker_index}] must be a string"
                )
            digest = _stable_digest(scope, path, marker)
            if marker in SCAN_RUN_INTERNAL_RESET_MARKERS:
                obligations.append(
                    _analyzer_obligation(
                        obligation_id=f"{source_kind}:{participant}:{digest}",
                        source_kind=source_kind,
                        artifact=artifact,
                        locator=(
                            f"{scope}/{entry_index}/contains/{marker_index}"
                            f"#path={path};marker={marker}"
                        ),
                        participant=participant,
                        mapping_origin="retained_internal_fault_projection",
                        classification="structural_analyzer",
                        analyzer_id="scan-run-local-ignore-reset-internal-faults",
                    )
                )
                continue
            obligations.append(
                _planned_runtime_obligation(
                    obligation_id=f"{source_kind}:{participant}:{digest}",
                    source_kind=source_kind,
                    artifact=artifact,
                    locator=(
                        f"{scope}/{entry_index}/contains/{marker_index}"
                        f"#path={path};marker={marker}"
                    ),
                    participant=participant,
                    mapping_origin=(
                        "legacy_consumer_marker"
                        if source_kind == "consumer_audit"
                        else "legacy_source_marker"
                    ),
                    family_id="crash-log-scan-run",
                    evidence_role=evidence_role,
                    planned_scenario_id=planned_scenario_id,
                    retained_analyzer_ids=("scan-run-contract-validator",),
                )
            )
    return obligations


def _scan_run_obligations(repo_root: Path) -> list[dict[str, Any]]:
    """Discover current Crash Log Scan Run acknowledgements, markers, and audits."""

    manifest = _read_json(repo_root, SCAN_RUN_MANIFEST)
    obligations: list[dict[str, Any]] = []

    contract_variants = _require_list(
        manifest.get("contractVariants"), "manifest.contractVariants"
    )
    for index, variant in enumerate(contract_variants):
        if not isinstance(variant, str) or not variant:
            raise LedgerValidationError(
                f"manifest.contractVariants[{index}] must be a string"
            )
        obligations.append(
            _analyzer_obligation(
                obligation_id=f"scan-run:contract-variant:{variant}",
                source_kind="scan_run_contract_variant",
                artifact=SCAN_RUN_MANIFEST,
                locator=f"/contractVariants/{index}#{variant}",
                participant="rust",
                mapping_origin="source_inventory_audit",
                classification="structural_analyzer",
                analyzer_id="scan-run-rust-enum-inventory",
            )
        )

    supported_adapters = _require_list(
        manifest.get("supportedAdapters"), "manifest.supportedAdapters"
    )
    for index, participant in enumerate(supported_adapters):
        if not isinstance(participant, str) or not participant:
            raise LedgerValidationError(
                f"manifest.supportedAdapters[{index}] must be a string"
            )
        obligations.append(
            _planned_runtime_obligation(
                obligation_id=f"scan-run:supported-adapter:{participant}",
                source_kind="scan_run_supported_adapter",
                artifact=SCAN_RUN_MANIFEST,
                locator=f"/supportedAdapters/{index}#{participant}",
                participant=participant,
                mapping_origin="legacy_applicability_claim",
                family_id="crash-log-scan-run",
                retained_analyzer_ids=("scan-run-contract-validator",),
            )
        )

    adapters = _require_object(manifest.get("adapters"), "manifest.adapters")
    for participant, raw_adapter in adapters.items():
        adapter = _require_object(raw_adapter, f"manifest.adapters.{participant}")
        variants = _require_list(
            adapter.get("acknowledgedVariants"),
            f"manifest.adapters.{participant}.acknowledgedVariants",
        )
        for index, variant in enumerate(variants):
            if not isinstance(variant, str) or not variant:
                raise LedgerValidationError(
                    f"manifest.adapters.{participant}.acknowledgedVariants[{index}] "
                    "must be a string"
                )
            locator = f"/adapters/{participant}/acknowledgedVariants/{index}#{variant}"
            if variant in SCAN_RUN_INTERNAL_RESET_VARIANTS:
                obligations.append(
                    _analyzer_obligation(
                        obligation_id=f"scan-run:variant:{participant}:{variant}",
                        source_kind="scan_run_variant_acknowledgement",
                        artifact=SCAN_RUN_MANIFEST,
                        locator=locator,
                        participant=participant,
                        mapping_origin="retained_internal_fault_projection",
                        classification="structural_analyzer",
                        analyzer_id="scan-run-local-ignore-reset-internal-faults",
                    )
                )
                continue
            obligations.append(
                _planned_runtime_obligation(
                    obligation_id=f"scan-run:variant:{participant}:{variant}",
                    source_kind="scan_run_variant_acknowledgement",
                    artifact=SCAN_RUN_MANIFEST,
                    locator=locator,
                    participant=participant,
                    mapping_origin="legacy_variant_acknowledgement",
                    family_id="crash-log-scan-run",
                    retained_analyzer_ids=("scan-run-contract-validator",),
                )
            )
        obligations.extend(
            _evidence_markers(
                artifact=SCAN_RUN_MANIFEST,
                entries=adapter.get("evidence"),
                scope=f"/adapters/{participant}/evidence",
                participant=participant,
                source_kind="scan_run_source_marker",
                evidence_role="semantic_adapter",
                planned_scenario_id=None,
            )
        )

    scenarios = _require_object(manifest.get("scenarios"), "manifest.scenarios")
    for scenario_id, raw_scenario in scenarios.items():
        scenario = _require_object(raw_scenario, f"manifest.scenarios.{scenario_id}")
        required_owners = _require_list(
            scenario.get("requiredOwners"),
            f"manifest.scenarios.{scenario_id}.requiredOwners",
        )
        for index, participant in enumerate(required_owners):
            if not isinstance(participant, str) or not participant:
                raise LedgerValidationError(
                    f"manifest.scenarios.{scenario_id}.requiredOwners[{index}] "
                    "must be a string"
                )
            obligations.append(
                _planned_runtime_obligation(
                    obligation_id=(
                        f"scan-run:required-participant:{scenario_id}:{participant}"
                    ),
                    source_kind="scan_run_required_participant",
                    artifact=SCAN_RUN_MANIFEST,
                    locator=(
                        f"/scenarios/{scenario_id}/requiredOwners/{index}#{participant}"
                    ),
                    participant=participant,
                    mapping_origin="legacy_applicability_claim",
                    family_id="crash-log-scan-run",
                    planned_scenario_id=scenario_id,
                    retained_analyzer_ids=("scan-run-contract-validator",),
                )
            )
        evidence = _require_object(
            scenario.get("evidence"), f"manifest.scenarios.{scenario_id}.evidence"
        )
        for participant, entries in evidence.items():
            obligations.extend(
                _evidence_markers(
                    artifact=SCAN_RUN_MANIFEST,
                    entries=entries,
                    scope=f"/scenarios/{scenario_id}/evidence/{participant}",
                    participant=participant,
                    source_kind="scan_run_source_marker",
                    evidence_role="semantic_adapter",
                    planned_scenario_id=scenario_id,
                )
            )

    presentations = _require_object(
        manifest.get("presentations"), "manifest.presentations"
    )
    for presentation_id, raw_presentation in presentations.items():
        presentation = _require_object(
            raw_presentation, f"manifest.presentations.{presentation_id}"
        )
        required_owners = _require_list(
            presentation.get("requiredOwners"),
            f"manifest.presentations.{presentation_id}.requiredOwners",
        )
        for index, participant in enumerate(required_owners):
            if not isinstance(participant, str) or not participant:
                raise LedgerValidationError(
                    f"manifest.presentations.{presentation_id}.requiredOwners[{index}] "
                    "must be a string"
                )
            obligations.append(
                _planned_runtime_obligation(
                    obligation_id=(
                        f"consumer:required-participant:{presentation_id}:{participant}"
                    ),
                    source_kind="consumer_required_participant",
                    artifact=SCAN_RUN_MANIFEST,
                    locator=(
                        f"/presentations/{presentation_id}/requiredOwners/{index}"
                        f"#{participant}"
                    ),
                    participant=participant,
                    mapping_origin="legacy_applicability_claim",
                    family_id="crash-log-scan-run",
                    evidence_role="consumer",
                    planned_scenario_id=presentation_id,
                    retained_analyzer_ids=("scan-run-contract-validator",),
                )
            )
        evidence = _require_object(
            presentation.get("evidence"),
            f"manifest.presentations.{presentation_id}.evidence",
        )
        for participant, entries in evidence.items():
            obligations.extend(
                _evidence_markers(
                    artifact=SCAN_RUN_MANIFEST,
                    entries=entries,
                    scope=f"/presentations/{presentation_id}/evidence/{participant}",
                    participant=participant,
                    source_kind="consumer_audit",
                    evidence_role="consumer",
                    planned_scenario_id=presentation_id,
                )
            )

    forbidden_exports = _require_object(
        manifest.get("forbiddenExports"), "manifest.forbiddenExports"
    )
    for participant, raw_groups in forbidden_exports.items():
        groups = _require_list(raw_groups, f"manifest.forbiddenExports.{participant}")
        for group_index, raw_group in enumerate(groups):
            group = _require_object(
                raw_group, f"manifest.forbiddenExports.{participant}[{group_index}]"
            )
            path = group.get("path")
            if not isinstance(path, str) or not path:
                raise LedgerValidationError(
                    f"manifest.forbiddenExports.{participant}[{group_index}] has no path"
                )
            symbols = _require_list(
                group.get("symbols"),
                f"manifest.forbiddenExports.{participant}[{group_index}].symbols",
            )
            for symbol_index, symbol in enumerate(symbols):
                if not isinstance(symbol, str) or not symbol:
                    raise LedgerValidationError(
                        f"manifest.forbiddenExports.{participant}[{group_index}]"
                        f".symbols[{symbol_index}] must be a string"
                    )
                locator = (
                    f"/forbiddenExports/{participant}/{group_index}/symbols/"
                    f"{symbol_index}#path={path};symbol={symbol}"
                )
                obligations.append(
                    _analyzer_obligation(
                        obligation_id=(
                            f"source-audit:{participant}:"
                            f"{_stable_digest(participant, path, symbol)}"
                        ),
                        source_kind="source_audit",
                        artifact=SCAN_RUN_MANIFEST,
                        locator=locator,
                        participant=participant,
                        mapping_origin="forbidden_export_audit",
                        classification="negative_analyzer",
                        analyzer_id="scan-run-forbidden-export-audit",
                    )
                )

    rust_enums = _require_list(manifest.get("rustEnums"), "manifest.rustEnums")
    for index, raw_enum in enumerate(rust_enums):
        enum = _require_object(raw_enum, f"manifest.rustEnums[{index}]")
        category = enum.get("category")
        path = enum.get("path")
        name = enum.get("name")
        if not all(
            isinstance(value, str) and value for value in (category, path, name)
        ):
            raise LedgerValidationError(
                f"manifest.rustEnums[{index}] must name category, path, and enum"
            )
        obligations.append(
            _analyzer_obligation(
                obligation_id=f"rust-enum-audit:{category}:{name}:{_stable_digest(path)}",
                source_kind="rust_enum_inventory_audit",
                artifact=SCAN_RUN_MANIFEST,
                locator=f"/rustEnums/{index}#category={category};path={path};name={name}",
                participant="rust",
                mapping_origin="source_inventory_audit",
                classification="structural_analyzer",
                analyzer_id="scan-run-rust-enum-inventory",
            )
        )
    return obligations


def _display_content_audit_obligations(repo_root: Path) -> list[dict[str, Any]]:
    """Discover retained ownership audits and positive consumer-routing assertions."""

    obligations: list[dict[str, Any]] = []
    for participant, artifact, negative_specs, runtime_specs in DISPLAY_AUDIT_SPECS:
        source = _read_text(repo_root, artifact)
        analyzer_id = f"display-content-ownership-{participant}"
        for semantic_id, selector in negative_specs:
            if selector not in source:
                raise LedgerValidationError(
                    f"{artifact} is missing display audit selector {selector!r}"
                )
            obligations.append(
                _analyzer_obligation(
                    obligation_id=f"display-source-audit:{participant}:{semantic_id}",
                    source_kind="display_content_source_audit",
                    artifact=artifact,
                    locator=f"semantic={semantic_id};selector={selector}",
                    participant=participant,
                    mapping_origin="consumer_source_audit",
                    classification="negative_analyzer",
                    analyzer_id=analyzer_id,
                )
            )
        for semantic_id, selector in runtime_specs:
            if selector not in source:
                raise LedgerValidationError(
                    f"{artifact} is missing display consumer selector {selector!r}"
                )
            obligations.append(
                _planned_runtime_obligation(
                    obligation_id=f"display-consumer-audit:{participant}:{semantic_id}",
                    source_kind="display_content_consumer_audit",
                    artifact=artifact,
                    locator=f"semantic={semantic_id};selector={selector}",
                    participant=participant,
                    mapping_origin="legacy_consumer_source_assertion",
                    family_id="display-content",
                    evidence_role="consumer",
                    retained_analyzer_ids=(analyzer_id,),
                )
            )

    tui_artifact = Path("ui-applications/classic-tui/tests/shared_runtime_audit.rs")
    tui_source = _read_text(repo_root, tui_artifact)
    missing = [
        selector
        for selector in TUI_SHARED_RUNTIME_SELECTORS
        if selector not in tui_source
    ]
    if missing:
        raise LedgerValidationError(
            f"{tui_artifact} is missing shared-runtime selectors: {', '.join(missing)}"
        )
    obligations.append(
        _analyzer_obligation(
            obligation_id="source-audit:tui:shared-runtime-ownership",
            source_kind="shared_runtime_source_audit",
            artifact=tui_artifact,
            locator="selectors=" + ",".join(TUI_SHARED_RUNTIME_SELECTORS),
            participant="tui",
            mapping_origin="consumer_source_audit",
            classification="structural_analyzer",
            analyzer_id="tui-shared-runtime-ownership",
        )
    )
    return obligations


def _user_settings_source_audit_obligations(
    repo_root: Path,
) -> list[dict[str, Any]]:
    """Discover the four stable User Settings source-ownership rules."""

    artifact = Path("tools/user_settings_ownership/check.py")
    source = _read_text(repo_root, artifact)
    rules_block_match = re.search(
        r"RULES:.*?=\s*\((.*?)\)\s*MIRROR_RULE\s*=",
        source,
        flags=re.DOTALL,
    )
    mirror_match = re.search(
        r"MIRROR_RULE\s*=\s*\(\s*[\"']([^\"']+)[\"']",
        source,
    )
    if rules_block_match is None or mirror_match is None:
        raise LedgerValidationError(
            f"{artifact} no longer exposes the expected RULES and MIRROR_RULE declarations"
        )
    rule_ids = re.findall(
        r"^[ ]{4,8}\(?[\"']([a-z][a-z0-9-]+)[\"'],(?:\s*$|\s*re\.compile)",
        rules_block_match.group(1),
        flags=re.MULTILINE,
    )
    rule_ids.append(mirror_match.group(1))
    if len(rule_ids) != 4 or len(set(rule_ids)) != 4:
        raise LedgerValidationError(
            f"{artifact} must expose four distinct ownership rule IDs, found {rule_ids}"
        )
    return [
        _analyzer_obligation(
            obligation_id=f"source-audit:user-settings:{rule_id}",
            source_kind="user_settings_source_audit",
            artifact=artifact,
            locator=f"rule={rule_id}",
            participant="shared",
            mapping_origin="source_ownership_rule",
            classification="negative_analyzer",
            analyzer_id="user-settings-exclusive-ownership",
        )
        for rule_id in rule_ids
    ]


def _consumer_case_names(artifact: Path, source: str) -> list[str]:
    """Extract current Catch2 or Qt source-inspection case names in source order."""

    if artifact.name == "test_app_update_wiring.cpp":
        return re.findall(r'^TEST_CASE\("([^"]+)"', source, flags=re.MULTILINE)
    return re.findall(
        r"^void\s+[A-Za-z0-9_]+::([A-Za-z0-9_]+)\(\)",
        source,
        flags=re.MULTILINE,
    )


def _consumer_analyzer_id(artifact: Path, classification: str) -> str:
    """Return the named analyzer ID for one source-only evidence kind."""

    kind = "negative" if classification == "negative_analyzer" else "structural"
    return f"consumer-source-audit:{artifact.stem}:{kind}"


def _consumer_source_audit_obligations(repo_root: Path) -> list[dict[str, Any]]:
    """Discover existing CLI/GUI source-inspection cases at semantic granularity."""

    obligations: list[dict[str, Any]] = []
    for participant, artifact, family_id in CONSUMER_SOURCE_AUDIT_SUITES:
        source = _read_text(repo_root, artifact)
        case_names = _consumer_case_names(artifact, source)
        if not case_names:
            raise LedgerValidationError(f"{artifact} contains no source-audit cases")
        for case_name in case_names:
            case_digest = _stable_digest(artifact.as_posix(), case_name)
            if case_name not in STRUCTURAL_CONSUMER_CASES:
                retained_analyzer_ids: tuple[str, ...] = ()
                if case_name in MIXED_CONSUMER_CASES:
                    retained_classification = (
                        "negative_analyzer"
                        if case_name in NEGATIVE_CONSUMER_CASES
                        else "structural_analyzer"
                    )
                    retained_analyzer_ids = (
                        _consumer_analyzer_id(artifact, retained_classification),
                    )
                obligations.append(
                    _planned_runtime_obligation(
                        obligation_id=(f"consumer-source:{participant}:{case_digest}"),
                        source_kind="consumer_source_audit",
                        artifact=artifact,
                        locator=f"case={case_name}",
                        participant=participant,
                        mapping_origin="legacy_consumer_source_assertion",
                        family_id=family_id,
                        evidence_role="consumer",
                        retained_analyzer_ids=retained_analyzer_ids,
                    )
                )
            else:
                classification = (
                    "negative_analyzer"
                    if case_name in NEGATIVE_CONSUMER_CASES
                    else "structural_analyzer"
                )
                obligations.append(
                    _analyzer_obligation(
                        obligation_id=f"consumer-source:{participant}:{case_digest}",
                        source_kind="consumer_source_audit",
                        artifact=artifact,
                        locator=f"case={case_name}",
                        participant=participant,
                        mapping_origin="consumer_source_audit",
                        classification=classification,
                        analyzer_id=_consumer_analyzer_id(artifact, classification),
                    )
                )
    return obligations


def discover_current_obligations(repo_root: Path) -> tuple[dict[str, Any], ...]:
    """Discover every Phase 0 evidence obligation from the live tracked sources.

    Returns a stable-ID-sorted tuple with exactly one row per source occurrence.
    Raises ``LedgerValidationError`` when a source is malformed or discovery
    produces duplicate IDs.
    """

    root = repo_root.resolve()
    obligations = (
        _parity_obligations(root)
        + _runtime_registry_obligations(root)
        + _scan_run_obligations(root)
        + _display_content_audit_obligations(root)
        + _user_settings_source_audit_obligations(root)
        + _consumer_source_audit_obligations(root)
        + [_policy_exception_obligation(root)]
    )
    counts = Counter(entry["id"] for entry in obligations)
    duplicates = sorted(
        obligation_id for obligation_id, count in counts.items() if count > 1
    )
    if duplicates:
        raise LedgerValidationError(
            f"discovered duplicate obligations: {', '.join(duplicates)}"
        )
    return tuple(sorted(obligations, key=lambda entry: entry["id"]))


def _analyzer_catalog(repo_root: Path) -> list[dict[str, Any]]:
    """Return the deterministic named-analyzer catalog used by ledger rows."""

    catalog = [dict(item) for item in BASE_ANALYZER_CATALOG]
    for participant, artifact, _negative, _runtime in DISPLAY_AUDIT_SPECS:
        catalog.append(
            {
                "id": f"display-content-ownership-{participant}",
                "evidenceKind": "negative",
                "paths": [artifact.as_posix()],
                "blockingWorkflow": WORKFLOW_BLOCKING_OWNERS[participant],
            }
        )
    for participant, artifact, _family_id in CONSUMER_SOURCE_AUDIT_SUITES:
        case_names = _consumer_case_names(artifact, _read_text(repo_root, artifact))
        analyzer_kinds: set[str] = set()
        for case_name in case_names:
            if (
                case_name in STRUCTURAL_CONSUMER_CASES
                or case_name in MIXED_CONSUMER_CASES
            ):
                analyzer_kinds.add(
                    "negative" if case_name in NEGATIVE_CONSUMER_CASES else "structural"
                )
        for analyzer_kind in sorted(analyzer_kinds):
            classification = f"{analyzer_kind}_analyzer"
            catalog.append(
                {
                    "id": _consumer_analyzer_id(artifact, classification),
                    "evidenceKind": analyzer_kind,
                    "paths": [artifact.as_posix()],
                    "blockingWorkflow": WORKFLOW_BLOCKING_OWNERS[participant],
                }
            )
    return sorted(catalog, key=lambda item: item["id"])


def _policy_exception_catalog() -> list[dict[str, Any]]:
    """Return documented policy exceptions that may classify ledger rows."""

    return [
        {
            "id": RESOURCE_EXCEPTION_ID,
            "participant": "cxx",
            "document": RESOURCE_EXCEPTION_POLICY.as_posix(),
            "rationale": (
                "classic-resource-core has no dedicated CXX bridge; C++ reaches "
                "its behavior transitively through classic-file-io-core."
            ),
        }
    ]


def _validate_catalog_paths(
    repo_root: Path, analyzers: Sequence[Mapping[str, Any]]
) -> None:
    """Require every analyzer artifact and blocking workflow marker to exist.

    Returns ``None`` on success. Raises ``LedgerValidationError`` when a named
    analyzer points at missing source or cannot be found in its claimed workflow
    command.
    """

    for analyzer in analyzers:
        paths = analyzer.get("paths")
        if not isinstance(paths, list) or not paths:
            raise LedgerValidationError(
                f"analyzer {analyzer.get('id')!r} must declare paths"
            )
        missing = [
            path
            for path in paths
            if not isinstance(path, str) or not (repo_root / path).exists()
        ]
        if missing:
            raise LedgerValidationError(
                f"analyzer {analyzer.get('id')!r} has missing paths: {missing}"
            )
        workflow = analyzer.get("blockingWorkflow")
        if isinstance(workflow, Mapping):
            workflow_path = repo_root / workflow["path"]
            command_marker = workflow["commandMarker"]
            if not workflow_path.is_file():
                raise LedgerValidationError(
                    f"analyzer {analyzer.get('id')!r} has missing blocking workflow "
                    f"{workflow['path']}"
                )
            workflow_source = workflow_path.read_text(encoding="utf-8")
            if command_marker not in workflow_source:
                raise LedgerValidationError(
                    f"analyzer {analyzer.get('id')!r} blocking workflow lacks "
                    f"command marker {command_marker!r}"
                )


def generate_ledger(repo_root: Path) -> dict[str, Any]:
    """Generate the deterministic, diagnostic-only Phase 0 migration ledger.

    Returns the complete serializable ledger envelope. Raises
    ``LedgerValidationError`` when live sources, catalogs, or generated rows do
    not satisfy the ledger contract.
    """

    root = repo_root.resolve()
    obligations = discover_current_obligations(root)
    analyzers = _analyzer_catalog(root)
    policy_exceptions = _policy_exception_catalog()
    _validate_catalog_paths(root, analyzers)
    by_kind = Counter(entry["sourceKind"] for entry in obligations)
    by_classification = Counter(entry["classification"] for entry in obligations)
    by_participant = Counter(entry["participant"] for entry in obligations)
    ledger: dict[str, Any] = {
        "schemaVersion": 1,
        "diagnosticOnly": True,
        "purpose": (
            "Classify current evidence migration targets without granting compliance "
            "or replacing any blocking check."
        ),
        "shadowTargetPolicy": (
            "A shadow runtime target may name its planned family while scenario and "
            "observation IDs remain null. Only executed receipts may justify a later state."
        ),
        "sourceSummary": {
            "total": len(obligations),
            "byKind": dict(sorted(by_kind.items())),
            "byClassification": dict(sorted(by_classification.items())),
            "byParticipant": dict(sorted(by_participant.items())),
        },
        "analyzers": analyzers,
        "policyExceptions": policy_exceptions,
        "obligations": list(obligations),
    }
    validate_ledger_entries(ledger, obligations)
    return ledger


def render_ledger_markdown(ledger: Mapping[str, Any]) -> str:
    """Render a concise human-readable summary of the full JSON ledger.

    Returns deterministic Markdown ending in a newline. The supplied mapping is
    expected to be a validated generated ledger.
    """

    summary = ledger["sourceSummary"]
    lines = [
        "# Evidence Migration Ledger",
        "",
        (
            "> **Diagnostic only.** This ledger classifies migration targets and does "
            "**not** grant compliance, runtime coverage, or permission to remove a gate."
        ),
        "",
        f"- Obligations: **{summary['total']:,}**",
        f"- Named retained analyzers: **{len(ledger['analyzers'])}**",
        f"- Documented policy exceptions: **{len(ledger['policyExceptions'])}**",
        "",
        "## Target dispositions",
        "",
        "| Classification | Obligations |",
        "| --- | ---: |",
    ]
    for classification, count in summary["byClassification"].items():
        lines.append(f"| `{classification}` | {count:,} |")
    lines.extend(
        (
            "",
            "## Current evidence sources",
            "",
            "| Source kind | Occurrences |",
            "| --- | ---: |",
        )
    )
    for source_kind, count in summary["byKind"].items():
        lines.append(f"| `{source_kind}` | {count:,} |")
    lines.extend(("", "## Retained analyzers", ""))
    for analyzer in ledger["analyzers"]:
        lines.append(
            f"- `{analyzer['id']}` ({analyzer['evidenceKind']}): "
            + ", ".join(f"`{path}`" for path in analyzer["paths"])
        )
    lines.extend(("", "## Policy exceptions", ""))
    for exception in ledger["policyExceptions"]:
        lines.append(
            f"- `{exception['id']}` ({exception['participant']}): "
            f"{exception['rationale']} See `{exception['document']}`."
        )
    lines.extend(
        (
            "",
            (
                "The JSON artifact is the complete occurrence ledger. Runtime entries "
                "remain `shadow` until executed receipts independently justify a later "
                "ratchet state; ledger text alone can never do so."
            ),
            "",
        )
    )
    return "\n".join(lines)


def write_ledger_artifacts(
    repo_root: Path, ledger_path: Path, summary_path: Path
) -> tuple[Path, Path]:
    """Generate and write the tracked JSON ledger and Markdown summary.

    Returns the resolved ledger and summary paths supplied by the caller. Raises
    ``LedgerValidationError`` for invalid live evidence and propagates filesystem
    errors if either tracked artifact cannot be written.
    """

    ledger = generate_ledger(repo_root)
    markdown = render_ledger_markdown(ledger)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(
        json.dumps(ledger, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    summary_path.write_text(markdown, encoding="utf-8")
    return ledger_path, summary_path


def check_ledger_artifacts(
    repo_root: Path, ledger_path: Path, summary_path: Path
) -> None:
    """Validate tracked artifacts against live discovery and deterministic output.

    Returns ``None`` on success. Raises ``LedgerValidationError`` when an
    artifact is missing, malformed, stale, or incomplete relative to live
    evidence discovery.
    """

    try:
        tracked = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LedgerValidationError(
            f"cannot read tracked ledger {ledger_path}: {error}"
        ) from error
    if not isinstance(tracked, dict):
        raise LedgerValidationError(
            f"tracked ledger {ledger_path} must be a JSON object"
        )
    expected = generate_ledger(repo_root)
    validate_ledger_entries(tracked, expected["obligations"])
    if tracked != expected:
        raise LedgerValidationError(
            "tracked ledger metadata differs from deterministic generation"
        )
    expected_summary = render_ledger_markdown(expected)
    try:
        tracked_summary = summary_path.read_text(encoding="utf-8")
    except OSError as error:
        raise LedgerValidationError(
            f"cannot read tracked ledger summary {summary_path}: {error}"
        ) from error
    if tracked_summary != expected_summary:
        raise LedgerValidationError(
            "tracked ledger Markdown summary differs from deterministic generation"
        )


def main(argv: Sequence[str] | None = None) -> int:
    """Check or refresh the tracked diagnostic migration-ledger artifacts.

    Returns a process-style status code: zero for success and one for a ledger
    validation failure. Argument-parser errors retain argparse's normal exit
    behavior.
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--ledger",
        type=Path,
        default=DEFAULT_LEDGER_PATH,
        help="Tracked JSON ledger path, relative to the repository root.",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=DEFAULT_SUMMARY_PATH,
        help="Tracked Markdown summary path, relative to the repository root.",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Regenerate the tracked ledger and summary from current evidence.",
    )
    arguments = parser.parse_args(argv)
    repo_root = arguments.repo_root.resolve()
    ledger_path = (
        arguments.ledger
        if arguments.ledger.is_absolute()
        else repo_root / arguments.ledger
    )
    summary_path = (
        arguments.summary
        if arguments.summary.is_absolute()
        else repo_root / arguments.summary
    )
    try:
        if arguments.update:
            write_ledger_artifacts(repo_root, ledger_path, summary_path)
            print(f"Updated diagnostic migration ledger: {ledger_path}")
        else:
            check_ledger_artifacts(repo_root, ledger_path, summary_path)
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            print(
                "Diagnostic migration ledger is complete: "
                f"{ledger['sourceSummary']['total']} obligations."
            )
    except LedgerValidationError as error:
        print(f"Evidence migration ledger validation failed: {error}", file=sys.stderr)
        return 1
    return 0


def validate_ledger_entries(
    ledger: Mapping[str, Any], discovered: Sequence[Mapping[str, Any]]
) -> None:
    """Validate exact obligation-ID coverage against a discovered inventory.

    Returns ``None`` when the diagnostic envelope, catalogs, row dispositions,
    source metadata, and occurrence sets agree exactly. Raises
    ``LedgerValidationError`` for every schema, classification, or drift error.
    """

    if ledger.get("schemaVersion") != 1:
        raise LedgerValidationError("ledger schemaVersion must be 1")
    if ledger.get("diagnosticOnly") is not True:
        raise LedgerValidationError("ledger diagnosticOnly must be true")
    forbidden_envelope_fields = sorted(
        field
        for field in ("complianceStatus", "coverage", "receipts")
        if field in ledger
    )
    if forbidden_envelope_fields:
        raise LedgerValidationError(
            "diagnostic ledger cannot contain coverage-granting fields: "
            f"{', '.join(forbidden_envelope_fields)}"
        )
    analyzer_kinds = _analyzer_kinds(ledger)
    policy_exception_ids = _catalog_ids(ledger, "policyExceptions")
    entries = ledger.get("obligations")
    if not isinstance(entries, list):
        raise LedgerValidationError("ledger obligations must be a list")

    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise LedgerValidationError(f"ledger obligation {index} must be an object")
        _validate_obligation_entry(
            entry,
            index=index,
            analyzer_kinds=analyzer_kinds,
            policy_exception_ids=policy_exception_ids,
        )

    ledger_ids: list[str] = [entry["id"] for entry in entries]
    discovered_ids: list[str] = []
    for index, entry in enumerate(discovered):
        if not isinstance(entry, Mapping):
            raise LedgerValidationError(
                f"discovered obligation {index} must be an object"
            )
        obligation_id = entry.get("id")
        if not isinstance(obligation_id, str) or not obligation_id:
            raise LedgerValidationError(
                f"discovered obligation {index} has no stable id"
            )
        discovered_ids.append(obligation_id)
    discovered_duplicates = sorted(
        str(obligation_id)
        for obligation_id, count in Counter(discovered_ids).items()
        if count > 1
    )
    if discovered_duplicates:
        raise LedgerValidationError(
            "discovered duplicate obligations: " + ", ".join(discovered_duplicates)
        )
    duplicate_ids = sorted(
        str(obligation_id)
        for obligation_id, count in Counter(ledger_ids).items()
        if count > 1
    )
    if duplicate_ids:
        raise LedgerValidationError(
            f"ledger contains duplicate obligations: {', '.join(duplicate_ids)}"
        )

    missing = sorted(set(discovered_ids) - set(ledger_ids))
    unexpected = sorted(set(ledger_ids) - set(discovered_ids))
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(
                f"missing obligations: {', '.join(str(item) for item in missing)}"
            )
        if unexpected:
            details.append(
                f"unexpected obligations: {', '.join(str(item) for item in unexpected)}"
            )
        raise LedgerValidationError("; ".join(details))

    ledger_by_id = {entry["id"]: entry for entry in entries}
    discovered_by_id = {entry["id"]: entry for entry in discovered}
    stale = sorted(
        str(obligation_id)
        for obligation_id in discovered_by_id
        if ledger_by_id[obligation_id] != discovered_by_id[obligation_id]
    )
    if stale:
        raise LedgerValidationError(f"stale obligation entries: {', '.join(stale)}")


if __name__ == "__main__":
    raise SystemExit(main())
