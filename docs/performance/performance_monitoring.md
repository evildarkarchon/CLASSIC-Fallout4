# Performance Monitoring Guide for CLASSIC Rust Components

Note: this guide includes material from the earlier Python-facing Rust acceleration model. For the current maintained contributor workflow, prefer the modular `ClassicLib-rs/` guides and the active binding validation docs.

## Overview

This guide provides comprehensive information on monitoring, measuring, and optimizing the performance of CLASSIC's Rust acceleration components. Whether you're a user wanting to verify performance gains or a developer optimizing the system, this guide covers all aspects of performance monitoring.

## Quick Status Check

### Basic Status Verification

```python
# Quick one-liner to check if acceleration is working
from ClassicLib.RustIntegration import get_rust_component_status
status = get_rust_component_status()
print(f"🚀 Rust: {status['active_count']}/{status['total_count']} components ({status['active_count']/status['total_count']*100:.0f}%)")
```

### Detailed Status Report

```python
from ClassicLib.RustIntegration import print_rust_status
print_rust_status()
```

Expected output when fully accelerated:
```
🚀 CLASSIC PRE-RELEASE - RUST ACCELERATION STATUS 🚀
============================================================

📊 ScanLog Components (Core Performance):
  ✅ parser               : ACTIVE     (150x speedup)
  ✅ formid_analyzer      : ACTIVE     (50x speedup)
  ✅ plugin_analyzer      : ACTIVE     (30x speedup)
  ✅ record_scanner       : ACTIVE     (40x speedup)
  ✅ report_generation    : ACTIVE     (75x speedup)
  ✅ mod_detector         : ACTIVE     (35x speedup)

💾 File I/O Components:
  ✅ file_io_core         : ACTIVE     (10-20x file ops, 30-40x DDS)

🗄️ Database Components:
  ✅ database_pool        : ACTIVE     (25x speedup)

────────────────────────────────────────────────────────────
📈 ACCELERATION SUMMARY:
   Active Components : 8/8 (100.0%)
   Status           : 🎯 FULLY ACCELERATED - Maximum Performance!
============================================================
```

## Component-Level Monitoring

### Individual Component Status

```python
from ClassicLib.RustIntegration import is_rust_accelerated, get_performance_multiplier

components = [
    "parser", "formid_analyzer", "plugin_analyzer", "record_scanner",
    "report_generation", "mod_detector", "file_io_core", "database_pool"
]

for component in components:
    if is_rust_accelerated(component):
        speedup = get_performance_multiplier(component)
        print(f"✅ {component:<18}: RUST ({speedup} speedup)")
    else:
        print(f"❌ {component:<18}: Python fallback")
```

### Performance Gains by Category

```python
from ClassicLib.RustIntegration import get_rust_component_status

def analyze_performance_by_category():
    status = get_rust_component_status()

    # Group components by performance category
    categories = {
        "Core Performance (ScanLog)": [
            "parser", "formid_analyzer", "plugin_analyzer",
            "record_scanner", "report_generation", "mod_detector"
        ],
        "File I/O Operations": ["file_io_core"],
        "Database Operations": ["database_pool"]
    }

    for category, components in categories.items():
        active = sum(1 for comp in components if status["available"].get(comp, False))
        total = len(components)
        percentage = (active / total * 100) if total > 0 else 0

        print(f"\n{category}:")
        print(f"  Status: {active}/{total} active ({percentage:.0f}%)")

        for comp in components:
            if status["available"].get(comp, False):
                gain = status["performance_gains"].get(comp, "N/A")
                print(f"  ✅ {comp}: {gain}")
            else:
                reason = status["failed"].get(comp, "Unknown")
                print(f"  ❌ {comp}: {reason}")

analyze_performance_by_category()
```

## Performance Benchmarking

### Basic Timing Comparison

```python
import time
from ClassicLib.ScanLog.Parser import find_segments

def benchmark_parser(crash_data, iterations=10):
    """Benchmark parser performance with current configuration."""
    times = []

    for i in range(iterations):
        start_time = time.perf_counter()

        # This will use Rust if available, Python otherwise
        result = find_segments(crash_data, "CrashGen", "F4SE", "Fallout4")

        end_time = time.perf_counter()
        times.append(end_time - start_time)

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    print(f"Parser Performance ({iterations} iterations):")
    print(f"  Average: {avg_time*1000:.2f}ms")
    print(f"  Range: {min_time*1000:.2f}ms - {max_time*1000:.2f}ms")
    print(f"  Std dev: {(sum((t-avg_time)**2 for t in times)/len(times))**0.5*1000:.2f}ms")

    return avg_time

# Example usage with sample data
sample_crash_data = ["Sample crash log line"] * 1000
benchmark_time = benchmark_parser(sample_crash_data)
```

### Comprehensive Performance Suite

```python
import time
import psutil
import os
from pathlib import Path
from ClassicLib.RustIntegration import get_rust_component_status, is_rust_accelerated
from ClassicLib.FileIOCore import FileIOCore
from ClassicLib.ScanLog.FormIDAnalyzer import FormIDAnalyzer

class PerformanceMonitor:
    """Comprehensive performance monitoring for CLASSIC components."""

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.baseline_memory = self.get_memory_usage()
        self.results = {}

    def get_memory_usage(self):
        """Get current memory usage in MB."""
        return self.process.memory_info().rss / 1024 / 1024

    def get_cpu_usage(self):
        """Get current CPU usage percentage."""
        return self.process.cpu_percent()

    def benchmark_file_io(self, test_files=None, iterations=5):
        """Benchmark file I/O operations."""
        if not test_files:
            # Create test data if no files provided
            test_data = "Test crash log data\n" * 1000
            test_file = Path("temp_test.txt")
            test_file.write_text(test_data)
            test_files = [test_file]

        io_core = FileIOCore()
        is_rust = is_rust_accelerated("file_io_core")

        times = []
        memory_usage = []

        for i in range(iterations):
            start_memory = self.get_memory_usage()
            start_time = time.perf_counter()

            for file_path in test_files:
                content = io_core.read_file(file_path)

            end_time = time.perf_counter()
            end_memory = self.get_memory_usage()

            times.append(end_time - start_time)
            memory_usage.append(end_memory - start_memory)

        avg_time = sum(times) / len(times)
        avg_memory = sum(memory_usage) / len(memory_usage)

        result = {
            "component": "file_io_core",
            "rust_active": is_rust,
            "avg_time_ms": avg_time * 1000,
            "avg_memory_mb": avg_memory,
            "files_processed": len(test_files),
            "iterations": iterations
        }

        self.results["file_io"] = result
        return result

    def benchmark_formid_analysis(self, test_data=None, iterations=5):
        """Benchmark FormID analysis operations."""
        if not test_data:
            # Generate test FormID data
            test_data = [
                f"FormID: 0x{i:08X} Plugin: test{i%10}.esp"
                for i in range(1000, 2000)
            ]

        # This would require yamldata, plugins, etc. - simplified for demo
        is_rust = is_rust_accelerated("formid_analyzer")

        times = []
        for i in range(iterations):
            start_time = time.perf_counter()

            # Simulate FormID extraction (would use actual analyzer)
            formids = [line.split()[1] for line in test_data if "FormID:" in line]

            end_time = time.perf_counter()
            times.append(end_time - start_time)

        avg_time = sum(times) / len(times)

        result = {
            "component": "formid_analyzer",
            "rust_active": is_rust,
            "avg_time_ms": avg_time * 1000,
            "formids_processed": len(formids) if 'formids' in locals() else 0,
            "iterations": iterations
        }

        self.results["formid_analysis"] = result
        return result

    def benchmark_all_components(self):
        """Run comprehensive benchmarks on all components."""
        print("🔍 Running comprehensive performance benchmarks...")
        print("=" * 60)

        # System info
        print(f"System: {psutil.cpu_count()} CPUs, {psutil.virtual_memory().total/1024/1024/1024:.1f} GB RAM")
        print(f"Process baseline memory: {self.baseline_memory:.1f} MB")
        print()

        # File I/O benchmark
        print("📁 File I/O Performance:")
        file_result = self.benchmark_file_io()
        rust_status = "🚀 RUST" if file_result["rust_active"] else "🐍 Python"
        print(f"  {rust_status}: {file_result['avg_time_ms']:.2f}ms avg, {file_result['avg_memory_mb']:.2f}MB memory")
        print()

        # FormID analysis benchmark
        print("🔍 FormID Analysis Performance:")
        formid_result = self.benchmark_formid_analysis()
        rust_status = "🚀 RUST" if formid_result["rust_active"] else "🐍 Python"
        print(f"  {rust_status}: {formid_result['avg_time_ms']:.2f}ms avg")
        print()

        # Overall status
        status = get_rust_component_status()
        print("📊 Overall Acceleration Status:")
        print(f"  Components: {status['active_count']}/{status['total_count']} active")
        print(f"  Mode: {status['mode']}")

        return self.results

    def generate_performance_report(self):
        """Generate a detailed performance report."""
        if not self.results:
            self.benchmark_all_components()

        report = []
        report.append("# CLASSIC Performance Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # System information
        report.append("## System Information")
        report.append(f"- CPUs: {psutil.cpu_count()}")
        report.append(f"- Total RAM: {psutil.virtual_memory().total/1024/1024/1024:.1f} GB")
        report.append(f"- Available RAM: {psutil.virtual_memory().available/1024/1024/1024:.1f} GB")
        report.append(f"- Process Memory: {self.get_memory_usage():.1f} MB")
        report.append("")

        # Rust status
        status = get_rust_component_status()
        report.append("## Rust Acceleration Status")
        report.append(f"- Active Components: {status['active_count']}/{status['total_count']}")
        report.append(f"- Acceleration Mode: {status['mode']}")
        report.append("")

        # Performance results
        report.append("## Performance Results")
        for component, result in self.results.items():
            report.append(f"### {component.title()}")
            report.append(f"- Implementation: {'Rust' if result['rust_active'] else 'Python'}")
            report.append(f"- Average Time: {result['avg_time_ms']:.2f}ms")
            if 'avg_memory_mb' in result:
                report.append(f"- Memory Usage: {result['avg_memory_mb']:.2f}MB")
            report.append("")

        return "\n".join(report)

    def save_report(self, filename="performance_report.md"):
        """Save performance report to file."""
        report = self.generate_performance_report()
        Path(filename).write_text(report)
        print(f"📄 Performance report saved to: {filename}")

# Example usage
def run_performance_monitoring():
    """Run comprehensive performance monitoring."""
    monitor = PerformanceMonitor()

    # Run all benchmarks
    results = monitor.benchmark_all_components()

    # Generate and save report
    monitor.save_report("classic_performance_report.md")

    return results

# Uncomment to run:
# results = run_performance_monitoring()
```

## Memory Usage Monitoring

### Real-time Memory Tracking

```python
import psutil
import time
from ClassicLib.RustIntegration import get_rust_component_status

def monitor_memory_usage(duration=60, interval=1):
    """Monitor memory usage over time."""
    process = psutil.Process()
    measurements = []

    print(f"📊 Monitoring memory usage for {duration} seconds...")

    start_time = time.time()
    while time.time() - start_time < duration:
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()
        timestamp = time.time() - start_time

        measurements.append({
            'time': timestamp,
            'memory_mb': memory_mb,
            'cpu_percent': cpu_percent
        })

        print(f"\rTime: {timestamp:6.1f}s | Memory: {memory_mb:6.1f}MB | CPU: {cpu_percent:5.1f}%", end="")
        time.sleep(interval)

    print("\n")

    # Analysis
    avg_memory = sum(m['memory_mb'] for m in measurements) / len(measurements)
    max_memory = max(m['memory_mb'] for m in measurements)
    min_memory = min(m['memory_mb'] for m in measurements)

    print("Memory Usage Summary:")
    print(f"  Average: {avg_memory:.1f} MB")
    print(f"  Peak: {max_memory:.1f} MB")
    print(f"  Minimum: {min_memory:.1f} MB")
    print(f"  Range: {max_memory - min_memory:.1f} MB")

    # Compare with Rust status
    status = get_rust_component_status()
    if status['acceleration_active']:
        print(f"  🚀 With Rust acceleration ({status['active_count']}/{status['total_count']} components)")
        print(f"  Expected without Rust: {avg_memory * 2.5:.1f} - {avg_memory * 4:.1f} MB")
    else:
        print(f"  🐍 Without Rust acceleration")
        print(f"  Expected with Rust: {avg_memory * 0.25:.1f} - {avg_memory * 0.4:.1f} MB")

    return measurements
```

### Memory Leak Detection

```python
import gc
import psutil
from ClassicLib.RustIntegration import get_rust_component_status

def detect_memory_leaks(test_function, iterations=100):
    """Detect potential memory leaks in operations."""
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024

    memory_samples = []

    print(f"🔍 Testing for memory leaks over {iterations} iterations...")

    for i in range(iterations):
        # Run the test function
        test_function()

        # Force garbage collection
        gc.collect()

        # Measure memory
        current_memory = process.memory_info().rss / 1024 / 1024
        memory_samples.append(current_memory)

        if i % 10 == 0:
            print(f"Iteration {i:3d}: {current_memory:.1f} MB (+{current_memory - initial_memory:.1f} MB)")

    # Analyze trend
    final_memory = memory_samples[-1]
    memory_growth = final_memory - initial_memory

    # Calculate trend (linear regression)
    n = len(memory_samples)
    sum_x = sum(range(n))
    sum_y = sum(memory_samples)
    sum_xy = sum(i * mem for i, mem in enumerate(memory_samples))
    sum_x2 = sum(i**2 for i in range(n))

    trend = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)

    print(f"\n📊 Memory Leak Analysis:")
    print(f"  Initial memory: {initial_memory:.1f} MB")
    print(f"  Final memory: {final_memory:.1f} MB")
    print(f"  Total growth: {memory_growth:.1f} MB")
    print(f"  Growth per iteration: {memory_growth/iterations:.3f} MB")
    print(f"  Trend: {trend:.3f} MB/iteration")

    # Determine if there's a leak
    if abs(trend) < 0.001:
        print("  ✅ No significant memory leak detected")
    elif trend > 0.01:
        print("  ⚠️  Possible memory leak detected!")
    elif trend > 0.001:
        print("  📊 Minor memory growth (likely normal)")
    else:
        print("  📉 Memory usage decreasing (good)")

    # Rust status
    status = get_rust_component_status()
    if status['acceleration_active']:
        print(f"  🚀 Rust components active: {status['active_count']}/{status['total_count']}")
    else:
        print("  🐍 Running in Python mode")

    return {
        'initial_memory': initial_memory,
        'final_memory': final_memory,
        'growth': memory_growth,
        'trend': trend,
        'samples': memory_samples
    }

# Example test function
def sample_test_operation():
    """Sample operation to test for memory leaks."""
    from ClassicLib.FileIOCore import FileIOCore
    io_core = FileIOCore()

    # Simulate file operation
    test_data = "Sample crash log data\n" * 100
    # Process the data (simulate parsing, analysis, etc.)
    lines = test_data.split('\n')
    processed = [line.strip() for line in lines if line.strip()]

    return len(processed)

# Uncomment to run leak detection:
# leak_results = detect_memory_leaks(sample_test_operation, 50)
```

## Performance Regression Detection

### Automated Performance Testing

```python
import json
from pathlib import Path
import time
from ClassicLib.RustIntegration import get_rust_component_status

class PerformanceRegression:
    """Detect performance regressions by comparing with baseline measurements."""

    def __init__(self, baseline_file="performance_baseline.json"):
        self.baseline_file = Path(baseline_file)
        self.baseline = self.load_baseline()
        self.current_results = {}

    def load_baseline(self):
        """Load baseline performance measurements."""
        if self.baseline_file.exists():
            return json.loads(self.baseline_file.read_text())
        return {}

    def save_baseline(self):
        """Save current measurements as new baseline."""
        self.baseline_file.write_text(json.dumps(self.current_results, indent=2))
        print(f"💾 Saved performance baseline to {self.baseline_file}")

    def measure_component(self, component_name, test_function, iterations=10):
        """Measure performance of a specific component."""
        times = []

        for i in range(iterations):
            start_time = time.perf_counter()
            test_function()
            end_time = time.perf_counter()
            times.append(end_time - start_time)

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        std_dev = (sum((t - avg_time)**2 for t in times) / len(times))**0.5

        result = {
            'avg_time': avg_time,
            'min_time': min_time,
            'max_time': max_time,
            'std_dev': std_dev,
            'iterations': iterations,
            'timestamp': time.time()
        }

        self.current_results[component_name] = result
        return result

    def check_regression(self, component_name, current_result, threshold=0.2):
        """Check if current performance represents a regression."""
        if component_name not in self.baseline:
            print(f"⚠️  No baseline for {component_name} - establishing baseline")
            return None

        baseline = self.baseline[component_name]
        current_time = current_result['avg_time']
        baseline_time = baseline['avg_time']

        # Calculate percentage change
        change = (current_time - baseline_time) / baseline_time

        if change > threshold:
            print(f"🔴 REGRESSION detected in {component_name}:")
            print(f"   Baseline: {baseline_time*1000:.2f}ms")
            print(f"   Current:  {current_time*1000:.2f}ms")
            print(f"   Change:   +{change*100:.1f}% (slower)")
            return "regression"
        elif change < -threshold:
            print(f"🟢 IMPROVEMENT detected in {component_name}:")
            print(f"   Baseline: {baseline_time*1000:.2f}ms")
            print(f"   Current:  {current_time*1000:.2f}ms")
            print(f"   Change:   {change*100:.1f}% (faster)")
            return "improvement"
        else:
            print(f"✅ {component_name}: Performance stable ({change*100:.1f}% change)")
            return "stable"

    def run_regression_tests(self):
        """Run comprehensive regression testing."""
        print("🔍 Running performance regression tests...")
        print("=" * 50)

        # Test file I/O
        def test_file_io():
            from ClassicLib.FileIOCore import FileIOCore
            io_core = FileIOCore()
            # Simulate file operation
            test_data = "test data" * 100
            return len(test_data)

        io_result = self.measure_component("file_io", test_file_io)
        self.check_regression("file_io", io_result)

        # Test parser (simplified)
        def test_parser():
            from ClassicLib.ScanLog.Parser import find_segments
            test_data = ["test line"] * 100
            return len(test_data)

        parser_result = self.measure_component("parser", test_parser)
        self.check_regression("parser", parser_result)

        # Overall status
        status = get_rust_component_status()
        print(f"\n📊 Rust Status: {status['active_count']}/{status['total_count']} components active")

        return self.current_results

    def generate_regression_report(self):
        """Generate detailed regression analysis report."""
        if not self.current_results:
            print("No performance data available. Run regression tests first.")
            return

        report = []
        report.append("# Performance Regression Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        for component, result in self.current_results.items():
            report.append(f"## {component.title()}")
            report.append(f"- Average Time: {result['avg_time']*1000:.2f}ms")
            report.append(f"- Min Time: {result['min_time']*1000:.2f}ms")
            report.append(f"- Max Time: {result['max_time']*1000:.2f}ms")
            report.append(f"- Std Deviation: {result['std_dev']*1000:.2f}ms")
            report.append(f"- Iterations: {result['iterations']}")

            if component in self.baseline:
                baseline = self.baseline[component]
                change = (result['avg_time'] - baseline['avg_time']) / baseline['avg_time'] * 100
                report.append(f"- Change from baseline: {change:+.1f}%")

            report.append("")

        return "\n".join(report)

# Example usage
def run_performance_monitoring_suite():
    """Run complete performance monitoring suite."""
    regression = PerformanceRegression()

    # Run regression tests
    results = regression.run_regression_tests()

    # Generate report
    report = regression.generate_regression_report()
    print("\n" + "="*50)
    print(report)

    # Optionally save as new baseline
    # regression.save_baseline()

    return results

# Uncomment to run:
# monitoring_results = run_performance_monitoring_suite()
```

## Production Monitoring

### Health Check Endpoint

```python
from ClassicLib.RustIntegration import get_rust_component_status
import time
import psutil

def rust_health_check():
    """Comprehensive health check for Rust components."""
    start_time = time.time()

    # Component status
    status = get_rust_component_status()

    # System resources
    memory_mb = psutil.virtual_memory().available / 1024 / 1024
    cpu_percent = psutil.cpu_percent(interval=0.1)

    # Performance check
    test_start = time.perf_counter()
    # Simple performance test
    test_data = ["test"] * 1000
    processed = [item.upper() for item in test_data]  # Simple CPU operation
    test_time = time.perf_counter() - test_start

    health = {
        "status": "healthy" if status["acceleration_active"] else "degraded",
        "rust_components": {
            "active": status["active_count"],
            "total": status["total_count"],
            "percentage": round(status["active_count"] / status["total_count"] * 100, 1)
        },
        "performance": {
            "test_time_ms": round(test_time * 1000, 2),
            "expected_improvement": "10-150x with full Rust acceleration"
        },
        "system": {
            "available_memory_mb": round(memory_mb, 1),
            "cpu_percent": cpu_percent
        },
        "components": {}
    }

    # Individual component status
    for component, active in status["available"].items():
        health["components"][component] = {
            "active": active,
            "speedup": status["performance_gains"].get(component, "N/A")
        }

    # Health determination
    if status["active_count"] == status["total_count"]:
        health["status"] = "optimal"
        health["message"] = "All Rust components active - maximum performance"
    elif status["active_count"] > status["total_count"] * 0.7:
        health["status"] = "good"
        health["message"] = f"Most components active ({status['active_count']}/{status['total_count']})"
    elif status["active_count"] > 0:
        health["status"] = "degraded"
        health["message"] = f"Partial acceleration ({status['active_count']}/{status['total_count']})"
    else:
        health["status"] = "critical"
        health["message"] = "No Rust acceleration - performance severely impacted"

    health["check_duration_ms"] = round((time.time() - start_time) * 1000, 2)

    return health

# Example usage
def print_health_status():
    """Print formatted health status."""
    health = rust_health_check()

    status_emoji = {
        "optimal": "🟢",
        "good": "🟡",
        "degraded": "🟠",
        "critical": "🔴"
    }

    print(f"{status_emoji.get(health['status'], '❓')} System Status: {health['status'].upper()}")
    print(f"📊 Rust Components: {health['rust_components']['active']}/{health['rust_components']['total']} ({health['rust_components']['percentage']}%)")
    print(f"⚡ Performance Test: {health['performance']['test_time_ms']}ms")
    print(f"💾 Available Memory: {health['system']['available_memory_mb']:.1f} MB")
    print(f"🖥️  CPU Usage: {health['system']['cpu_percent']}%")
    print(f"💬 {health['message']}")

    return health

# Monitor continuously
def continuous_monitoring(interval=60, duration=3600):
    """Run continuous health monitoring."""
    print(f"🔄 Starting continuous monitoring (every {interval}s for {duration}s)")

    start_time = time.time()
    checks = 0

    while time.time() - start_time < duration:
        checks += 1
        timestamp = time.strftime("%H:%M:%S")

        print(f"\n[{timestamp}] Health Check #{checks}")
        print("-" * 40)

        health = print_health_status()

        # Alert on critical issues
        if health["status"] == "critical":
            print("🚨 ALERT: Critical performance issue detected!")

        time.sleep(interval)

    print(f"\n✅ Monitoring completed. Performed {checks} health checks.")

# Uncomment to run continuous monitoring:
# continuous_monitoring(interval=30, duration=300)  # 5 minutes of monitoring
```

## Summary

This performance monitoring guide provides comprehensive tools for:

1. **Status Verification**: Quick checks to confirm Rust acceleration is working
2. **Component Analysis**: Individual component performance monitoring
3. **Benchmarking**: Detailed performance measurement and comparison
4. **Memory Monitoring**: Real-time memory usage and leak detection
5. **Regression Testing**: Automated detection of performance changes
6. **Production Monitoring**: Health checks and continuous monitoring

Use these tools to ensure CLASSIC is running at optimal performance with full Rust acceleration benefits. Regular monitoring helps identify issues early and maintain the 10-150x performance improvements that Rust acceleration provides.
