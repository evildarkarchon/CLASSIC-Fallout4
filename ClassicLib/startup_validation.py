"""Entrypoint bootstrap for Rust binding contract validation.

Import this module before importing other ClassicLib modules in entrypoints.
It validates required Rust bindings immediately and raises typed binding
exceptions with remediation text when anything is missing.
"""

from __future__ import annotations

from ClassicLib.integration.factory import validate_rust_modules


def ensure_startup_bindings(contract: str = "startup_all") -> None:
    """Validate required Rust bindings for a startup contract."""
    validate_rust_modules(contract)


# Validate at import time so entrypoints fail early with typed diagnostics.
ensure_startup_bindings("startup_all")
