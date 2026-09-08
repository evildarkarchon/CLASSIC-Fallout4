"""Loose-file facts retain every category and read-only filesystem postconditions."""

from collections.abc import Mapping
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy
from .file_operations import _files
from .scan_game import _directories


def _observed(observation: Mapping[str, Any]) -> bool:
    """Require complete sorted native results and unchanged files/empty directories."""
    if set(observation) != {
        "beforeFiles",
        "beforeDirectories",
        "issues",
        "files",
        "directories",
    }:
        return False
    if (
        not _files(observation["files"])
        or not _directories(observation["directories"])
        or observation["beforeFiles"] != observation["files"]
        or observation["beforeDirectories"] != observation["directories"]
    ):
        return False
    issues = observation["issues"]
    return (
        isinstance(issues, Mapping)
        and set(issues)
        == {"animation", "formats", "sounds", "scripts", "previs", "dds"}
        and all(
            isinstance(values, list)
            and all(isinstance(value, str) for value in values)
            and values == sorted(set(values))
            for values in issues.values()
        )
    )


UNPACKED_SCAN_COVERAGE_POLICY = FamilyCoveragePolicy(
    "unpacked-scan",
    (
        CoveragePredicate(
            "unpacked-files",
            "unpacked-scan.scan",
            "unpacked-scan.scan",
            "unpacked-issues",
            ("UnpackedScanner", "UnpackedIssues", "scan_directory"),
            _observed,
            runtime_operations=(
                None,
                "__init__",
                "scan_directory",
                "scan_unpacked_files",
                "scanUnpackedFiles",
                "has_issues",
                "total_count",
            ),
        ),
    ),
)
