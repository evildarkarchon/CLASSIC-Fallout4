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
    ]
    run.receipt_path.write_text(json.dumps(receipt))
    return pack, run, receipt
