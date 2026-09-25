"""Log collection requires actual paths backed by complete move/copy inventories."""

from collections.abc import Mapping
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy
from .file_operations import _files


def _observed(observation: Mapping[str, Any]) -> bool:
    """Reject invented discoveries and deletion or replacement of preserved source logs."""
    if set(observation) != {
        "before",
        "first",
        "afterFirst",
        "second",
        "files",
    } or not all(_files(observation[key]) for key in ("before", "afterFirst", "files")):
        return False
    before = {item["path"]: item["content"] for item in observation["before"]}
    first = {item["path"]: item["content"] for item in observation["afterFirst"]}
    after = {item["path"]: item["content"] for item in observation["files"]}
    for key, inventory in (("first", first), ("second", after)):
        paths = observation[key]
        if (
            not isinstance(paths, list)
            or paths != sorted(set(paths))
            or not all(path in inventory and path.endswith(".log") for path in paths)
        ):
            return False
    if not all(path in observation["second"] for path in observation["first"]):
        return False
    return all(
        (first.get(path) == content and after.get(path) == content)
        if path.startswith(("xse/", "custom/")) or not path.startswith("base/crash-")
        else (
            path not in first
            and first.get("base/Crash Logs/" + path.split("/")[-1]) == content
        )
        for path, content in before.items()
    )


_PYTHON_COLLECTOR = "parity:python:file_io.log_collection.PyLogCollector"
LOG_COLLECTION_COVERAGE_POLICY = FamilyCoveragePolicy(
    "log-collection",
    (
        CoveragePredicate(
            "targeted-resolver",
            "log-collection.collect",
            "log-collection.collect",
            "collection-effects",
            ("resolve_targeted_inputs",),
            _observed,
            runtime_operations=("resolve_targeted_inputs",),
        ),
        CoveragePredicate(
            "collected-logs",
            "log-collection.collect",
            "log-collection.collect",
            "collection-effects",
            (
                "LogCollector",
                "collect_all",
                "collect_crash_logs",
                "CRASH_AUTOSCAN_PATTERN",
                "CRASH_LOG_PATTERN",
            ),
            _observed,
            binding_obligation_ids=(
                "parity:cxx:1462d027a7cba8dd",
                "parity:cxx:acf327fd1cc5bdc2",
                "parity:cxx:8d5f7aa4b18d4e1f",
                "parity:node:scanlog.JsLogCollector",
                "parity:node:aux-phase4c-crash-autoscan-pattern",
                "parity:node:scanlog.patterns.CRASH_LOG_PATTERN",
                _PYTHON_COLLECTOR,
                *(
                    _PYTHON_COLLECTOR + "." + name
                    for name in (
                        "__init__",
                        "collect_all",
                        "collect_crash_logs",
                        "copy_from_xse_folder",
                        "crash_logs_dir",
                        "move_from_base_folder",
                        "pastebin_dir",
                    )
                ),
            ),
            runtime_operations=(
                None,
                "log_collector_new",
                "log_collector_collect_all",
                "log_collector_collect_crash_logs",
                *(
                    "PyLogCollector." + name
                    for name in (
                        "__init__",
                        "collect_all",
                        "collect_crash_logs",
                        "copy_from_xse_folder",
                        "crash_logs_dir",
                        "move_from_base_folder",
                        "pastebin_dir",
                    )
                ),
            ),
        ),
        CoveragePredicate(
            "configured-collector",
            "log-collection.configured",
            "log-collection.configured",
            "collection-effects",
            ("new_for_scan",),
            _observed,
            runtime_operations=("log_collector_new_for_scan",),
        ),
    ),
)
