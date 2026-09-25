"""Observe fixture-seeded Version Registry metadata through actual Python bindings."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def observe_version_registry(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Invoke lookup/matching in a dedicated serial process and restore its cwd.

    Every fixture carries identical YAML because the public registry initializes
    once per process. Unrelated adapter exceptions propagate as execution failures.
    """
    import classic_version_registry

    if set(fixture) != {"operation", "registryYaml", "request"} or fixture[
        "operation"
    ] not in {"lookup", "match", "enumerate", "crashgen", "xse", "details", "values"}:
        raise ValueError("unsupported version registry fixture")
    previous = Path.cwd()
    with tempfile.TemporaryDirectory(
            prefix="classic-version-registry-conformance-"
    ) as directory:
        root = Path(directory)
        (root / "CLASSIC Main.yaml").write_bytes(
            fixture["registryYaml"].encode("utf-8")
        )
        try:
            # Isolate first-use YAML discovery from repository/user configuration.
            os.chdir(root)
            observation = _observe(fixture, classic_version_registry.VersionRegistry())
            if (
                    _observe(fixture, classic_version_registry.get_version_registry())
                    != observation
            ):
                raise ValueError(
                    "registry constructor and singleton entry point disagree"
                )
            files = []
            for path in sorted(root.iterdir()):
                if path.is_symlink() or not path.is_file():
                    raise ValueError(
                        "unexpected non-file in version registry workspace"
                    )
                files.append(
                    {"path": path.name, "content": path.read_bytes().decode("utf-8")}
                )
            return {**observation, "files": files}
        finally:
            os.chdir(previous)


def _observe(fixture: Mapping[str, Any], registry: Any) -> dict[str, Any]:
    """Convert native success/error carriers without inferring results from inputs."""
    request = fixture["request"]
    if fixture["operation"] == "values":
        info = registry.get_by_id(request["id"])
        clone = registry.get_by_id(request["id"])
        other = registry.get_by_id(request["otherId"])
        bounds = info.compatible_range
        crashgen = info.get_crashgen_for_version(request["crashgen"])
        return {
            "result": {
                "range": [bounds.min_version, bounds.max_version],
                "contains": [
                    bounds.contains(version) for version in request["versions"]
                ],
                "versionCompatible": [
                    info.is_compatible_with(version) for version in request["versions"]
                ],
                "crashgenCompatible": [
                    crashgen.is_compatible_with(version)
                    for version in request["versions"]
                ],
                "compatibleCrashgens": [
                    [
                        config.version
                        for config in info.get_compatible_crashgens(version)
                    ]
                    for version in request["versions"]
                ],
                "defaultCrashgens": [
                    config.version for config in info.get_compatible_crashgens()
                ],
                "versions": info.get_crashgen_version_strings(),
                "selected": crashgen.version,
                "missing": info.get_crashgen_for_version("missing"),
                "equalClone": info == clone,
                "differentId": info == other,
                "hashClone": hash(info) == hash(clone),
            },
            "error": None,
        }
    if fixture["operation"] == "details":
        try:
            by_version = registry.get_by_version(request["version"])
        except ValueError as failure:
            if not str(failure).startswith("Invalid version: Invalid version string:"):
                raise
            return {"result": None, "error": {"code": "invalid_version"}}
        by_name = registry.get_by_short_name(request["shortName"])
        info = registry.get_by_id(request["id"])
        handling = registry.unknown_version_handling
        if (
                info is not None
                and info.address_library is not None
                and info.address_library.filename
                != registry.get_address_library_filename(info.version, info.is_vr)
        ):
            raise ValueError(
                "address-library carrier and public filename query disagree"
            )
        if (
                info is not None
                and info.get_crashgen_version_strings()
                != registry.get_crashgen_versions(request["id"])
        ):
            raise ValueError("registry and value crashgen version strings disagree")
        return {
            "result": {
                "byVersion": None if by_version is None else by_version.id,
                "byShortName": None if by_name is None else by_name.id,
                "correctIds": sorted(
                    info.id for info in registry.get_correct_versions(request["isVr"])
                ),
                "wrongIds": sorted(
                    info.id for info in registry.get_wrong_versions(request["isVr"])
                ),
                "addressLibrary": registry.get_address_library_filename(
                    request["version"], request["isVr"]
                ),
                "crashgenVersions": registry.get_crashgen_versions(request["id"]),
                "exeHashes": sorted(
                    registry.get_all_exe_hashes(request["game"], request["isVr"])
                ),
                "scriptHashes": {
                    key: sorted(values)
                    for key, values in registry.get_all_script_hashes(
                        request["game"], request["isVr"]
                    ).items()
                },
                "versionScriptHashes": registry.get_script_hashes_for_version(
                    request["id"]
                ),
                "strategy": handling.strategy,
                "logLevel": handling.log_level,
                "defaultId": handling.get_default(request["game"]),
                "compatible": info is not None
                              and info.is_compatible_with(request["version"]),
                "snapshotIds": [
                    info.id
                    for info in registry.get_all_for_game(
                        request["game"], request["isVr"]
                    )
                ],
            },
            "error": None,
        }
    if fixture["operation"] == "enumerate":
        ids = sorted(info.id for info in registry.get_all())
        filtered = sorted(
            info.id
            for info in registry.get_all_for_game(request["game"], request["isVr"])
        )
        return {
            "result": {"ids": ids, "count": len(ids), "filteredIds": filtered},
            "error": None,
        }
    if fixture["operation"] == "crashgen":
        configs = [
            _crashgen(config) for config in registry.get_crashgen_configs(request["id"])
        ]
        selected = registry.get_crashgen_for_version(request["id"], request["version"])
        info = registry.get_by_id(request["id"])
        if info is not None:
            value_selected = info.get_crashgen_for_version(request["version"])
            if (None if selected is None else _crashgen(selected)) != (
                    None if value_selected is None else _crashgen(value_selected)
            ):
                raise ValueError("registry and value crashgen selection disagree")
        return {
            "result": {
                "configs": configs,
                "selected": None if selected is None else _crashgen(selected),
            },
            "error": None,
        }
    if fixture["operation"] == "xse":
        info = registry.get_by_id(request["id"])
        xse = None if info is None else info.xse
        result = (
            None
            if xse is None
            else {
                "acronym": xse.acronym,
                "fullName": xse.full_name,
                "compatibleVersion": xse.compatible_version,
                "loader": xse.loader,
                "fileCount": xse.file_count,
            }
        )
        return {"result": result, "error": None}
    if fixture["operation"] == "lookup":
        info = registry.get_by_id(request["id"])
        result = (
            None
            if info is None
            else {
                "id": info.id,
                "version": info.version,
                "shortName": info.short_name,
                "game": info.game,
                "docsName": info.docs_name,
                "steamId": info.steam_id,
                "isVr": info.is_vr,
            }
        )
        return {"result": result, "error": None}
    try:
        matched = registry.match_version(
            request["version"], request["game"], request["isVr"]
        )
        import classic_version_registry

        convenience = classic_version_registry.match_version_string(
            request["version"], request["game"], request["isVr"]
        )
        if _match_result(matched) != _match_result(convenience):
            raise ValueError("registry matching entry points disagree")
    except ValueError as failure:
        if not str(failure).startswith("Invalid version: Invalid version string:"):
            raise
        return {"result": None, "error": {"code": "invalid_version"}}
    return {"result": _match_result(matched), "error": None}


def _match_result(matched: Any) -> dict[str, Any]:
    """Compare both Python matching entry points through native result fields."""
    confidence = matched.confidence_enum
    copy = matched.confidence_enum
    if confidence != copy or hash(confidence) != hash(copy):
        raise ValueError("confidence copies disagree in equality or hash")
    if confidence.is_high_confidence() != (str(confidence) in {"exact", "range"}):
        raise ValueError("confidence predicate disagrees with public confidence name")
    if str(confidence) != matched.confidence:
        raise ValueError("confidence object and public string disagree")
    return {
        "matchedId": None if matched.version_info is None else matched.version_info.id,
        "confidence": str(matched.confidence),
        "message": matched.message,
    }


def _crashgen(config: Any) -> dict[str, Any]:
    """Project common crash generator metadata from the native object."""
    return {
        "version": config.version,
        "name": config.name,
        "acronym": config.acronym,
        "dllFile": config.dll_file,
        "description": config.description,
        "downloadUrl": config.download_url,
    }
