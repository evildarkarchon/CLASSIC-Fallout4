"""YAML update consent guards and byte-authenticated owned rollback effects."""

import re
from collections.abc import Mapping
from functools import partial

from ..coverage import CoveragePredicate, FamilyCoveragePolicy

_CACHE = "cache/CLASSIC/yaml-cache/"
_MANIFEST_FILES = {_CACHE + "manifest-latest.json", _CACHE + "manifest.etag"}


def _files(value):
    """Accept a complete sorted file inventory with exact bytes or parsed manifest JSON."""
    if not isinstance(value, list) or any(
        not isinstance(item, Mapping)
        or set(item) not in ({"path", "hex"}, {"path", "json"})
        for item in value
    ):
        return None
    paths = [item["path"] for item in value]
    if any(
        not isinstance(path, str)
        or (path != ".env" and not path.startswith("cache/"))
        or ".." in path.split("/")
        for path in paths
    ) or paths != sorted(set(paths)):
        return None
    for item in value:
        if "hex" in item:
            if (
                not isinstance(item["hex"], str)
                or re.fullmatch(r"(?:[0-9a-f]{2})*", item["hex"]) is None
            ):
                return None
        elif item["path"] != _CACHE + "manifest-latest.json" or not isinstance(
            item["json"], Mapping
        ):
            return None
    return {item["path"]: item for item in value}


def _base(observation):
    """Require both independently read file checkpoints and actual native result records."""
    return (
        set(observation) == {"results", "beforeFiles", "files"}
        and isinstance(observation["results"], list)
        and all(isinstance(result, Mapping) for result in observation["results"])
        and _files(observation["beforeFiles"]) is not None
        and _files(observation["files"]) is not None
    )


def _payloads_unchanged(observation):
    """Manifest caching may change metadata; consent guards may not install YAML payloads."""
    before = _files(observation["beforeFiles"])
    after = _files(observation["files"])
    return {
        path: value for path, value in before.items() if path not in _MANIFEST_FILES
    } == {path: value for path, value in after.items() if path not in _MANIFEST_FILES}


def matches_check(api, observation):
    """Require an explicit disabled or available status without payload mutation."""
    if not _base(observation) or not _payloads_unchanged(observation):
        return False
    return any(
        result.get("api") == api
        and set(result)
        == {
            "api",
            "tag",
            "releaseTag",
            "publishedAt",
            "compatible",
            "incompatible",
            "incompatibleReasons",
            "unknownReason",
            "error",
        }
        and result["error"] is None
        and result["tag"] in (0, 1)
        and result["incompatible"] == []
        and result["incompatibleReasons"] == []
        and result["unknownReason"] == ""
        and (
            (
                result["tag"] == 0
                and result["compatible"] == []
                and result["releaseTag"] == ""
                and observation["beforeFiles"] == observation["files"]
            )
            or (
                result["tag"] == 1
                and bool(result["compatible"])
                and bool(result["releaseTag"])
            )
        )
        for result in observation["results"]
    )


def matches_apply(api, observation):
    """Require empty-consent success or a native refusal, with every payload unchanged."""
    if not _base(observation) or not _payloads_unchanged(observation):
        return False
    return any(
        result.get("api") == api
        and set(result) == {"api", "installed", "failed", "error"}
        and result["installed"] == []
        and result["failed"] == []
        and result["error"]
        in (None, "disabled", "malformed_approval", "stale_decision")
        for result in observation["results"]
    )


def matches_rollback(api, observation):
    """Authenticate restored generations rather than trusting a rolled-back flag."""
    if not _base(observation):
        return False
    before, after = _files(observation["beforeFiles"]), _files(observation["files"])
    for result in observation["results"]:
        if result.get("api") != api:
            continue
        if api == "yaml_rollback_update":
            if set(result) != {"api", "fileName", "rolledBack", "error"}:
                continue
            if result["error"] in ("invalid_name", "local_ignore_refused"):
                return before == after and result["rolledBack"] is False
            names, absent = (
                ([result["fileName"]], [])
                if result["rolledBack"] is True
                else ([], [result["fileName"]])
            )
            if result["error"] is not None:
                continue
        else:
            if (
                set(result)
                != {"api", "rolledBack", "noPrevious", "failedFiles", "failureReasons"}
                or result["failedFiles"] != []
                or result["failureReasons"] != []
            ):
                continue
            names, absent = result["rolledBack"], result["noPrevious"]
        valid = True
        for name in names:
            target = _CACHE + name
            previous = before.get(target + ".prev")
            current = before.get(target)
            restored = after.get(target)
            valid = (
                valid
                and previous is not None
                and restored is not None
                and "hex" in previous
                and "hex" in restored
                and restored["hex"] == previous["hex"]
            )
            if current is not None:
                valid = valid and after.get(target + ".prev", {}).get(
                    "hex"
                ) == current.get("hex")
        for name in absent:
            target = _CACHE + name
            valid = (
                valid
                and target + ".prev" not in before
                and before.get(target) == after.get(target)
            )
        if valid:
            return True
    return False


YAML_UPDATE_OPERATIONS_COVERAGE_POLICY = FamilyCoveragePolicy(
    "yaml-update-operations",
    tuple(
        CoveragePredicate(
            "yaml-update-operations." + suffix,
            "yaml-update-operations.execute",
            "yaml-update-operations.execute",
            family,
            (symbol,),
            partial(matcher, api),
            runtime_operations=(api,),
        )
        for suffix, symbol, api, family, matcher in (
            (
                "check",
                "check_yaml_update",
                "yaml_check_update",
                "values",
                matches_check,
            ),
            (
                "data-check",
                "check_yaml_data_update",
                "yaml_data_check_update",
                "values",
                matches_check,
            ),
            (
                "apply",
                "apply_yaml_update_with_decision",
                "yaml_apply_update",
                "durable-effects",
                matches_apply,
            ),
            (
                "data-apply",
                "apply_yaml_data_update_with_decision",
                "yaml_data_apply_update",
                "durable-effects",
                matches_apply,
            ),
            (
                "rollback",
                "rollback_yaml_update",
                "yaml_rollback_update",
                "durable-effects",
                matches_rollback,
            ),
            (
                "data-rollback",
                "rollback_yaml_data_update",
                "yaml_data_rollback_update",
                "durable-effects",
                matches_rollback,
            ),
        )
    ),
)
