#!/usr/bin/env python3
"""Prepare one fresh input-only semantic family plan for native CXX."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_REPO_ROOT = SCRIPT_PATH.parents[4]
sys.path.insert(0, str(DEFAULT_REPO_ROOT / "tools" / "binding_compliance"))

from conformance.packs import (
    MaterializationError,
    MaterializedRun,
    PackValidationError,
    load_and_validate_pack,
    materialize_run_plan,
)

PACK_RELATIVE_PATH = Path("tests/conformance/packs/crash_log_scan_run/v1.json")
DEFAULT_ARTIFACT_ROOT = Path("tools/binding_compliance/artifacts")
SUPPORTED_COMPILERS = ("msvc", "clang-cl")
SUPPORTED_FAMILIES = ("crash-log-scan-run", "user-settings")


def _cxx_source_paths(
    repo_root: Path, family: str = "crash-log-scan-run"
) -> tuple[Path, ...]:
    """Return current native runner and core inputs bound into source identity."""

    paths = (
        SCRIPT_PATH,
        repo_root
        / "tools"
        / "binding_compliance"
        / "conformance"
        / "adapters"
        / "run_cxx_conformance.ps1",
        repo_root / "classic-cli" / "CMakeLists.txt",
        repo_root / "classic-cli" / "build_cli.ps1",
        repo_root / "classic-cli" / "vcpkg.json",
        repo_root
        / "classic-cli"
        / "tests"
        / "conformance"
        / "classic_cxx_conformance.cpp",
        repo_root
        / "classic-cli"
        / "tests"
        / "conformance"
        / "classic_cxx_user_settings_conformance.h",
        repo_root / "cpp-bindings" / "classic-cpp-bridge" / "src" / "scanner.rs",
        repo_root
        / "cpp-bindings"
        / "classic-cpp-bridge"
        / "include"
        / "classic_cxx_bridge"
        / "scan_run_observer.h",
        repo_root / "business-logic" / "classic-scanlog-core" / "src" / "scan_run",
        repo_root / "business-logic" / "classic-scan-presentation" / "src",
    )
    if family == "user-settings":
        paths += (
            repo_root / "cpp-bindings" / "classic-cpp-bridge" / "src" / "settings.rs",
            repo_root / "business-logic" / "classic-user-settings-core" / "src",
        )
    return paths


def prepare_cxx_run(
    repo_root: Path,
    *,
    compiler: str,
    artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
    family: str = "crash-log-scan-run",
) -> MaterializedRun:
    """Materialize one CXX execution-instance plan in a fresh artifact directory.

    ``compiler`` selects the supported Windows/MSVC-ABI execution instance and
    ``family`` selects the trusted repository pack. The
    returned receipt path is reserved but intentionally absent until native C++
    traverses the generated bridge and publishes its observations.
    """

    if compiler not in SUPPORTED_COMPILERS:
        raise ValueError(
            "CXX conformance compiler must be one of: " + ", ".join(SUPPORTED_COMPILERS)
        )
    if family not in SUPPORTED_FAMILIES:
        raise ValueError("unsupported CXX conformance family: " + family)
    root = repo_root.resolve(strict=True)
    pack_path = (
        Path("tests/conformance/packs/user_settings/v1.json")
        if family == "user-settings"
        else PACK_RELATIVE_PATH
    )
    pack = load_and_validate_pack(root, root / pack_path)
    return materialize_run_plan(
        pack,
        participant_id="cxx",
        participant_role="semantic-adapter",
        execution_instance_id=f"windows-{compiler}",
        source_paths=_cxx_source_paths(root, family),
        artifact_root=artifact_root,
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the private preparation command used by the PowerShell launcher."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    parser.add_argument("--compiler", choices=SUPPORTED_COMPILERS, required=True)
    parser.add_argument(
        "--family", choices=SUPPORTED_FAMILIES, default="crash-log-scan-run"
    )
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Prepare the invocation and print absolute launcher-owned paths as JSON."""

    args = build_argument_parser().parse_args(argv)
    try:
        prepared = prepare_cxx_run(
            args.repo_root,
            compiler=args.compiler,
            artifact_root=args.artifact_root,
            family=args.family,
        )
        plan = prepared.document()
    except (OSError, MaterializationError, PackValidationError, ValueError) as error:
        print(f"CXX conformance preparation failed: {error}")
        return 1
    print(
        json.dumps(
            {
                "artifactDir": str(prepared.artifact_dir),
                "runPlanPath": str(prepared.run_plan_path),
                "receiptPath": str(prepared.receipt_path),
                "invocationId": plan["invocation"]["id"],
                "sourceIdentity": plan["invocation"]["sourceIdentity"],
                "executionInstanceId": plan["participant"]["executionInstanceId"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
