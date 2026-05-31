"""Structured import diagnostics for maintained CLASSIC Python bindings."""

from __future__ import annotations

import importlib
from dataclasses import asdict, dataclass
from types import ModuleType
from typing import Any


EXPECTED_BINDINGS = [
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
    "classic_update",
    "classic_version",
    "classic_version_registry",
    "classic_web",
    "classic_xse",
]


@dataclass(frozen=True)
class BindingDiagnostic:
    """Import status and public surface metadata for one binding module."""

    module: str
    importable: bool
    version: str | None = None
    public_exports: list[str] | None = None
    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable diagnostic dictionary."""

        return asdict(self)


def public_exports(module: ModuleType) -> list[str]:
    """Discover non-private public attributes exposed by a binding module."""

    exports = getattr(module, "__all__", None)
    if exports is None:
        exports = [name for name in dir(module) if not name.startswith("_")]
    return sorted(str(name) for name in exports)[:100]


def inspect_binding(module_name: str) -> BindingDiagnostic:
    """Import a binding module and return structured diagnostics."""

    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001 - report stale wheels and loader failures uniformly.
        return BindingDiagnostic(module=module_name, importable=False, error_type=type(exc).__name__, error_message=str(exc))
    return BindingDiagnostic(module=module_name, importable=True, version=getattr(module, "__version__", None), public_exports=public_exports(module))


def list_bindings(module_names: list[str] | None = None) -> list[BindingDiagnostic]:
    """Inspect all maintained binding modules or a supplied subset."""

    return [inspect_binding(name) for name in (module_names or EXPECTED_BINDINGS)]


def require_binding(module_name: str) -> ModuleType:
    """Import a required binding or raise ImportError with module context."""

    try:
        return importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001 - normalize all dynamic loader failures as binding import failures.
        raise ImportError(f"Required binding {module_name!r} is unavailable: {exc}") from exc
