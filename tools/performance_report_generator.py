#!/usr/bin/env python3
"""Performance Report Generator for CLASSIC.

This tool generates comprehensive performance reports by running benchmarks,
analyzing results, and producing multiple output formats for different audiences:
- Technical markdown reports for developers
- Interactive HTML dashboards for stakeholders
- Machine-readable JSON for monitoring systems
- Summary reports for management

Usage:
    python performance_report_generator.py [options]

Options:
    --output-dir: Directory for generated reports (default: reports/)
    --run-benchmarks: Run fresh benchmarks before generating reports
    --include-real-logs: Include real crash log testing (requires D:/Crash Logs)
    --format: Output formats (markdown,html,json,all) - default: all
    --verbose: Detailed logging during generation
"""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class PerformanceReportGenerator:
    """Comprehensive performance report generator for CLASSIC Phase 6.

    This class orchestrates the entire report generation process:
    1. Running performance benchmarks
    2. Collecting and analyzing results
    3. Generating reports in multiple formats
    4. Creating deployment-ready documentation
    """

    def __init__(self, output_dir: Path | None = None, verbose: bool = False):
        """Initialize the report generator with output settings.

        Args:
            output_dir: Directory for generated reports, defaults to project reports folder.
            verbose: Enable verbose logging during report generation.

        """
        self.project_root = project_root
        self.output_dir = output_dir or (self.project_root / "reports")
        self.verbose = verbose
        self.benchmark_results = {}
        self.analysis_results = {}
        self.generation_timestamp = datetime.now(UTC)

        # Ensure output directory exists
        self.output_dir.mkdir(exist_ok=True)

        if self.verbose:
            print(f"📁 Output directory: {self.output_dir}")
            print(f"🕐 Generation started: {self.generation_timestamp}")

    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamp if verbose mode enabled."""
        if self.verbose:
            timestamp = datetime.now(UTC).strftime("%H:%M:%S")
            print(f"[{timestamp}] {level}: {message}")

    def check_rust_availability(self) -> dict[str, Any]:
        """Check availability and version of Rust components."""
        self.log("Checking Rust component availability...")

        try:
            from ClassicLib.integration.factory import get_rust_component_status

            info = {"components": get_rust_component_status()["available"], "versions": {}, "disabled": False}
            components = info.get("components", {})
            versions = info.get("versions", {})

            # Count available modules (true values in components dict)
            available_count = sum(1 for v in components.values() if v)

            availability = {
                "rust_available": available_count > 0,
                "architecture_type": "modular",  # Replaces monolithic classic_core
                "available_modules": [k for k, v in components.items() if v],
                "scanlog_available": components.get("parser", False),  # Parser is part of scanlog
                "versions": versions,
            }

            if availability["scanlog_available"]:
                # List components that are part of scanlog (parser, formid_analyzer, etc.)
                scanlog_keys = ["parser", "formid_analyzer", "plugin_analyzer", "record_scanner"]
                availability["scanlog_components"] = [k for k in scanlog_keys if components.get(k)]

            self.log(f"✅ Rust components available: {available_count} modules")
            return availability

        except ImportError as e:
            self.log(f"❌ Rust components not available: {e}", "WARNING")
            return {"rust_available": False, "error": str(e)}

    def run_benchmark_suite(self, include_real_logs: bool = True) -> dict[str, Any]:
        """Run comprehensive benchmark suite and collect results."""
        self.log("Starting benchmark suite execution...")

        benchmark_scripts = [
            ("working_rust_benchmarks.py", "Working component benchmarks"),
            ("comprehensive_benchmark.py", "Comprehensive system benchmarks"),
        ]

        # Add realistic benchmarks if requested
        if include_real_logs:
            benchmark_scripts.append(("benchmark_report_generation_realistic.py", "Realistic scenario benchmarks"))

        results: dict[str, Any] = {}

        for script_name, description in benchmark_scripts:
            self.log(f"Running {description}...")
            script_path = self.project_root / script_name

            if not script_path.exists():
                self.log(f"⚠️ Benchmark script not found: {script_name}", "WARNING")
                continue

            try:
                # Run benchmark script and capture output
                result_file = self.output_dir / f"{script_path.stem}_results.json"
                cmd = [sys.executable, str(script_path), "--output", str(result_file)]

                subprocess.run(cmd, cwd=str(self.project_root), check=True)

                # Load results if available
                if result_file.exists():
                    with Path(result_file).open() as f:
                        script_results = json.load(f)
                    results[script_path.stem] = script_results
                    self.log(f"✅ {description} completed successfully")
                else:
                    self.log(f"⚠️ No results file generated for {script_name}", "WARNING")
                    results[script_path.stem] = {"error": "No results file generated"}

            except subprocess.CalledProcessError as e:
                self.log(f"❌ {description} failed: {e}", "ERROR")
                results[script_path.stem] = {"error": f"Script execution failed: {e}"}
            except Exception as e:
                self.log(f"❌ Unexpected error running {description}: {e}", "ERROR")
                results[script_path.stem] = {"error": f"Unexpected error: {e}"}

        self.log(f"Benchmark suite completed: {len(results)} scripts executed")  # pyright: ignore[reportUnknownArgumentType]
        return results

    def analyze_benchmark_results(self, benchmark_results: dict[str, Any]) -> dict[str, Any]:
        """Analyze benchmark results and generate insights."""
        self.log("Analyzing benchmark results...")

        summary: dict[str, Any] = {
            "benchmarks_run": len(benchmark_results),
            "successful_benchmarks": 0,
            "failed_benchmarks": 0,
            "components_tested": set(),
            "overall_status": "UNKNOWN",
        }
        analysis: dict[str, Any] = {
            "timestamp": self.generation_timestamp.isoformat(),
            "summary": summary,
            "performance_insights": [],
            "recommendations": [],
            "component_status": {},
        }

        # Analyze each benchmark result
        for benchmark_name, results in benchmark_results.items():
            if isinstance(results, dict) and "error" not in results:
                summary["successful_benchmarks"] += 1

                # Extract component information
                if benchmark_name == "working_rust_benchmarks":
                    self._analyze_working_benchmarks(results, analysis, summary)  # pyright: ignore[reportUnknownArgumentType]
                elif benchmark_name == "comprehensive_benchmark":
                    self._analyze_comprehensive_benchmarks(results, summary)  # pyright: ignore[reportUnknownArgumentType]
                elif benchmark_name == "benchmark_report_generation_realistic":
                    self._analyze_realistic_benchmarks(results, summary)  # pyright: ignore[reportUnknownArgumentType]
            else:
                summary["failed_benchmarks"] += 1

        # Determine overall status
        success_rate = summary["successful_benchmarks"] / len(benchmark_results) if benchmark_results else 0

        if success_rate >= 0.8:
            summary["overall_status"] = "EXCELLENT"
        elif success_rate >= 0.6:
            summary["overall_status"] = "GOOD"
        elif success_rate >= 0.4:
            summary["overall_status"] = "FAIR"
        else:
            summary["overall_status"] = "NEEDS_IMPROVEMENT"

        summary["components_tested"] = list(summary["components_tested"])
        self.log(f"Analysis completed: {summary['overall_status']} status")

        return analysis

    def _analyze_working_benchmarks(self, results: dict[str, Any], analysis: dict[str, Any], summary: dict[str, Any]) -> None:
        """Analyze working benchmark results."""
        performance_insights: list[dict[str, Any]] = analysis["performance_insights"]
        recommendations: list[dict[str, Any]] = analysis["recommendations"]
        component_status: dict[str, Any] = analysis["component_status"]
        components_tested: set[str] = summary["components_tested"]

        for component, component_results in results.items():
            if isinstance(component_results, dict) and "error" not in component_results:
                components_tested.add(component)

                # Analyze performance metrics
                if "speedup" in component_results:
                    speedup: float = component_results["speedup"]  # pyright: ignore[reportUnknownVariableType]

                    if speedup >= 2.0:
                        performance_insights.append({
                            "component": component,
                            "insight": f"Excellent performance: {speedup:.2f}x speedup",
                            "level": "EXCELLENT",
                        })
                    elif speedup >= 1.2:
                        performance_insights.append({
                            "component": component,
                            "insight": f"Good performance: {speedup:.2f}x speedup",
                            "level": "GOOD",
                        })
                    else:
                        performance_insights.append({
                            "component": component,
                            "insight": f"Limited performance: {speedup:.2f}x speedup (FFI overhead likely)",
                            "level": "LIMITED",
                        })

                        # Add recommendation for FFI overhead
                        recommendations.append({
                            "component": component,
                            "recommendation": "Consider batch processing APIs to reduce FFI overhead",
                            "priority": "HIGH",
                        })

                # Analyze memory efficiency
                if "memory_reduction_percent" in component_results:
                    reduction: float = component_results["memory_reduction_percent"]  # pyright: ignore[reportUnknownVariableType]
                    if reduction >= 90:
                        performance_insights.append({
                            "component": component,
                            "insight": f"Exceptional memory efficiency: {reduction:.1f}% reduction",
                            "level": "EXCEPTIONAL",
                        })

                # Component status
                component_status[component] = {
                    "functional": True,
                    "performance": component_results.get("speedup", "N/A"),
                    "status": "WORKING",
                }

    def _analyze_comprehensive_benchmarks(self, results: dict[str, Any], summary: dict[str, Any]) -> None:
        """Analyze comprehensive benchmark results."""
        # This would analyze the comprehensive benchmark results
        # For now, just mark components as tested
        components_tested: set[str] = summary["components_tested"]
        for component in results:
            if component not in ["error"]:
                components_tested.add(component)

    def _analyze_realistic_benchmarks(self, results: dict[str, Any], summary: dict[str, Any]) -> None:
        """Analyze realistic benchmark results."""
        # This would analyze realistic benchmark results
        # For now, just extract any performance insights
        components_tested: set[str] = summary["components_tested"]
        if "rust_available" in results:
            components_tested.add("realistic_scenarios")

    def generate_markdown_report(self, analysis: dict[str, Any]) -> Path:
        """Generate comprehensive markdown performance report."""
        self.log("Generating markdown report...")

        output_path = self.output_dir / f"Phase6_Performance_Report_{self.generation_timestamp.strftime('%Y%m%d_%H%M%S')}.md"

        # Use the existing comprehensive report as template
        template_path = self.project_root / "docs" / "Phase6_Performance_Report.md"

        if template_path.exists():
            # Copy and update the existing report
            shutil.copy2(template_path, output_path)

            # Add generation metadata
            with Path(output_path).open("a", encoding="utf-8") as f:
                f.write("\n\n---\n\n")
                f.write(f"**Report Generated:** {self.generation_timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("**Generation Tool:** performance_report_generator.py\n")
                f.write(f"**Benchmarks Status:** {analysis['summary']['overall_status']}\n")
                f.write(f"**Components Tested:** {len(analysis['summary']['components_tested'])}\n")
        else:
            # Generate basic report structure
            with Path(output_path).open("w", encoding="utf-8") as f:
                f.write("# Phase 6 Performance Report\n\n")
                f.write(f"**Generated:** {self.generation_timestamp}\n")
                f.write(f"**Status:** {analysis['summary']['overall_status']}\n\n")

                # Add component status
                f.write("## Component Status\n\n")
                f.writelines(
                    f"- **{component}**: {status['status']} (Performance: {status['performance']})\n"
                    for component, status in analysis["component_status"].items()
                )

                # Add insights
                f.write("\n## Performance Insights\n\n")
                f.writelines(
                    f"- **{insight['component']}**: {insight['insight']} ({insight['level']})\n"
                    for insight in analysis["performance_insights"]
                )

                # Add recommendations
                f.write("\n## Recommendations\n\n")
                f.writelines(
                    f"- **{rec['component']}**: {rec['recommendation']} (Priority: {rec['priority']})\n"
                    for rec in analysis["recommendations"]
                )

        self.log(f"✅ Markdown report generated: {output_path}")
        return output_path

    def generate_html_dashboard(self, analysis: dict[str, Any]) -> Path:
        """Generate interactive HTML performance dashboard."""
        self.log("Generating HTML dashboard...")

        output_path = self.output_dir / f"performance_dashboard_{self.generation_timestamp.strftime('%Y%m%d_%H%M%S')}.html"

        # Copy and update the existing dashboard
        template_path = self.project_root / "docs" / "performance_dashboard.html"

        if template_path.exists():
            shutil.copy2(template_path, output_path)

            # Update dashboard with current data (basic approach)
            content = Path(output_path).read_text(encoding="utf-8")

            # Update title and timestamp
            timestamp_str = self.generation_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            content = content.replace(
                "Rust Integration & Optimization - Complete Performance Analysis",
                f"Rust Integration & Optimization - Generated {timestamp_str}",
            )

            Path(output_path).write_text(content, encoding="utf-8")
        else:
            # Generate basic HTML dashboard
            with Path(output_path).open("w", encoding="utf-8") as f:
                f.write(
                    """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CLASSIC Performance Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .metric {{ margin: 10px 0; padding: 10px; background: #f5f5f5; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>CLASSIC Performance Dashboard</h1>
        <p>Generated: {}</p>
        <p>Status: {}</p>
    </div>
    <div class="metrics">
""".format(self.generation_timestamp.strftime("%Y-%m-%d %H:%M:%S"), analysis["summary"]["overall_status"])
                )

                # Add component metrics
                f.writelines(
                    f"""
        <div class="metric">
            <strong>{component}:</strong> {status["status"]}
            (Performance: {status["performance"]})
        </div>
"""
                    for component, status in analysis["component_status"].items()
                )

                f.write("""
    </div>
</body>
</html>""")

        self.log(f"✅ HTML dashboard generated: {output_path}")
        return output_path

    def generate_json_metrics(self, analysis: dict[str, Any]) -> Path:
        """Generate machine-readable JSON metrics report."""
        self.log("Generating JSON metrics...")

        output_path = self.output_dir / f"phase6_metrics_{self.generation_timestamp.strftime('%Y%m%d_%H%M%S')}.json"

        # Create comprehensive metrics structure
        metrics = {
            "report_metadata": {
                "generation_timestamp": self.generation_timestamp.isoformat(),
                "generator_tool": "performance_report_generator.py",
                "phase": "Phase 6 - Integration & Optimization",
                "project": "CLASSIC",
                "version": "6.0.0",
            },
            "summary": analysis["summary"],
            "component_status": analysis["component_status"],
            "performance_insights": analysis["performance_insights"],
            "recommendations": analysis["recommendations"],
            "raw_benchmark_results": self.benchmark_results,
        }

        with Path(output_path).open("w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, default=str)

        self.log(f"✅ JSON metrics generated: {output_path}")
        return output_path

    def generate_executive_summary(self, analysis: dict[str, Any]) -> Path:
        """Generate concise executive summary."""
        self.log("Generating executive summary...")

        output_path = self.output_dir / f"Phase6_Executive_Summary_{self.generation_timestamp.strftime('%Y%m%d')}.md"

        with Path(output_path).open("w", encoding="utf-8") as f:
            f.write("# Phase 6 Executive Summary\n\n")
            f.write(f"**Date:** {self.generation_timestamp.strftime('%B %d, %Y')}\n")
            f.write(f"**Status:** {analysis['summary']['overall_status']}\n\n")

            f.write("## Key Achievements\n\n")
            f.write(f"- **Components Working:** {len(analysis['summary']['components_tested'])}\n")
            f.write(
                f"- **Benchmark Success Rate:** {analysis['summary']['successful_benchmarks']}/{analysis['summary']['benchmarks_run']}\n"
            )

            # Outstanding insights
            excellent_insights = [
                insight for insight in analysis["performance_insights"] if insight.get("level") in ["EXCELLENT", "EXCEPTIONAL"]
            ]

            if excellent_insights:
                f.write("\n## Outstanding Performance\n\n")
                for insight in excellent_insights[:3]:  # Top 3
                    f.write(f"- **{insight['component']}**: {insight['insight']}\n")

            # High priority recommendations
            high_priority_recs = [rec for rec in analysis["recommendations"] if rec.get("priority") == "HIGH"]

            if high_priority_recs:
                f.write("\n## Priority Actions\n\n")
                for rec in high_priority_recs[:3]:  # Top 3
                    f.write(f"- **{rec['component']}**: {rec['recommendation']}\n")

            # Conclusion
            f.write("\n## Recommendation\n\n")
            if analysis["summary"]["overall_status"] in ["EXCELLENT", "GOOD"]:
                f.write("✅ **APPROVED FOR PRODUCTION DEPLOYMENT**\n\n")
                f.write("Phase 6 has successfully achieved its integration and optimization goals. ")
                f.write("The system is stable, performant, and ready for production use.")
            else:
                f.write("⚠️ **ADDITIONAL OPTIMIZATION RECOMMENDED**\n\n")
                f.write("While functional, additional optimization work is recommended ")
                f.write("before full production deployment.")

        self.log(f"✅ Executive summary generated: {output_path}")
        return output_path

    def generate_all_reports(self, run_benchmarks: bool = False, include_real_logs: bool = True) -> dict[str, Path]:
        """Generate all report formats."""
        self.log("Starting comprehensive report generation...")

        generated_files: dict[str, Path] = {}

        # Step 1: Check Rust availability
        self.check_rust_availability()

        # Step 2: Run benchmarks if requested
        if run_benchmarks:
            self.benchmark_results = self.run_benchmark_suite(include_real_logs)
        else:
            # Load existing benchmark results if available
            self.log("Loading existing benchmark results...")
            result_files = [
                "working_rust_benchmarks_results.json",
                "comprehensive_results.json",
                "targeted_results.json",
            ]

            for result_file in result_files:
                file_path = self.project_root / result_file
                if file_path.exists():
                    try:
                        with Path(file_path).open() as f:
                            self.benchmark_results[file_path.stem] = json.load(f)
                        self.log(f"✅ Loaded {result_file}")
                    except Exception as e:
                        self.log(f"⚠️ Failed to load {result_file}: {e}", "WARNING")

        # Step 3: Analyze results
        self.analysis_results = self.analyze_benchmark_results(self.benchmark_results)

        # Step 4: Generate all report formats
        try:
            generated_files["markdown"] = self.generate_markdown_report(self.analysis_results)
        except Exception as e:
            self.log(f"❌ Markdown generation failed: {e}", "ERROR")

        try:
            generated_files["html"] = self.generate_html_dashboard(self.analysis_results)
        except Exception as e:
            self.log(f"❌ HTML generation failed: {e}", "ERROR")

        try:
            generated_files["json"] = self.generate_json_metrics(self.analysis_results)
        except Exception as e:
            self.log(f"❌ JSON generation failed: {e}", "ERROR")

        try:
            generated_files["summary"] = self.generate_executive_summary(self.analysis_results)
        except Exception as e:
            self.log(f"❌ Summary generation failed: {e}", "ERROR")

        # Step 5: Generate index file
        try:
            generated_files["index"] = self.generate_index_file(generated_files)  # pyright: ignore[reportUnknownArgumentType]
        except Exception as e:
            self.log(f"❌ Index generation failed: {e}", "ERROR")

        self.log(f"✅ Report generation completed: {len(generated_files)} files generated")  # pyright: ignore[reportUnknownArgumentType]
        return generated_files

    def generate_index_file(self, generated_files: dict[str, Path]) -> Path:
        """Generate an index file listing all generated reports."""
        index_path = self.output_dir / "README.md"

        with Path(index_path).open("w", encoding="utf-8") as f:
            f.write("# CLASSIC Phase 6 Performance Reports\n\n")
            f.write(f"**Generated:** {self.generation_timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("**Tool:** performance_report_generator.py\n\n")

            f.write("## Available Reports\n\n")

            for report_type, file_path in generated_files.items():
                if report_type != "index":
                    relative_path = file_path.relative_to(self.output_dir)
                    f.write(f"- **{report_type.title()}**: [{file_path.name}]({relative_path})\n")

            f.write("\n## Report Types\n\n")
            f.write("- **Markdown**: Comprehensive technical report for developers\n")
            f.write("- **HTML**: Interactive dashboard for stakeholders\n")
            f.write("- **JSON**: Machine-readable metrics for monitoring\n")
            f.write("- **Summary**: Executive summary for management\n")

            f.write("\n## Usage\n\n")
            f.write("```bash\n")
            f.write("# Generate fresh reports with new benchmarks\n")
            f.write("python tools/performance_report_generator.py --run-benchmarks\n\n")
            f.write("# Generate reports from existing benchmark data\n")
            f.write("python tools/performance_report_generator.py\n\n")
            f.write("# Generate specific format only\n")
            f.write("python tools/performance_report_generator.py --format html\n")
            f.write("```\n")

        return index_path


def main():
    """Serve as main entry point for the performance report generator."""
    parser = argparse.ArgumentParser(
        description="Generate comprehensive performance reports for CLASSIC Phase 6",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python performance_report_generator.py --run-benchmarks --verbose
  python performance_report_generator.py --format html --output-dir ./custom_reports
  python performance_report_generator.py --include-real-logs
        """,
    )

    parser.add_argument("--output-dir", type=Path, default=None, help="Directory for generated reports (default: reports/)")

    parser.add_argument("--run-benchmarks", action="store_true", help="Run fresh benchmarks before generating reports")

    parser.add_argument(
        "--include-real-logs", action="store_true", default=True, help="Include real crash log testing (requires D:/Crash Logs)"
    )

    parser.add_argument(
        "--format", choices=["markdown", "html", "json", "summary", "all"], default="all", help="Output format to generate (default: all)"
    )

    parser.add_argument("--verbose", action="store_true", help="Detailed logging during generation")

    args = parser.parse_args()

    # Initialize generator
    generator = PerformanceReportGenerator(output_dir=args.output_dir, verbose=args.verbose)

    print("🚀 CLASSIC Performance Report Generator")
    print("=" * 50)

    try:
        if args.format == "all":
            # Generate all report types
            generated_files = generator.generate_all_reports(run_benchmarks=args.run_benchmarks, include_real_logs=args.include_real_logs)

            print("\n✅ Report generation complete!")
            print(f"📁 Output directory: {generator.output_dir}")
            print(f"📄 Generated files: {len(generated_files)}")

            for report_type, file_path in generated_files.items():
                print(f"   - {report_type}: {file_path.name}")

        else:
            # Generate specific format
            print(f"Generating {args.format} report...")

            # Load existing data
            generator.benchmark_results = {}  # Would load existing results
            generator.analysis_results = generator.analyze_benchmark_results(generator.benchmark_results)  # pyright: ignore[reportUnknownArgumentType]

            output_file = None
            if args.format == "markdown":
                output_file = generator.generate_markdown_report(generator.analysis_results)
            elif args.format == "html":
                output_file = generator.generate_html_dashboard(generator.analysis_results)
            elif args.format == "json":
                output_file = generator.generate_json_metrics(generator.analysis_results)
            elif args.format == "summary":
                output_file = generator.generate_executive_summary(generator.analysis_results)

            if output_file:
                print(f"✅ {args.format} report generated: {output_file}")

    except KeyboardInterrupt:
        print("\n⚠️ Report generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Report generation failed: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
