"""Input-only native parser, literal matcher, and cache-lifetime observations."""

import math
import warnings
from collections.abc import Mapping
from typing import Any


def observe_log_parsing(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Execute public parser methods and retain their actual returned values."""
    from classic_scanlog import LogParser, PatternMatcher

    if fixture["operation"] == "crashgen-version":
        import classic_scanlog as native

        value = native.parse_crashgen_version(fixture["version"])
        version = None if value is None else list(value.to_tuple())
        if value is not None:
            constructed = native.CrashgenVersion(fixture["version"])
            normalized = native.CrashgenVersion(".".join(str(part) for part in version))
            if (
                constructed != normalized
                or hash(constructed) != hash(normalized)
                or constructed.original != fixture["version"]
            ):
                raise ValueError(
                    "version construction/equality/hash changed numeric identity"
                )
            if (
                list(constructed.to_tuple()) != version
                or [constructed.major, constructed.minor, constructed.patch] != version
            ):
                raise ValueError("version getters disagree with native parser")
        return {
            "operation": "crashgen-version",
            "version": version,
            "status": str(
                native.check_crashgen_version_status(
                    fixture["version"], fixture["supported"]
                )
            ),
        }

    if fixture["operation"] == "gpu":
        import classic_scanlog as native

        detector = native.GpuDetector()
        info = detector.extract_gpu_info(fixture["lines"])
        values = {
            "primary": info.primary,
            "secondary": info.secondary,
            "manufacturer": info.manufacturer,
            "rival": info.rival,
        }
        if (
            info.to_dict() != values
            or str(native.GpuVendor(fixture["vendor"])) != values["manufacturer"]
        ):
            raise ValueError("GPU public conversion differs from detected fields")
        empty = native.GpuInfo().to_dict()
        if detector.extract_gpu_info([]).to_dict() != empty:
            raise ValueError("GPU default carrier differs from empty detection")
        return {
            "operation": "gpu",
            "info": values,
            "empty": empty,
            "batch": [
                value.to_dict()
                for value in detector.extract_gpu_info_batch([fixture["lines"], []])
            ],
        }

    if fixture["operation"] in {"formids", "plugins", "records"}:
        return _observe_extractors(fixture)

    if fixture["operation"] == "patterns":
        matcher = PatternMatcher(fixture["patterns"])
        before = list(matcher.get_stats())
        matches = [list(value) for value in matcher.find_all(fixture["text"])]
        cached = list(matcher.get_stats())
        first = matcher.find_first(fixture["text"])
        result = {
            "operation": "patterns",
            "before": before,
            "matches": matches,
            "first": None if first is None else list(first),
            "hasMatch": matcher.has_match(fixture["text"]),
            "replaced": matcher.replace_all(fixture["text"], fixture["replacement"]),
            "cached": cached,
        }
        matcher.clear_cache()
        result["afterClear"] = list(matcher.get_stats())
        if [list(value) for value in matcher.find_all(fixture["text"])] != matches:
            raise ValueError("matcher cache clear changed semantic results")
        return result
    if fixture["operation"] != "parser":
        raise ValueError("unknown parser operation")
    parser = LogParser()
    parser.add_pattern("custom", fixture["pattern"])
    patterns = sorted(
        [list(value) for value in parser.find_patterns(fixture["patternLines"])]
    )
    if (
        sorted(
            [
                list(value)
                for value in parser.find_patterns_chunked(fixture["patternLines"], 1)
            ]
        )
        != patterns
    ):
        raise ValueError("chunked parser changed pattern results")
    sections = parser.parse_all_sections(fixture["lines"])
    with warnings.catch_warnings():
        # This compatibility alias is intentionally exercised despite its deprecation.
        warnings.simplefilter("ignore", DeprecationWarning)
        if parser.parse_segments_parallel(fixture["lines"], 1) != sections:
            raise ValueError("parallel section alias changed parser results")
    complete = parser.parse_complete(fixture["lines"])
    if complete.segments != sections:
        raise ValueError("complete parser changed named segments")
    headers = parser.parse_crash_header(fixture["lines"])
    if (complete.game_version, complete.crashgen_version, complete.main_error) != tuple(
        headers.get(key, "UNKNOWN")
        for key in ("game_version", "crashgen_version", "main_error")
    ):
        raise ValueError("complete parser changed header fields")
    benchmark = parser.benchmark(fixture["lines"], 16)
    result = {
        "operation": "parser",
        "patterns": patterns,
        "section": parser.extract_section(fixture["sectionLines"], "START", "END"),
        "sectionBatch": parser.extract_sections_batch(
            fixture["sectionLines"], [("START", "END"), ("ABSENT", "END")]
        ),
        "headers": headers,
        "sections": sections,
        "system": parser.get_section(fixture["lines"], "system"),
        "sizes": parser.get_segment_sizes(fixture["lines"]),
        "formids": parser.extract_formids(fixture["extractLines"]),
        "plugins": [
            list(value) for value in parser.extract_plugins(fixture["extractLines"])
        ],
        "addresses": parser.extract_addresses(fixture["extractLines"]),
        "errors": [
            list(value) for value in parser.find_errors(fixture["extractLines"])
        ],
        "benchmarkKeys": sorted(benchmark),
        "benchmarkFinite": all(
            math.isfinite(value) and value >= 0 for value in benchmark.values()
        ),
    }
    parser.clear_caches()
    result["afterClear"] = parser.get_stats()
    return result


def _observe_extractors(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Execute standalone and object-based extraction, retaining ordered results."""
    import classic_scanlog as native

    operation = fixture["operation"]
    if operation == "formids":
        analyzer = native.FormIDAnalyzer()
        result = {
            "operation": operation,
            "extracted": analyzer.extract_formids(fixture["lines"]),
            "extractedBatch": native.extract_formids_batch([fixture["lines"], []]),
            "parsed": [analyzer.parse_formid(value) for value in fixture["ids"]],
            "resolved": [
                list(value)
                for value in analyzer.analyze_batch(fixture["ids"], fixture["plugins"])
            ],
            "valid": [native.is_valid_formid(value) for value in fixture["ids"]],
            "validBatch": native.validate_formids_batch(fixture["ids"]),
            "cache": list(analyzer.cache_stats()),
        }
        analyzer.clear_cache()
        result["afterClear"] = list(analyzer.cache_stats())
        if [
            list(value)
            for value in analyzer.analyze_batch(fixture["ids"], fixture["plugins"])
        ] != result["resolved"]:
            raise ValueError("FormID cache clear changed plugin resolution")
        return result
    if operation == "plugins":
        analyzer = native.PluginAnalyzer(
            [], fixture["ignore"], "Buffout 4", "1.10.163", "1.2.72"
        )
        plugins, triggered, disabled = analyzer.loadorder_scan_log(
            fixture["lines"], "1.10.163", "1.28.6"
        )
        limits = list(
            analyzer.check_plugin_limit(fixture["lines"], "1.10.163", "1.28.6")
        )
        return {
            "operation": operation,
            "plugins": [list(value) for value in plugins.items()],
            "limits": [triggered, disabled],
            "checkedLimits": limits,
            "filtered": [
                list(value)
                for value in analyzer.filter_ignored_plugins(plugins).items()
            ],
            "batch": [
                [list(value) for value in mapping.items()]
                for mapping in native.detect_plugins_batch(
                    ["\n".join(fixture["lines"]), ""]
                )
            ],
            "contains": [native.contains_plugin(line) for line in fixture["lines"]],
        }
    scanner = native.RecordScanner(fixture["targets"], fixture["ignore"])
    records = scanner.extract_records(fixture["lines"])
    result = {
        "operation": operation,
        "records": records,
        "batch": native.scan_records_batch(
            [fixture["lines"], []], fixture["targets"], fixture["ignore"]
        ),
        "contains": [
            native.contains_record(line, fixture["targets"], fixture["ignore"])
            for line in fixture["lines"]
        ],
    }
    scanner.clear_cache()
    result["afterClear"] = scanner.extract_records(fixture["lines"])
    return result
