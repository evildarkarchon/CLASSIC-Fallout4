"""Tests for the shared Crash Log Scan Run contract manifest."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_ROOT = REPO_ROOT / "tools" / "binding_compliance"
sys.path.insert(0, str(TOOLS_ROOT))

from scan_run_contract import (  # type: ignore  # noqa: E402
    ManifestValidationError,
    _validate_forbidden_exports,
    load_manifest,
    validate_manifest,
)


def test_live_scan_run_contract_manifest_is_complete() -> None:
    """The repository manifest acknowledges every variant and scenario."""

    manifest = load_manifest(REPO_ROOT)

    validate_manifest(REPO_ROOT, manifest)


def test_missing_adapter_variant_acknowledgement_fails_closed() -> None:
    """Every supported adapter must explicitly acknowledge every variant."""

    manifest = copy.deepcopy(load_manifest(REPO_ROOT))
    manifest["adapters"]["node"]["acknowledgedVariants"].remove("event.log_finished")

    with pytest.raises(
        ManifestValidationError,
        match=r"node.*event\.log_finished",
    ):
        validate_manifest(REPO_ROOT, manifest)


def test_forbidden_legacy_export_fails_closed(tmp_path: Path) -> None:
    """A removed execution seam cannot reappear in a supported adapter."""

    source = tmp_path / "adapter.rs"
    source.write_text("pub fn process_logs_batch() {}\n", encoding="utf-8")

    with pytest.raises(
        ManifestValidationError,
        match=r"node.*process_logs_batch",
    ):
        _validate_forbidden_exports(
            tmp_path,
            {
                "node": [
                    {
                        "path": "adapter.rs",
                        "symbols": ["process_logs_batch"],
                    }
                ]
            },
        )


def test_forbidden_export_identifier_does_not_match_final_contract_name(
    tmp_path: Path,
) -> None:
    """A contracted prefix does not reject the surviving final entry point."""

    source = tmp_path / "adapter.rs"
    source.write_text("pub fn scan_run_contract_execute() {}\n", encoding="utf-8")

    _validate_forbidden_exports(
        tmp_path,
        {
            "cxx": [
                {
                    "path": "adapter.rs",
                    "symbols": ["scan_run_execute"],
                }
            ]
        },
    )


def test_missing_required_forbidden_export_surface_fails_closed(
    tmp_path: Path,
) -> None:
    """A misspelled or unexpectedly absent tracked contract file is not ignored."""

    with pytest.raises(
        ManifestValidationError,
        match=r"python.*missing\.pyi",
    ):
        _validate_forbidden_exports(
            tmp_path,
            {
                "python": [
                    {
                        "path": "missing.pyi",
                        "symbols": ["Orchestrator"],
                    }
                ]
            },
        )


def test_unregistered_rust_enum_variant_fails_closed(tmp_path: Path) -> None:
    """A new Rust contract variant cannot bypass the shared manifest."""

    manifest = copy.deepcopy(load_manifest(REPO_ROOT))
    source = tmp_path / "contract.rs"
    source.write_text(
        "pub enum Event { DiscoveryCompleted, AdapterForgottenVariant }\n",
        encoding="utf-8",
    )
    manifest["rustEnums"] = [
        {
            "category": "event",
            "path": str(source.relative_to(tmp_path)),
            "name": "Event",
        }
    ]

    with pytest.raises(
        ManifestValidationError,
        match="event.adapter_forgotten_variant",
    ):
        validate_manifest(tmp_path, manifest)


def test_missing_shared_log_failure_stage_fails_closed() -> None:
    """The shared failure result must exercise every typed per-log stage."""

    manifest = copy.deepcopy(load_manifest(REPO_ROOT))
    manifest["failureFixtures"]["logResult"]["failures"].pop()

    with pytest.raises(
        ManifestValidationError,
        match="unsolved_logs_finalization",
    ):
        validate_manifest(REPO_ROOT, manifest)


def test_missing_shared_infrastructure_stage_fails_closed() -> None:
    """The shared run-wide failures must exercise every infrastructure stage."""

    manifest = copy.deepcopy(load_manifest(REPO_ROOT))
    manifest["failureFixtures"]["infrastructureErrors"].pop()

    with pytest.raises(
        ManifestValidationError,
        match="internal_invariant",
    ):
        validate_manifest(REPO_ROOT, manifest)


def test_missing_reset_fixture_root_fails_closed() -> None:
    """Reset parity cannot survive after its shared fixture corpus is detached."""

    manifest = copy.deepcopy(load_manifest(REPO_ROOT))
    manifest.pop("fixtureRoot")

    with pytest.raises(ManifestValidationError, match="fixtureRoot"):
        validate_manifest(REPO_ROOT, manifest)


def test_missing_reset_fixture_fails_closed() -> None:
    """The shared reset outcomes cannot disappear while adapter evidence remains."""

    manifest = copy.deepcopy(load_manifest(REPO_ROOT))
    manifest["fixtures"].pop("installedYamlData")

    with pytest.raises(
        ManifestValidationError,
        match=r"fixtures\.installedYamlData",
    ):
        validate_manifest(REPO_ROOT, manifest)


def test_missing_reset_outcome_fails_closed() -> None:
    """Every stable reset error category remains owned by the shared fixture."""

    manifest = copy.deepcopy(load_manifest(REPO_ROOT))
    manifest["fixtures"]["installedYamlData"]["resetOutcomes"].pop(
        "replacementFailureCode"
    )

    with pytest.raises(
        ManifestValidationError,
        match=r"replacementFailureCode",
    ):
        validate_manifest(REPO_ROOT, manifest)


def test_missing_durability_unknown_reset_outcome_fails_closed() -> None:
    """The visible-but-unconfirmed replacement receipt remains a shared outcome."""

    manifest = copy.deepcopy(load_manifest(REPO_ROOT))
    manifest["fixtures"]["installedYamlData"]["resetOutcomes"].pop(
        "durabilityUnknownCode"
    )

    with pytest.raises(
        ManifestValidationError,
        match=r"durabilityUnknownCode",
    ):
        validate_manifest(REPO_ROOT, manifest)


def test_changed_reset_fixture_semantics_fail_closed() -> None:
    """Reset success retains its typed state, diagnostics, and durable outcome facts."""

    manifest = copy.deepcopy(load_manifest(REPO_ROOT))
    manifest["fixtures"]["installedYamlData"]["expectedResetToDefault"][
        "localIgnoreState"
    ] = "existing"

    with pytest.raises(
        ManifestValidationError,
        match=r"expectedResetToDefault\.localIgnoreState",
    ):
        validate_manifest(REPO_ROOT, manifest)


def test_missing_reset_scenario_fails_closed() -> None:
    """All supported adapters must retain executable Reset To Default evidence."""

    manifest = copy.deepcopy(load_manifest(REPO_ROOT))
    manifest["scenarios"].pop("reset_to_default_continuation")

    with pytest.raises(
        ManifestValidationError,
        match="reset_to_default_continuation",
    ):
        validate_manifest(REPO_ROOT, manifest)


def test_manifest_is_machine_readable_json() -> None:
    """The fixture manifest remains consumable by every language runner."""

    manifest_path = (
        REPO_ROOT / "tests" / "fixtures" / "crash_log_scan_run" / "manifest.json"
    )

    parsed = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert parsed["schemaVersion"] == 1
