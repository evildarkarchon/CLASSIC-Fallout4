"""Actual empty-state cache controls; populated-state tests remain independent."""

from collections.abc import Mapping
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _observed(observation: Mapping[str, Any]) -> bool:
    """Require complete public zero-state statistics and independently returned sizes."""
    if set(observation) != {
        "initial",
        "initialSize",
        "afterReset",
        "afterClear",
        "finalSize",
    }:
        return False
    empty = {"hits": 0, "misses": 0, "hitRate": "0.000", "size": 0, "capacity": 1024}
    return (
        all(
            observation[key] == empty for key in ("initial", "afterReset", "afterClear")
        )
        and type(observation["initialSize"]) is int
        and observation["initialSize"] == 0
        and type(observation["finalSize"]) is int
        and observation["finalSize"] == 0
    )


HASH_CACHE_CONTROLS_COVERAGE_POLICY = FamilyCoveragePolicy(
    "hash-cache-controls",
    (
        CoveragePredicate(
            "empty-cache-controls",
            "hash-cache-controls.empty",
            "hash-cache-controls.empty",
            "cache-state",
            ("clear_cache", "cache_size", "cache_stats", "reset_cache_stats"),
            _observed,
            runtime_operations=(
                "hash_cache_clear",
                "hash_cache_size",
                "hash_cache_stats",
                "reset_hash_cache_stats",
            ),
        ),
    ),
)
