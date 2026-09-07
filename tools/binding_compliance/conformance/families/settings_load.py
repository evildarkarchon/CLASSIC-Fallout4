"""Generic settings loading owns counts, attributed errors and cache effects."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy

SYMBOLS = (
    "load_settings_sync",
    "load_settings_async",
    "load_batch_sync",
    "load_batch_async",
    "is_cached",
)
OPERATIONS = (
    None,
    "load_settings_sync",
    "load_settings_async",
    "load_batch_sync",
    "load_batch_async",
    "is_cached",
    "loadSettingsSync",
    "loadSettingsAsync",
    "loadBatchSync",
    "loadBatchAsync",
    "isCached",
    "settings_load_sync",
    "settings_load_async_blocking",
    "settings_load_batch_sync",
    "settings_load_batch_async_blocking",
    "settings_is_cached",
)


def _relative(value: Any) -> bool:
    """Permit only portable, contained fixture paths before filesystem writes."""
    return (
        isinstance(value, str)
        and bool(value)
        and not any(char in value for char in "\\:")
        and all(part not in {"", ".", ".."} for part in value.split("/"))
    )


def _observed(value: Mapping[str, Any]) -> bool:
    """Require all loader outcomes, explicit cache effects and final input bytes."""
    if set(value) != {
        "sync",
        "async",
        "batchSync",
        "batchAsync",
        "files",
    } or not isinstance(value["files"], dict):
        return False
    if not all(
        _relative(path) and isinstance(content, str)
        for path, content in value["files"].items()
    ):
        return False
    for operation in ("sync", "async", "batchSync", "batchAsync"):
        result = value[operation]
        if not isinstance(result, dict) or set(result) != {
            "count",
            "error",
            "cached",
            "afterClear",
        }:
            return False
        error = result["error"]
        if error is None:
            if type(result["count"]) is not int or result["count"] < 0:
                return False
        elif not (
            result["count"] is None
            and isinstance(error, dict)
            and set(error) == {"kind", "path"}
            and error["kind"] in {"io", "yaml-parse"}
            and _relative(error["path"])
        ):
            return False
        if not isinstance(result["cached"], list) or not all(
            type(item) is bool for item in result["cached"]
        ):
            return False
        if (
            not isinstance(result["afterClear"], list)
            or len(result["afterClear"]) != len(result["cached"])
            or any(item is not False for item in result["afterClear"])
        ):
            return False
    return True


def validate_settings_load_pack(
    document: Mapping[str, Any], root: Path
) -> tuple[Path, ...]:
    """Validate input-only requests and authored observation structure independently."""
    fixture_root = (root / document["fixtureRoot"]).resolve()
    paths = []
    for case in document["scenarios"]:
        reference = case["input"].get("fixtureRef")
        if (
            case["action"] != "settings-load.execute"
            or case["input"] != {"fixtureRef": reference}
            or case["fixtureRefs"] != [reference]
        ):
            raise ValueError("settings scenario must declare its sole input fixture")
        path = (fixture_root / document["fixtures"][reference]).resolve()
        if not path.is_relative_to(fixture_root):
            raise ValueError("settings fixture escapes fixture root")
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(fixture, dict)
            or set(fixture) != {"files", "request"}
            or not isinstance(fixture["files"], dict)
        ):
            raise ValueError("malformed settings fixture")
        request = fixture["request"]
        if (
            not isinstance(request, dict)
            or set(request) != {"single", "batch"}
            or not _relative(request["single"])
            or not isinstance(request["batch"], list)
            or not all(_relative(item) for item in request["batch"])
        ):
            raise ValueError("settings request needs contained relative paths")
        if not all(
            _relative(path) and isinstance(content, str)
            for path, content in fixture["files"].items()
        ) or not _observed(case["expected"]):
            raise ValueError("settings files or observation malformed")
        paths.append(path)
    return tuple(paths)


def settings_load_coverage_policy() -> FamilyCoveragePolicy:
    """Credit the executed generic loaders and presence query, not YAML class methods."""
    return FamilyCoveragePolicy(
        "settings-load",
        (
            CoveragePredicate(
                id="settings-load-observed",
                capability_id="settings-load.execute",
                action="settings-load.execute",
                observation_family="settings-load",
                rust_symbols=SYMBOLS,
                matches=_observed,
                runtime_operations=OPERATIONS,
            ),
        ),
    )
