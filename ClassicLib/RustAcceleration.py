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

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ClassicLib.integration.factory import (
    get_database_pool,
    get_file_io,
    get_formid_analyzer,
    get_parser,
    get_plugin_analyzer,
    get_record_scanner,
)
from ClassicLib.integration.status import (
    get_rust_component_status,
    is_rust_accelerated,
)
# Import the module-level status dicts
from ClassicLib.integration.status import RUST_AVAILABLE, RUST_STATUS

logger = logging.getLogger(__name__)


class ComponentType(Enum):
    """Types of Rust components available for acceleration."""
    PARSER = "parser"
    FORMID_ANALYZER = "formid_analyzer"
    PLUGIN_ANALYZER = "plugin_analyzer"
    RECORD_SCANNER = "record_scanner"
    REPORT_GENERATION = "report_generation"
    DATABASE_POOL = "database_pool"
    FILE_IO_CORE = "file_io_core"
    MOD_DETECTOR = "mod_detector"


class OptimizationLevel(Enum):
    """Optimization levels for Rust components."""
    DISABLED = 0  # Component disabled
    MINIMAL = 1   # Minimal optimization, maximum compatibility
    BALANCED = 2  # Balanced performance and resource usage (default)
    AGGRESSIVE = 3  # Maximum performance, higher resource usage
    ADAPTIVE = 4  # Dynamically adjust based on workload


@dataclass
class ComponentMetrics:
    """Performance metrics for a Rust component."""
    name: str
    calls: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    errors: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    last_error: Optional[str] = None

    @property
    def avg_time(self) -> float:
        """Calculate average execution time."""
        return self.total_time / self.calls if self.calls > 0 else 0.0

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0

    def record_call(self, duration: float, cache_hit: bool = False) -> None:
        """Record a component call with timing."""
        self.calls += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)

        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    def record_error(self, error: str) -> None:
        """Record an error occurrence."""
        self.errors += 1
        self.last_error = error


@dataclass
class WorkloadCharacteristics:
    """Characteristics of the current workload for optimization decisions (Phase 6 Enhanced)."""
    file_count: int = 0
    total_file_size: int = 0
    formid_count: int = 0
    plugin_count: int = 0
    database_queries: int = 0
    report_fragments: int = 0
    is_batch_operation: bool = False
    is_memory_constrained: bool = False
    extended_metrics: Dict[str, Any] = field(default_factory=dict)  # Phase 6 addition

    def determine_optimization_level(self) -> OptimizationLevel:
        """
        Determine optimal settings based on workload with Phase 6 enhanced decision logic.

        This method now considers extended metrics like acceleration percentage,
        component errors, and performance timings for more intelligent optimization.
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
        Calculate a performance score based on current metrics.

        Returns:
            Float between 0.0 and 100.0 representing overall performance
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
    Central coordination for all Rust-accelerated components in CLASSIC.

    This singleton class manages the entire Rust subsystem, providing:
    - Component lifecycle management
    - Performance monitoring and optimization
    - Unified error handling
    - Dynamic workload adaptation
    """

    _instance: Optional[RustAcceleration] = None

    def __new__(cls) -> RustAcceleration:
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the Rust acceleration coordinator."""
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self.optimization_level = OptimizationLevel.BALANCED
        self.metrics: Dict[ComponentType, ComponentMetrics] = {}
        self.workload = WorkloadCharacteristics()
        self._components_cache: Dict[str, Any] = {}
        self._start_time = time.time()

        # Initialize metrics for all components
        for component in ComponentType:
            self.metrics[component] = ComponentMetrics(name=component.value)

        # Log initialization
        logger.info("🚀 RustAcceleration coordinator initialized")
        self._log_status()

    def _log_status(self) -> None:
        """Log current acceleration status."""
        status = get_rust_component_status()
        active = status['active_count']
        total = status['total_count']

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
        Get a Rust-accelerated component instance with automatic fallback.

        Args:
            component_type: Type of component to retrieve
            *args, **kwargs: Arguments for component initialization

        Returns:
            Component instance (Rust-accelerated if available, Python fallback otherwise)
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
                from ClassicLib.AsyncDatabasePool import get_database_pool
                component = get_database_pool(*args, **kwargs)
            elif component_type == ComponentType.REPORT_GENERATION:
                # Import here to avoid circular dependency
                from ClassicLib.ScanLog.RustReportGeneration import get_report_generator
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
        file_count: Optional[int] = None,
        formid_count: Optional[int] = None,
        plugin_count: Optional[int] = None,
        is_batch: Optional[bool] = None,
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
        Set the optimization level for all components.

        Args:
            level: Desired optimization level
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
        """Configure components for maximum performance."""
        # These would normally configure the Rust components
        # For now, we log the intent
        logger.debug("Configuring aggressive optimization settings:")
        logger.debug("  - Maximum thread pool size")
        logger.debug("  - Large cache sizes")
        logger.debug("  - Aggressive prefetching")
        logger.debug("  - Parallel I/O operations")

    def _configure_minimal_settings(self) -> None:
        """Configure components for minimal resource usage."""
        logger.debug("Configuring minimal optimization settings:")
        logger.debug("  - Reduced thread pool size")
        logger.debug("  - Small cache sizes")
        logger.debug("  - Serial operations")

    def _configure_balanced_settings(self) -> None:
        """Configure components with balanced settings."""
        logger.debug("Configuring balanced optimization settings:")
        logger.debug("  - Moderate thread pool size")
        logger.debug("  - Standard cache sizes")
        logger.debug("  - Selective parallelism")

    def get_performance_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive performance report.

        Returns:
            Dictionary containing performance metrics for all components
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
        """Print a formatted performance summary to console."""
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

    def health_check(self) -> Tuple[bool, List[str]]:
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
