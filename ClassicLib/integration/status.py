"""
Status and Monitoring Module

Provides functions for monitoring and reporting the status of Rust components
and their performance characteristics.
"""

from __future__ import annotations

import logging
from typing import Any

__all__ = [
    "RUST_AVAILABLE",
    "RUST_STATUS",
    "get_rust_component_status",
    "is_rust_accelerated",
    "get_performance_multiplier",
    "update_status",
    "print_rust_status",
]

from .config import (
    ALL_COMPONENTS,
    COMPONENT_CATEGORIES,
    PERFORMANCE_MULTIPLIERS,
    PERFORMANCE_THRESHOLD_EXCELLENT,
    PERFORMANCE_THRESHOLD_GOOD,
    PERFORMANCE_THRESHOLD_PARTIAL,
)
from .detector import detect_rust_components, get_available_components

logger = logging.getLogger(__name__)

# Status tracking for diagnostics - exported for backward compatibility
RUST_STATUS: dict[str, dict[str, Any]] = {
    "initialized": {},
    "failed": {},
    "performance_gains": {},
}

# For backward compatibility with old imports
_status_info = RUST_STATUS

# Export RUST_AVAILABLE for backward compatibility
# This is dynamically populated from detect_rust_components()
RUST_AVAILABLE: dict[str, bool] = {}

# Flag to track if initialization has been done
_initialized = False


def _initialize_rust_available() -> None:
    """Initialize RUST_AVAILABLE dictionary with current component status."""
    global RUST_AVAILABLE, _initialized
    if not _initialized:
        RUST_AVAILABLE = detect_rust_components()
        _initialized = True


def _ensure_initialized() -> None:
    """Ensure RUST_AVAILABLE is initialized before use."""
    if not _initialized:
        _initialize_rust_available()


def get_rust_component_status() -> dict[str, Any]:
    """
    Get detailed status of all Rust components.

    Returns:
        Dictionary with comprehensive status information including:
        - available: Dict of component availability
        - initialized: Components successfully initialized
        - failed: Components that failed with reasons
        - performance_gains: Performance improvements per component
        - active_count: Number of active components
        - total_count: Total number of components
        - acceleration_active: Whether any acceleration is active
        - acceleration_level: Overall acceleration level
    """
    components = detect_rust_components()
    info = get_available_components()

    # Update RUST_AVAILABLE for backward compatibility
    global RUST_AVAILABLE
    RUST_AVAILABLE.update(components)

    active_count = sum(1 for v in components.values() if v)
    total_count = len(components)
    percentage = (active_count / total_count * 100) if total_count > 0 else 0

    # Determine acceleration level
    if percentage >= PERFORMANCE_THRESHOLD_EXCELLENT * 100:
        acceleration_level = "FULLY ACCELERATED"
    elif percentage >= PERFORMANCE_THRESHOLD_GOOD * 100:
        acceleration_level = "HIGHLY ACCELERATED"
    elif percentage >= PERFORMANCE_THRESHOLD_PARTIAL * 100:
        acceleration_level = "PARTIALLY ACCELERATED"
    elif active_count > 0:
        acceleration_level = "MINIMAL ACCELERATION"
    else:
        acceleration_level = "NO ACCELERATION"

    # Get performance gains for active components
    performance_gains = {
        comp: PERFORMANCE_MULTIPLIERS.get(comp, "N/A")
        for comp, active in components.items()
        if active
    }

    return {
        "available": components,
        "initialized": _status_info["initialized"],
        "failed": _status_info["failed"],
        "performance_gains": performance_gains,
        "active_count": active_count,
        "total_count": total_count,
        "percentage": percentage,
        "acceleration_active": active_count > 0,
        "acceleration_level": acceleration_level,
        "version": info["version"],
        "disabled": info["disabled"],
    }


def is_rust_accelerated(component_name: str) -> bool:
    """
    Check if a specific component is using Rust acceleration.

    Args:
        component_name: Name of the component to check

    Returns:
        True if the component is using Rust, False otherwise
    """
    _ensure_initialized()
    return RUST_AVAILABLE.get(component_name, False)


def get_performance_multiplier(component_name: str) -> str:
    """
    Get the performance multiplier for a specific component.

    Args:
        component_name: Name of the component

    Returns:
        Performance gain string (e.g., "150x") or "1x" if not accelerated
    """
    _ensure_initialized()
    if is_rust_accelerated(component_name):
        return PERFORMANCE_MULTIPLIERS.get(component_name, "N/A")
    return "1x"


def update_status(component: str, status: str, reason: str | None = None) -> None:
    """
    Update the status of a component.

    Args:
        component: Component name
        status: Status type ("initialized", "failed")
        reason: Optional reason for the status
    """
    if status in _status_info:
        _status_info[status][component] = reason or f"{component} {status}"


def print_rust_status() -> None:
    _ensure_initialized()
    """Print comprehensive status of Rust module availability."""
    status = get_rust_component_status()

    print("\n" + "=" * 60)
    print("🚀 CLASSIC RUST ACCELERATION STATUS 🚀")
    print("=" * 60)

    if status["disabled"]:
        print("\n⚠️  Rust acceleration is DISABLED via environment variable")
        print(f"   To enable: unset {DISABLE_RUST_ENV_VAR}")
        print("=" * 60)
        return

    print(f"\nVersion: {status['version']}")

    # Display components by category
    for category_name, component_list in COMPONENT_CATEGORIES.items():
        print(f"\n📊 {category_name}:")
        for component in component_list:
            is_active = status["available"].get(component, False)
            icon = "✅" if is_active else "❌"
            status_text = "ACTIVE" if is_active else "FALLBACK"

            if is_active:
                speedup = f" ({PERFORMANCE_MULTIPLIERS.get(component, 'N/A')})"
            else:
                speedup = ""

            # Check for failure reasons
            failure_reason = ""
            if component in status["failed"] and not is_active:
                failure_reason = f" - {status['failed'][component]}"

            print(f"  {icon} {component:<20} : {status_text:<10}{speedup}{failure_reason}")

    # Summary statistics
    print("\n" + "─" * 60)
    print("📈 ACCELERATION SUMMARY:")
    print(f"   Active Components : {status['active_count']}/{status['total_count']} ({status['percentage']:.1f}%)")
    print(f"   Status           : {status['acceleration_level']}")

    if status["acceleration_level"] == "FULLY ACCELERATED":
        print("   🎯 Maximum Performance Achieved!")
    elif status["acceleration_level"] == "NO ACCELERATION":
        print("   ⚠️  Performance Degraded - No Rust components active")
        print("   Action Required  : Build and install Rust extension:")
        print("                      cd classic-rust")
        print("                      maturin build --release --out dist")
        print("                      uv pip install dist/classic-*.whl --force-reinstall")

    # List missing components if any
    if status["active_count"] < status["total_count"]:
        missing = [k for k, v in status["available"].items() if not v]
        print(f"\n   Missing Components: {', '.join(missing)}")

    print("=" * 60)


def get_performance_report() -> dict[str, Any]:
    """
    Generate a performance report for active components.

    Returns:
        Dictionary containing performance metrics and recommendations
    """
    status = get_rust_component_status()

    # Calculate potential vs actual speedup
    max_speedup = len(PERFORMANCE_MULTIPLIERS)
    actual_speedup = sum(1 for comp in PERFORMANCE_MULTIPLIERS if status["available"].get(comp, False))

    report = {
        "acceleration_level": status["acceleration_level"],
        "active_percentage": status["percentage"],
        "speedup_coverage": (actual_speedup / max_speedup * 100) if max_speedup > 0 else 0,
        "active_components": [comp for comp, active in status["available"].items() if active],
        "inactive_components": [comp for comp, active in status["available"].items() if not active],
        "performance_gains": status["performance_gains"],
    }

    # Add recommendations
    recommendations = []
    if status["percentage"] < PERFORMANCE_THRESHOLD_EXCELLENT * 100:
        if status["disabled"]:
            recommendations.append("Enable Rust acceleration by unsetting CLASSIC_DISABLE_RUST")
        elif status["active_count"] == 0:
            recommendations.append("Build and install the Rust extension for significant performance gains")
        else:
            recommendations.append(f"Additional components available for acceleration: {', '.join(report['inactive_components'])}")

    report["recommendations"] = recommendations

    return report
