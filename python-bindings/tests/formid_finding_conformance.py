"""Input-only aggregate FormID Finding calls through public Python factories."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any


def observe_formid_finding(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Retain native counts/statuses and distinguish constructor and analysis failures."""
    import classic_scanlog as native

    mode = fixture["mode"]
    try:
        if mode == "disabled":
            analyzer = native.FormIDFindingAnalyzer()
        elif mode == "in-memory":
            entries = [
                native.FormIDFindingLookupEntry(
                    entry["formid"],
                    entry["plugin"],
                    native.FormIDFindingLookupReplyKind.OperationalFailure
                    if entry.get("failure") is not None
                    else native.FormIDFindingLookupReplyKind.Found
                    if entry.get("value") is not None
                    else native.FormIDFindingLookupReplyKind.Missing,
                    value=entry.get("value"),
                    error_message=entry.get("failure"),
                )
                for entry in fixture["entries"]
            ]
            analyzer = native.FormIDFindingAnalyzer.in_memory(entries)
        elif mode == "sqlite-missing":
            if Path(fixture["databasePath"]).exists():
                raise ValueError("missing SQLite fixture path unexpectedly exists")
            analyzer = native.FormIDFindingAnalyzer.sqlite(
                fixture["databasePath"], "Fallout4"
            )
            raise ValueError("missing SQLite analyzer unexpectedly constructed")
        else:
            raise ValueError("unknown FormID Finding mode")
        if analyzer.kind.code != "formid_finding":
            raise ValueError("incorrect native analyzer identity")
        request = native.FormIDFindingAnalysisInput(
            fixture["lines"],
            [
                native.FormIDPlugin(plugin["name"], plugin["prefix"])
                for plugin in fixture["plugins"]
            ],
        )
        result = analyzer.analyze(request)
        statuses = {
            "NotApplicable": "not_applicable",
            "Disabled": "disabled",
            "Missing": "missing",
            "Found": "found",
        }
        return {
            "mode": mode,
            "findings": [
                {
                    "identifier": finding.identifier,
                    "occurrences": finding.occurrences,
                    "plugin": finding.plugin,
                    "status": statuses[str(finding.value_lookup_status).split(".")[-1]],
                    "value": finding.value,
                }
                for finding in result.findings
            ],
            "error": None,
        }
    except native.AnalyzerError as error:
        if error.analyzer_kind.code != "formid_finding":
            raise ValueError("incorrect native error identity") from error
        return {
            "mode": mode,
            "findings": None,
            "error": {"code": error.code, "message": error.message},
        }
