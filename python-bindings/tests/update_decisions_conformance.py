"""Observe strict version decisions through actual Python update bindings."""

from collections.abc import Mapping
from typing import Any


def observe_update_decisions(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Compare explicit versions without invoking any network-facing client method."""
    import classic_update

    if set(fixture) != {"current", "latest"} or any(
            not isinstance(value, str) for value in fixture.values()
    ):
        raise ValueError("unsupported update decision fixture")
    client = classic_update.GithubClient("conformance", "unused")
    try:
        result = client.has_update(fixture["current"], fixture["latest"])
        return {"hasUpdate": result, "error": None}
    except ValueError as failure:
        # Only strict semver errors belong to this domain; initialization failures propagate.
        if not str(failure).startswith("Version error: Version error:"):
            raise
        return {"hasUpdate": None, "error": {"code": "invalid_version"}}
