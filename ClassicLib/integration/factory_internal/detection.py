"""Low-level Rust component detection helpers for integration factory."""

from __future__ import annotations

import logging
from typing import Any

from ClassicLib.integration.exceptions import (
    RustBindingImportError,
    RustBindingInitError,
)

logger = logging.getLogger(__name__)

# Canonical startup-all contract used by all Python entrypoints.
STARTUP_ALL_BINDING_CONTRACT: list[tuple[str, str | None]] = [
    ("classic_scanlog", "LogParser"),
    ("classic_scanlog", "PluginAnalyzer"),
    ("classic_scanlog", "RecordScanner"),
    ("classic_scanlog", "ReportGenerator"),
    ("classic_scanlog", "SuspectScanner"),
    ("classic_scanlog", "SettingsValidator"),
    ("classic_scanlog", "GpuDetector"),
    ("classic_scanlog", "FcxModeHandler"),
    ("classic_scanlog", "AnalysisConfig"),
    ("classic_scanlog", "AnalysisResult"),
    ("classic_scanlog", "Orchestrator"),
    ("classic_scanlog", "detect_mods_single"),
    ("classic_scanlog", "detect_mods_double"),
    ("classic_scanlog", "detect_mods_important"),
    ("classic_scanlog", "detect_mods_batch"),
    ("classic_file_io", "FileIOCore"),
    ("classic_yaml", "YamlOperations"),
    ("classic_database", "DatabasePool"),
    ("classic_config", "YamlData"),
    ("classic_path", None),
    ("classic_constants", None),
    ("classic_version", None),
    ("classic_resource", None),
    ("classic_xse", None),
    ("classic_web", None),
    ("classic_message", None),
    ("classic_perf", None),
    ("classic_pybridge", None),
    ("classic_settings", None),
]

BINDING_CONTRACTS: dict[str, list[tuple[str, str | None]]] = {
    "startup_all": STARTUP_ALL_BINDING_CONTRACT,
    "cli": STARTUP_ALL_BINDING_CONTRACT,
    "gui": STARTUP_ALL_BINDING_CONTRACT,
    "tui": STARTUP_ALL_BINDING_CONTRACT,
    "library": STARTUP_ALL_BINDING_CONTRACT,
}


def _binding_label(module_name: str, class_name: str | None = None) -> str:
    return f"{module_name}.{class_name}" if class_name else module_name


def detect_component(module_name: str, class_name: str | None = None) -> tuple[bool, Any | None]:
    """Detect if a Rust component is available via try-import."""
    try:
        module = __import__(module_name)

        if class_name:
            if not hasattr(module, class_name):
                return (False, None)
            return (True, getattr(module, class_name))

        return (True, module)  # noqa: TRY300
    except ImportError:
        return (False, None)


def _load_component_strict(module_name: str, class_name: str | None = None) -> Any:
    """Load a required binding and raise typed errors on failure."""
    binding = _binding_label(module_name, class_name)

    try:
        module = __import__(module_name)
    except ImportError as exc:
        raise RustBindingImportError(binding=binding, details=str(exc)) from exc

    if class_name is None:
        if module is None:
            raise RustBindingInitError(binding=binding, details="Imported module is None")
        return module

    if not hasattr(module, class_name):
        raise RustBindingImportError(binding=binding, details=f"Missing attribute '{class_name}'")

    component = getattr(module, class_name)
    if component is None:
        raise RustBindingInitError(binding=binding, details="Resolved binding attribute is None")
    return component


def get_component(module_name: str, class_name: str | None = None) -> Any:
    """Get a required Rust component or raise typed binding errors."""
    return _load_component_strict(module_name, class_name)


def get_binding_contract(contract: str = "startup_all") -> list[tuple[str, str | None]]:
    """Return an immutable copy of a named binding contract."""
    if contract not in BINDING_CONTRACTS:
        known = ", ".join(sorted(BINDING_CONTRACTS))
        raise ValueError(f"Unknown binding contract '{contract}'. Known contracts: {known}")
    return list(BINDING_CONTRACTS[contract])


def validate_rust_modules(contract: str = "startup_all") -> None:
    """Validate that every required Rust binding in a contract is importable."""
    for module_name, class_name in get_binding_contract(contract):
        _load_component_strict(module_name, class_name)
    logger.debug("Rust binding contract '%s' validated successfully", contract)
