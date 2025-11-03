"""
A high-level diagnostic and management utility for Rust component integration.

This module provides utility functions and global configuration for detecting,
managing, and reporting the status of Rust-accelerated components within the
application. It is responsible for initializing component availability,
tracking their status, and providing detailed diagnostics to users.

The primary responsibilities include:
- Detecting available Rust components and their performance gains.
- Providing status updates and reports for Rust acceleration.
- Ensuring backward compatibility with older imports and configurations.
"""

from __future__ import annotations

import logging
from typing import Any

__all__ = [
    "RUST_AVAILABLE",
    "RUST_STATUS",
    "get_performance_multiplier",
    "get_rust_component_status",
    "is_rust_accelerated",
    "print_rust_status",
    "update_status",
]

from .config import (
    COMPONENT_CATEGORIES,
    DISABLE_RUST_ENV_VAR,
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
    """
    Initializes the availability of Rust components.

    This function checks for the presence of necessary Rust components by calling
    `detect_rust_components` and sets the global variable `RUST_AVAILABLE`
    accordingly. It ensures that this initialization is only performed once per
    runtime by maintaining an `_initialized` state.

    Raises:
        ImportError: If the required Rust components cannot be detected.
    """
    global RUST_AVAILABLE, _initialized
    if not _initialized:
        RUST_AVAILABLE = detect_rust_components()
        _initialized = True


def _ensure_initialized() -> None:
    """
    Ensures that the system is initialized before proceeding.

    This function checks the status of initialization and performs the
    necessary setup if the system is not yet initialized.

    Raises:
        RuntimeError: If the system fails to initialize properly.
    """
    if not _initialized:
        _initialize_rust_available()


def get_rust_component_status() -> dict[str, Any]:
    """
    Retrieves the current status of Rust-based components integrated into the system.

    This function gathers information about the availability and initialization state
    of Rust components, calculates the percentage of active components, and determines
    an acceleration level based on predefined performance thresholds. Additionally,
    it compiles performance gains for the active components. The information is then
    summarized in a structured dictionary for further use.

    Returns:
        dict[str, Any]: A dictionary containing detailed information about the
        availability and performance status of Rust components, including initialized
        states, performance gains, total and active counts, acceleration level, and
        the version and disabled components list.
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
    Checks if a given component is accelerated using Rust.

    This function determines whether a specific component benefits from a Rust-based
    implementation for performance optimization.

    Args:
        component_name (str): The name of the component to check for Rust acceleration.

    Returns:
        bool: True if the component is accelerated using Rust, False otherwise.
    """
    _ensure_initialized()
    return RUST_AVAILABLE.get(component_name, False)


def get_performance_multiplier(component_name: str) -> str:
    """
    Determines and returns the performance multiplier for a given component.

    This function checks if the specified component is accelerated using Rust.
    If it is, it retrieves the corresponding performance multiplier from a predefined
    dictionary. If the component is not found in the dictionary, it defaults to "N/A".
    If the component is not accelerated by Rust, the function returns a default
    performance multiplier of "1x".

    Args:
        component_name (str): The name of the component for which the performance
            multiplier is being retrieved.

    Returns:
        str: The performance multiplier string for the specified component.
    """
    _ensure_initialized()
    if is_rust_accelerated(component_name):
        return PERFORMANCE_MULTIPLIERS.get(component_name, "N/A")
    return "1x"


def update_status(component: str, status: str, reason: str | None = None) -> None:
    """
    Updates the status information for a specific component. The function updates
    or adds the status of a given component in the internal status tracking
    dictionary. If a reason is provided, it will be used; otherwise, a default
    reason is generated automatically.

    Args:
        component (str): The name of the component whose status needs to be
            updated.
        status (str): The new status to assign to the component.
        reason (str | None): An optional detailed reason for the status update.
            If not provided, a default reason is generated.
    """
    if status in _status_info:
        _status_info[status][component] = reason or f"{component} {status}"


def print_rust_status() -> None:
    """
    Prints the status of Rust acceleration for the application, including detailed
    information about available, active, and missing components categorized by
    functionality. Additionally, displays summary statistics and provides guidance
    on enabling Rust components if they are not active.

    Raises:
        Exception: If an issue occurs while retrieving ClassicLib settings, defaults
            to not displaying Rust acceleration status.
    """
    _ensure_initialized()

    # Check if debug messages are enabled
    try:
        from ClassicLib.YamlSettingsCache import classic_settings
        debug_enabled = classic_settings(bool, "Debug Messages")
        if not debug_enabled:
            return
    except Exception:
        # If we can't check the setting, default to not showing
        return

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
    Generates a performance report detailing the acceleration metrics, active and inactive components,
    performance gains, and actionable recommendations based on the availability and utilization
    of Rust acceleration components.

    The function analyzes Rust acceleration status and calculates various metrics, including the
    percentage of performance improvement achieved, the number of components utilized, and the
    potential for further optimization. Recommendations are added to guide further improvements
    if necessary.

    Returns:
        dict[str, Any]: A dictionary containing the following keys:
            - "acceleration_level" (str): The current level of performance acceleration.
            - "active_percentage" (float): The active percentage of acceleration utilization.
            - "speedup_coverage" (float): Percentage of utilized components relative to the total
              potential components.
            - "active_components" (list[str]): List of currently active acceleration components.
            - "inactive_components" (list[str]): List of currently inactive or unavailable
              acceleration components.
            - "performance_gains" (dict): Key-value pairs providing insights into performance gains
              from individual components.
            - "recommendations" (list[str]): Suggested actions to further enhance performance.

    Raises:
        AnyError: Raises an error if a Rust component failure, invalid configuration,
        or other critical mismatch occurs during status evaluation.
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
