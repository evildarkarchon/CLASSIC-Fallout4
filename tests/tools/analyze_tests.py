#!/usr/bin/env python
"""
Test Analyzer Tool for CLASSIC-Fallout4

Analyzes test files to categorize tests as unit, integration, or E2E.
Helps identify files that need to be split and provides detailed reports.

Usage:
    python tests/tools/analyze_tests.py path/to/test_file.py
    python tests/tools/analyze_tests.py tests/  # Analyze all test files
"""

import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class TestInfo:
    """Information about a single test function."""
    name: str
    line_number: int
    category: str
    reasons: list[str]
    has_async: bool
    uses_fixtures: bool


@dataclass
class FileAnalysis:
    """Analysis results for a test file."""
    file_path: Path
    total_lines: int
    total_tests: int
    unit_tests: list[TestInfo]
    integration_tests: list[TestInfo]
    e2e_tests: list[TestInfo]
    performance_tests: list[TestInfo]
    unknown_tests: list[TestInfo]
    imports: list[str]
    fixtures_used: set[str]
    needs_split: bool
    violations: list[str]
    is_performance_file: bool = False


class TestCategorizer(ast.NodeVisitor):
    """AST visitor to categorize test functions."""

    def __init__(self):
        self.tests = []
        self.imports = []
        self.current_class = None
        self.fixtures_used = set()
        self.is_performance_file = False

    def visit_Import(self, node: ast.Import) -> Any:
        """Track import statements."""
        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        """Track from-import statements."""
        if node.module:
            for alias in node.names:
                self.imports.append(f"{node.module}.{alias.name}")

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        """Track test classes."""
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        """Analyze test functions."""
        if node.name.startswith('test_'):
            test_name = f"{self.current_class}.{node.name}" if self.current_class else node.name

            # Extract fixtures from function signature
            fixtures = []
            for arg in node.args.args[1:]:  # Skip 'self'
                fixtures.append(arg.arg)
                self.fixtures_used.add(arg.arg)

            # Analyze function body
            analyzer = TestBodyAnalyzer()
            analyzer.visit(node)

            category, reasons = self._categorize_test(analyzer, fixtures)

            test_info = TestInfo(
                name=test_name,
                line_number=node.lineno,
                category=category,
                reasons=reasons,
                has_async=isinstance(node, ast.AsyncFunctionDef),
                uses_fixtures=bool(fixtures)
            )

            self.tests.append(test_info)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        """Handle async test functions."""
        self.visit_FunctionDef(node)

    def _categorize_test(self, analyzer: 'TestBodyAnalyzer', fixtures: list[str]) -> tuple[str, list[str]]:
        """Categorize a test based on its characteristics."""
        reasons = []

        # Performance test detection (highest priority)
        if analyzer.is_performance_test or self.is_performance_file:
            if analyzer.performance_indicators:
                reasons.extend(analyzer.performance_indicators)
            if self.is_performance_file:
                reasons.append("File identified as performance test file")
            return "performance", reasons

        # Unit test indicators
        unit_indicators = 0
        if analyzer.has_mocks:
            unit_indicators += 2
            reasons.append("Uses mocks")

        if not analyzer.has_file_io:
            unit_indicators += 1
            reasons.append("No file I/O detected")

        if not analyzer.has_database_calls:
            unit_indicators += 1
            reasons.append("No database calls")

        if analyzer.is_simple_logic:
            unit_indicators += 1
            reasons.append("Simple logic testing")

        # Integration test indicators
        integration_indicators = 0
        if analyzer.has_file_io and not analyzer.has_entry_points:
            integration_indicators += 2
            reasons.append("Has file I/O operations")

        if analyzer.has_database_calls:
            integration_indicators += 2
            reasons.append("Has database interactions")

        if analyzer.has_multiple_components:
            integration_indicators += 1
            reasons.append("Tests multiple components")

        if "tmp_path" in fixtures:
            integration_indicators += 1
            reasons.append("Uses temporary file fixtures")

        # E2E test indicators
        e2e_indicators = 0
        if analyzer.has_entry_points:
            e2e_indicators += 3
            reasons.append("Tests application entry points")

        if analyzer.has_complete_workflows:
            e2e_indicators += 2
            reasons.append("Tests complete workflows")

        if analyzer.has_gui_interactions:
            e2e_indicators += 2
            reasons.append("Has GUI interactions")

        # Determine category based on strongest indicators
        if e2e_indicators >= 2:
            return "e2e", reasons
        elif integration_indicators >= 2:
            return "integration", reasons
        elif unit_indicators >= 2:
            return "unit", reasons
        else:
            return "unknown", reasons or ["Could not determine test type"]


class TestBodyAnalyzer(ast.NodeVisitor):
    """Analyzes the body of a test function to detect patterns."""

    def __init__(self):
        self.has_mocks = False
        self.has_file_io = False
        self.has_database_calls = False
        self.has_entry_points = False
        self.has_complete_workflows = False
        self.has_gui_interactions = False
        self.has_multiple_components = False
        self.is_simple_logic = True
        self.is_performance_test = False
        self.performance_indicators = []
        self.function_calls = []
        self.attributes_accessed = []

    def visit_Call(self, node: ast.Call) -> Any:
        """Analyze function calls for patterns."""
        # Get the function name
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            if isinstance(node.func.value, ast.Name):
                full_name = f"{node.func.value.id}.{func_name}"
                self.function_calls.append(full_name)

        self.function_calls.append(func_name)

        # Mock detection
        if any(mock_term in func_name.lower() for mock_term in ['mock', 'patch', 'magicmock']):
            self.has_mocks = True

        # File I/O detection - be more specific about actual file operations
        file_io_patterns = [
            'open(', 'read_text', 'write_text', 'read_bytes', 'write_bytes',
            'Path(', '.read()', '.write()', 'file.', 'save_to_file', 'load_from_file'
        ]
        if any(io_pattern in str(node) for io_pattern in file_io_patterns):
            if not any(mock_term in func_name.lower() for mock_term in ['mock', 'patch']):
                self.has_file_io = True

        # Database detection
        if any(db_term in func_name.lower() for db_term in ['database', 'sql', 'query', 'execute', 'fetch']):
            self.has_database_calls = True

        # GUI detection
        if any(gui_term in func_name.lower() for gui_term in ['show', 'click', 'press', 'dialog', 'widget']):
            self.has_gui_interactions = True

        # Entry point detection - be more specific to avoid false positives
        # Look for actual application entry points, not just any 'run' method
        entry_patterns = [
            'app.run', 'application.run', 'main(', '__main__',
            'scanner.process_crashlog', 'scanner.scan', 'app.start'
        ]
        if any(entry in str(node) for entry in entry_patterns):
            self.has_entry_points = True
        # Also check for specific entry point function names (but not run_async)
        elif func_name in ['main', 'start_application', 'run_app'] and 'run_async' not in func_name:
            self.has_entry_points = True

        # Performance test detection - be more specific to avoid false positives
        # Look for actual performance measurement patterns, not just any 'time' reference
        performance_patterns = [
            'perf_counter', 'benchmark', 'measure_time', 'measure_performance',
            'performance_test', 'baseline', 'memory_info', 'scalability_test',
            'throughput', 'latency', 'cpu_usage', 'memory_usage', 'profile', 'metric'
        ]

        # Check for specific performance measurement calls
        if any(perf in func_name.lower() for perf in performance_patterns):
            self.is_performance_test = True
            self.performance_indicators.append(f"Performance function: {func_name}")
        # Also check for time.perf_counter specifically (not just any time call)
        elif 'perf_counter' in func_name or 'process_time' in func_name:
            self.is_performance_test = True
            self.performance_indicators.append(f"Timing measurement: {func_name}")

        # Check for specific timing measurement calls (not just any time reference)
        timing_calls = ['time.perf_counter', 'time.process_time', 'time.monotonic', 'timeit.']
        if any(timing in str(node) for timing in timing_calls):
            self.is_performance_test = True
            self.performance_indicators.append(f"Timing measurement: {func_name}")

        # Check for memory monitoring
        memory_calls = ['memory_info', 'memory_usage', 'psutil', 'resource.getrusage']
        if any(mem in func_name for mem in memory_calls):
            self.is_performance_test = True
            self.performance_indicators.append(f"Memory monitoring: {func_name}")

        # Complexity indicators
        if len(self.function_calls) > 10:
            self.is_simple_logic = False
            self.has_multiple_components = True

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        """Track attribute access patterns."""
        if isinstance(node.value, ast.Name):
            self.attributes_accessed.append(f"{node.value.id}.{node.attr}")

        self.generic_visit(node)


def _detect_performance_file(file_path: Path, content: str) -> bool:
    """Detect if this is a performance test file based on file-level indicators."""
    # Check file path
    path_indicators = ['performance', 'benchmark', 'speed', 'timing', 'baseline']
    if any(indicator in str(file_path).lower() for indicator in path_indicators):
        return True

    # Check file content for performance patterns
    content_lower = content.lower()

    # Performance imports
    performance_imports = [
        'time.perf_counter', 'time.process_time', 'time.monotonic',
        'psutil', 'memory_profiler', 'cProfile', 'profile',
        'benchmark', 'timeit', 'performance'
    ]

    if any(imp in content_lower for imp in performance_imports):
        return True

    # Performance markers
    performance_markers = [
        '@pytest.mark.performance', '@pytest.mark.benchmark', '@pytest.mark.slow',
        'performance test', 'benchmark test', 'baseline test', 'speed test'
    ]

    if any(marker in content_lower for marker in performance_markers):
        return True

    # Performance-related docstrings/comments
    performance_docs = [
        'performance', 'benchmark', 'baseline', 'timing', 'speed',
        'memory usage', 'cpu usage', 'scalability', 'throughput'
    ]

    # Count performance-related terms
    performance_count = sum(content_lower.count(term) for term in performance_docs)
    if performance_count >= 5:  # Threshold for performance file
        return True

    return False


def analyze_file(file_path: Path) -> FileAnalysis:
    """Analyze a single test file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.splitlines()

        # Check for file-level performance indicators
        is_performance_file = _detect_performance_file(file_path, content)

        # Parse the AST
        tree = ast.parse(content, filename=str(file_path))

        # Analyze the file
        categorizer = TestCategorizer()
        categorizer.is_performance_file = is_performance_file
        categorizer.visit(tree)

        # Categorize tests
        unit_tests = [t for t in categorizer.tests if t.category == "unit"]
        integration_tests = [t for t in categorizer.tests if t.category == "integration"]
        e2e_tests = [t for t in categorizer.tests if t.category == "e2e"]
        performance_tests = [t for t in categorizer.tests if t.category == "performance"]
        unknown_tests = [t for t in categorizer.tests if t.category == "unknown"]

        # Check for violations
        violations = []
        if len(lines) > 300:
            violations.append(f"File exceeds 300 lines ({len(lines)} lines)")

        # Check if mixed types (performance tests are handled specially)
        if performance_tests:
            # Performance files can be split by functional scope if too large
            needs_split = len(lines) > 300
            if len(lines) > 300:
                violations.append("Performance file exceeds 300 lines (consider splitting by functional scope)")
        else:
            # Regular test type checking
            type_count = sum([
                1 if unit_tests else 0,
                1 if integration_tests else 0,
                1 if e2e_tests else 0
            ])

            needs_split = type_count > 1 or len(lines) > 300

            if type_count > 1:
                violations.append("Mixed test types in same file")

        return FileAnalysis(
            file_path=file_path,
            total_lines=len(lines),
            total_tests=len(categorizer.tests),
            unit_tests=unit_tests,
            integration_tests=integration_tests,
            e2e_tests=e2e_tests,
            performance_tests=performance_tests,
            unknown_tests=unknown_tests,
            imports=categorizer.imports,
            fixtures_used=categorizer.fixtures_used,
            needs_split=needs_split,
            violations=violations,
            is_performance_file=is_performance_file
        )

    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return FileAnalysis(
            file_path=file_path,
            total_lines=0,
            total_tests=0,
            unit_tests=[],
            integration_tests=[],
            e2e_tests=[],
            performance_tests=[],
            unknown_tests=[],
            imports=[],
            fixtures_used=set(),
            needs_split=False,
            violations=[f"Parse error: {e}"],
            is_performance_file=False
        )


def print_analysis(analysis: FileAnalysis) -> None:
    """Print a detailed analysis report."""
    print(f"\n{'='*60}")
    try:
        relative_path = analysis.file_path.relative_to(Path.cwd())
        print(f"File: {relative_path}")
    except ValueError:
        print(f"File: {analysis.file_path}")
    print(f"{'='*60}")
    print(f"Total lines: {analysis.total_lines}")
    print(f"Total tests: {analysis.total_tests}")

    if analysis.violations:
        print(f"\n⚠️  VIOLATIONS:")
        for violation in analysis.violations:
            print(f"   • {violation}")

    if analysis.unit_tests:
        print(f"\n✅ Unit tests ({len(analysis.unit_tests)}):")
        for test in analysis.unit_tests:
            print(f"   • {test.name} (line {test.line_number})")
            for reason in test.reasons:
                print(f"     - {reason}")

    if analysis.integration_tests:
        print(f"\n🔗 Integration tests ({len(analysis.integration_tests)}):")
        for test in analysis.integration_tests:
            print(f"   • {test.name} (line {test.line_number})")
            for reason in test.reasons:
                print(f"     - {reason}")

    if analysis.e2e_tests:
        print(f"\n🔄 E2E tests ({len(analysis.e2e_tests)}):")
        for test in analysis.e2e_tests:
            print(f"   • {test.name} (line {test.line_number})")
            for reason in test.reasons:
                print(f"     - {reason}")

    if analysis.performance_tests:
        print(f"\n⚡ Performance tests ({len(analysis.performance_tests)}):")
        for test in analysis.performance_tests:
            print(f"   • {test.name} (line {test.line_number})")
            for reason in test.reasons:
                print(f"     - {reason}")

    if analysis.unknown_tests:
        print(f"\n❓ Unknown tests ({len(analysis.unknown_tests)}):")
        for test in analysis.unknown_tests:
            print(f"   • {test.name} (line {test.line_number})")
            for reason in test.reasons:
                print(f"     - {reason}")

    if analysis.fixtures_used:
        print(f"\n📦 Fixtures used: {', '.join(sorted(analysis.fixtures_used))}")

    if analysis.is_performance_file:
        print(f"\n⚡ Performance file detected!")
        if analysis.needs_split:
            print(f"📊 Recommended action: SPLIT BY FUNCTIONAL SCOPE")
            print("   Performance files should be split by functional areas (comparisons, baselines, etc.)")
        else:
            print(f"📊 Recommended action: OK (Performance file under 300 lines)")
    else:
        print(f"\n📊 Recommended action: {'SPLIT' if analysis.needs_split else 'OK'}")
        if analysis.needs_split:
            print("   This file should be split to follow test organization rules.")


def main():
    """Main script entry point."""
    if len(sys.argv) != 2:
        print("Usage: python analyze_tests.py <test_file_or_directory>")
        sys.exit(1)

    path = Path(sys.argv[1])

    if not path.exists():
        print(f"Error: {path} does not exist")
        sys.exit(1)

    files_to_analyze = []

    if path.is_file():
        if path.name.startswith('test_') and path.suffix == '.py':
            files_to_analyze.append(path)
        else:
            print(f"Error: {path} is not a test file")
            sys.exit(1)
    else:
        # Find all test files in directory
        files_to_analyze = list(path.rglob('test_*.py'))
        if not files_to_analyze:
            print(f"No test files found in {path}")
            sys.exit(1)

    print(f"Analyzing {len(files_to_analyze)} test file(s)...")

    all_analyses = []
    for file_path in files_to_analyze:
        analysis = analyze_file(file_path)
        all_analyses.append(analysis)
        print_analysis(analysis)

    # Summary report
    if len(all_analyses) > 1:
        total_files = len(all_analyses)
        files_needing_split = sum(1 for a in all_analyses if a.needs_split)
        total_tests = sum(a.total_tests for a in all_analyses)
        total_lines = sum(a.total_lines for a in all_analyses)

        print(f"\n{'='*60}")
        print("SUMMARY REPORT")
        print(f"{'='*60}")
        print(f"Total files analyzed: {total_files}")
        print(f"Files needing split: {files_needing_split}")
        print(f"Total tests: {total_tests}")
        print(f"Total lines: {total_lines}")
        print(f"Compliance rate: {((total_files - files_needing_split) / total_files * 100):.1f}%")


if __name__ == "__main__":
    main()
