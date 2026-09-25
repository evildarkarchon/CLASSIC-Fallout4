"""Input-only native typed INI cache and ModIniScanner observations."""

import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from file_operations_conformance import _files, _owned_path


def observe_mod_ini(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Read controlled configuration files and project native cache/scan results."""
    import classic_scangame as native

    with tempfile.TemporaryDirectory(prefix="classic-mod-ini-") as directory:
        root = Path(directory)
        for path, content in fixture["files"].items():
            target = _owned_path(root, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content.encode("utf-8"))
        observation = {"operation": fixture["operation"], "before": _files(root)}
        if fixture["operation"] == "cache":
            cache = native.RustConfigFileCache(root)
            path = cache.get_path("sample.ini")
            scale = cache.get_float("sample.ini", "Settings", "scale")
            observation["result"] = {
                "names": sorted(cache.config_files()),
                "contains": cache.contains("sample.ini"),
                "path": None if path is None else path.relative_to(root).as_posix(),
                "name": cache.get_str("sample.ini", "Settings", "name"),
                "enabled": cache.get_bool("sample.ini", "Settings", "enabled"),
                "count": cache.get_int("sample.ini", "Settings", "count"),
                "scale": None if scale is None else f"{scale:.3f}",
                "hasName": cache.has_setting("sample.ini", "Settings", "name"),
                "missing": cache.get_str("absent.ini", "Settings", "name"),
                "duplicates": {
                    name: sorted(path.relative_to(root).as_posix() for path in paths)
                    for name, paths in cache.get_duplicates().items()
                },
            }
        elif fixture["operation"] == "duplicates":
            detector = native.ConfigDuplicateDetector()

            def groups(values: Any) -> list[dict[str, Any]]:
                """Keep the native canonical-path choice and ordered duplicate membership."""
                return sorted(
                    [
                        {
                            "original": group.original.relative_to(root).as_posix(),
                            "duplicates": sorted(
                                path.relative_to(root).as_posix()
                                for path in group.duplicates
                            ),
                        }
                        for group in values
                    ],
                    key=lambda group: group["original"],
                )

            def mapping(values: Any) -> dict[str, list[str]]:
                """Normalize only invocation-root spelling in actual map values."""
                return {
                    name: [path.relative_to(root).as_posix() for path in paths]
                    for name, paths in values.items()
                }

            initial = groups(detector.detect_duplicates(root))
            initial_map = mapping(detector.get_duplicate_map(root))
            if groups(native.detect_config_duplicates(root)) != initial:
                raise ValueError(
                    "duplicate convenience function disagrees with detector"
                )
            _owned_path(root, fixture["replacement"]["path"]).write_bytes(
                fixture["replacement"]["content"].encode("utf-8")
            )
            observation["result"] = {
                "initialGroups": initial,
                "initialMap": initial_map,
                "afterGroups": groups(detector.detect_duplicates(root)),
                "afterMap": mapping(detector.get_duplicate_map(root)),
            }
        elif fixture["operation"] == "scan":
            scanner = native.RustModIniScanner()
            value = scanner.scan(root, fixture["game"])
            if native.scan_mod_inis(root, fixture["game"]) != value.message:
                raise ValueError("mod INI convenience alias changed report text")
            observation["result"] = {
                "message": value.message.replace(str(root), "<ROOT>").replace(
                    "\\", "/"
                ),
                "issues": [
                    {
                        "filePath": issue.file_path.relative_to(root).as_posix(),
                        "section": issue.section,
                        "setting": issue.setting,
                        "currentValue": issue.current_value,
                        "recommendedValue": issue.recommended_value,
                        "description": issue.description,
                        "severity": str(issue.severity).split(".")[-1],
                    }
                    for issue in value.issues
                ],
                "vsync": [
                    {
                        "path": entry.file_path.relative_to(root).as_posix(),
                        "setting": entry.setting,
                    }
                    for entry in value.vsync_files
                ],
                "duplicates": [
                    {
                        "name": entry.file_name,
                        "paths": sorted(
                            path.relative_to(root).as_posix() for path in entry.paths
                        ),
                    }
                    for entry in value.duplicates
                ],
            }
        else:
            raise ValueError("unsupported mod INI operation")
        observation["files"] = _files(root)
        return observation
