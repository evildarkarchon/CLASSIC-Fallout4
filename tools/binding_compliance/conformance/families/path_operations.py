"""Path-domain fixture validation and narrowly attributed runtime observations."""

from __future__ import annotations

import json
from collections.abc import Mapping
from functools import partial
from pathlib import Path
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _relative(value: object) -> bool:
    """Accept portable contained fixture names, excluding host-dependent paths."""
    return (
        isinstance(value, str)
        and bool(value)
        and not any(c in value for c in "\\:")
        and all(part not in {"", ".", ".."} for part in value.split("/"))
    )


def validate_path_operations_pack(
    document: Mapping[str, Any], root: Path
) -> tuple[Path, ...]:
    """Reject malformed or escaping input fixtures before an adapter is launched."""
    family = document["familyId"]
    action = (
        "path-operations.validate"
        if family == "path-operations"
        else "path-normalization.resolve"
    )
    fixture_root = (root / document["fixtureRoot"]).resolve()
    paths = []
    for scenario in document["scenarios"]:
        reference = scenario["input"].get("fixtureRef")
        if (
            scenario["action"] != action
            or scenario["input"] != {"fixtureRef": reference}
            or scenario["fixtureRefs"] != [reference]
        ):
            raise ValueError("path scenario must declare its sole input fixture")
        path = (fixture_root / document["fixtures"][reference]).resolve()
        if not path.is_relative_to(fixture_root):
            raise ValueError("path fixture escapes fixture root")
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if set(fixture) != {"directories", "files", "request"}:
            raise ValueError("path fixture has unexpected fields")
        directories, files, request = (
            fixture["directories"],
            fixture["files"],
            fixture["request"],
        )
        if not isinstance(directories, list) or not all(
            _relative(item) for item in directories
        ):
            raise ValueError("path directories must be contained relative paths")
        if not isinstance(files, dict) or not all(
            _relative(key) and isinstance(value, str) for key, value in files.items()
        ):
            raise ValueError("path files must contain relative names and UTF-8 content")
        if family == "path-operations":
            valid = (
                set(request) == {"path", "requiredFiles"}
                and _relative(request["path"])
                and isinstance(request["requiredFiles"], list)
                and all(_relative(item) for item in request["requiredFiles"])
            )
            observation = _validation_observation(scenario["expected"])
        else:
            valid = (
                set(request) == {"base", "components", "validatePaths"}
                and _relative(request["base"])
                and isinstance(request["components"], list)
                and all(
                    _relative(item) or item in {".", ".."}
                    for item in request["components"]
                )
                and isinstance(request["validatePaths"], list)
                and all(_relative(item) for item in request["validatePaths"])
            )
            # Parent traversal is allowed only inside the explicitly owned base.
            depth = len(request.get("base", "").split("/"))
            for component in request.get("components", []):
                depth += -1 if component == ".." else (0 if component == "." else 1)
                valid = valid and depth > 0
            observation = _resolution_observation(scenario["expected"])
        if not valid or not observation:
            raise ValueError("path request or expected domain observation is malformed")
        paths.append(path)
    return tuple(paths)


def _validation_observation(value: Mapping[str, Any]) -> bool:
    """Require explicit predicate and Result facts, including domain failures."""
    if (
        set(value) != {"path", "exists", "requiredFiles"}
        or not _relative(value["path"])
        or type(value["exists"]) is not bool
    ):
        return False
    result = value["requiredFiles"]
    return (
        isinstance(result, Mapping)
        and set(result) == {"accepted", "error"}
        and type(result["accepted"]) is bool
        and (
            result["error"] is None
            if result["accepted"]
            else isinstance(result["error"], str) and bool(result["error"])
        )
    )


def _validation_variant(variant: str, value: Mapping[str, Any]) -> bool:
    """Distinguish success, existence miss, wrong kind and required-file failure."""
    if not _validation_observation(value):
        return False
    result = value["requiredFiles"]
    if variant == "success":
        return value["exists"] and result["accepted"]
    prefixes = {
        "missing": "Path does not exist: ",
        "wrong-kind": "Path is not a directory: ",
        "required-missing": "Required file '",
    }
    return (
        not result["accepted"]
        and result["error"].startswith(prefixes[variant])
        and value["exists"] is (variant != "missing")
    )


def _resolution_observation(value: Mapping[str, Any]) -> bool:
    """Require both path values and ordered hit/miss facts from batch validation."""
    return (
        set(value) == {"joinedPath", "normalizedPath", "validation"}
        and isinstance(value["joinedPath"], str)
        and bool(value["joinedPath"])
        and _relative(value["normalizedPath"])
        and isinstance(value["validation"], list)
        and bool(value["validation"])
        and all(
            isinstance(item, Mapping)
            and set(item) == {"path", "exists"}
            and _relative(item["path"])
            and type(item["exists"]) is bool
            for item in value["validation"]
        )
    )


def path_operations_coverage_policy() -> FamilyCoveragePolicy:
    """Credit only the two public operations each validation scenario actually calls."""
    return FamilyCoveragePolicy(
        "path-operations",
        tuple(
            CoveragePredicate(
                id=f"{operation.replace('_', '-')}-{variant}",
                capability_id=capability,
                action="path-operations.validate",
                observation_family="path-validation",
                rust_symbols=(symbol,),
                matches=partial(_validation_variant, variant),
                runtime_operations=(None, operation, *aliases),
                # CXX can export the same name in several namespaces. Exact
                # source identities prevent a new namespace from borrowing proof.
                binding_obligation_ids={
                    "is_valid_path": (
                        "parity:cxx:ef0c70d7c9e34cd5",
                        "parity:cxx:18b69f0fbebc68bc",
                        "parity:cxx:5318454026bb9a08",
                        "parity:node:aux-phase4a-is-valid-path",
                        "parity:python:path.lib.PathValidator.is_valid_path",
                    ),
                    "validate_required_files": (
                        "parity:cxx:cff13ceeb2ccbf58",
                        "parity:node:aux-phase4a-validate-required-files",
                        "parity:python:path.lib.PathValidator.validate_required_files",
                    ),
                }[operation],
            )
            for operation, capability, symbol, aliases in (
                (
                    "is_valid_path",
                    "path-operations.validate",
                    "is_valid_path",
                    ("validate_path", "PathValidator.is_valid_path", "isValidPath"),
                ),
                (
                    "validate_required_files",
                    "path-operations.validate",
                    "validate_required_files",
                    (
                        "path_validate_required_files",
                        "PathValidator.validate_required_files",
                        "validateRequiredFiles",
                    ),
                ),
            )
            for variant in ("success", "missing", "wrong-kind", "required-missing")
        ),
    )


def path_normalization_coverage_policy() -> FamilyCoveragePolicy:
    """Limit shared handler coverage to normalize, join and batch validation."""
    return FamilyCoveragePolicy(
        "path-normalization",
        tuple(
            CoveragePredicate(
                id=operation.replace("_", "-"),
                capability_id="path-normalization.resolve",
                action="path-normalization.resolve",
                observation_family="path-resolution",
                rust_symbols=("PathHandler", operation),
                matches=_resolution_observation,
                runtime_operations=(
                    None,
                    operation,
                    "new",
                    "__init__",
                    "cache_stats",
                    "cache_metrics",
                    "clear_cache",
                    "cleanup_cache",
                    "get_filename",
                    "get_extension",
                    "get_parent",
                    "split_path",
                    "split_path_fast",
                    "is_absolute",
                    "to_absolute",
                    "common_prefix",
                )
                if operation == "normalize_path"
                else (
                    None,
                    operation,
                    "validate_paths_batch_fast",
                ),
            )
            for operation in ("normalize_path", "join_paths", "validate_paths_batch")
        ),
    )
