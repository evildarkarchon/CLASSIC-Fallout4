"""Read valid, input-only BA2 bytes through native Python scanner APIs."""

import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def _issues(value: Any) -> dict[str, list[str]]:
    """Project every actual issue vector and verify public count/query methods."""
    result = {
        "dimensions": value.tex_dims,
        "formats": value.tex_frmt,
        "sounds": value.snd_frmt,
        "scripts": value.xse_file,
    }
    total = sum(len(values) for values in result.values())
    if value.total_count() != total or value.has_issues() is not bool(total):
        raise ValueError("BA2 public summary disagrees with issue vectors")
    return result


def observe_ba2_scan(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Execute direct, discovery, batch and convenience scans without host archive parsing."""
    import classic_scangame as native

    if fixture["operation"] != "full":
        raise ValueError("Python uses the full scanner surface")
    with tempfile.TemporaryDirectory(prefix="classic-ba2-") as directory:
        root = Path(directory)
        path = root / "fixture.ba2"
        path.write_bytes(bytes(fixture["bytes"]))
        scanner = native.BA2Scanner()
        issues = _issues(scanner.scan_archive(path))
        found = sorted(
            value.relative_to(root).as_posix() for value in scanner.find_ba2_files(root)
        )
        batch = [
            [value.relative_to(root).as_posix(), _issues(result)]
            for value, result in scanner.scan_archives_batch([path])
        ]
        if [
            [value.relative_to(root).as_posix(), _issues(result)]
            for value, result in native.scan_all_ba2_archives(root)
        ] != batch:
            raise ValueError("BA2 directory convenience scan disagrees with batch")
        return {
            "issues": issues,
            "found": found,
            "batch": batch,
            "bytes": list(path.read_bytes()),
        }
