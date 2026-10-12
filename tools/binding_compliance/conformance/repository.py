"""Aggregate authenticated family receipts against every tracked family."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .command import (
    ConformanceCommandError,
    _repository_path,
    _run_plan_family,
    build_conformance_report_from_receipts,
)
from .enforcement import enforcement_for_family
from .packs import discover_pack_paths, load_and_validate_pack


def discover_repository_receipts(repo_root: Path, directory: Path) -> tuple[Path, ...]:
    """Collect downloaded receipts without relocating or rewriting their plans.

    Artifact-name subdirectories preserve colliding participant filenames. Empty
    downloads, missing sibling plans, and paths escaping the checkout raise
    ``ConformanceCommandError``; central receipt validation still authenticates
    each plan and its source identity before any evidence can contribute.
    """
    root = repo_root.resolve()
    artifact_root = _repository_path(
        root, directory, label="receipt directory", must_exist=True
    )
    if not artifact_root.is_dir():
        raise ConformanceCommandError("receipt directory must be a directory")
    receipts = tuple(sorted(artifact_root.rglob("receipt.json")))
    if not receipts:
        raise ConformanceCommandError("receipt directory contains no receipts")
    for receipt in receipts:
        _repository_path(root, receipt, label="receipt path", must_exist=True)
        plan = _repository_path(
            root, receipt.parent / "run_plan.json", label="run plan", must_exist=True
        )
        if not receipt.is_file() or not plan.is_file():
            raise ConformanceCommandError("receipt and sibling run plan must be files")
    return receipts


def build_repository_report(
    repo_root: Path, receipt_paths: Sequence[Path]
) -> dict[str, Any]:
    """Require every tracked blocking family to pass its full applicability.

    Family validation authenticates current source and immutable plans before
    any receipt is counted, and each family report requires every applicable
    (participant, execution instance) from ``participants.json`` and the
    consumer obligation catalog. Missing families fail closed.
    Returns a failing report for incomplete proof and raises
    ``ConformanceCommandError`` for invalid catalogs or receipt inputs.
    """
    root = repo_root.resolve()
    try:
        families = [
            load_and_validate_pack(root, path).document()["familyId"]
            for path in discover_pack_paths(root)
        ]
        if not families or len(families) != len(set(families)):
            raise ValueError(
                "repository conformance requires a unique nonempty pack catalog"
            )
    except ValueError as error:
        raise ConformanceCommandError(str(error)) from error

    grouped: dict[str, list[Path]] = defaultdict(list)
    for path in receipt_paths:
        receipt = _repository_path(root, path, label="receipt path", must_exist=False)
        family = _run_plan_family(receipt.parent / "run_plan.json")
        if family not in families:
            raise ConformanceCommandError(f"receipt names untracked family: {family}")
        grouped[family].append(receipt)

    reports = [
        build_conformance_report_from_receipts(
            root,
            profile="full",
            participant_id=None,
            execution_instance_id=None,
            receipt_paths=grouped[family],
        )
        for family in sorted(grouped)
    ]
    missing = sorted(set(families) - grouped.keys())
    unpromoted = sorted(
        family for family in families if enforcement_for_family(family) != "blocking"
    )
    complete = not (missing or unpromoted) and all(
        report["repositoryComplete"] for report in reports
    )
    return {
        "schemaVersion": 1,
        "scope": {"kind": "full-repository"},
        "enforcement": "blocking",
        "result": "pass" if complete else "fail",
        "repositoryComplete": complete,
        "requiredFamilies": sorted(families),
        "missingFamilies": missing,
        "unpromotedFamilies": unpromoted,
        "families": reports,
    }
