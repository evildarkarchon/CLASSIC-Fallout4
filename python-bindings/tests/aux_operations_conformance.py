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
        sites = []
        for factory in (
                web.ModSite.nexus_mods,
                web.ModSite.bethesda_net,
                web.ModSite.mod_db,
        ):
            site = factory()
            if (
                    str(site) != site.name()
                    or repr(site) != f"ModSite.{factory.__name__}()"
            ):
                raise ValueError(
                    "ModSite display methods disagree with public site identity"
                )
            if not site == factory() or (site == web.ModSite.nexus_mods()) != (
                    factory == web.ModSite.nexus_mods
            ):
                raise ValueError("ModSite equality disagrees with constructor identity")
            sites.append({"name": site.name(), "baseUrl": site.base_url()})
        return {
            "userAgent": web.get_user_agent(),
            "userAgentWithSuffix": web.get_user_agent_with_suffix(request["suffix"]),
            "sites": sites,
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
        catalog = []
        for name in request["types"]:
            variant = getattr(resource.ResourceType, name)()
            token = variant.as_str()
            if str(variant) != token or repr(variant) != f"ResourceType.{token}()":
                raise ValueError("resource type representation lost its public token")
            if (variant == parsed) != (token == parsed.as_str()):
                raise ValueError(
                    "resource type equality disagrees with public identity"
                )
            catalog.append(token)

        def observed_info(value, root=None):
            """Verify Python representation layout against the resource's observed public fields."""
            path, kind, size = (
                value.path(),
                value.resource_type().as_str(),
                value.size(),
            )
            expected = f"ResourceInfo(path='{path}', type='{kind}', size={size})"
            if str(value) != expected or repr(value) != expected:
                raise ValueError("resource representation lost path, type, or size")
            return {
                "path": path
                if root is None
                else Path(path).relative_to(root).as_posix(),
                "type": kind,
                "size": size,
            }

        observation = {
            "detected": resource.detect_resource_type(request["path"]).as_str(),
            "supported": resource.is_supported_resource(request["path"]),
            "parsed": parsed.as_str(),
            "typeCatalog": catalog,
            "extensions": parsed.extensions(),
            "info": observed_info(info),
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
                    observed_info(item, root)
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
