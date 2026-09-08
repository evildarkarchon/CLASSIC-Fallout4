"""Configured notification facts over hermetic HTTP inputs and durable bytes."""

import json
from collections.abc import Mapping
from functools import partial

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _matches(outcome, observation):
    """Grant facts only for complete notification results with explicit effects."""
    if set(observation) != {"results", "files"} or not isinstance(
        observation["results"], list
    ):
        return False
    if not observation["results"] or not isinstance(observation["files"], list):
        return False
    for item in observation["files"]:
        if not isinstance(item, Mapping) or set(item) != {"path", "hex"}:
            return False
        if not isinstance(item["path"], str) or not isinstance(item["hex"], str):
            return False
    for result in observation["results"]:
        if not isinstance(result, Mapping) or set(result) != {"status", "error"}:
            return False
        if result["status"] is None:
            if result["error"] != {"code": outcome} or observation["files"]:
                return False
        else:
            status = result["status"]
            if result["error"] is not None or not isinstance(status, Mapping):
                return False
            if set(status) != {
                "classification",
                "latestVersion",
                "publishedAt",
                "minSupportedVersion",
                "display",
                "parseError",
            }:
                return False
            if status["classification"] != outcome:
                return False
    return True


UPDATE_SERVICES_COVERAGE_POLICY = FamilyCoveragePolicy(
    "update-services",
    tuple(
        CoveragePredicate(
            id="update-services." + outcome.replace("_", "-"),
            capability_id="update-services.notification",
            action="update-services.notification",
            observation_family="notification-result",
            rust_symbols=("check_app_notification_configured",),
            matches=partial(_matches, outcome),
            runtime_operations=(
                "check_app_notification_configured",
                "checkAppNotificationConfigured",
            ),
        )
        for outcome in (
            "update_available",
            "up_to_date",
            "deprecated_client",
            "not_published",
            "fetch_failed",
            "unsupported_version",
            "installed_version",
        )
    ),
)


def validate_update_services_pack(document, root):
    """Reject remote routes and hidden fixture inputs before any adapter launch."""
    paths = []
    for scenario in document["scenarios"]:
        reference = scenario["input"].get("fixtureRef")
        if (
            scenario["action"] != "update-services.notification"
            or scenario["input"] != {"fixtureRef": reference}
            or scenario["fixtureRefs"] != [reference]
        ):
            raise ValueError("update service requires one explicit input fixture")
        path = (
            root / document["fixtureRoot"] / document["fixtures"][reference]
        ).resolve()
        if not path.is_relative_to((root / document["fixtureRoot"]).resolve()):
            raise ValueError("update service fixture escapes root")
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if set(fixture) != {"installedVersion", "timeoutMs", "checks", "service"}:
            raise ValueError("update service has unexpected input fields")
        if (
            not isinstance(fixture["installedVersion"], str)
            or type(fixture["timeoutMs"]) is not int
            or not 1 <= fixture["timeoutMs"] <= 5000
            or type(fixture["checks"]) is not int
            or not 1 <= fixture["checks"] <= 2
        ):
            raise ValueError("update service requires bounded explicit inputs")
        service = fixture["service"]
        if not isinstance(service, dict) or set(service) != {"pages", "api"}:
            raise ValueError("update service permits only local pages and api routes")
        for route, responses in service.items():
            if not isinstance(responses, list) or len(responses) > 2:
                raise ValueError("update service response sequence must be bounded")
            for response in responses:
                if response == {"stall": True}:
                    continue
                if (
                    not isinstance(response, dict)
                    or set(response) - {"status", "body", "headers", "ifNoneMatch"}
                    or not {"status", "body", "headers"} <= set(response)
                ):
                    raise ValueError("invalid controlled response")
                if (
                    type(response["status"]) is not int
                    or response["status"] not in {200, 304, 404, 503}
                    or not isinstance(response["body"], str)
                ):
                    raise ValueError("invalid controlled response status/body")
                if (
                    route == "api"
                    and response["status"] == 200
                    and response["body"] != "[]"
                ):
                    raise ValueError(
                        "release lists must be empty: remote asset URLs are forbidden"
                    )
                headers = response["headers"]
                if (
                    not isinstance(headers, dict)
                    or set(headers) - {"ETag"}
                    or any(
                        not isinstance(v, str) or "\r" in v or "\n" in v
                        for v in headers.values()
                    )
                ):
                    raise ValueError(
                        "controlled responses cannot redirect or inject headers"
                    )
                if "ifNoneMatch" in response and not isinstance(
                    response["ifNoneMatch"], str
                ):
                    raise ValueError("conditional request must be a string")
        paths.append(path)
    return tuple(paths)
