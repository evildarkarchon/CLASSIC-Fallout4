"""Actual Address Library factories and plugin checks over disposable files."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory


def observe_xse_plugins(fixture):
    """Read native metadata and compare convenience validation to the typed checker."""
    import classic_scangame as native

    with TemporaryDirectory(prefix="classic-xse-plugins-") as directory:
        root = Path(directory)
        for name, content in fixture["files"].items():
            (root / name).write_bytes(content.encode())
        previous = Path.cwd()
        try:
            # Registry fallback must use embedded data, never ambient checkout YAML.
            os.chdir(root)
            factory = {"Original": "original", "NextGen": "next_gen", "Vr": "vr"}[
                fixture["version"]
            ]
            info = getattr(native.AddressLibInfo, factory)()
            version = getattr(native.GameVersion, fixture["version"])
            checker = native.XseChecker(root, version)
            before = {
                p.name: p.read_bytes().decode() for p in root.iterdir() if p.is_file()
            }
            result = checker.check()
            message = checker.validate()
            if native.check_xse_plugins(root, version) != message:
                raise ValueError("XSE convenience validation disagrees with checker")
            return {
                "info": {
                    "version": str(info.version).split(".")[-1],
                    "filename": info.filename,
                    "description": info.description,
                    "url": info.url,
                },
                "result": str(result).split(".")[-1],
                "message": message,
                "beforeFiles": before,
                "files": {
                    p.name: p.read_bytes().decode()
                    for p in root.iterdir()
                    if p.is_file()
                },
            }
        finally:
            os.chdir(previous)
