"""Observe fixture-owned XSE metadata and detection through Python bindings."""

import tempfile
from pathlib import Path


def observe_xse_operations(fixture):
    """Use only fixed local filenames and normalize public absence sentinels."""
    import classic_xse

    variant = fixture.get("kind", "F4SE")
    if (
        set(fixture) not in ({"files"}, {"files", "kind"})
        or variant not in {"F4SE", "F4SEVR", "SKSE", "SKSE64", "SKSEVR", "SFSE"}
        or not isinstance(fixture["files"], list)
        or any(
            name
            not in (f"{variant.lower()}_loader.exe", f"{variant.lower()}_1_10_163.dll")
            for name in fixture["files"]
        )
    ):
        raise ValueError("unsupported XSE fixture")
    with tempfile.TemporaryDirectory(prefix="classic-xse-conformance-") as directory:
        root = Path(directory)
        for name in fixture["files"]:
            (root / name).write_bytes(b"")
        kind = getattr(classic_xse.XseType, variant.lower())()
        if classic_xse.parse_xse_type(variant).as_str() != kind.as_str():
            raise ValueError("XSE constructor and parser disagree")
        if str(kind) != kind.as_str() or repr(kind) != f"XseType.{variant.lower()}()":
            raise ValueError("XSE type display disagrees with native identity")
        for other in ("F4SE", "F4SEVR", "SKSE", "SKSE64", "SKSEVR", "SFSE"):
            if kind.__eq__(classic_xse.parse_xse_type(other)) is not (other == variant):
                raise ValueError("XSE equality changed type identity")
        try:
            detected = classic_xse.detect_xse_version(
                str(root / kind.loader_name()), kind
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
        constructed = classic_xse.XseInfo(kind, str(root))
        if (
            constructed.installed()
            or constructed.version() is not None
            or constructed.xse_type().as_str() != kind.as_str()
        ):
            raise ValueError("XSE information constructor changed its initial state")
        for value in (info, constructed):
            if (
                Path(value.path()) != root
                or Path(value.loader_path()) != root / kind.loader_name()
                or value.check_installed() != info.installed()
            ):
                raise ValueError(
                    "XSE path/installation accessors disagree with owned files"
                )
            formatted_version = (
                "Unknown"
                if value.version() is None
                else ".".join(map(str, value.version()))
            )
            display = f"XseInfo(type='{value.xse_type().as_str()}', installed={str(value.installed()).lower()}, version='{formatted_version}')"
            if str(value) != display or repr(value) != display:
                raise ValueError("XSE information display disagrees with public values")
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
