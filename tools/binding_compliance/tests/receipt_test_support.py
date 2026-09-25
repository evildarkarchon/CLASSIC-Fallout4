"""Shared isolated repository and synthetic receipt setup for domain tests."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from conformance.packs import (
    MaterializedRun,
    ValidatedPack,
    load_and_validate_pack,
    materialize_run_plan,
)


def copy_source_inventory(repo_root: Path, destination: Path) -> None:
    """Copy parity rows and the real source needed to corroborate structural dispositions.

    Native binaries and virtual environments are excluded. Tests still mutate
    their own copies, so source-spoof and future-export checks remain isolated.
    """
    files = {Path("Cargo.toml"), Path("cpp-bindings/classic-cpp-bridge/build.rs")}
    files.update(
        Path(f"docs/implementation/{binding}_api_parity/baseline/parity_contract.json")
        for binding in ("cxx", "node", "python")
    )
    files.update(
        Path("node-bindings/classic-node") / name
        for name in ("Cargo.toml", "index.d.ts", "src/lib.rs")
    )
    for base in ("python-bindings", "foundation"):
        for crate in (repo_root / base).glob("classic-*-py"):
            files.update(path.relative_to(repo_root) for path in crate.glob("*.pyi"))
            files.update(
                path.relative_to(repo_root) for path in (crate / "src").rglob("*.rs")
            )
    files.update(
        path.relative_to(repo_root)
        for path in (repo_root / "cpp-bindings/classic-cpp-bridge/src").rglob("*.rs")
    )
    for relative in sorted(files):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo_root / relative, target)


def prepare_receipt_case(
        repo_root: Path,
        tmp_path: Path,
        pack_path: Path,
        participant: str,
        *,
        runner_id: str,
) -> tuple[ValidatedPack, MaterializedRun, dict[str, Any]]:
    """Copy a pack into an isolated Git repository and write a complete receipt.

    The returned mutable receipt is synthetic input for central validation tests,
    not native execution evidence. Each call owns its repository and invocation;
    filesystem, Git, and pack-validation errors propagate to the calling test.
    """
    source_pack = load_and_validate_pack(repo_root, pack_path)
    (tmp_path / pack_path).parent.mkdir(parents=True)
    shutil.copyfile(repo_root / pack_path, tmp_path / pack_path)
    fixture_path = source_pack.fixture_root.relative_to(repo_root)
    shutil.copytree(source_pack.fixture_root, tmp_path / fixture_path)
    if any(
            capability.get("operationScoped", False)
            for capability in source_pack.document()["capabilities"]
    ):
        # Scoped plans derive participation from source inventories even in an
        # isolated repository; copying their bytes preserves the real selection.
        copy_source_inventory(repo_root, tmp_path)
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
    pack = load_and_validate_pack(tmp_path, pack_path)
    run = materialize_run_plan(
        pack,
        participant_id=participant,
        participant_role="semantic-adapter",
        execution_instance_id=participant,
        source_paths=(pack_path,),
    )
    plan = run.document()
    receipt = {
        key: plan[key]
        for key in (
            "schemaVersion",
            "familyId",
            "familyVersion",
            "expectationDigest",
            "invocation",
            "participant",
        )
    }
    receipt["runner"] = {
        "id": runner_id,
        "version": 1,
        "platform": "windows",
        "toolchain": participant,
    }
    # Synthetic receipts exercise the trusted central boundary; native runners
    # receive the input-only plan and never have these authored expectations.
    receipt["scenarios"] = [
        {
            "id": scenario["id"],
            "executionStatus": "completed",
            "capabilityIds": scenario["capabilityIds"],
            "observation": scenario["expected"],
            "failure": None,
        }
        for scenario in pack.document()["scenarios"]
        if scenario["id"] in {item["id"] for item in plan["scenarios"]}
    ]
    run.receipt_path.write_text(json.dumps(receipt))
    return pack, run, receipt
