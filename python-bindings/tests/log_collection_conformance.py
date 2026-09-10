"""Input-only log moves, XSE copies, and additive custom-directory discovery."""

import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from file_operations_conformance import _files, _owned_path


def observe_log_collection(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Execute full and individual collection APIs while inventorying actual bytes."""
    from classic_file_io import PyLogCollector

    with tempfile.TemporaryDirectory(prefix="classic-log-collection-") as directory:
        root = Path(directory)
        for folder in ("base", "xse", "custom"):
            (root / folder).mkdir()
        for path, content in fixture["files"].items():
            target = _owned_path(root, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content.encode("utf-8"))
        collector = PyLogCollector(
            str(root / "base"), str(root / "xse"), str(root / "custom")
        )
        normalize = lambda paths: sorted(
            Path(path).relative_to(root).as_posix() for path in paths
        )
        result = {"before": _files(root), "first": normalize(collector.collect_all())}
        if normalize(collector.collect_crash_logs()) != result["first"]:
            raise ValueError("crash-only discovery disagrees with full collection")
        if (
            Path(collector.crash_logs_dir()) != root / "base/Crash Logs"
            or Path(collector.pastebin_dir()) != root / "base/Crash Logs/Pastebin"
        ):
            raise ValueError(
                "collector path accessors disagree with durable directories"
            )
        result["afterFirst"] = _files(root)
        for path, content in fixture["later"].items():
            _owned_path(root, path).write_bytes(content.encode("utf-8"))
        moved = collector.move_from_base_folder()
        copied = collector.copy_from_xse_folder()
        if moved != sum(
            path.startswith("base/") for path in fixture["later"]
        ) or copied != sum(path.startswith("xse/") for path in fixture["later"]):
            raise ValueError("individual collector returned wrong move/copy counts")
        result["second"] = normalize(collector.collect_crash_logs())
        if normalize(collector.collect_all()) != result["second"]:
            raise ValueError("full collection disagrees after individual operations")
        result["files"] = _files(root)
        return result
