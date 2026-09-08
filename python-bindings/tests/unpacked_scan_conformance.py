"""Native loose-file scanning with complete read-only filesystem observations."""

import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from file_operations_conformance import _files, _owned_path
from scan_game_conformance import _directories


def _issues(value: Any, root: Path) -> dict[str, list[str]]:
    """Project every native set and preserve DDS paths separately from issue counts."""
    fields = {
        "animation": value.animdata,
        "formats": value.tex_frmt,
        "sounds": value.snd_frmt,
        "scripts": value.xse_file,
        "previs": value.previs,
    }
    count = sum(len(values) for values in fields.values())
    if value.total_count() != count or value.has_issues() is not bool(count):
        raise ValueError("unpacked summary counted DDS inventory as issues")
    result = {
        key: sorted(text.replace("\\", "/") for text in values)
        for key, values in fields.items()
    }
    result["dds"] = sorted(
        path.relative_to(root).as_posix() for path in value.dds_files
    )
    return result


def observe_unpacked_scan(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Execute public object and convenience scanners over identical owned files."""
    import classic_scangame as native

    with tempfile.TemporaryDirectory(prefix="classic-unpacked-") as directory:
        root = Path(directory)
        for path in fixture["directories"]:
            _owned_path(root, path).mkdir(parents=True, exist_ok=True)
        for path, content in fixture["files"].items():
            target = _owned_path(root, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content.encode("utf-8"))
        result = {"beforeFiles": _files(root), "beforeDirectories": _directories(root)}
        scanner = native.UnpackedScanner()
        result["issues"] = _issues(
            scanner.scan_directory(root, fixture["scripts"]), root
        )
        if (
            _issues(native.scan_unpacked_files(root, fixture["scripts"]), root)
            != result["issues"]
        ):
            raise ValueError("unpacked convenience scan disagrees with object scan")
        result.update(files=_files(root), directories=_directories(root))
        return result
