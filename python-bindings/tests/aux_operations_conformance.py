"""Observe pure auxiliary operations through the installed public Python modules."""

from __future__ import annotations

import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


def _result(operation: Callable[[], str]) -> dict[str, Any]:
    """Transport documented ValueError domain failures without masking runner bugs."""
    try:
        return {"value": operation(), "error": None}
    except ValueError as error:
        return {"value": None, "error": str(error)}


def observe_aux_operations(family: str, fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Call only public operations using authored inputs, never pack expectations."""
    request = fixture["request"]
    if family.startswith("version-") and "operation" in request:
        from version_extended_conformance import observe_version_extended

        return observe_version_extended(fixture)
    if family == "web-operations":
        import classic_web as web

        url = request["url"]
        return {
            "valid": web.is_valid_url(url),
            "validated": _result(lambda: web.validate_url(url)),
            "domain": _result(lambda: web.extract_domain(url)),
            "joined": _result(lambda: web.join_url(url, request["path"])),
            "query": _result(
                lambda: web.build_url_with_query(
                    url, [tuple(pair) for pair in request["params"]]
                )
            ),
        }
    if family == "resource-operations":
        import classic_resource as resource

        parsed = resource.parse_resource_type(request["type"])
        info = resource.ResourceInfo(request["path"])
        observation = {
            "detected": resource.detect_resource_type(request["path"]).as_str(),
            "supported": resource.is_supported_resource(request["path"]),
            "parsed": parsed.as_str(),
            "typeCatalog": [
                getattr(resource.ResourceType, name)().as_str()
                for name in request["types"]
            ],
            "extensions": parsed.extensions(),
            "info": {
                "path": info.path(),
                "type": info.resource_type().as_str(),
                "size": info.size(),
            },
        }
        with tempfile.TemporaryDirectory(
            prefix="classic-resource-conformance-"
        ) as directory:
            root = Path(directory)
            for relative, content in fixture["files"].items():
                path = _owned(root, relative)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content.encode("utf-8"))
            observation["resources"] = sorted(
                (
                    {
                        "path": Path(item.path()).relative_to(root).as_posix(),
                        "type": item.resource_type().as_str(),
                        "size": item.size(),
                    }
                    for item in resource.enumerate_resources(str(root), None)
                ),
                key=lambda item: item["path"],
            )
            observation["counts"] = sorted(
                (
                    {"type": kind.as_str(), "count": count}
                    for kind, count in resource.count_resources_by_type(str(root))
                ),
                key=lambda item: item["type"],
            )
            validation = []
            for relative in request["validate"]:
                error = None
                try:
                    resource.validate_resource(str(_owned(root, relative)))
                except OSError as failure:
                    if not str(failure).startswith("Resource not found: "):
                        raise
                    error = "not_found"
                except ValueError as failure:
                    if not str(failure).startswith("Path is not a file: "):
                        raise
                    error = "invalid_type"
                validation.append({"path": relative, "error": error})
            observation["validation"] = validation
            # Python obtains size-bearing ResourceInfo through enumeration; it
            # has no separate public with-size constructor.
            observation["sizedInfo"] = observation["resources"][0]
            # Inventory all actual files, including unsupported resources, so
            # silent mutation or unexpected output cannot hide behind type filters.
            files = []
            for path in sorted(root.rglob("*")):
                if path.is_symlink():
                    raise ValueError("unexpected symlink in resource workspace")
                if path.is_file():
                    files.append(
                        {
                            "path": path.relative_to(root).as_posix(),
                            "hex": path.read_bytes().hex(),
                        }
                    )
                elif not path.is_dir():
                    raise ValueError("unexpected special file in resource workspace")
            observation["files"] = sorted(files, key=lambda item: item["path"])
        return observation
    if family == "version-operations":
        import classic_version as version

        parsed = _result(
            lambda: ".".join(map(str, version.parse_version(request["version"])))
        )
        optional = version.try_parse_version(request["version"])
        comparison = formatted = None
        if parsed["error"] is None:
            # Python transports versions as triples; invoke its public parser for
            # both operands rather than rebuilding a domain parser in the runner.
            native = version.parse_version(request["version"])
            other = version.parse_version(request["other"])
            comparison = version.compare_versions(native, other)
            # This binding uses None for its default "v" prefix and an empty
            # prefix for the core's unprefixed formatting operation.
            formatted = version.format_version(native, "")
        return {
            "parsed": parsed,
            "optional": None if optional is None else ".".join(map(str, optional)),
            "comparison": comparison,
            "formatted": formatted,
        }
    raise ValueError("unsupported auxiliary owner domain")


def _owned(root: Path, relative: str) -> Path:
    """Reject escape paths before writing temporary resource fixture files."""
    if (
        not relative
        or any(char in relative for char in "\\:")
        or any(part in {"", ".", ".."} for part in relative.split("/"))
    ):
        raise ValueError("resource fixture path must be contained")
    return root / relative
