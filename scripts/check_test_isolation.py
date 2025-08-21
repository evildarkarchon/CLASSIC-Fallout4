#!/usr/bin/env python
"""
Pre-commit hook to check for test isolation violations.

This script scans test files for patterns that indicate potential
production data access or modification. It uses context-aware checking
to avoid false positives for legitimate test patterns.
"""

import argparse
import re
import sys
from pathlib import Path


class TestIsolationChecker:
    """Check test files for isolation violations with context awareness."""

    def __init__(self, verbose: bool = False):
        """Initialize the checker."""
        self.verbose = verbose
        self.violations: list[tuple[Path, int, str, str]] = []

    def _is_safe_yaml_usage(self, line: str, prev_lines: list[str]) -> bool:
        """
        Check if YAML.Main/Settings/Game_Local usage is safe.

        Safe patterns include:
        - Mock assertions (assert_called_with, assert_called_once_with)
        - Inside patch/mock decorators or contexts
        - Comparisons with YAML.TEST
        - Assertions checking mock call arguments
        """
        # Check if it's in an assertion about mock calls
        if any(pattern in line for pattern in
               ["assert_called_once_with", "assert_called_with", "assert_any_call", "assert_has_calls"]):
            return True

        # Check if it's in an assertion or comparison (likely checking mock args)
        if line.strip().startswith("assert "):
            return True
        if any(op in line for op in [" == ", " != ", " is ", " is not "]):
            # Likely a comparison, not actual usage
            return True

        # Check if it's a comparison with YAML.TEST
        if "YAML.TEST" in line:
            return True

        # Check if it's in a string literal or comment
        if re.search(r'["\'].*YAML\.(Main|Settings|Game_Local).*["\']', line):
            return True
        if line.strip().startswith("#"):
            return True

        # Check previous lines for mock/patch context
        for prev_line in prev_lines[-3:]:  # Check last 3 lines
            if any(pattern in prev_line for pattern in ["@patch", "with patch", "@mock", "with mock"]):
                return True

        return False

    def _is_safe_path_usage(self, line: str, prev_lines: list[str]) -> bool:
        """
        Check if "CLASSIC Data" or "Crash Logs" usage is safe.

        Safe patterns include:
        - Subdirectories of tmp_path
        - Inside mock/patch contexts
        - String literals for comparison
        """
        # Check if it's a subdirectory of tmp_path
        if "tmp_path" in line:
            return True

        # Check if self.tmp_path is on the same line or recent lines
        if "self.tmp_path" in line:
            return True
        for prev_line in prev_lines[-2:]:
            if "self.tmp_path" in prev_line:
                return True

        # Check if it's in a string comparison or assertion
        if any(pattern in line for pattern in ["assert", "==", "!=", "in", "not in"]):
            # Might be comparing paths, which is OK
            return True

        # Check if it's inside a mock/patch
        for prev_line in prev_lines[-3:]:
            if any(pattern in prev_line for pattern in ["@patch", "with patch", "mock_path"]):
                return True

        return False

    def _is_safe_write_operation(self, line: str, file_lines: list[str], line_num: int) -> bool:
        """
        Check if a write_text/write_bytes operation is safe.

        Safe patterns include:
        - Writing to files created from tmp_path
        - Writing to files in fixtures with tmp_path parameter
        """
        # Extract the variable being written to
        match = re.search(r"(\w+)\.write_(text|bytes)\(", line)
        if not match:
            return False

        var_name = match.group(1)

        # Track variable origins - build a chain of assignments
        derived_from = {var_name}

        # Look backwards for where this variable was defined and track derivations
        for i in range(max(0, line_num - 30), line_num):
            if i >= len(file_lines):
                continue
            check_line = file_lines[i]

            # Check if any tracked variable is assigned from another variable
            for tracked_var in list(derived_from):
                # Pattern: tracked_var = something / "path"
                if re.search(rf"{tracked_var}\s*=\s*(\w+)\s*/", check_line):
                    match = re.search(rf"{tracked_var}\s*=\s*(\w+)\s*/", check_line)
                    if match:
                        derived_from.add(match.group(1))

                # Pattern: tracked_var = Path(...)
                if re.search(rf"{tracked_var}\s*=\s*Path\(", check_line):
                    # Check if it's Path("CLASSIC Ignore.yaml") - special case
                    if 'Path("CLASSIC Ignore.yaml")' in check_line:
                        return True

            # Check if any tracked variable comes from tmp_path
            for tracked_var in derived_from:
                if tracked_var in check_line and any(
                        pattern in check_line for pattern in ["tmp_path /", "tmp_path/", "self.tmp_path", "tmp_path\\"]
                ):
                    return True

        # Check if we're in a test function with tmp_path fixture
        if self._has_tmp_path_fixture(file_lines, line_num):
            # If the test has tmp_path fixture and uses self.tmp_path, it's safe
            for i in range(max(0, line_num - 30), line_num):
                if i >= len(file_lines):
                    continue
                if "self.tmp_path" in file_lines[i]:
                    return True

        return False

    def _has_tmp_path_fixture(self, lines: list[str], line_num: int) -> bool:
        """Check if the current function has tmp_path fixture."""
        # Look backwards for any function definition (test function or fixture)
        for i in range(line_num - 1, max(0, line_num - 100), -1):
            line = lines[i].strip()
            # Check for test functions or any function that might be a fixture
            if line.startswith("def "):
                # Check if it's a fixture by looking for @pytest.fixture decorator
                is_fixture = False
                for j in range(max(0, i - 5), i):
                    if "@pytest.fixture" in lines[j]:
                        is_fixture = True
                        break

                # If it's a test function or a fixture, check for tmp_path
                if line.startswith("def test_") or is_fixture:
                    # Check this line and potentially the next few for parameters
                    full_def = line
                    # Handle multi-line function definitions
                    j = i
                    while j < len(lines) - 1 and not full_def.rstrip().endswith(":"):
                        j += 1
                        full_def += " " + lines[j].strip()
                    if "tmp_path" in full_def or "temp_path" in full_def:
                        return True

            if line.startswith("class ") and "Test" in line:
                # Check if class has setup method with tmp_path
                for j in range(i, min(i + 20, len(lines))):
                    if "def setup" in lines[j] and "tmp_path" in lines[j]:
                        return True
                break
        return False

    def check_file(self, filepath: Path) -> bool:
        """
        Check a single test file for isolation violations.

        Returns True if violations found, False otherwise.
        """
        if not filepath.name.startswith("test_"):
            return False

        try:
            content = filepath.read_text(encoding="utf-8")
            lines = content.splitlines()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return False

        file_has_violations = False

        for line_num, line in enumerate(lines, 1):
            # Skip empty lines and comments
            if not line.strip() or line.strip().startswith("#"):
                continue

            # Get previous lines for context
            prev_lines = lines[max(0, line_num - 4): line_num - 1]

            # Check for YAML.Main/Settings/Game_Local usage
            if re.search(r"YAML\.(Main|Settings|Game_Local)", line):
                if not self._is_safe_yaml_usage(line, prev_lines):
                    self.violations.append(
                        (filepath, line_num, line.strip(), "Using production YAML store - use YAML.TEST or mock"))
                    file_has_violations = True
                    if self.verbose:
                        print(f"{filepath}:{line_num}: Production YAML usage")
                        print(f"  > {line.strip()}")

            # Check for "CLASSIC Data" or "Crash Logs" paths
            if re.search(r'["\'](CLASSIC Data|Crash Logs)["\']', line):
                if not self._is_safe_path_usage(line, prev_lines):
                    self.violations.append(
                        (filepath, line_num, line.strip(), "Using production path - ensure it's under tmp_path"))
                    file_has_violations = True
                    if self.verbose:
                        print(f"{filepath}:{line_num}: Production path usage")
                        print(f"  > {line.strip()}")

            # Check for write operations
            if ".write_text(" in line or ".write_bytes(" in line:
                # Only check if NOT in a test with tmp_path fixture
                if not self._has_tmp_path_fixture(lines, line_num):
                    if not self._is_safe_write_operation(line, lines, line_num):
                        self.violations.append(
                            (filepath, line_num, line.strip(), "Writing files without tmp_path fixture"))
                        file_has_violations = True
                        if self.verbose:
                            print(f"{filepath}:{line_num}: File write without tmp_path")
                            print(f"  > {line.strip()}")

            # Check for os.chdir without monkeypatch
            if "os.chdir(" in line:
                if not any(pattern in line for pattern in ["monkeypatch", "tmp_path"]):
                    # Check previous lines for monkeypatch context
                    has_monkeypatch = any("monkeypatch" in prev for prev in prev_lines[-3:])
                    if not has_monkeypatch:
                        self.violations.append(
                            (filepath, line_num, line.strip(), "Using os.chdir without monkeypatch.chdir"))
                        file_has_violations = True

        return file_has_violations

    def check_directory(self, directory: Path) -> int:
        """
        Check all test files in a directory.

        Returns the number of files with violations.
        """
        test_files = list(directory.rglob("test_*.py"))
        files_with_violations = 0

        for test_file in test_files:
            if self.check_file(test_file):
                files_with_violations += 1

        return files_with_violations

    def print_summary(self):
        """Print a summary of all violations found."""
        if not self.violations:
            print("✅ No test isolation violations found!")
            return

        print(f"\n❌ Found {len(self.violations)} test isolation violations:\n")

        # Group by file
        by_file = {}
        for filepath, line_num, line, message in self.violations:
            if filepath not in by_file:
                by_file[filepath] = []
            by_file[filepath].append((line_num, line, message))

        for filepath, file_violations in by_file.items():
            print(f"\n{filepath}:")
            for line_num, line, message in file_violations:
                print(f"  Line {line_num}: {message}")
                print(f"    {line[:80]}...")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Check test files for isolation violations")
    parser.add_argument("files", nargs="*", help="Test files to check (if empty, checks all test files)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--directory", "-d", default="tests", help="Directory to scan for test files (default: tests)")

    args = parser.parse_args()

    checker = TestIsolationChecker(verbose=args.verbose)

    if args.files:
        # Check specific files
        violations_found = False
        for filepath in args.files:
            path = Path(filepath)
            if path.exists() and checker.check_file(path):
                violations_found = True
    else:
        # Check all test files in directory
        test_dir = Path(args.directory)
        if not test_dir.exists():
            print(f"Test directory '{test_dir}' not found")
            return 1

        files_with_violations = checker.check_directory(test_dir)
        violations_found = files_with_violations > 0

    checker.print_summary()

    # Exit with error code if violations found
    return 1 if violations_found else 0


if __name__ == "__main__":
    sys.exit(main())
