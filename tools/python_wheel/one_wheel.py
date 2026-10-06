#!/usr/bin/env python3
"""Install hygiene and verification for the one CLASSIC Python wheel.

The 18 direct-import ``classic_*`` modules ship in one wheel
(``classic-python-bindings``): 18 pure-Python facade packages over one native
extension, ``_classic_native._native``. Before #259 each module was its own
maturin wheel (``classic-config-py``, ..., ``classic-shared-py``) whose package
directory held a private ``classic_<name>.pyd``. Those legacy files share
directory names with the new facades, so a stale legacy ``.pyd`` or an
uninstall of a legacy distribution could make a broken install look healthy or
delete the new facade files. This tool removes them before install and proves
the result afterwards.

Subcommands (run with the interpreter of the environment to inspect):

``remove-obsolete``
    Delete every legacy distribution's recorded files, its ``.dist-info``, and
    any leftover legacy native module or top-level stub for the 18 facades.
    Run this *before* installing the new wheel.

``verify --expected-version X``
    Import all 18 facades and check ``__version__``, that each facade is the
    pure-Python package from the one wheel, that every exported name is the
    canonical object of its native submodule, and that no legacy distribution
    or native artifact remains. Prints a JSON report; exits non-zero on failure.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import shutil
import sys
import sysconfig
from pathlib import Path

#: The 18 direct-import facades served by the one wheel.
FACADES: tuple[str, ...] = (
    "classic_config",
    "classic_database",
    "classic_file_io",
    "classic_message",
    "classic_path",
    "classic_perf",
    "classic_registry",
    "classic_resource",
    "classic_scangame",
    "classic_scanlog",
    "classic_settings",
    "classic_shared",
    "classic_update",
    "classic_user_settings",
    "classic_version",
    "classic_version_registry",
    "classic_web",
    "classic_xse",
)

#: Distribution name of the one wheel.
DISTRIBUTION = "classic-python-bindings"
#: Package that owns the native extension.
NATIVE_PACKAGE = "_classic_native"
#: Native extension module inside :data:`NATIVE_PACKAGE`.
NATIVE_MODULE = f"{NATIVE_PACKAGE}._native"
#: File suffixes of compiled extension modules.
NATIVE_SUFFIXES = (".pyd", ".so", ".dll", ".dylib")


def legacy_distribution(facade: str) -> str:
    """Return the normalized legacy per-module distribution name for a facade.

    ``classic_config`` was shipped as ``classic-config-py``, whose wheel and
    ``.dist-info`` use the normalized form ``classic_config_py``.
    """
    return f"{facade}_py"


def site_packages() -> Path:
    """Return the running interpreter's purelib site-packages directory."""
    return Path(sysconfig.get_paths()["purelib"])


def _normalized(name: str) -> str:
    return name.lower().replace("-", "_").replace(".", "_")


def _legacy_dist_infos(root: Path) -> list[Path]:
    """Find ``.dist-info`` directories of the 18 legacy per-module wheels."""
    legacy = {legacy_distribution(facade) for facade in FACADES}
    found = []
    for entry in sorted(root.glob("*.dist-info")):
        name = _normalized(entry.name[: -len(".dist-info")].rsplit("-", 1)[0])
        if name in legacy:
            found.append(entry)
    return found


def _legacy_native_files(root: Path) -> list[Path]:
    """Find legacy native modules and stubs that a partial uninstall can leave.

    A legacy wheel installed ``classic_x/classic_x.pyd``; older layouts also
    placed ``classic_x*.pyd`` or ``classic_x.pyi`` directly in site-packages.
    The new facades are pure Python, so any compiled file named after a facade
    is obsolete.
    """
    found: list[Path] = []
    for facade in FACADES:
        package = root / facade
        if package.is_dir():
            found.extend(
                path for path in sorted(package.iterdir())
                if path.is_file() and path.name.startswith(facade)
                and path.suffix in NATIVE_SUFFIXES
            )
        found.extend(
            path for path in sorted(root.glob(f"{facade}*"))
            if path.is_file()
            and (path.suffix in NATIVE_SUFFIXES or path.name == f"{facade}.pyi")
        )
    return found


def remove_obsolete(root: Path) -> list[str]:
    """Remove legacy distributions and native leftovers beneath ``root``.

    Files listed in each legacy ``RECORD`` are deleted first (only paths that
    resolve inside ``root``), then the ``.dist-info`` itself, then any legacy
    native module or top-level stub that remains, and finally facade package
    directories the removal left empty. Returns the removed paths, relative to
    ``root``, for logging.
    """
    removed: list[str] = []
    resolved_root = root.resolve()

    def delete(path: Path) -> None:
        try:
            relative = path.resolve().relative_to(resolved_root)
        except ValueError:
            # A RECORD entry outside site-packages (scripts, data) is never ours to touch.
            return
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
        else:
            return
        removed.append(relative.as_posix())

    for dist_info in _legacy_dist_infos(root):
        record = dist_info / "RECORD"
        if record.is_file():
            for line in record.read_text(encoding="utf-8").splitlines():
                entry = line.split(",", 1)[0].strip()
                if entry and not entry.startswith(dist_info.name):
                    delete(root / entry)
        delete(dist_info)
    for path in _legacy_native_files(root):
        delete(path)
    for facade in FACADES:
        package = root / facade
        pycache = package / "__pycache__"
        if pycache.is_dir() and not (package / "__init__.py").exists():
            delete(pycache)
        if package.is_dir() and not any(package.iterdir()):
            package.rmdir()
            removed.append(facade + "/")
    return removed


def verify(expected_version: str, root: Path | None = None) -> dict[str, object]:
    """Check the installed one-wheel layout and return a JSON-ready report.

    ``report["ok"]`` is ``False`` when any facade fails to import, reports the
    wrong ``__version__``, is not the pure-Python package from the one wheel,
    exports a name that is not its native submodule's canonical object, or when
    a legacy distribution or native artifact remains in ``root``.
    """
    root = root or site_packages()
    errors: list[str] = []
    facades: dict[str, dict[str, object]] = {}

    try:
        native = importlib.import_module(NATIVE_MODULE)
    except Exception as exc:  # noqa: BLE001 - report every loader failure.
        return {"ok": False, "errors": [f"{NATIVE_MODULE}: {type(exc).__name__}: {exc}"]}
    native_file = Path(getattr(native, "__file__", "") or "")

    for facade in FACADES:
        try:
            module = importlib.import_module(facade)
        except Exception as exc:  # noqa: BLE001 - report stale wheels uniformly.
            errors.append(f"{facade}: import failed: {type(exc).__name__}: {exc}")
            continue
        version = getattr(module, "__version__", None)
        origin = Path(getattr(module, "__file__", "") or "")
        facades[facade] = {"version": version, "origin": str(origin)}
        if version != expected_version:
            errors.append(f"{facade}: __version__ {version!r} != {expected_version!r}")
        if origin.name != "__init__.py" or origin.parent.name != facade:
            errors.append(f"{facade}: not loaded from its facade package: {origin}")
        elif any(
            path.suffix in NATIVE_SUFFIXES for path in origin.parent.iterdir()
        ):
            errors.append(f"{facade}: facade package still contains a native module")
        native_facade = sys.modules.get(f"{NATIVE_MODULE}.{facade}")
        if native_facade is None:
            errors.append(f"{facade}: native submodule {NATIVE_MODULE}.{facade} missing")
            continue
        for name in getattr(module, "__all__", ()):
            if getattr(module, name, None) is not getattr(native_facade, name, object()):
                errors.append(f"{facade}.{name}: not the canonical native object")

    try:
        installed = importlib.metadata.version(DISTRIBUTION)
    except importlib.metadata.PackageNotFoundError:
        installed = None
    if installed != expected_version:
        errors.append(f"{DISTRIBUTION}: installed version {installed!r} != {expected_version!r}")

    legacy = [path.name for path in _legacy_dist_infos(root)]
    leftovers = [path.relative_to(root).as_posix() for path in _legacy_native_files(root)]
    if legacy:
        errors.append(f"legacy distributions still installed: {legacy}")
    if leftovers:
        errors.append(f"legacy native artifacts remain: {leftovers}")

    return {
        "ok": not errors,
        "errors": errors,
        "native": str(native_file),
        "distribution": installed,
        "facades": facades,
        "site_packages": str(root),
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; see the module docstring for subcommands."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    remove = sub.add_parser("remove-obsolete", help="remove legacy per-module wheels")
    remove.add_argument("--site-packages", type=Path, default=None)
    check = sub.add_parser("verify", help="verify the installed one-wheel layout")
    check.add_argument("--expected-version", required=True)
    check.add_argument("--site-packages", type=Path, default=None)
    args = parser.parse_args(argv)

    root = args.site_packages or site_packages()
    if args.command == "remove-obsolete":
        removed = remove_obsolete(root)
        print(json.dumps({"site_packages": str(root), "removed": removed}, indent=2))
        return 0
    report = verify(args.expected_version, root)
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
