"""Facts for actual typed cache getters and complete read-only mod INI scans."""

from collections.abc import Mapping
from functools import partial
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy
from .file_operations import _files


def _observed(operation: str, observation: Mapping[str, Any]) -> bool:
    """Require exact file preservation and every projected native result field."""
    if (
        set(observation) != {"operation", "before", "result", "files"}
        or observation["operation"] != operation
        or not _files(observation["files"])
        or observation["before"] != observation["files"]
    ):
        return False
    value = observation["result"]
    if not isinstance(value, Mapping):
        return False
    if operation == "cache":
        return (
            set(value)
            == {
                "names",
                "contains",
                "path",
                "name",
                "enabled",
                "count",
                "scale",
                "hasName",
                "missing",
                "duplicates",
            }
            and isinstance(value["names"], list)
            and value["names"] == sorted(set(value["names"]))
            and value["contains"] is ("sample.ini" in value["names"])
            and (value["path"] is not None) == value["contains"]
            and value["hasName"] is (value["name"] is not None)
            and value["missing"] is None
            and isinstance(value["duplicates"], Mapping)
            and (value["enabled"] is None or type(value["enabled"]) is bool)
            and (value["count"] is None or type(value["count"]) is int)
            and (value["scale"] is None or isinstance(value["scale"], str))
        )
    return (
        set(value) == {"message", "issues", "vsync", "duplicates"}
        and isinstance(value["message"], str)
        and all(
            isinstance(value[key], list) for key in ("issues", "vsync", "duplicates")
        )
        and all(
            isinstance(entry, Mapping)
            and set(entry) == {"path", "setting"}
            and all(isinstance(item, str) for item in entry.values())
            for entry in value["vsync"]
        )
    )


def _vsync(observation: Mapping[str, Any]) -> bool:
    """Only a nonempty native VSync list proves construction of its entry carrier."""
    return _observed("scan", observation) and bool(observation["result"]["vsync"])


def _duplicates(observation: Mapping[str, Any]) -> bool:
    """Require published groups/maps to agree before and after a real file replacement."""
    if (
        set(observation) != {"operation", "before", "result", "files"}
        or observation["operation"] != "duplicates"
        or not _files(observation["before"])
        or not _files(observation["files"])
    ):
        return False
    before = {item["path"]: item["content"] for item in observation["before"]}
    after = {item["path"]: item["content"] for item in observation["files"]}
    value = observation["result"]
    if (
        set(before) != set(after)
        or sum(before[path] != after[path] for path in before) != 1
        or not isinstance(value, Mapping)
        or set(value) != {"initialGroups", "initialMap", "afterGroups", "afterMap"}
    ):
        return False
    groups = value["initialGroups"]
    if (
        not isinstance(groups, list)
        or not groups
        or value["afterGroups"] != []
        or value["afterMap"] != {}
    ):
        return False
    expected = {}
    for group in groups:
        if (
            not isinstance(group, Mapping)
            or set(group) != {"original", "duplicates"}
            or not isinstance(group["original"], str)
            or not isinstance(group["duplicates"], list)
            or not group["duplicates"]
        ):
            return False
        paths = [group["original"], *group["duplicates"]]
        if (
            not all(path in before for path in paths)
            or len(paths) != len(set(paths))
            or any(before[path] != before[paths[0]] for path in paths)
        ):
            return False
        expected[group["original"].split("/")[-1].lower()] = paths
    return value["initialMap"] == expected


MOD_INI_COVERAGE_POLICY = FamilyCoveragePolicy(
    "mod-ini",
    (
        CoveragePredicate(
            "duplicate-lifecycle",
            "mod-ini.duplicates",
            "mod-ini.duplicates",
            "duplicate-groups",
            ("ConfigDuplicateDetector", "DuplicateGroup"),
            _duplicates,
            runtime_operations=(
                None,
                "__init__",
                "detect_duplicates",
                "get_duplicate_map",
                "detect_config_duplicates",
                "detectConfigDuplicates",
            ),
        ),
        CoveragePredicate(
            "typed-cache",
            "mod-ini.cache",
            "mod-ini.cache",
            "ini-cache",
            ("ConfigFileCache",),
            partial(_observed, "cache"),
            runtime_operations=(
                None,
                *(
                    f"RustConfigFileCache.{name}"
                    for name in (
                        "__init__",
                        "config_files",
                        "contains",
                        "get_bool",
                        "get_duplicates",
                        "get_float",
                        "get_int",
                        "get_path",
                        "get_str",
                        "has_setting",
                    )
                ),
            ),
        ),
        CoveragePredicate(
            "mod-scan",
            "mod-ini.scan",
            "mod-ini.scan",
            "mod-scan",
            ("ModIniScanner", "scan", "ModIniScanResult"),
            partial(_observed, "scan"),
            runtime_operations=(
                None,
                "RustModIniScanner.__init__",
                "RustModIniScanner.scan",
                "scan_mod_inis",
                "scanModInis",
            ),
        ),
        CoveragePredicate(
            "vsync-entry",
            "mod-ini.scan",
            "mod-ini.scan",
            "mod-scan",
            ("VsyncEntry",),
            _vsync,
            runtime_operations=(None,),
        ),
    ),
)
