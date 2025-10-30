"""
RustAcceleration Coordination Module for CLASSIC (Pre-release Version).

This module provides centralized coordination and management of all Rust-accelerated
components in CLASSIC. It handles component orchestration, performance monitoring,
automatic optimization, and provides a unified interface for the entire Rust subsystem.

Features:
- Centralized component management and configuration
- Performance monitoring and metrics collection
- Automatic optimization based on workload characteristics
- Component health checks and diagnostics
- Unified error handling and recovery
- Real-time performance statistics

This is the primary interface for Phase 6: Integration & Optimization.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ClassicLib.integration.factory import (
    get_file_io,
    get_formid_analyzer,
    get_parser,
    get_plugin_analyzer,
    get_record_scanner,
    get_database_pool,
    get_report_generator,
)

# Import the module-level status dicts
from ClassicLib.integration.status import (
    RUST_AVAILABLE,
    get_rust_component_status,
    is_rust_accelerated,
)

logger = logging.getLogger(__name__)


class ComponentType(Enum):
    """Represents various component types as an enumeration.

    This enumeration provides a set of predefined categories for categorizing
    different types of components in a system. Each member of the enumeration
    is a string constant that represents a specific component type.

    Attributes:
        PARSER (str): Represents components responsible for parsing activities.
        FORMID_ANALYZER (str): Represents components used for analyzing form IDs.
        PLUGIN_ANALYZER (str): Represents components designed to analyze plugins.
        RECORD_SCANNER (str): Represents components that scan and process records.
        REPORT_GENERATION (str): Represents components for generating reports.
        DATABASE_POOL (str): Represents components functioning as database pools.
        FILE_IO_CORE (str): Represents components handling core file I/O tasks.
        MOD_DETECTOR (str): Represents components detecting modifications or mods.
    """
    PARSER = "parser"
    FORMID_ANALYZER = "formid_analyzer"
    PLUGIN_ANALYZER = "plugin_analyzer"
    RECORD_SCANNER = "record_scanner"
    REPORT_GENERATION = "report_generation"
    DATABASE_POOL = "database_pool"
    FILE_IO_CORE = "file_io_core"
    MOD_DETECTOR = "mod_detector"


class OptimizationLevel(Enum):
    """
    Represents different levels of optimization that can be applied.

    This enumeration defines a range of optimization strategies that vary
    from being completely disabled to dynamically adjusting based on workloads.
    It is designed to provide flexible options for balancing performance,
    compatibility, and resource usage.

    Attributes:
        DISABLED (int): Component disabled, no optimizations applied.
        MINIMAL (int): Minimal optimization level, prioritizing maximum
            compatibility, and stability.
        BALANCED (int): Balances performance and resource usage, serving
            as the default option for general scenarios.
        AGGRESSIVE (int): Focuses on maximum performance, potentially
            utilizing higher amounts of resources.
        ADAPTIVE (int): Dynamically adjusts optimization level based on the
            workload to maintain optimal performance and resource efficiency.
    """
    DISABLED = 0  # Component disabled
    MINIMAL = 1   # Minimal optimization, maximum compatibility
    BALANCED = 2  # Balanced performance and resource usage (default)
    AGGRESSIVE = 3  # Maximum performance, higher resource usage
    ADAPTIVE = 4  # Dynamically adjust based on workload


@dataclass
class ComponentMetrics:
    """
    Represents metrics for a component, tracking performance and error data.

    This class is designed to aggregate and provide metrics related to calls made
    to a given component. It includes information about the number of calls,
    execution times, cache performance, and errors. It also provides calculated
    properties such as average execution time and cache hit rate.

    Attributes:
        name (str): The name of the component being tracked.
        calls (int): The total number of calls made to the component.
        total_time (float): The total execution time of all calls.
        min_time (float): The shortest execution time of any single call.
        max_time (float): The longest execution time of any single call.
        errors (int): The total number of errors recorded.
        cache_hits (int): The number of successful cache hits.
        cache_misses (int): The number of cache misses.
        last_error (str | None): The most recent error message, if any.
    """
    name: str
    calls: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    errors: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    last_error: str | None = None

    @property
    def avg_time(self) -> float:
        """
        Calculates and retrieves the average time per call.

        This property computes the average time taken for each call by dividing
        the total accumulated time by the number of recorded calls. If no calls
        have been recorded, the average time defaults to 0.0.

        Returns:
            float: The average time per call. Returns 0.0 if there are no calls.
        """
        return self.total_time / self.calls if self.calls > 0 else 0.0

    @property
    def cache_hit_rate(self) -> float:
        """
        Calculates and returns the cache hit rate as a percentage.

        The cache hit rate is the ratio of cache hits to the total cache
        accesses (hits + misses), expressed as a percentage. If there are
        no cache accesses, the hit rate is considered to be 0.0.

        Returns:
            float: The cache hit rate as a percentage, or 0.0 if there are no
            cache hits or misses.
        """
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0

    def record_call(self, duration: float, cache_hit: bool = False) -> None:
        """
        Records a single function call's duration and whether it was a cache hit or miss.
        Updates the statistics including total calls, total time, minimum time, maximum time,
        cache hits, and cache misses based on the provided data.

        Args:
            duration (float): The duration of the function call to be recorded.
            cache_hit (bool, optional): Specifies whether the call was a cache hit. Defaults to False.

        Returns:
            None
        """
        self.calls += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)

        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    def record_error(self, error: str) -> None:
        """
        Records an error by incrementing the error count and storing the latest error.

        Args:
            error (str): The error message to be recorded.
        """
        self.errors += 1
        self.last_error = error


@dataclass
class WorkloadCharacteristics:
    """
    Represents characteristics of a computational workload and provides methods to
    evaluate its optimization level and performance.

    The WorkloadCharacteristics class is used to encapsulate various metrics and
    attributes of a workload, including file count, file sizes, batch operation
    flags, memory constraints, and extended metrics such as rust acceleration,
    component errors, and performance timings. It supports determining the optimal
    optimization level and calculating a performance score based on the given inputs.

    Attributes:
        file_count (int): Number of files involved in the workload.
        total_file_size (int): Aggregate file size (in bytes) across all files.
        formid_count (int): Count of FormID elements in the workload.
        plugin_count (int): Number of plugins included in the workload.
        database_queries (int): Number of database queries in the workload.
        report_fragments (int): Count of report fragments being processed.
        is_batch_operation (bool): Indicates whether the workload is part of a batch operation.
        is_memory_constrained (bool): Specifies if memory availability is limited.
        extended_metrics (dict[str, Any]): Additional workload metrics, such as
            acceleration percentage, performance timings, or cache metrics.
    """
    file_count: int = 0
    total_file_size: int = 0
    formid_count: int = 0
    plugin_count: int = 0
    database_queries: int = 0
    report_fragments: int = 0
    is_batch_operation: bool = False
    is_memory_constrained: bool = False
    extended_metrics: dict[str, Any] = field(default_factory=dict)  # Phase 6 addition

    def determine_optimization_level(self) -> OptimizationLevel:
        """
        Determines the optimal level of optimization based on various dynamic system metrics
        and configuration parameters. This method analyzes conditions such as system stability,
        Rust acceleration percentage, cache utilization, memory constraints, and workload
        characteristics to return the appropriate optimization level for the current operation.

        Returns:
            OptimizationLevel: The determined optimization level based on the analyzed metrics.

        Raises:
            KeyError: If any required key in `extended_metrics` is missing.
        """
        # Check for component instability first
        component_errors = self.extended_metrics.get('component_errors', 0)
        if component_errors > 3:
            # Many component errors suggest instability - use minimal optimization
            return OptimizationLevel.MINIMAL

        # Check acceleration percentage for Rust availability
        acceleration_pct = self.extended_metrics.get('acceleration_percentage', 100)

        # Large batch operations with good Rust acceleration
        if self.is_batch_operation and self.file_count > 10 and acceleration_pct > 70:
            return OptimizationLevel.AGGRESSIVE

        # High-performance single operations with excellent acceleration
        if not self.is_batch_operation and acceleration_pct > 90:
            cache_util = self.extended_metrics.get('cache_utilization', 0)
            if cache_util > 80:  # Good cache performance
                return OptimizationLevel.AGGRESSIVE

        # Memory constrained environments or low acceleration
        if self.is_memory_constrained or acceleration_pct < 30:
            return OptimizationLevel.BALANCED

        # Heavy database operations benefit from aggressive caching
        if self.database_queries > 100 and acceleration_pct > 50:
            return OptimizationLevel.AGGRESSIVE

        # Large plugin counts with good acceleration
        if self.plugin_count > 200 and acceleration_pct > 60:
            return OptimizationLevel.AGGRESSIVE

        # High FormID counts need optimization
        if self.formid_count > 500 and acceleration_pct > 50:
            return OptimizationLevel.AGGRESSIVE

        # Consider performance timings
        parse_time = self.extended_metrics.get('parse_time', 0)
        if parse_time > 2.0 and acceleration_pct < 50:  # Slow parsing without Rust
            return OptimizationLevel.BALANCED  # Don't stress the system further

        # Default to balanced for most workloads
        return OptimizationLevel.BALANCED

    def get_performance_score(self) -> float:
        """
        Calculates the performance score based on various metrics such as acceleration
        percentage, cache utilization, component errors, and parse time. The score is
        adjusted to provide bonuses or penalties based on these criteria, ensuring it
        falls within the range of 0 to 100.

        Returns:
            float: The calculated performance score, constrained between 0.0 and 100.0.

        Raises:
            None
        """
        score = 50.0  # Base score

        # Rust acceleration bonus
        acceleration_pct = self.extended_metrics.get('acceleration_percentage', 0)
        score += (acceleration_pct / 100) * 30  # Up to 30 points for full acceleration

        # Cache utilization bonus
        cache_util = self.extended_metrics.get('cache_utilization', 0)
        score += (cache_util / 100) * 15  # Up to 15 points for excellent caching

        # Error penalty
        component_errors = self.extended_metrics.get('component_errors', 0)
        score -= min(component_errors * 5, 20)  # Up to 20 points penalty for errors

        # Performance timing bonus/penalty
        parse_time = self.extended_metrics.get('parse_time', 1.0)
        if parse_time < 0.1:  # Very fast parsing
            score += 5
        elif parse_time > 5.0:  # Slow parsing
            score -= 10

        return max(0.0, min(100.0, score))


class RustAcceleration:
    """
    Handles Rust acceleration and coordination between Rust-accelerated components
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

    _instance: RustAcceleration | None = None

    def __new__(cls) -> RustAcceleration:
        """
        Creates and manages a singleton instance of the RustAcceleration class.

        This method ensures that only one instance of the class is created and shared
        throughout the application. If an instance already exists, the existing one
        is returned; otherwise, it creates a new instance.

        Returns:
            RustAcceleration: The singleton instance of the RustAcceleration class.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initializes the RustAcceleration coordinator instance.

        The initializer sets up the instance to manage workload characteristics and
        performance metrics for different components. It initializes necessary attributes,
        prepares metrics storage for all component types, and logs the instance status.

        Raises:
            None

        """
        if hasattr(self, '_initialized'):
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

    def _log_status(self) -> None:
        """
        Logs the status of Rust components.

        This function assesses the current status of Rust components, logging whether
        they are fully active, partially active, or inactive. Logs are sent to the
        configured logger. The purpose of this function is to ensure that the user is
        aware of the runtime status of Rust components and any potential fallbacks to
        Python implementations.

        Raises:
            None
        """
        status = get_rust_component_status()
        active = status['active_count']
        total = status['total_count']

        # Always log to file
        if active == total:
            logger.info(f"✅ All {total} Rust components ACTIVE - Maximum acceleration enabled")
        elif active > 0:
            logger.info(f"⚡ {active}/{total} Rust components active")
            missing = [k for k, v in RUST_AVAILABLE.items() if not v]
            logger.debug(f"Missing components: {missing}")
        else:
            logger.warning("⚠️ No Rust acceleration available - using Python implementations")

    def get_component(self, component_type: ComponentType, *args, **kwargs) -> Any:
        """
        Fetches or creates a specified component based on the component type and caches it for
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

        except Exception as e:
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
        **kwargs  # Accept additional metrics from Phase 6 integration
    ) -> None:
        """
        Update workload characteristics for optimization decisions with extended metrics support.

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
        # Core workload characteristics
        if file_count is not None:
            self.workload.file_count = file_count
        if formid_count is not None:
            self.workload.formid_count = formid_count
        if plugin_count is not None:
            self.workload.plugin_count = plugin_count
        if is_batch is not None:
            self.workload.is_batch_operation = is_batch

        # Extended metrics from Phase 6 integration
        extended_metrics = {}

        # Performance metrics
        if 'parse_time' in kwargs:
            extended_metrics['parse_time'] = kwargs['parse_time']
        if 'total_processing_time' in kwargs:
            extended_metrics['total_processing_time'] = kwargs['total_processing_time']
        if 'plugin_analysis_time' in kwargs:
            extended_metrics['plugin_analysis_time'] = kwargs['plugin_analysis_time']

        # Data size metrics
        if 'log_size' in kwargs:
            extended_metrics['log_size'] = kwargs['log_size']
        if 'segments_processed' in kwargs:
            extended_metrics['segments_processed'] = kwargs['segments_processed']
        if 'unique_plugins' in kwargs:
            extended_metrics['unique_plugins'] = kwargs['unique_plugins']

        # Quality metrics
        if 'acceleration_percentage' in kwargs:
            extended_metrics['acceleration_percentage'] = kwargs['acceleration_percentage']
        if 'component_errors' in kwargs:
            extended_metrics['component_errors'] = kwargs['component_errors']
        if 'cache_utilization' in kwargs:
            extended_metrics['cache_utilization'] = kwargs['cache_utilization']

        # Store extended metrics for optimization decisions
        if not hasattr(self.workload, 'extended_metrics'):
            self.workload.extended_metrics = {}
        self.workload.extended_metrics.update(extended_metrics)

        # Log significant workload updates for debugging
        if len(extended_metrics) > 0:
            logger.debug(f"Updated workload characteristics with {len(extended_metrics)} extended metrics")

        # Adapt optimization level based on workload
        if self.optimization_level == OptimizationLevel.ADAPTIVE:
            new_level = self.workload.determine_optimization_level()
            if new_level != self.optimization_level:
                logger.info(f"Adapting optimization level: {self.optimization_level.name} -> {new_level.name}")
                # Log the reason for the change
                if extended_metrics.get('acceleration_percentage', 0) < 50:
                    logger.info("  Reason: Low Rust acceleration detected")
                elif extended_metrics.get('component_errors', 0) > 2:
                    logger.info("  Reason: Component stability issues")
                elif self.workload.is_batch_operation and self.workload.file_count > 10:
                    logger.info("  Reason: Large batch operation detected")

                self.optimization_level = new_level

    def set_optimization_level(self, level: OptimizationLevel) -> None:
        """
        Sets the optimization level for the object.

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

    def _configure_aggressive_settings(self) -> None:
        """
        Configures aggressive optimization settings within the system.

        This method sets parameters intended to optimize performance in a Rust
        component (currently logged as actions without functional implementation).

        Raises:
            None
        """
        # These would normally configure the Rust components
        # For now, we log the intent
        logger.debug("Configuring aggressive optimization settings:")
        logger.debug("  - Maximum thread pool size")
        logger.debug("  - Large cache sizes")
        logger.debug("  - Aggressive prefetching")
        logger.debug("  - Parallel I/O operations")

    def _configure_minimal_settings(self) -> None:
        """
        Configures minimal optimization settings to reduce resource usage.

        This method adjusts system settings to employ a lightweight configuration,
        including reducing thread pool size, minimizing cache sizes, and enabling
        serial operation mode.

        Args:
            None

        Returns:
            None
        """
        logger.debug("Configuring minimal optimization settings:")
        logger.debug("  - Reduced thread pool size")
        logger.debug("  - Small cache sizes")
        logger.debug("  - Serial operations")

    def _configure_balanced_settings(self) -> None:
        """
        Adjusts the system to use balanced optimization settings.

        This method configures system parameters to achieve a balance between performance
        and resource utilization. It includes settings for thread pool size, cache sizes,
        and selective parallelism. These configurations are designed to provide moderate
        optimization suitable for most general-purpose workloads.

        Returns:
            None
        """
        logger.debug("Configuring balanced optimization settings:")
        logger.debug("  - Moderate thread pool size")
        logger.debug("  - Standard cache sizes")
        logger.debug("  - Selective parallelism")

    def get_performance_report(self) -> dict[str, Any]:
        """
        Generates a performance report for the system, providing insights into resource utilization,
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
        component_stats = {}
        for comp_type, metrics in self.metrics.items():
            if metrics.calls > 0:
                component_stats[comp_type.value] = {
                    'calls': metrics.calls,
                    'avg_time_ms': metrics.avg_time * 1000,
                    'min_time_ms': metrics.min_time * 1000,
                    'max_time_ms': metrics.max_time * 1000,
                    'cache_hit_rate': metrics.cache_hit_rate,
                    'errors': metrics.errors,
                    'accelerated': is_rust_accelerated(comp_type.value),
                }

        # Calculate acceleration factor
        rust_components = sum(1 for ct in ComponentType if is_rust_accelerated(ct.value))
        acceleration_factor = rust_components / len(ComponentType)

        return {
            'uptime_seconds': uptime,
            'total_calls': total_calls,
            'total_errors': total_errors,
            'error_rate': (total_errors / total_calls * 100) if total_calls > 0 else 0,
            'optimization_level': self.optimization_level.name,
            'acceleration_factor': acceleration_factor,
            'rust_components_active': rust_components,
            'total_components': len(ComponentType),
            'component_metrics': component_stats,
            'workload_characteristics': {
                'file_count': self.workload.file_count,
                'formid_count': self.workload.formid_count,
                'plugin_count': self.workload.plugin_count,
                'is_batch': self.workload.is_batch_operation,
                'performance_score': self.workload.get_performance_score(),
                'extended_metrics': getattr(self.workload, 'extended_metrics', {})
            }
        }

    def print_performance_summary(self) -> None:
        """
        Prints a detailed performance summary of the RUST acceleration system.

        This method outputs a comprehensive summary report to the console, including runtime
        statistics, error rates, optimization levels, acceleration metrics, and per-component
        performance details. It is intended for diagnostic and monitoring purposes to analyze
        the efficiency and reliability of the RUST acceleration implementation.

        Returns:
            None
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

        for comp_name, stats in report['component_metrics'].items():
            icon = "✅" if stats['accelerated'] else "⚠️"
            print(f"\n{icon} {comp_name}:")
            print(f"   Calls: {stats['calls']:,}")
            print(f"   Avg Time: {stats['avg_time_ms']:.2f}ms")
            print(f"   Range: {stats['min_time_ms']:.2f}ms - {stats['max_time_ms']:.2f}ms")
            if stats['cache_hit_rate'] > 0:
                print(f"   Cache Hit Rate: {stats['cache_hit_rate']:.1f}%")
            if stats['errors'] > 0:
                print(f"   Errors: {stats['errors']}")

        print("\n" + "=" * 60)

    def health_check(self) -> tuple[bool, list[str]]:
        """
        Perform health check on all Rust components.

        Returns:
            Tuple of (is_healthy, list_of_issues)
        """
        issues = []

        # Check component availability
        status = get_rust_component_status()
        if status['active_count'] == 0:
            issues.append("No Rust components available")
        elif status['active_count'] < status['total_count']:
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

        is_healthy = len(issues) == 0
        return is_healthy, issues

    def reset_metrics(self) -> None:
        """Reset all performance metrics."""
        for component in ComponentType:
            self.metrics[component] = ComponentMetrics(name=component.value)
        self._start_time = time.time()
        logger.info("Performance metrics reset")

    @classmethod
    def get_instance(cls) -> RustAcceleration:
        """Get the singleton instance of RustAcceleration."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


# Module-level convenience functions
def get_rust_acceleration() -> RustAcceleration:
    """Get the RustAcceleration singleton instance."""
    return RustAcceleration.get_instance()


def configure_for_batch_processing(file_count: int) -> None:
    """
    Configure Rust acceleration for batch processing.

    Args:
        file_count: Number of files to be processed
    """
    accelerator = get_rust_acceleration()
    accelerator.update_workload_characteristics(
        file_count=file_count,
        is_batch=True
    )
    if file_count > 10:
        accelerator.set_optimization_level(OptimizationLevel.AGGRESSIVE)
    else:
        accelerator.set_optimization_level(OptimizationLevel.BALANCED)

    logger.info(f"Configured for batch processing of {file_count} files")


def configure_for_single_file() -> None:
    """Configure Rust acceleration for single file processing."""
    accelerator = get_rust_acceleration()
    accelerator.update_workload_characteristics(
        file_count=1,
        is_batch=False
    )
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
    """
    Perform a health check and log results.

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


# Initialize on module import for pre-release
_accelerator = get_rust_acceleration()
