"""Negative runtime proof for default update APIs, distinct from successful service fetches."""

import json
from functools import partial

from ..coverage import CoveragePredicate, FamilyCoveragePolicy

SPECS = {
    "latest": (
        ("GithubClient", "get_latest_release"),
        (
            "get_latest_release",
            "getLatestRelease",
            "checkForUpdates",
            "github_check_for_updates",
        ),
    ),
    "all": (
        ("GithubClient", "get_all_releases"),
        ("get_all_releases", "getAllReleases"),
    ),
    "notification": (
        ("check_app_notification",),
        ("check_app_notification", "checkAppNotification"),
    ),
    "metadata": (("GithubClient",), ("repo_url",)),
}


def _negative(operation, value):
    """Only exact caller/request-builder rejection proves this negative execution path."""
    if operation == "metadata":
        return value == {"repoUrl": "https://github.com/conformance/fixture"}
    return (
        value
        == {
            "boundary": "caller-validation"
            if operation == "notification"
            else "request-builder",
            "error": "invalid-installed-version"
            if operation == "notification"
            else "builder-error",
            "requestBuilt": False,
        }
        and value["requestBuilt"] is False
    )


UPDATE_REJECTION_COVERAGE_POLICY = FamilyCoveragePolicy(
    "update-rejection",
    tuple(
        CoveragePredicate(
            id=f"update-rejection.{operation}",
            capability_id=f"update-rejection.{operation}",
            action=f"update-rejection.{operation}",
            observation_family="values"
            if operation == "metadata"
            else "negative-runtime",
            rust_symbols=symbols,
            runtime_operations=operations,
            matches=partial(_negative, operation),
        )
        for operation, (symbols, operations) in SPECS.items()
    ),
)


def validate_update_rejection_pack(document, root):
    """Admit only a synthetic invalid header or invalid installed-version fixture."""
    paths = []
    fixture_root = (root / document["fixtureRoot"]).resolve()
    for scenario in document["scenarios"]:
        operation = scenario["action"].removeprefix("update-rejection.")
        reference = scenario["input"].get("fixtureRef")
        if (
            operation not in SPECS
            or scenario["input"] != {"fixtureRef": reference}
            or scenario["fixtureRefs"] != [reference]
        ):
            raise ValueError("invalid update rejection input")
        path = (fixture_root / document["fixtures"][reference]).resolve()
        if not path.is_relative_to(fixture_root):
            raise ValueError("update rejection fixture escapes root")
        expected_input = {
            "operation": operation,
            "owner": "conformance",
            "repo": "fixture",
            "token": "synthetic\ninvalid",
            "currentVersion": "1.0.0",
            "invalidVersion": "invalid",
        }
        if json.loads(
            path.read_text(encoding="utf-8")
        ) != expected_input or not _negative(operation, scenario["expected"]):
            raise ValueError(
                "update rejection must use synthetic pre-transport failures"
            )
        paths.append(path)
    return tuple(paths)
