#!/usr/bin/env python
"""
Test Structure Validator for CLASSIC-Fallout4

Validates that all test files comply with the test organization rules:
- Maximum 300 lines per file
- Proper naming conventions (test_<component>_<type>.py)
- No mixed test types in same file
- Tests are in appropriate subdirectories

Usage:
    python tests/tools/validate_structure.py [--fix] [--verbose]
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from analyze_tests import analyze_file


@dataclass
class ValidationResult:
    """Results of validating the test suite structure."""

    total_files: int
    compliant_files: int
    oversized_files: list[tuple[Path, int]]
    mixed_type_files: list[tuple[Path, list[str]]]
    badly_named_files: list[tuple[Path, str]]
    misplaced_files: list[tuple[Path, str]]
    violations: list[str]
    compliance_percentage: float


def check_file_size(file_path: Path, max_lines: int = 300) -> tuple[bool, int]:
    """Check if file exceeds the line limit."""
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
        line_count = len(lines)
        return line_count <= max_lines, line_count
    except Exception:
        return True, 0


def check_naming_convention(file_path: Path) -> tuple[bool, str]:
    """Check if file follows proper naming convention."""
    filename = file_path.name

    # Skip special files
    if filename in ["conftest.py", "__init__.py"]:
        return True, "Special file"

    # Must start with test_
    if not filename.startswith("test_"):
        return False, "Must start with 'test_'"

    # Must end with .py
    if not filename.endswith(".py"):
        return False, "Must be a Python file"

    # Extract component and type
    name_without_ext = filename[:-3]  # Remove .py
    name_without_test = name_without_ext[5:]  # Remove test_

    # Check for type suffix
    valid_types = ["_unit", "_integration", "_e2e"]
    has_type_suffix = any(name_without_test.endswith(suffix) for suffix in valid_types)

    if not has_type_suffix:
        # This is acceptable for files that only contain one type
        return True, "No type suffix (acceptable if single type)"

    return True, "Properly named"


def check_directory_placement(file_path: Path, test_root: Path) -> tuple[bool, str]:
    """Check if file is in appropriate directory."""
    relative_path = file_path.relative_to(test_root)

    # Get the absolute path and check if we're in a subdirectory of tests
    test_root_abs = test_root.resolve()

    # Check if the test_root itself is a subdirectory within tests/
    # This handles cases like --test-dir ../performance or tests/performance
    if "tests" in test_root_abs.parts:
        tests_index = test_root_abs.parts.index("tests")
        # If there are parts after "tests", we're in a subdirectory
        if tests_index < len(test_root_abs.parts) - 1:
            # We're in a subdirectory like tests/performance
            return True, "Properly placed"

    # Files should not be in root tests/ directory
    if len(relative_path.parts) == 1:
        if relative_path.name not in ["conftest.py", "__init__.py"]:
            return False, "Test files should be in subdirectories"

    return True, "Properly placed"


def get_test_types_in_file(file_path: Path) -> list[str]:
    """Get the types of tests in a file."""
    analysis = analyze_file(file_path)

    types = []
    if analysis.performance_tests:
        types.append("performance")
    elif analysis.unit_tests:
        types.append("unit")
    if analysis.integration_tests:
        types.append("integration")
    if analysis.e2e_tests:
        types.append("e2e")

    return types


def validate_test_suite(test_dir: Path, verbose: bool = False) -> ValidationResult:
    """Validate the entire test suite structure."""
    if verbose:
        print(f"🔍 Scanning test files in {test_dir}")

    # Find all test files
    test_files = list(test_dir.rglob("test_*.py"))

    if verbose:
        print(f"Found {len(test_files)} test files")

    total_files = len(test_files)
    compliant_files = 0
    oversized_files = []
    mixed_type_files = []
    badly_named_files = []
    misplaced_files = []
    violations = []

    for file_path in test_files:
        if verbose:
            print(f"  Checking {file_path.relative_to(test_dir)}")

        file_compliant = True

        # Check file size
        size_ok, line_count = check_file_size(file_path)
        if not size_ok:
            oversized_files.append((file_path, line_count))
            violations.append(f"{file_path.relative_to(test_dir)}: Exceeds 300 lines ({line_count} lines)")
            file_compliant = False

        # Check naming convention
        naming_ok, naming_reason = check_naming_convention(file_path)
        if not naming_ok:
            badly_named_files.append((file_path, naming_reason))
            violations.append(f"{file_path.relative_to(test_dir)}: {naming_reason}")
            file_compliant = False

        # Check directory placement
        placement_ok, placement_reason = check_directory_placement(file_path, test_dir)
        if not placement_ok:
            misplaced_files.append((file_path, placement_reason))
            violations.append(f"{file_path.relative_to(test_dir)}: {placement_reason}")
            file_compliant = False

        # Check for mixed test types (skip for performance files)
        test_types = get_test_types_in_file(file_path)

        # Performance files are allowed to contain only performance tests
        if "performance" in test_types:
            # Performance files should only contain performance tests
            non_performance_types = [t for t in test_types if t != "performance"]
            if non_performance_types:
                mixed_type_files.append((file_path, test_types))
                violations.append(f"{file_path.relative_to(test_dir)}: Performance file mixed with: {', '.join(non_performance_types)}")
                file_compliant = False
        elif len(test_types) > 1:
            mixed_type_files.append((file_path, test_types))
            violations.append(f"{file_path.relative_to(test_dir)}: Mixed test types: {', '.join(test_types)}")
            file_compliant = False

        if file_compliant:
            compliant_files += 1

    compliance_percentage = (compliant_files / total_files * 100) if total_files > 0 else 100

    return ValidationResult(
        total_files=total_files,
        compliant_files=compliant_files,
        oversized_files=oversized_files,
        mixed_type_files=mixed_type_files,
        badly_named_files=badly_named_files,
        misplaced_files=misplaced_files,
        violations=violations,
        compliance_percentage=compliance_percentage,
    )


def _print_header() -> None:
    """Print report header."""
    print(f"\n{'=' * 60}")
    print("TEST SUITE STRUCTURE VALIDATION REPORT")
    print(f"{'=' * 60}")


def _print_overview(result: ValidationResult) -> None:
    """Print overview section."""
    print("📊 Overview:")
    print(f"   Total test files: {result.total_files}")
    print(f"   Compliant files: {result.compliant_files}")
    print(f"   Non-compliant files: {result.total_files - result.compliant_files}")
    print(f"   Compliance rate: {result.compliance_percentage:.1f}%")


def _print_violation_section(items: list, title: str, icon: str, test_dir: Path, format_func=None) -> None:
    """Print a violation section."""
    if items:
        print(f"\n{icon} {title} ({len(items)}):")
        for item in items:
            if format_func:
                format_func(item, test_dir)
            else:
                file_path, detail = item
                rel_path = file_path.relative_to(test_dir)
                if isinstance(detail, list):
                    print(f"   • {rel_path} (contains: {', '.join(detail)})")
                elif isinstance(detail, int):
                    print(f"   • {rel_path} ({detail} lines)")
                else:
                    print(f"   • {rel_path} - {detail}")


def _print_priority_actions(result: ValidationResult, test_dir: Path) -> None:
    """Print priority actions section."""
    print("\n🎯 Priority Actions:")

    if result.oversized_files:
        largest_files = sorted(result.oversized_files, key=lambda x: x[1], reverse=True)[:3]
        print("   1. Split largest files first:")
        for file_path, line_count in largest_files:
            rel_path = file_path.relative_to(test_dir)
            print(f"      • {rel_path} ({line_count} lines)")

    if result.mixed_type_files:
        print("   2. Separate mixed test types:")
        for file_path, _test_types in result.mixed_type_files[:3]:
            rel_path = file_path.relative_to(test_dir)
            print(f"      • {rel_path}")


def _print_success_message(compliance_percentage: float) -> None:
    """Print success/progress message."""
    if compliance_percentage == 100:
        print("\n🎉 Congratulations! All test files are compliant with the organization rules.")
    elif compliance_percentage >= 80:
        print(f"\n✨ Good progress! You're {compliance_percentage:.1f}% compliant.")
    else:
        print(f"\n🚧 Keep going! {compliance_percentage:.1f}% compliance - focus on the priority actions above.")


def print_validation_report(result: ValidationResult, test_dir: Path) -> None:
    """Print a detailed validation report."""
    _print_header()
    _print_overview(result)

    # Print violation sections
    violations = [
        (result.oversized_files, "Files exceeding 300 lines", "❌"),
        (result.mixed_type_files, "Files with mixed test types", "🔀"),
        (result.badly_named_files, "Files with naming violations", "📛"),
        (result.misplaced_files, "Misplaced files", "📂"),
    ]

    for items, title, icon in violations:
        _print_violation_section(items, title, icon, test_dir)

    _print_priority_actions(result, test_dir)
    _print_success_message(result.compliance_percentage)


def suggest_fixes(result: ValidationResult, test_dir: Path) -> None:
    """Suggest specific commands to fix violations."""
    if not result.violations:
        return

    print("\n🔧 Suggested fixes:")

    for file_path, _line_count in result.oversized_files[:3]:
        rel_path = file_path.relative_to(test_dir)
        print("   Split oversized file:")
        print(f"   python tests/tools/migrate_tests.py {rel_path}")

    for file_path, _test_types in result.mixed_type_files[:3]:
        rel_path = file_path.relative_to(test_dir)
        print("   Split mixed types:")
        print(f"   python tests/tools/migrate_tests.py {rel_path}")


def main():
    """Main script entry point."""
    parser = argparse.ArgumentParser(description="Validate test suite structure compliance")
    parser.add_argument("--test-dir", default="tests", help="Test directory to validate (default: tests)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--suggest-fixes", action="store_true", help="Suggest specific commands to fix violations")

    args = parser.parse_args()

    test_dir = Path(args.test_dir)

    if not test_dir.exists():
        print(f"Error: Test directory {test_dir} does not exist")
        sys.exit(1)

    if not test_dir.is_dir():
        print(f"Error: {test_dir} is not a directory")
        sys.exit(1)

    # Run validation
    result = validate_test_suite(test_dir, verbose=args.verbose)

    # Print report
    print_validation_report(result, test_dir)

    # Suggest fixes if requested
    if args.suggest_fixes:
        suggest_fixes(result, test_dir)

    # Exit with appropriate code
    if result.compliance_percentage < 100:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
