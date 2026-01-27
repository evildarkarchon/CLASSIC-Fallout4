"""RustAcceleration Coordinator for CLASSIC.

This module provides the main RustAcceleration class for centralized coordination
and management of all Rust-accelerated components in CLASSIC.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, ClassVar

from ClassicLib.acceleration.metrics import ComponentMetrics
from ClassicLib.acceleration.types import ComponentType
from ClassicLib.acceleration.workload import OptimizationLevel, WorkloadCharacteristics
from ClassicLib.integration.factory import (
    get_database_pool,
    get_file_io,
    get_formid_analyzer,
    get_parser,
    get_plugin_analyzer,
    get_record_scanner,
    get_report_generator,
)
from ClassicLib.integration.status import (
    RUST_AVAILABLE,
    get_rust_component_status,
    is_rust_accelerated,
)

logger = logging.getLogger(__name__)


class RustAcceleration:
    """Handle Rust acceleration and coordination between Rust-accelerated components
    with fallback to Python implementations. Ensures singleton pattern for its
    instance and manages workload characteristics for optimization decisions.

    The class provides methods to initialize, retrieve, and manage Rust-accelerated
    components with caching, error handling, and performance logging. Additionally,
    it supports dynamic workload updates and adjusts optimization levels accordingly.

    Attributes:
        optimization_level (OptimizationLevel): Current optimization level for
            Rust acceleration.
        metrics (dict[ComponentType, ComponentMetrics]): Metrics tracking
            performance and errors for each component type.
        workload (WorkloadCharacteristics): Characteristics of the current
            workload to assist in optimization decisions.

    """

    _instance: ClassVar[RustAcceleration | None] = None
    _lock: ClassVar[threading.RLock] = threading.RLock()  # RLock allows reentrant locking

    def __new__(cls) -> RustAcceleration:
        """Create and manages a singleton instance of the RustAcceleration class.

        This method ensures that only one instance of the class is created and shared
        throughout the application. Uses double-checked locking for thread-safety
        in multi-threaded GUI contexts.

        Returns:
            RustAcceleration: The singleton instance of the RustAcceleration class.

        """
        # Fast path - instance already exists
        if cls._instance is None:
            # Slow path - need thread-safe creation
            with cls._lock:
                # Double-check pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the RustAcceleration coordinator instance.

        The initializer sets up the instance to manage workload characteristics and
        performance metrics for different components. It initializes necessary attributes,
        prepares metrics storage for all component types, and logs the instance status.
        """
        if hasattr(self, "_initialized"):
            return

        self._initialized = True
        self.optimization_level = OptimizationLevel.BALANCED
        self.metrics: dict[ComponentType, ComponentMetrics] = {}
        self.workload = WorkloadCharacteristics()
        self._components_cache: dict[str, Any] = {}
        self._start_time = time.time()

        # Initialize metrics for all components
        for component in ComponentType:
            self.metrics[component] = ComponentMetrics(name=component.value)

        # Log initialization
        logger.info("🚀 RustAcceleration coordinator initialized")
        self._log_status()

    @staticmethod
    def _log_status() -> None:
        """Log the status of Rust components.

        This function assesses the current status of Rust components, logging whether
        they are fully active, partially active, or inactive. Logs are sent to the
        configured logger. The purpose of this function is to ensure that the user is
        aware of the runtime status of Rust components and any potential fallbacks to
        Python implementations.
        """
        status = get_rust_component_status()
        active = status["active_count"]
        total = status["total_count"]

        # Always log to file
        if active == total:
            logger.info(f"✅ All {total} Rust components ACTIVE - Maximum acceleration enabled")
        elif active > 0:
            logger.info(f"⚡ {active}/{total} Rust components active")
            missing = [k for k, v in RUST_AVAILABLE.items() if not v]
            logger.debug(f"Missing components: {missing}")
        else:
            logger.warning("⚠️ No Rust acceleration available - using Python implementations")

    def get_component(self, component_type: ComponentType, *args: Any, **kwargs: Any) -> Any:
        """Fetch or creates a specified component based on the component type and caches it for
        future use. The method checks the cache for an existing instance of the component, and if
        not found, it creates the component using the appropriate helper function. Metrics such
        as call duration and errors are logged accordingly.

        Args:
            component_type: The type of component to fetch or create.
            *args: Additional positional arguments that may be required for certain component
                creations.
            **kwargs: Additional keyword arguments that may be needed for specific component
                initializations.

        Returns:
            The requested component instance, either retrieved from the cache or newly created.

        Raises:
            The method might propagate exceptions raised during the creation of the component,
            which are also logged for metrics recording.

        """
        cache_key = f"{component_type.value}_{args}_{kwargs}"

        # Check cache first
        if cache_key in self._components_cache:
            return self._components_cache[cache_key]

        # Create component based on type
        component = None
        start_time = time.time()

        try:
            if component_type == ComponentType.PARSER:
                component = get_parser()
            elif component_type == ComponentType.FORMID_ANALYZER:
                component = get_formid_analyzer(*args, **kwargs)
            elif component_type == ComponentType.PLUGIN_ANALYZER:
                component = get_plugin_analyzer(*args, **kwargs)
            elif component_type == ComponentType.RECORD_SCANNER:
                component = get_record_scanner(*args, **kwargs)
            elif component_type == ComponentType.FILE_IO_CORE:
                component = get_file_io(*args, **kwargs)
            elif component_type == ComponentType.DATABASE_POOL:
                # Import here to avoid circular dependency
                component = get_database_pool(*args, **kwargs)
            elif component_type == ComponentType.REPORT_GENERATION:
                # Import here to avoid circular dependency
                component = get_report_generator()
            else:
                logger.warning(f"Unknown component type: {component_type}")

            # Cache the component
            if component:
                self._components_cache[cache_key] = component

        except (ImportError, AttributeError, TypeError, ValueError, RuntimeError) as e:
            logger.error(f"Failed to create component {component_type}: {e}")
            self.metrics[component_type].record_error(str(e))

        # Record metrics
        duration = time.time() - start_time
        self.metrics[component_type].record_call(duration)

        return component

    def update_workload_characteristics(
        self,
        file_count: int | None = None,
        formid_count: int | None = None,
        plugin_count: int | None = None,
        is_batch: bool | None = None,
        **kwargs: Any,  # Accept additional metrics from Phase 6 integration
    ) -> None:
        """Update workload characteristics for optimization decisions with extended metrics support.

        This method now supports additional metrics from the Phase 6 OrchestratorCore integration
        including performance timings, error rates, and cache utilization.

        Args:
            file_count: Number of files being processed
            formid_count: Number of FormIDs being analyzed
            plugin_count: Number of plugins in load order
            is_batch: Whether this is a batch operation
            **kwargs: Additional metrics including:
                - acceleration_percentage: Percentage of components accelerated
                - component_errors: Number of component initialization errors
                - parse_time: Time spent parsing logs
                - log_size: Size of processed logs
                - segments_processed: Number of log segments processed
                - total_processing_time: Total time for processing
                - cache_utilization: Cache hit rate percentage
                - plugin_analysis_time: Time spent on plugin analysis
                - unique_plugins: Number of unique plugins encountered

        """
        # Core workload characteristics - using dict to reduce branches
        core_updates = {
            "file_count": file_count,
            "formid_count": formid_count,
            "plugin_count": plugin_count,
            "is_batch_operation": is_batch,
        }
        for attr, value in core_updates.items():
            if value is not None:
                setattr(self.workload, attr, value)

        # Extended metrics from Phase 6 integration - data-driven approach
        metric_keys = [
            "parse_time",
            "total_processing_time",
            "plugin_analysis_time",
            "log_size",
            "segments_processed",
            "unique_plugins",
            "acceleration_percentage",
            "component_errors",
            "cache_utilization",
        ]
        extended_metrics = {key: kwargs[key] for key in metric_keys if key in kwargs}

        # Store extended metrics for optimization decisions
        if not hasattr(self.workload, "extended_metrics"):
            self.workload.extended_metrics = {}
        self.workload.extended_metrics.update(extended_metrics)

        # Log significant workload updates for debugging
        if extended_metrics:
            logger.debug(f"Updated workload characteristics with {len(extended_metrics)} extended metrics")

        # Adapt optimization level based on workload
        if self.optimization_level == OptimizationLevel.ADAPTIVE:
            new_level = self.workload.determine_optimization_level()
            if new_level != self.optimization_level:
                # Determine reason for change using dict mapping
                reasons = {
                    (extended_metrics.get("acceleration_percentage", 0) < 50): "Low Rust acceleration detected",
                    (extended_metrics.get("component_errors", 0) > 2): "Component stability issues",
                    (self.workload.is_batch_operation and self.workload.file_count > 10): "Large batch operation detected",
                }
                reason = next((msg for condition, msg in reasons.items() if condition), "Workload characteristics changed")

                logger.info(f"Adapting optimization level: {self.optimization_level.name} -> {new_level.name}")
                logger.info(f"  Reason: {reason}")
                self.optimization_level = new_level

    def set_optimization_level(self, level: OptimizationLevel) -> None:
        """Set the optimization level for the object.

        This method allows the user to configure the optimization level of the object
        by assigning a specific level from the `OptimizationLevel` enumeration. It also
        applies relevant optimization settings based on the selected level and logs the
        change for traceability.

        Args:
            level (OptimizationLevel): The desired optimization level to apply.

        """
        self.optimization_level = level
        logger.info(f"Optimization level set to: {level.name}")

        # Apply optimization settings
        self._apply_optimization_settings()

    def _apply_optimization_settings(self) -> None:
        """Apply optimization settings based on current level."""
        if self.optimization_level == OptimizationLevel.AGGRESSIVE:
            # Maximize parallelism and caching
            self._configure_aggressive_settings()
        elif self.optimization_level == OptimizationLevel.MINIMAL:
            # Minimize resource usage
            self._configure_minimal_settings()
        elif self.optimization_level == OptimizationLevel.BALANCED:
            # Balanced settings (default)
            self._configure_balanced_settings()

    @staticmethod
    def _configure_aggressive_settings() -> None:
        """Configure aggressive optimization settings within the system.

        This method sets parameters intended to optimize performance in a Rust
        component (currently logged as actions without functional implementation).
        """
        # These would normally configure the Rust components
        # For now, we log the intent
        logger.debug("Configuring aggressive optimization settings:")
        logger.debug("  - Maximum thread pool size")
        logger.debug("  - Large cache sizes")
        logger.debug("  - Aggressive prefetching")
        logger.debug("  - Parallel I/O operations")

    @staticmethod
    def _configure_minimal_settings() -> None:
        """Configure minimal optimization settings to reduce resource usage.

        This method adjusts system settings to employ a lightweight configuration,
        including reducing thread pool size, minimizing cache sizes, and enabling
        serial operation mode.
        """
        logger.debug("Configuring minimal optimization settings:")
        logger.debug("  - Reduced thread pool size")
        logger.debug("  - Small cache sizes")
        logger.debug("  - Serial operations")

    @staticmethod
    def _configure_balanced_settings() -> None:
        """Adjust the system to use balanced optimization settings.

        This method configures system parameters to achieve a balance between performance
        and resource utilization. It includes settings for thread pool size, cache sizes,
        and selective parallelism. These configurations are designed to provide moderate
        optimization suitable for most general-purpose workloads.
        """
        logger.debug("Configuring balanced optimization settings:")
        logger.debug("  - Moderate thread pool size")
        logger.debug("  - Standard cache sizes")
        logger.debug("  - Selective parallelism")

    def get_performance_report(self) -> dict[str, Any]:
        """Generate a performance report for the system, providing insights into resource utilization,
        error rates, optimization levels, and component-specific metrics. This report also includes
        workload characteristics and evaluates acceleration factors for components leveraging Rust.

        Returns:
            dict[str, Any]: A dictionary containing the system's performance metrics, component-specific
            statistics, workload characteristics, and calculated measures such as uptime, error rate, and
            optimization level.

        Raises:
            None

        """
        uptime = time.time() - self._start_time
        total_calls = sum(m.calls for m in self.metrics.values())
        total_errors = sum(m.errors for m in self.metrics.values())

        # Component-specific metrics
        component_stats: dict[str, Any] = {}
        for comp_type, metrics in self.metrics.items():
            if metrics.calls > 0:
                component_stats[comp_type.value] = {
                    "calls": metrics.calls,
                    "avg_time_ms": metrics.avg_time * 1000,
                    "min_time_ms": metrics.min_time * 1000,
                    "max_time_ms": metrics.max_time * 1000,
                    "cache_hit_rate": metrics.cache_hit_rate,
                    "errors": metrics.errors,
                    "accelerated": is_rust_accelerated(comp_type.value),
                }

        # Calculate acceleration factor
        rust_components = sum(1 for ct in ComponentType if is_rust_accelerated(ct.value))
        acceleration_factor = rust_components / len(ComponentType)

        return {
            "uptime_seconds": uptime,
            "total_calls": total_calls,
            "total_errors": total_errors,
            "error_rate": (total_errors / total_calls * 100) if total_calls > 0 else 0,
            "optimization_level": self.optimization_level.name,
            "acceleration_factor": acceleration_factor,
            "rust_components_active": rust_components,
            "total_components": len(ComponentType),
            "component_metrics": component_stats,
            "workload_characteristics": {
                "file_count": self.workload.file_count,
                "formid_count": self.workload.formid_count,
                "plugin_count": self.workload.plugin_count,
                "is_batch": self.workload.is_batch_operation,
                "performance_score": self.workload.get_performance_score(),
                "extended_metrics": getattr(self.workload, "extended_metrics", {}),
            },
        }

    def print_performance_summary(self) -> None:
        """Print a detailed performance summary of the RUST acceleration system.

        This method outputs a comprehensive summary report to the console, including runtime
        statistics, error rates, optimization levels, acceleration metrics, and per-component
        performance details. It is intended for diagnostic and monitoring purposes to analyze
        the efficiency and reliability of the RUST acceleration implementation.
        """
        report = self.get_performance_report()

        print("\n" + "=" * 60)
        print("📊 RUST ACCELERATION PERFORMANCE SUMMARY")
        print("=" * 60)

        print(f"\nUptime: {report['uptime_seconds']:.1f} seconds")
        print(f"Total Operations: {report['total_calls']:,}")
        print(f"Error Rate: {report['error_rate']:.2f}%")
        print(f"Optimization Level: {report['optimization_level']}")
        print(f"Acceleration Factor: {report['acceleration_factor']:.1%}")

        print("\n🚀 Component Performance:")
        print("-" * 60)

        for comp_name, stats in report["component_metrics"].items():
            icon = "✅" if stats["accelerated"] else "⚠️"
            print(f"\n{icon} {comp_name}:")
            print(f"   Calls: {stats['calls']:,}")
            print(f"   Avg Time: {stats['avg_time_ms']:.2f}ms")
            print(f"   Range: {stats['min_time_ms']:.2f}ms - {stats['max_time_ms']:.2f}ms")
            if stats["cache_hit_rate"] > 0:
                print(f"   Cache Hit Rate: {stats['cache_hit_rate']:.1f}%")
            if stats["errors"] > 0:
                print(f"   Errors: {stats['errors']}")

        print("\n" + "=" * 60)

    def health_check(self) -> tuple[bool, list[str]]:
        """Perform health check on all Rust components.

        Returns:
            Tuple of (is_healthy, list_of_issues)

        """
        issues = []

        # Check component availability
        status = get_rust_component_status()
        if status["active_count"] == 0:
            issues.append("No Rust components available")
        elif status["active_count"] < status["total_count"]:
            missing = [k for k, v in RUST_AVAILABLE.items() if not v]
            issues.append(f"Missing components: {', '.join(missing)}")

        # Check error rates
        for comp_type, metrics in self.metrics.items():
            if metrics.calls > 0:
                error_rate = (metrics.errors / metrics.calls) * 100
                if error_rate > 5.0:  # More than 5% error rate is concerning
                    issues.append(f"{comp_type.value}: High error rate ({error_rate:.1f}%)")

        # Check performance degradation
        for comp_type, metrics in self.metrics.items():
            if metrics.calls > 10 and metrics.avg_time > 1.0:  # Taking more than 1 second average
                issues.append(f"{comp_type.value}: Slow performance (avg {metrics.avg_time:.2f}s)")

        is_healthy: bool = len(issues) == 0  # pyright: ignore[reportUnknownArgumentType]
        return is_healthy, issues  # pyright: ignore[reportUnknownVariableType]

    def reset_metrics(self) -> None:
        """Reset all performance metrics."""
        for component in ComponentType:
            self.metrics[component] = ComponentMetrics(name=component.value)
        self._start_time = time.time()
        logger.info("Performance metrics reset")

    @classmethod
    def get_instance(cls) -> RustAcceleration:
        """Get the singleton instance of RustAcceleration.

        This method uses double-checked locking for thread-safety in
        multi-threaded GUI contexts while maintaining performance.

        Returns:
            RustAcceleration: The singleton instance of the RustAcceleration coordinator.

        """
        # Fast path - instance already exists
        if cls._instance is not None:
            return cls._instance

        # Slow path - need thread-safe creation
        with cls._lock:
            # Double-check pattern - another thread may have created it
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance - test environments only.

        This method is intended for test isolation to ensure each test starts
        with a fresh instance. It is guarded to only work in pytest environments.

        Raises:
            RuntimeError: If called outside of a pytest testing context.

        """
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            msg = "reset_instance() is only allowed in testing contexts"
            raise RuntimeError(msg)
        with cls._lock:
            cls._instance = None


# Module-level convenience functions
def get_rust_acceleration() -> RustAcceleration:
    """Get the RustAcceleration singleton instance.

    Returns:
        RustAcceleration: The singleton instance of the RustAcceleration coordinator.

    """
    return RustAcceleration.get_instance()


def configure_for_batch_processing(file_count: int) -> None:
    """Configure Rust acceleration for batch processing.

    Args:
        file_count: Number of files to be processed

    """
    accelerator = get_rust_acceleration()
    accelerator.update_workload_characteristics(file_count=file_count, is_batch=True)
    if file_count > 10:
        accelerator.set_optimization_level(OptimizationLevel.AGGRESSIVE)
    else:
        accelerator.set_optimization_level(OptimizationLevel.BALANCED)

    logger.info(f"Configured for batch processing of {file_count} files")


def configure_for_single_file() -> None:
    """Configure Rust acceleration for single file processing."""
    accelerator = get_rust_acceleration()
    accelerator.update_workload_characteristics(file_count=1, is_batch=False)
    accelerator.set_optimization_level(OptimizationLevel.BALANCED)

    logger.info("Configured for single file processing")


def print_acceleration_status() -> None:
    """Print the current Rust acceleration status."""
    from ClassicLib.integration.status import print_rust_status

    # First print component availability
    print_rust_status()

    # Then print performance metrics if available
    accelerator = get_rust_acceleration()
    if any(m.calls > 0 for m in accelerator.metrics.values()):
        accelerator.print_performance_summary()


def perform_health_check() -> bool:
    """Perform a health check and log results.

    Returns:
        True if healthy, False if issues detected

    """
    accelerator = get_rust_acceleration()
    is_healthy, issues = accelerator.health_check()

    if is_healthy:
        logger.info("✅ Rust acceleration health check: All systems operational")
    else:
        logger.warning(f"⚠️ Rust acceleration health check: {len(issues)} issues detected")
        for issue in issues:
            logger.warning(f"  - {issue}")

    return is_healthy


__all__ = [
    "RustAcceleration",
    "configure_for_batch_processing",
    "configure_for_single_file",
    "get_rust_acceleration",
    "perform_health_check",
    "print_acceleration_status",
]
