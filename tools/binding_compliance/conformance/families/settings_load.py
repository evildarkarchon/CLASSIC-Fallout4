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
    "invalidate",
    "clear_cache",
    "cache_size",
    "cache_keys",
    "cache_stats",
    "reset_cache_stats",
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
    "invalidate",
    "clear_cache",
    "cache_size",
    "cache_keys",
    "cache_stats",
    "reset_cache_stats",
    "invalidateSettings",
    "clearSettingsCache",
    "settingsCacheSize",
    "settingsCacheKeys",
    "getSettingsCacheStats",
    "resetSettingsCacheStats",
    "settings_invalidate",
    "settings_clear_cache",
    "settings_cache_size",
    "settings_cache_keys",
    "settings_cache_stats",
    "settings_reset_cache_stats",
    "settings_cache_clear",
    "reset_settings_cache_stats",
    "yaml_ops_clear_cache",
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
            "cacheState",
        }:
            return False
        state = result["cacheState"]
        if not isinstance(result["cached"], list) or not all(
            type(item) is bool for item in result["cached"]
        ):
            return False
        if not isinstance(state, dict) or set(state) != {
            "keys",
            "size",
            "invalidated",
            "invalidatedAgain",
            "afterInvalidate",
            "stats",
            "resetStats",
        }:
            return False
        if (
            not isinstance(state["keys"], list)
            or not all(isinstance(key, str) for key in state["keys"])
            or type(state["size"]) is not int
            or state["size"] != len(state["keys"])
            or state["afterInvalidate"] != 0
        ):
            return False
        if state["invalidated"] != result["cached"] or state["invalidatedAgain"] != [
            False
        ] * len(result["cached"]):
            return False
        for field in ("stats", "resetStats"):
            stats = state[field]
            if (
                not isinstance(stats, dict)
                or set(stats) != {"hits", "misses", "hitRateZero", "size", "bounded"}
                or stats["bounded"] is not True
                or any(
                    type(stats[k]) is not int or stats[k] < 0
                    for k in ("hits", "misses", "size")
                )
                or type(stats["hitRateZero"]) is not bool
            ):
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
    """Credit executed loaders and cache lifecycle operations, not YAML class methods."""
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


YAML_SYMBOLS = (
    "YamlOperations",
    "new",
    "parse_yaml",
    "dump_yaml",
    "load_yaml_file",
    "save_yaml_file",
    "get_setting",
    "get_string_value",
    "get_vec_value",
    "get_hashmap_value",
    "set_setting",
    "yaml_cache_stats",
    "YamlCacheStats",
)
YAML_OPERATIONS = (
    None,
    "__init__",
    "parse_yaml",
    "dump_yaml",
    "load_yaml_file",
    "save_yaml_file",
    "get_setting",
    "get_string_value",
    "get_vec_value",
    "get_hashmap_value",
    "set_setting",
    "clear_cache",
    "get_cache_stats",
    "yaml_ops_new",
    "yaml_ops_parse",
    "yaml_ops_dump",
    "yaml_ops_load_file",
    "yaml_ops_save_file",
    "yaml_ops_get_setting_value",
    "yaml_ops_get_string",
    "yaml_ops_get_vec",
    "yaml_ops_set_string_setting",
    "yaml_ops_set_integer_setting",
    "yaml_ops_set_bool_setting",
    "yaml_ops_set_vec_setting",
    "yaml_ops_has_document",
    "yaml_ops_cache_size",
    "yaml_ops_cache_stats",
    "yamlParse",
    "yamlStringify",
    "yamlLoadFile",
    "yamlSaveFile",
    "yamlGetValue",
    "yamlGetStringValue",
    "yamlGetVecValue",
    "yamlGetHashmapValue",
    "yamlSetSetting",
)


def _yaml_observed(value: Mapping[str, Any]) -> bool:
    """Require typed values, actual saved bytes and a complete cache transition."""
    if set(value) != {"before", "after", "persisted", "files", "cache"}:
        return False
    before, after, persisted, files, cache = (
        value[key] for key in ("before", "after", "persisted", "files", "cache")
    )
    return (
        isinstance(before, dict)
        and set(before) == {"name", "missing", "items", "mapping"}
        and isinstance(before["name"], str)
        and isinstance(before["missing"], str)
        and isinstance(before["items"], list)
        and all(isinstance(item, str) for item in before["items"])
        and isinstance(before["mapping"], dict)
        and all(isinstance(item, str) for item in before["mapping"].values())
        and all(
            isinstance(item, dict)
            and set(item) == {"name", "ready", "size", "values"}
            and isinstance(item["name"], str)
            and type(item["ready"]) is bool
            and type(item["size"]) is int
            and isinstance(item["values"], list)
            and all(isinstance(entry, str) for entry in item["values"])
            for item in (after, persisted)
        )
        and isinstance(files, dict)
        and set(files) == {"saved.yaml"}
        and isinstance(files["saved.yaml"], str)
        and isinstance(cache, dict)
        and set(cache) == {"hits", "misses", "size", "afterClear"}
        and all(type(entry) is int and entry >= 0 for entry in cache.values())
    )


def validate_settings_yaml_pack(
    document: Mapping[str, Any], root: Path
) -> tuple[Path, ...]:
    """Validate input-only YAML fixtures independently of authored observations."""
    fixture_root = (root / document["fixtureRoot"]).resolve()
    paths = []
    for case in document["scenarios"]:
        reference = case["input"].get("fixtureRef")
        if (
            case["action"] != "settings-yaml.execute"
            or case["input"] != {"fixtureRef": reference}
            or case["fixtureRefs"] != [reference]
        ):
            raise ValueError("YAML scenario must declare its sole input fixture")
        path = (fixture_root / document["fixtures"][reference]).resolve()
        if not path.is_relative_to(fixture_root):
            raise ValueError("YAML fixture escapes root")
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if (
            set(fixture) != {"kind", "content", "updates", "updateOrder"}
            or fixture["kind"] != "yaml"
            or not isinstance(fixture["content"], str)
            or not _yaml_observed(case["expected"])
        ):
            raise ValueError("malformed YAML fixture or observation")
        updates = fixture["updates"]
        if (
            not isinstance(updates, dict)
            or set(updates) != {"name", "ready", "size", "values"}
            or not isinstance(updates["name"], str)
            or type(updates["ready"]) is not bool
            or type(updates["size"]) is not int
            or not isinstance(updates["values"], list)
            or not all(isinstance(item, str) for item in updates["values"])
        ):
            raise ValueError("malformed YAML typed updates")
        if fixture["updateOrder"] != ["name", "ready", "size", "values"]:
            raise ValueError("YAML updates require explicit common order")
        paths.append(path)
    return tuple(paths)


def settings_yaml_coverage_policy() -> FamilyCoveragePolicy:
    """Credit only public methods executed by the typed YAML lifecycle adapters."""
    return FamilyCoveragePolicy(
        "settings-yaml",
        (
            CoveragePredicate(
                id="settings-yaml-observed",
                capability_id="settings-yaml.execute",
                action="settings-yaml.execute",
                observation_family="settings-yaml",
                rust_symbols=YAML_SYMBOLS,
                matches=_yaml_observed,
                runtime_operations=YAML_OPERATIONS,
            ),
        ),
    )


def _yaml_batch_observed(value: Mapping[str, Any]) -> bool:
    """Retain ordered entry arrays and typed batch/mapping results."""
    return (
        set(value) == {"before", "ordered", "vectors", "after"}
        and all(
            isinstance(value[key], dict)
            and all(isinstance(item, str) for item in value[key].values())
            for key in ("before", "after")
        )
        and isinstance(value["ordered"], list)
        and all(
            isinstance(pair, list)
            and len(pair) == 2
            and all(isinstance(item, str) for item in pair)
            for pair in value["ordered"]
        )
        and isinstance(value["vectors"], dict)
        and all(
            isinstance(items, list) and all(isinstance(item, str) for item in items)
            for items in value["vectors"].values()
        )
    )


def validate_settings_yaml_batch_pack(
    document: Mapping[str, Any], root: Path
) -> tuple[Path, ...]:
    """Reject malformed or expectation-bearing batch YAML fixtures."""
    fixture_root = (root / document["fixtureRoot"]).resolve()
    paths = []
    for case in document["scenarios"]:
        reference = case["input"].get("fixtureRef")
        if (
            case["action"] != "settings-yaml-batch.execute"
            or case["input"] != {"fixtureRef": reference}
            or case["fixtureRefs"] != [reference]
        ):
            raise ValueError("YAML batch fixture must be solely declared")
        path = (fixture_root / document["fixtures"][reference]).resolve()
        if not path.is_relative_to(fixture_root):
            raise ValueError("YAML batch fixture escapes root")
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if (
            set(fixture) != {"kind", "content", "keys", "updates"}
            or fixture["kind"] != "yaml-batch"
            or not isinstance(fixture["content"], str)
            or not isinstance(fixture["keys"], list)
            or not all(isinstance(key, str) for key in fixture["keys"])
            or not isinstance(fixture["updates"], dict)
            or not all(isinstance(value, str) for value in fixture["updates"].values())
            or not _yaml_batch_observed(case["expected"])
        ):
            raise ValueError("malformed YAML batch fixture or observation")
        paths.append(path)
    return tuple(paths)


def settings_yaml_batch_coverage_policy() -> FamilyCoveragePolicy:
    """Credit only the batch and ordered-map public operations actually invoked."""
    symbols = (
        "get_settings_batch",
        "set_settings_batch",
        "get_indexmap_value",
        "get_hashmap_vec_value",
    )
    return FamilyCoveragePolicy(
        "settings-yaml-batch",
        (
            CoveragePredicate(
                id="settings-yaml-batch-observed",
                capability_id="settings-yaml-batch.execute",
                action="settings-yaml-batch.execute",
                observation_family="settings-yaml-batch",
                rust_symbols=symbols,
                matches=_yaml_batch_observed,
                runtime_operations=(
                    None,
                    "yamlGetSettingsBatch",
                    "yamlSetSettingsBatch",
                    "yamlGetIndexmapValue",
                    "yamlGetHashmapVecValue",
                ),
            ),
        ),
    )
