"""Strict update comparison facts without credit for release network operations."""

from collections.abc import Mapping
from functools import partial
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _matches(result: bool | None, observation: Mapping[str, Any]) -> bool:
    """Preserve typed errors and reject integer lookalikes for boolean decisions."""
    return (
        set(observation) == {"hasUpdate", "error"}
        and observation["hasUpdate"] is result
        and observation["error"]
        == ({"code": "invalid_version"} if result is None else None)
    )


UPDATE_DECISIONS_COVERAGE_POLICY = FamilyCoveragePolicy(
    "update-decisions",
    tuple(
        CoveragePredicate(
            id=f"update-decisions.{name}",
            capability_id="update-decisions.compare",
            action="update-decisions.compare",
            observation_family="errors" if result is None else "values",
            rust_symbols=("GithubClient", "has_update"),
            matches=partial(_matches, result),
            runtime_operations=(
                None,
                "new",
                "__init__",
                "has_update",
                "hasUpdate",
                "github_has_update",
            ),
        )
        for name, result in (("newer", True), ("not-newer", False))
    ),
)


def validate_update_decisions_pack(document, root):
    """Accept only explicit current/latest version inputs, never network requests."""
    import json

    paths = []
    for case in document["scenarios"]:
        reference = case["input"].get("fixtureRef")
        if (
            case["action"] != "update-decisions.compare"
            or case["input"] != {"fixtureRef": reference}
            or case["fixtureRefs"] != [reference]
        ):
            raise ValueError("update decision requires its sole version fixture")
        path = (
            root / document["fixtureRoot"] / document["fixtures"][reference]
        ).resolve()
        if not path.is_relative_to((root / document["fixtureRoot"]).resolve()):
            raise ValueError("update decision fixture escapes root")
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if set(fixture) != {"current", "latest"} or any(
            not isinstance(value, str) for value in fixture.values()
        ):
            raise ValueError("update decision requires two version strings")
        paths.append(path)
    return tuple(paths)
