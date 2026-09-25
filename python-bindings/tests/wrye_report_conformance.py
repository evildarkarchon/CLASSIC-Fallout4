"""Input-only Wrye HTML parsing and exact public formatter observations."""

from collections.abc import Mapping
from typing import Any


def observe_wrye_report(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Project every native issue field and compare the public convenience formatter."""
    import classic_scangame as native

    parser = native.WryeBashParser(fixture["warnings"])
    issues = parser.parse(fixture["html"])
    report = parser.format_report(issues)
    if native.parse_wrye_report(fixture["html"], fixture["warnings"]) != report:
        raise ValueError("Wrye convenience parser changed formatted report")
    return {
        "issues": [
            {
                "section": issue.section_title,
                "plugins": issue.plugins,
                "warning": issue.warning_message,
                "severity": str(issue.severity).split(".")[-1],
            }
            for issue in issues
        ],
        "report": report,
    }
