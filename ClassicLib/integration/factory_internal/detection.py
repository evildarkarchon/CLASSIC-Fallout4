"""Low-level Rust component detection helpers for integration factory."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

REQUIRED_RUST_MODULES: list[tuple[str, str | None]] = [
    ("classic_scanlog", "LogParser"),
    ("classic_scanlog", "PluginAnalyzer"),
    ("classic_scanlog", "RecordScanner"),
    ("classic_scanlog", "ReportGenerator"),
    ("classic_file_io", "FileIOCore"),
    ("classic_yaml", "YamlOperations"),
]


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


def get_component(module_name: str, class_name: str) -> Any:
    """Get a Rust component or raise ImportError."""
    available, component = detect_component(module_name, class_name)
    if not available:
        msg = f"Rust component {module_name}.{class_name} not available"
        raise ImportError(msg)
    return component


def validate_rust_modules() -> None:
    """Validate that all required Rust modules are importable at startup."""
    for module_name, class_name in REQUIRED_RUST_MODULES:
        available, _ = detect_component(module_name, class_name)
        if not available:
            component_label = f"{module_name}.{class_name}" if class_name else module_name
            msg = (
                f"Required Rust module '{component_label}' is not available. "
                f"CLASSIC cannot start without its Rust extensions. "
                f"Please reinstall CLASSIC or rebuild Rust modules with: ./rebuild_rust.ps1"
            )
            raise RuntimeError(msg)
    logger.debug("All required Rust modules validated successfully")
