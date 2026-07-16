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


def test_manifest_is_machine_readable_json() -> None:
    """The fixture manifest remains consumable by every language runner."""

    manifest_path = (
        REPO_ROOT / "tests" / "fixtures" / "crash_log_scan_run" / "manifest.json"
    )

    parsed = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert parsed["schemaVersion"] == 1
