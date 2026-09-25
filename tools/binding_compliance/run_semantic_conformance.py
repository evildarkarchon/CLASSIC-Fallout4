#!/usr/bin/env python3
"""Run one focused semantic family through the shared authenticated lifecycle."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from run_scan_run_conformance import (
    DEFAULT_ARTIFACT_ROOT,
    REPO_ROOT,
    ConformanceCommandError,
    PackValidationError,
    ParticipantCommand,
)
from run_scan_run_conformance import run_participant as run_prepared_participant

SUPPORTED_FAMILIES = (
    "markdown-rendering",
    "report-discovery",
    "windows-platform-paths",
    "file-generation",
    "mod-ini",
    "wrye-report",
    "log-collection",
    "crash-pattern",
    "formid-finding",
    "ba2-scan",
    "unpacked-scan",
    "hash-cache-controls",
    "crashgen-check",
    "dds-header",
    "yaml-file-values",
    "shared-performance",
    "log-parsing",
    "papyrus-monitor",
    "settings-load",
    "settings-yaml",
    "settings-validation",
    "settings-cached-docs",
    "version-registry-details",
    "xse-operations",
    "xse-folder",
    "installation-paths",
    "game-identity",
    "runtime-access",
    "file-fingerprint",
    "performance",
    "performance-timers",
    "message-logging",
    "update-rejection",
    "update-decisions",
    "update-services",
    "string-operations",
    "registry-operations",
    "registry-game",
    "registry-gui",
    "registry-context",
    "registry-keys",
    "game-version-parse",
    "game-version-distance",
    "game-version-order",
    "fallout4-identity",
    "fallout4-paths",
    "fallout4-metadata",
    "version-registry-values",
    "settings-yaml-batch",
    "registry-paths",
    "web-operations",
    "resource-operations",
    "version-operations",
    "version-extraction",
    "version-f4se",
    "version-pe",
    "version-pe-path",
    "crash-suspect",
    "crashgen-settings",
    "mod-guidance",
    "formid-lookup",
    "named-record",
    "plugin-evidence",
    "installed-yaml-data",
    "config-vocabulary",
    "scan-run-vocabulary",
    "config-operations",
    "yaml-source-values",
    "file-backups",
    "xse-plugin-validation",
    "path-backups",
    "game-integrity",
    "game-orchestration",
    "game-setup-intake",
    "yaml-update-operations",
    "file-operations",
    "database-operations",
    "version-registry",
    "scan-game",
    "path-operations",
    "path-normalization",
    "message-operations",
)

_COMMON_SOURCES = (
    REPO_ROOT / "tools/binding_compliance/platform_path_oracle.ps1",
    REPO_ROOT / "business-logic/classic-settings-core/src",
    REPO_ROOT / "business-logic/classic-xse-core/src",
    REPO_ROOT / "business-logic/classic-perf-core/src",
    REPO_ROOT / "business-logic/classic-registry-core/src",
    REPO_ROOT / "business-logic/classic-web-core/src",
    REPO_ROOT / "business-logic/classic-resource-core/src",
    REPO_ROOT / "business-logic/classic-version-core/src",
    REPO_ROOT / "business-logic/classic-update-core/src",
    Path(__file__).resolve(),
    REPO_ROOT / "tools/binding_compliance/run_scan_run_conformance.py",
    REPO_ROOT / "business-logic/classic-scanlog-core/src",
    REPO_ROOT / "business-logic/classic-scanlog-core/Cargo.toml",
    REPO_ROOT / "business-logic/classic-database-core/src",
    REPO_ROOT / "business-logic/classic-version-registry-core/src",
    REPO_ROOT / "CLASSIC Data/databases/CLASSIC Main.yaml",
    REPO_ROOT / "business-logic/classic-scangame-core/src",
    REPO_ROOT / "business-logic/classic-config-core/src",
    REPO_ROOT / "business-logic/classic-user-settings-core/src",
    REPO_ROOT / "business-logic/classic-durable-publication/src",
    REPO_ROOT / "foundation/classic-vocabulary/src",
    REPO_ROOT / "foundation/classic-shared-core/src",
    REPO_ROOT / "business-logic/classic-file-io-core/src",
    REPO_ROOT / "business-logic/classic-path-core/src",
    REPO_ROOT / "business-logic/classic-message-core/src",
)
PARTICIPANT_COMMANDS = {
    "rust": ParticipantCommand(
        arguments=(
            "cargo",
            "test",
            "-p",
            "classic-scanlog-core",
            "--test",
            "semantic_conformance",
            "--",
            "--nocapture",
        ),
        working_directory=REPO_ROOT,
        source_paths=(
            REPO_ROOT
            / "business-logic/classic-scanlog-core/tests/semantic_conformance.rs",
            REPO_ROOT
            / "business-logic/classic-scanlog-core/tests/semantic_conformance",
            *_COMMON_SOURCES,
        ),
    ),
    "node": ParticipantCommand(
        arguments=("bun", "run", "conformance:semantic"),
        working_directory=REPO_ROOT / "node-bindings/classic-node",
        source_paths=(
            REPO_ROOT
            / "node-bindings/classic-node/__test__/semantic_conformance_runner.ts",
            REPO_ROOT
            / "node-bindings/classic-node/__test__/installed_yaml_conformance.ts",
            REPO_ROOT / "node-bindings/classic-node/__test__/vocabulary_conformance.ts",
            REPO_ROOT
            / "node-bindings/classic-node/__test__/config_operations_conformance.ts",
            REPO_ROOT
            / "node-bindings/classic-node/__test__/config_yaml_values_conformance.ts",
            REPO_ROOT
            / "node-bindings/classic-node/__test__/yaml_source_values_conformance.ts",
            REPO_ROOT
            / "node-bindings/classic-node/__test__/file_backups_conformance.ts",
            REPO_ROOT
            / "node-bindings/classic-node/__test__/xse_plugin_validation_conformance.ts",
            REPO_ROOT
            / "node-bindings/classic-node/__test__/path_backups_conformance.ts",
            REPO_ROOT
            / "node-bindings/classic-node/__test__/game_integrity_conformance.ts",
            REPO_ROOT
            / "node-bindings/classic-node/__test__/game_orchestration_conformance.ts",
            REPO_ROOT
            / "node-bindings/classic-node/__test__/game_setup_intake_conformance.ts",
            REPO_ROOT
            / "node-bindings/classic-node/__test__/file_operations_conformance.ts",
            REPO_ROOT
            / "node-bindings/classic-node/__test__/path_message_conformance.ts",
            REPO_ROOT
            / "node-bindings/classic-node/__test__/database_operations_conformance.ts",
            REPO_ROOT
            / "node-bindings/classic-node/__test__/version_registry_conformance.ts",
            REPO_ROOT / "node-bindings/classic-node/__test__/scan_game_conformance.ts",
            REPO_ROOT / "node-bindings/classic-node/src",
            REPO_ROOT
            / "node-bindings/classic-node/__test__/windows_platform_paths_conformance.ts",
            REPO_ROOT
            / "node-bindings/classic-node/__test__/settings_load_conformance.ts",
            REPO_ROOT
            / "node-bindings/classic-node/__test__/xse_operations_conformance.ts",
            REPO_ROOT
            / "node-bindings/classic-node/__test__/shared_identity_conformance.ts",
            REPO_ROOT
            / "node-bindings/classic-node/__test__/yaml_file_values_conformance.ts",
            *(
                REPO_ROOT
                / "node-bindings/classic-node/__test__"
                / (module + "_conformance.ts")
                for module in (
                "file_fingerprint",
                "performance",
                "message_logging",
                "update_rejection",
                "update_decisions",
                "update_services",
                "shared_registry",
                "registry_accessors",
                "aux_operations",
                "version_extended",
                "version_values",
                "settings_extended",
                "installation_paths",
            )
            ),
            REPO_ROOT / "node-bindings/classic-node/package.json",
            *_COMMON_SOURCES,
        ),
    ),
    "python": ParticipantCommand(
        arguments=(
            "uv",
            "run",
            "--project",
            "python-bindings",
            "python",
            "python-bindings/tests/semantic_conformance_runner.py",
        ),
        working_directory=REPO_ROOT,
        source_paths=(
            REPO_ROOT / "python-bindings/tests/semantic_conformance_runner.py",
            REPO_ROOT / "python-bindings/tests/installed_yaml_conformance.py",
            REPO_ROOT / "python-bindings/tests/vocabulary_conformance.py",
            REPO_ROOT / "python-bindings/tests/config_operations_conformance.py",
            REPO_ROOT / "python-bindings/tests/config_yaml_values_conformance.py",
            REPO_ROOT / "python-bindings/tests/yaml_source_values_conformance.py",
            REPO_ROOT / "python-bindings/tests/xse_plugin_validation_conformance.py",
            REPO_ROOT / "python-bindings/tests/path_backups_conformance.py",
            REPO_ROOT / "python-bindings/tests/game_integrity_conformance.py",
            REPO_ROOT / "python-bindings/tests/game_orchestration_conformance.py",
            REPO_ROOT / "python-bindings/tests/game_setup_intake_conformance.py",
            REPO_ROOT / "python-bindings/tests/file_operations_conformance.py",
            REPO_ROOT / "python-bindings/tests/path_message_conformance.py",
            REPO_ROOT / "python-bindings/tests/database_operations_conformance.py",
            REPO_ROOT / "python-bindings/tests/version_registry_conformance.py",
            REPO_ROOT / "python-bindings/tests/scan_game_conformance.py",
            REPO_ROOT / "python-bindings/classic-file-io-py/src",
            REPO_ROOT / "python-bindings/classic-settings-py/src",
            REPO_ROOT / "python-bindings/tests/settings_load_conformance.py",
            REPO_ROOT / "python-bindings/classic-xse-py/src",
            REPO_ROOT / "python-bindings/tests/xse_operations_conformance.py",
            REPO_ROOT / "python-bindings/tests/shared_identity_conformance.py",
            REPO_ROOT / "python-bindings/tests/yaml_file_values_conformance.py",
            REPO_ROOT / "python-bindings/tests/shared_performance_conformance.py",
            *(
                REPO_ROOT / "python-bindings/tests" / (module + "_conformance.py")
                for module in (
                "file_fingerprint",
                "performance",
                "message_logging",
                "update_rejection",
                "update_decisions",
                "update_services",
                "shared_registry",
                "registry_accessors",
                "registry_keys",
                "aux_operations",
                "version_extended",
                "version_values",
                "settings_extended",
                "installation_paths",
            )
            ),
            *(
                REPO_ROOT / "python-bindings" / ("classic-" + owner + "-py/src")
                for owner in (
                "perf",
                "registry",
                "web",
                "resource",
                "version",
                "update",
            )
            ),
            REPO_ROOT / "python-bindings/classic-path-py/src",
            REPO_ROOT / "python-bindings/classic-message-py/src",
            REPO_ROOT / "foundation/classic-shared-py/src",
            REPO_ROOT / "python-bindings/classic-config-py/src",
            REPO_ROOT / "python-bindings/classic-scanlog-py/src",
            REPO_ROOT / "python-bindings/classic-database-py/src",
            REPO_ROOT / "python-bindings/classic-version-registry-py/src",
            REPO_ROOT / "python-bindings/classic-scangame-py/src",
            *_COMMON_SOURCES,
        ),
    ),
}


def run_participant(
        participant_id: str,
        *,
        family: str,
        artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
        timeout_seconds: int = 1_200,
) -> tuple[int, Path]:
    """Execute every scenario for one family and validate fresh typed receipts.

    Family input comes only from the authenticated run plan. Each invocation
    retains the shared launcher's bounded execution and failure diagnostics.
    Native CXX runs separately through the repository's approved CLI wrapper.
    """

    if family not in SUPPORTED_FAMILIES:
        raise ValueError("unsupported semantic conformance family: " + family)
    command = PARTICIPANT_COMMANDS[participant_id]
    if participant_id == "rust" and family in {
        "markdown-rendering",
        "report-discovery",
    }:
        test_name = (
            "markdown::tests::writes_markdown_conformance_receipt"
            if family == "markdown-rendering"
            else "files::tests::writes_report_discovery_conformance_receipt"
        )
        command = ParticipantCommand(
            arguments=(
                "pwsh",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "tools/enter_vs_dev_shell.ps1",
                "-WorkingDirectory",
                str(REPO_ROOT),
                "-Command",
                f"cargo test -p classic-cpp-bridge --lib {test_name} -- --exact --nocapture",
            ),
            working_directory=REPO_ROOT,
            source_paths=(
                *command.source_paths,
                REPO_ROOT / "cpp-bindings/classic-cpp-bridge/src",
                REPO_ROOT / "cpp-bindings/classic-cpp-bridge/Cargo.toml",
                REPO_ROOT / "cpp-bindings/classic-cpp-bridge/build.rs",
                REPO_ROOT / "tools/enter_vs_dev_shell.ps1",
            ),
        )
    return run_prepared_participant(
        participant_id,
        artifact_root=artifact_root,
        timeout_seconds=timeout_seconds,
        pack_path=REPO_ROOT
                  / "tests/conformance/packs"
                  / family.replace("-", "_")
                  / "v1.json",
        command=command,
    )


def main(argv: list[str] | None = None) -> int:
    """Launch one selected family/adapter and print its retained artifact path."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=SUPPORTED_FAMILIES, required=True)
    parser.add_argument(
        "--participant", choices=sorted(PARTICIPANT_COMMANDS), required=True
    )
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--timeout-seconds", type=int, default=1_200)
    args = parser.parse_args(argv)
    try:
        result, artifact_dir = run_participant(
            args.participant,
            family=args.family,
            artifact_root=args.artifact_root,
            timeout_seconds=args.timeout_seconds,
        )
    except (ConformanceCommandError, PackValidationError, ValueError) as error:
        print(f"Semantic conformance launch failed: {error}", file=sys.stderr)
        return 1
    print(artifact_dir)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
