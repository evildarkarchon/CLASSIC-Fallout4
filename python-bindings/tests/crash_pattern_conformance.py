"""Input-only public Python crash-token observations."""

from collections.abc import Mapping
from typing import Any


def observe_crash_pattern(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Read the real shared native classifier result without host token inference."""
    from classic_scanlog import detect_crash_pattern

    if fixture["operation"] == "vr":
        from classic_scanlog import LogParser

        return {"vr": LogParser().detect_vr_log(fixture["content"])}
    if fixture["operation"] != "classify":
        raise ValueError("Python does not expose the legacy CXX error-text alias")
    return {"token": detect_crash_pattern(fixture["content"])}
