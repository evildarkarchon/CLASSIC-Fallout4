"""Narrow evidence and hermetic inputs for the remaining version operations."""

import re
from collections.abc import Mapping
from functools import partial

from ..coverage import CoveragePredicate

OPERATIONS = {
    "extract": (
        "extract_version_from_filename",
        "extract_version_from_log",
        "extract_all_versions",
    ),
    "known-fallout4": ("is_known_fallout4_version",),
    "known-f4se": ("is_known_f4se_version",),
    "pe-extract": ("extract_pe_version",),
    "pe-path": ("is_valid_executable_path",),
}


def observation(operation, value):
    """Require complete operation-specific observations without crediting unrelated calls."""
    if not isinstance(value, Mapping):
        return False
    if operation == "extract":
        return (
            set(value) == {"filename", "log", "all"}
            and all(
                value[k] is None or isinstance(value[k], str)
                for k in ("filename", "log")
            )
            and isinstance(value["all"], list)
            and all(isinstance(v, str) for v in value["all"])
        )
    if operation.startswith("known-"):
        return set(value) == {operation} and type(value[operation]) is bool
    key = "peVersion" if operation == "pe-extract" else "validPath"
    return set(value) == {key} and (
        isinstance(value[key], str)
        if operation == "pe-extract"
        else type(value[key]) is bool
    )


def validate_fixture(fixture, expected):
    """Reject escaped paths, malformed bytes, and unrecognized operation requests."""
    request = fixture["request"]
    operation = request.get("operation")
    fields = {
        "extract": {"operation", "filename", "content"},
        "known-fallout4": {"operation", "version"},
        "known-f4se": {"operation", "version"},
        "pe-extract": {"operation", "path"},
        "pe-path": {"operation", "path"},
    }
    if (
        operation not in fields
        or set(request) != fields[operation]
        or not all(isinstance(v, str) for v in request.values())
    ):
        raise ValueError("malformed extended version request")
    pe = operation.startswith("pe-")
    if set(fixture) != ({"request", "files"} if pe else {"request"}):
        raise ValueError("version fixture must contain only authored inputs")
    if pe:
        from .aux_operations import _relative

        if (
            not _relative(request["path"])
            or not isinstance(fixture["files"], Mapping)
            or not all(
                _relative(k)
                and isinstance(v, str)
                and re.fullmatch(r"(?:[0-9a-f]{2})*", v)
                for k, v in fixture["files"].items()
            )
        ):
            raise ValueError("PE fixtures must use contained paths and hex bytes")
    if not observation(operation, expected):
        raise ValueError("malformed extended version observation")


def predicates(family):
    """Return exact predicates matching only the public operations executed per scenario."""
    groups = {
        "version-extraction": ["extract", "known-fallout4"],
        "version-f4se": ["known-f4se"],
        "version-pe": ["pe-extract"],
        "version-pe-path": ["pe-path"],
    }
    for operation in groups.get(family, ()):
        symbols = OPERATIONS[operation]
        for symbol in symbols:
            aliases = {
                "extract_pe_version": ("extract_pe_version_string",),
                "is_valid_executable_path": ("is_valid_pe_path",),
            }.get(symbol, ())
            yield CoveragePredicate(
                id="version-" + symbol.replace("_", "-"),
                capability_id=family + ".observe",
                action=family + ".observe",
                observation_family="version-" + operation,
                rust_symbols=(symbol,),
                matches=partial(observation, operation),
                runtime_operations=(None, symbol, *aliases),
            )
