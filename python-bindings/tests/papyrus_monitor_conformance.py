"""Input-only Papyrus monitoring through public Python objects."""

import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def _stats(stats: Any) -> dict[str, Any]:
    """Project every portable public statistic and native ratio query."""
    return {
        "dumps": stats.dumps,
        "stacks": stats.stacks,
        "warnings": stats.warnings,
        "errors": stats.errors,
        "lines": stats.lines_processed,
        "ratio": f"{stats.dumps_to_stacks_ratio():.3f}",
    }


def observe_papyrus_monitor(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Observe full parsing, tail-from-end, incremental updates, idle and reset."""
    from classic_scanlog import PapyrusAnalyzer, PapyrusStats, papyrus_logging

    with tempfile.TemporaryDirectory(
            prefix="classic-papyrus-conformance-"
    ) as directory:
        path = Path(directory) / "Papyrus.0.log"
        if fixture["content"] is not None:
            path.write_bytes(fixture["content"].encode("utf-8"))
        analyzer = PapyrusAnalyzer(path)
        result = {
            "exists": analyzer.log_exists(),
            "error": None,
            "initial": None,
            "tailStart": None,
            "updated": None,
            "idle": None,
            "afterReset": None,
            "finalContent": None,
        }
        if analyzer.log_path() != path or _stats(analyzer.stats()) != _stats(
                PapyrusStats()
        ):
            raise ValueError(
                "new Papyrus analyzer has wrong path or nonempty statistics"
            )
        try:
            result["initial"] = _stats(analyzer.analyze_full())
        except FileNotFoundError:
            result["error"] = "missing"
            return result
        summary = analyzer.analyze_to_string()
        initial = result["initial"]
        expected_summary = (
            f"NUMBER OF DUMPS    : {initial['dumps']}\nNUMBER OF STACKS   : {initial['stacks']}\n"
            f"DUMPS/STACKS RATIO : {initial['ratio']}\nNUMBER OF WARNINGS : {initial['warnings']}\n"
            f"NUMBER OF ERRORS   : {initial['errors']}\nLINES PROCESSED    : {initial['lines']}"
        )
        if summary != expected_summary:
            raise ValueError(
                "formatted Papyrus summary disagrees with native statistics"
            )
        if papyrus_logging(path) != (summary, initial["dumps"]):
            raise ValueError(
                "Papyrus convenience function disagrees with native statistics"
            )
        analyzer.start_monitoring()
        if analyzer.check_for_updates() is not None:
            raise ValueError("tail start replayed old content")
        result["tailStart"] = _stats(analyzer.stats())
        with path.open("ab") as stream:
            stream.write(fixture["append"].encode("utf-8"))
        update = analyzer.check_for_updates()
        if update is not None and update[0] != fixture["append"].splitlines():
            raise ValueError("incremental monitor returned different lines")
        result["updated"] = _stats(analyzer.stats())
        if analyzer.check_for_updates() is not None:
            raise ValueError("idle Papyrus poll replayed content")
        result["idle"] = _stats(analyzer.stats())
        analyzer.reset()
        result["afterReset"] = _stats(analyzer.analyze_full())
        result["finalContent"] = path.read_bytes().decode("utf-8")
        return result
