"""Facts for actual log extraction results and literal matcher cache transitions."""

from collections.abc import Mapping
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _patterns(observation: Mapping[str, Any]) -> bool:
    """Require complete matches, first/any agreement and native cache invalidation."""
    if (
        set(observation)
        != {
            "operation",
            "before",
            "matches",
            "first",
            "hasMatch",
            "replaced",
            "cached",
            "afterClear",
        }
        or observation["operation"] != "patterns"
    ):
        return False
    before, cached, after = (
        observation[key] for key in ("before", "cached", "afterClear")
    )
    matches = observation["matches"]
    return (
        isinstance(before, list)
        and len(before) == 2
        and type(before[0]) is int
        and before[0] > 0
        and before[1] == 0
        and cached == [before[0], 1]
        and after == before
        and isinstance(matches, list)
        and all(
            isinstance(item, list)
            and len(item) == 2
            and type(item[0]) is int
            and item[0] >= 0
            and isinstance(item[1], str)
            for item in matches
        )
        and observation["first"] == (matches[0] if matches else None)
        and observation["hasMatch"] is bool(matches)
        and isinstance(observation["replaced"], str)
    )


def _parser(observation: Mapping[str, Any]) -> bool:
    """Require complete extraction, named-section sizes and cleared native caches."""
    if (
        set(observation)
        != {
            "operation",
            "patterns",
            "section",
            "sectionBatch",
            "headers",
            "sections",
            "system",
            "sizes",
            "formids",
            "plugins",
            "addresses",
            "errors",
            "benchmarkKeys",
            "benchmarkFinite",
            "afterClear",
        }
        or observation["operation"] != "parser"
    ):
        return False
    sections = observation["sections"]
    if not isinstance(sections, Mapping) or set(sections) != {
        "settings",
        "system",
        "callstack",
        "modules",
        "xse_modules",
        "plugins",
        "registers",
        "stack_dump",
    }:
        return False
    if not all(
        isinstance(lines, list) and all(isinstance(line, str) for line in lines)
        for lines in sections.values()
    ):
        return False
    return (
        observation["sizes"] == {key: len(lines) for key, lines in sections.items()}
        and observation["system"] == (sections["system"] or None)
        and observation["sectionBatch"] == [observation["section"], None]
        and isinstance(observation["headers"], Mapping)
        and all(isinstance(value, str) for value in observation["headers"].values())
        and all(
            isinstance(observation[key], list)
            for key in ("patterns", "formids", "plugins", "addresses", "errors")
        )
        and observation["benchmarkKeys"]
        == ["find_patterns_avg_ms", "lines_per_second", "parse_segments_avg_ms"]
        and observation["benchmarkFinite"] is True
        and observation["afterClear"]
        == {
            "segment_cache_size": 0,
            "pattern_cache_size": 0,
            "custom_patterns": 1,
            "compiled_patterns": 7,
        }
    )


def _extractors(observation: Mapping[str, Any]) -> bool:
    """Require independent batch/individual agreement and exact cache postconditions."""
    operation = observation.get("operation")
    if operation == "formids":
        return (
            set(observation)
            == {
                "operation",
                "extracted",
                "extractedBatch",
                "parsed",
                "resolved",
                "valid",
                "validBatch",
                "cache",
                "afterClear",
            }
            and isinstance(observation["extracted"], list)
            and observation["extractedBatch"] == [observation["extracted"], []]
            and isinstance(observation["parsed"], list)
            and isinstance(observation["resolved"], list)
            and len(observation["parsed"])
            == len(observation["resolved"])
            == len(observation["valid"])
            and all(type(value) is bool for value in observation["valid"])
            and observation["valid"] == observation["validBatch"]
            and observation["cache"] == observation["afterClear"] == [0, 0]
        )
    if operation == "plugins":
        return (
            set(observation)
            == {
                "operation",
                "plugins",
                "limits",
                "checkedLimits",
                "filtered",
                "batch",
                "contains",
            }
            and isinstance(observation["plugins"], list)
            and isinstance(observation["filtered"], list)
            and all(item in observation["plugins"] for item in observation["filtered"])
            and observation["batch"] == [observation["plugins"], []]
            and observation["limits"] == observation["checkedLimits"]
            and len(observation["limits"]) == 2
            and all(type(value) is bool for value in observation["limits"])
            and all(type(value) is bool for value in observation["contains"])
        )
    if operation == "records":
        return (
            set(observation)
            == {"operation", "records", "batch", "contains", "afterClear"}
            and isinstance(observation["records"], list)
            and all(isinstance(value, str) for value in observation["records"])
            and observation["records"] == observation["afterClear"]
            and observation["batch"] == [observation["records"], []]
            and all(type(value) is bool for value in observation["contains"])
        )
    return False


def _gpu(observation: Mapping[str, Any]) -> bool:
    """Require complete GPU fields, vendor/rival agreement, defaults and batch order."""
    if (
        set(observation) != {"operation", "info", "empty", "batch"}
        or observation["operation"] != "gpu"
    ):
        return False
    info = observation["info"]
    if not isinstance(info, Mapping) or set(info) != {
        "primary",
        "secondary",
        "manufacturer",
        "rival",
    }:
        return False
    empty = {
        "primary": "Unknown",
        "secondary": None,
        "manufacturer": "Unknown",
        "rival": None,
    }
    return (
        isinstance(info["primary"], str)
        and (info["secondary"] is None or isinstance(info["secondary"], str))
        and info["manufacturer"] in {"AMD", "Nvidia", "Intel", "Unknown"}
        and info["rival"]
        == {"AMD": "nvidia", "Nvidia": "amd"}.get(info["manufacturer"])
        and observation["empty"] == empty
        and observation["batch"] == [info, empty]
    )


def _node_parser(observation: Mapping[str, Any]) -> bool:
    """Require all public segment fields, count agreement and actual extraction lists."""
    if (
        set(observation) != {"operation", "segments", "formids", "plugins"}
        or observation["operation"] != "node-parser"
    ):
        return False
    segments = observation["segments"]
    if not isinstance(segments, Mapping) or set(segments) != {
        "header",
        "system",
        "stack",
        "modules",
        "plugins",
        "segmentCount",
    }:
        return False
    names = ("header", "system", "stack", "modules", "plugins")
    return (
        all(
            isinstance(segments[name], list)
            and all(isinstance(line, str) for line in segments[name])
            for name in names
        )
        and segments["segmentCount"] == sum(bool(segments[name]) for name in names)
        and all(
            isinstance(observation[key], list)
            and all(isinstance(value, str) for value in observation[key])
            for key in ("formids", "plugins")
        )
    )


def _crashgen_version(observation: Mapping[str, Any]) -> bool:
    """Keep failed parsing distinct from supported-floor status and numeric components."""
    if (
        set(observation) != {"operation", "version", "status"}
        or observation["operation"] != "crashgen-version"
    ):
        return False
    version = observation["version"]
    return (
        version is None
        or isinstance(version, list)
        and len(version) == 3
        and all(type(part) is int and part >= 0 for part in version)
    ) and observation["status"] in {
        "valid",
        "outdated",
        "newer_than_known",
        "no_supported_version",
    }


def _version_carrier(observation: Mapping[str, Any]) -> bool:
    """Only a parsed value proves the native constructor/equality/hash protocol ran."""
    return _crashgen_version(observation) and observation["version"] is not None


LOG_PARSING_COVERAGE_POLICY = FamilyCoveragePolicy(
    "log-parsing",
    (
        CoveragePredicate(
            "crashgen-version",
            "log-parsing.crashgen-version",
            "log-parsing.crashgen-version",
            "version-values",
            ("CrashgenVersion", "check_crashgen_version_status"),
            _crashgen_version,
            runtime_operations=(
                "parse_crashgen_version",
                "parseCrashgenVersion",
                "check_crashgen_version_status",
                "checkCrashgenVersionStatus",
            ),
        ),
        CoveragePredicate(
            "version-carrier",
            "log-parsing.crashgen-version",
            "log-parsing.crashgen-version",
            "version-values",
            ("CrashgenVersion",),
            _version_carrier,
            runtime_operations=(None, "__init__", "__eq__", "__hash__", "to_tuple"),
        ),
        CoveragePredicate(
            "node-parsed-log",
            "log-parsing.node-parser",
            "log-parsing.node-parser",
            "node-log-values",
            ("LogParser",),
            _node_parser,
            runtime_operations=(
                "parseLogSegments",
                "extractFormIds",
                "extractPluginList",
            ),
        ),
        CoveragePredicate(
            "gpu-fields",
            "log-parsing.gpu",
            "log-parsing.gpu",
            "gpu-fields",
            ("GpuDetector", "GpuInfo", "GpuVendor"),
            _gpu,
            runtime_operations=(
                None,
                "__init__",
                "extract_gpu_info",
                "extract_gpu_info_batch",
                "to_dict",
                "detectGpuInfo",
            ),
        ),
        CoveragePredicate(
            "literal-matches",
            "log-parsing.patterns",
            "log-parsing.patterns",
            "literal-matches",
            ("PatternMatcher",),
            _patterns,
            runtime_operations=(
                None,
                "__init__",
                "find_all",
                "find_first",
                "has_match",
                "replace_all",
                "clear_cache",
                "get_stats",
            ),
        ),
        CoveragePredicate(
            "parsed-log",
            "log-parsing.parser",
            "log-parsing.parser",
            "parsed-log",
            ("LogParser",),
            _parser,
            runtime_operations=(
                None,
                "__init__",
                "add_pattern",
                "clear_caches",
                "find_patterns",
                "find_patterns_chunked",
                "extract_section",
                "extract_sections_batch",
                "parse_crash_header",
                "get_section",
                "parse_all_sections",
                "parse_complete",
                "parse_segments_parallel",
                "get_segment_sizes",
                "get_stats",
                "extract_formids",
                "extract_plugins",
                "extract_addresses",
                "find_errors",
                "benchmark",
            ),
        ),
        *(
            CoveragePredicate(
                f"extracted-{operation}",
                f"log-parsing.{operation}",
                f"log-parsing.{operation}",
                "extracted-values",
                symbols,
                _extractors,
                runtime_operations=operations,
            )
            for operation, symbols, operations in (
                (
                    "formids",
                    (
                        "RustFormIDAnalyzer",
                        "extract_formids_batch",
                        "is_valid_formid",
                        "validate_formids_batch",
                    ),
                    (
                        None,
                        "FormIDAnalyzer.__init__",
                        "FormIDAnalyzer.extract_formids",
                        "FormIDAnalyzer.parse_formid",
                        "FormIDAnalyzer.analyze_batch",
                        "FormIDAnalyzer.clear_cache",
                        "FormIDAnalyzer.cache_stats",
                        "extract_formids_batch",
                        "is_valid_formid",
                        "validate_formids_batch",
                    ),
                ),
                (
                    "plugins",
                    ("PluginAnalyzer", "detect_plugins_batch", "contains_plugin"),
                    (
                        None,
                        "__init__",
                        "loadorder_scan_log",
                        "check_plugin_limit",
                        "filter_ignored_plugins",
                        "detect_plugins_batch",
                        "contains_plugin",
                    ),
                ),
                (
                    "records",
                    ("RecordScanner", "scan_records_batch", "contains_record"),
                    (
                        None,
                        "__init__",
                        "extract_records",
                        "clear_cache",
                        "scan_records_batch",
                        "contains_record",
                    ),
                ),
            )
        ),
    ),
)
