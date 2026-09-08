"""BA2 facts require actual issue-vector values over preserved valid archive bytes."""

from collections.abc import Mapping
from functools import partial
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _observed(full: bool, observation: Mapping[str, Any]) -> bool:
    """Require every archive issue column and, where exposed, discovery/batch agreement."""
    if set(observation) != (
        {"issues", "bytes", "found", "batch"} if full else {"issues", "bytes"}
    ):
        return False
    issues = observation["issues"]
    if not isinstance(issues, Mapping) or set(issues) != {
        "dimensions",
        "formats",
        "sounds",
        "scripts",
    }:
        return False
    if not all(
        isinstance(values, list)
        and all(isinstance(value, str) and value for value in values)
        for values in issues.values()
    ):
        return False
    raw = observation["bytes"]
    if (
        not isinstance(raw, list)
        or len(raw) < 24
        or raw[:4] != [66, 84, 68, 88]
        or not all(type(value) is int and 0 <= value <= 255 for value in raw)
    ):
        return False
    return (
        not full
        or observation["found"] == ["fixture.ba2"]
        and observation["batch"] == [["fixture.ba2", issues]]
    )


BA2_SCAN_COVERAGE_POLICY = FamilyCoveragePolicy(
    "ba2-scan",
    (
        CoveragePredicate(
            "full-archive",
            "ba2-scan.full",
            "ba2-scan.full",
            "archive-issues",
            ("BA2Scanner", "BA2Issues", "scan_archives_batch"),
            partial(_observed, True),
            runtime_operations=(
                None,
                "__init__",
                "find_ba2_files",
                "scan_archive",
                "scan_archives_batch",
                "has_issues",
                "total_count",
                "scan_all_ba2_archives",
                "scanAllBa2Archives",
            ),
        ),
        CoveragePredicate(
            "bridge-archive",
            "ba2-scan.bridge",
            "ba2-scan.bridge",
            "archive-issues",
            ("scan_archive",),
            partial(_observed, False),
            runtime_operations=(
                "ba2_scan_archive_summary",
                "ba2_get_tex_dims_for_archive",
                "ba2_get_tex_frmt_for_archive",
                "ba2_get_snd_frmt_for_archive",
                "ba2_get_xse_files_for_archive",
            ),
        ),
    ),
)
