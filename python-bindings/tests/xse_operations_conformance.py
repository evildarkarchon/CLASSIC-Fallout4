"""Observe fixture-owned XSE metadata and detection through Python bindings."""

import tempfile
from pathlib import Path


def observe_xse_operations(fixture):
    """Use only fixed local filenames and normalize public absence sentinels."""
    import classic_xse

    if (
        set(fixture) != {"files"}
        or not isinstance(fixture["files"], list)
        or any(
            name not in ("f4se_loader.exe", "f4se_1_10_163.dll")
            for name in fixture["files"]
        )
    ):
        raise ValueError("unsupported XSE fixture")
    with tempfile.TemporaryDirectory(prefix="classic-xse-conformance-") as directory:
        root = Path(directory)
        for name in fixture["files"]:
            (root / name).write_bytes(b"")
        kind = classic_xse.XseType.f4se()
        if classic_xse.parse_xse_type("f4se").as_str() != kind.as_str():
            raise ValueError("XSE constructor and parser disagree")
        try:
            detected = classic_xse.detect_xse_version(
                str(root / "f4se_loader.exe"), kind
            )
            version = ".".join(map(str, detected))
        except OSError as error:
            # Only the two native absence cases match Node/CXX's null/empty sentinel.
            if not str(error).startswith(
                ("XSE not found at:", "Failed to detect XSE version:")
            ):
                raise
            version = None
        info = classic_xse.get_xse_info(str(root), kind)
        return {
            "typeName": kind.as_str(),
            "loaderName": kind.loader_name(),
            "dllPrefix": kind.dll_prefix(),
            "installed": classic_xse.is_xse_installed(str(root), kind),
            "version": version,
            "info": {
                "typeName": info.xse_type().as_str(),
                "installed": info.installed(),
                "version": None
                if info.version() is None
                else ".".join(map(str, info.version())),
            },
            "files": [
                {"path": path.name, "hex": path.read_bytes().hex()}
                for path in sorted(root.iterdir())
            ],
        }
