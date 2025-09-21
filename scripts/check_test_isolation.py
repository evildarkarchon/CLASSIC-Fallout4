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

    # Pattern constants optimized with sets for O(1) lookup performance
    COMPARISON_OPERATORS: set[str] = {" == ", " != ", " is ", " is not "}
    MOCK_PATTERNS: set[str] = {"@patch", "with patch", "@mock", "with mock"}
    ASSERTION_PATTERNS: set[str] = {"assert", "==", "!=", "in", "not in"}
    MOCK_PATH_PATTERNS: set[str] = {"@patch", "with patch", "mock_path"}
    SAFE_TEST_PATTERNS: set[str] = {"monkeypatch", "tmp_path"}

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
        # Check various safe patterns
        if self._is_mock_assertion(line):
            return True

        if self._is_assertion_or_comparison(line):
            return True

        if self._is_test_yaml_comparison(line):
            return True

        if self._is_string_literal_or_comment(line):
            return True

        if self._has_mock_context(prev_lines):
            return True

        if self._is_yaml_infrastructure_test(line, prev_lines):
            return True

        return False

    def _is_mock_assertion(self, line: str) -> bool:
        """Check if line contains mock assertion patterns."""
        mock_assertions = [
            "assert_called_once_with", "assert_called_with",
            "assert_any_call", "assert_has_calls"
        ]
        return any(pattern in line for pattern in mock_assertions)

    def _is_assertion_or_comparison(self, line: str) -> bool:
        """Check if line is an assertion or comparison."""
        if line.strip().startswith("assert "):
            return True
        return any(op in line for op in self.COMPARISON_OPERATORS)

    def _is_test_yaml_comparison(self, line: str) -> bool:
        """Check if line contains YAML.TEST comparison."""
        return "YAML.TEST" in line

    def _is_string_literal_or_comment(self, line: str) -> bool:
        """Check if YAML reference is in string literal or comment."""
        if line.strip().startswith("#"):
            return True
        return bool(re.search(r'["\'].*YAML\.(Main|Settings|Game_Local).*["\']', line))

    def _has_mock_context(self, prev_lines: list[str]) -> bool:
        """Check if previous lines contain mock/patch context."""
        for prev_line in prev_lines[-3:]:  # Check last 3 lines
            if any(pattern in prev_line for pattern in self.MOCK_PATTERNS):
                return True
        return False

    def _is_yaml_infrastructure_test(self, line: str, prev_lines: list[str]) -> bool:
        """Check if testing YAML infrastructure itself (needs real enum values)."""
        if "test_yaml" not in line and "YamlSettingsCache" not in line:
            return False

        # If it's in a with patch context, it's mocked
        for prev_line in prev_lines[-10:]:
            if "with patch" in prev_line:
                return True
        return False

    def _is_safe_path_usage(self, line: str, prev_lines: list[str]) -> bool:
        """
        Check if "CLASSIC Data" or "Crash Logs" usage is safe.

        Safe patterns include:
        - Subdirectories of tmp_path
        - Inside mock/patch contexts
        - String literals for comparison
        - Path construction relative to __file__ (test fixtures)
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

        # Check if it's using Path(__file__).parent to reference test fixtures
        if "__file__" in line and "Path" in line:
            # This is likely referencing test fixtures relative to the test file
            return True

        # Check if it's in a string comparison or assertion
        if any(pattern in line for pattern in self.ASSERTION_PATTERNS):
            # Might be comparing paths, which is OK
            return True

        # Check if it's inside a mock/patch
        for prev_line in prev_lines[-3:]:
            if any(pattern in prev_line for pattern in self.MOCK_PATH_PATTERNS):
                return True

        return False

    def _is_safe_write_operation(self, line: str, file_lines: list[str], line_num: int) -> bool:
        """
        Check if a write_text/write_bytes operation is safe.

        Safe patterns include:
        - Writing to files created from tmp_path
        - Writing to files in fixtures with tmp_path parameter
        - Writing to files within tempfile.TemporaryDirectory() context
        """
        # Extract the variable being written to
        var_name = self._extract_write_variable(line)
        if not var_name:
            return False

        # Track variable origins and check if derived from tmp_path
        if self._is_variable_from_tmp_path(var_name, file_lines, line_num):
            return True

        # Check if we're within a tempfile.TemporaryDirectory() context
        if self._is_in_tempfile_context(file_lines, line_num):
            return True

        # Check if we're in a test function with tmp_path fixture and using self.tmp_path
        if self._is_using_fixture_tmp_path(file_lines, line_num):
            return True

        return False

    def _extract_write_variable(self, line: str) -> str | None:
        """Extract the variable name from a write operation."""
        match = re.search(r"(\w+)\.write_(text|bytes)\(", line)
        return match.group(1) if match else None

    def _is_variable_from_tmp_path(self, var_name: str, file_lines: list[str], line_num: int) -> bool:
        """
        Check if a variable is derived from tmp_path by tracking assignments.

        This method traces variable assignments backwards to determine if the variable
        originates from tmp_path or a related safe source.
        """
        # Track variable origins - build a chain of assignments
        derived_from = {var_name}

        # Look backwards for where this variable was defined and track derivations
        for i in range(max(0, line_num - 50), line_num):
            if i >= len(file_lines):
                continue
            check_line = file_lines[i]

            # Expand tracked variables with new derivations
            new_derivations = self._find_variable_derivations(derived_from, check_line)
            derived_from.update(new_derivations)

            # Check for special cases
            if self._has_special_path_case(derived_from, check_line):
                return True

            # Check if any tracked variable comes from tmp_path
            if self._has_tmp_path_origin(derived_from, check_line):
                return True

        return False

    def _find_variable_derivations(self, tracked_vars: set[str], line: str) -> set[str]:
        """Find new variable derivations from a line of code."""
        new_vars = set()
        for tracked_var in tracked_vars:
            # Pattern: tracked_var = something / "path"
            match = re.search(rf"{tracked_var}\s*=\s*(\w+)\s*/", line)
            if match:
                new_vars.add(match.group(1))
        return new_vars

    def _has_special_path_case(self, tracked_vars: set[str], line: str) -> bool:
        """Check for special path cases like Path("CLASSIC Ignore.yaml")."""
        for tracked_var in tracked_vars:
            if re.search(rf"{tracked_var}\s*=\s*Path\(", line):
                # Check if it's Path("CLASSIC Ignore.yaml") - special case
                if 'Path("CLASSIC Ignore.yaml")' in line:
                    return True
        return False

    def _has_tmp_path_origin(self, tracked_vars: set[str], line: str) -> bool:
        """Check if any tracked variable comes from tmp_path."""
        tmp_path_patterns = ["tmp_path /", "tmp_path/", "self.tmp_path", "tmp_path\\"]
        for tracked_var in tracked_vars:
            if tracked_var in line and any(pattern in line for pattern in tmp_path_patterns):
                return True
        return False

    def _is_using_fixture_tmp_path(self, file_lines: list[str], line_num: int) -> bool:
        """Check if the test has tmp_path fixture and uses self.tmp_path."""
        if not self._has_tmp_path_fixture(file_lines, line_num):
            return False

        # If the test has tmp_path fixture, check if self.tmp_path is used
        for i in range(max(0, line_num - 30), line_num):
            if i < len(file_lines) and "self.tmp_path" in file_lines[i]:
                return True
        return False

    def _is_in_tempfile_context(self, lines: list[str], line_num: int) -> bool:
        """
        Check if the current line is within a tempfile.TemporaryDirectory() context.

        Safe patterns include:
        - with tempfile.TemporaryDirectory() as temp_dir:
        - with TemporaryDirectory() as temp_dir:
        """
        # Track indentation level
        current_line = lines[line_num - 1] if line_num <= len(lines) else ""
        current_indent = len(current_line) - len(current_line.lstrip())

        # Look backwards for tempfile context
        for i in range(line_num - 2, max(0, line_num - 50), -1):
            line = lines[i]

            # Skip empty lines
            if not line.strip():
                continue

            # Get indentation of this line
            line_indent = len(line) - len(line.lstrip())

            # If we've gone to a lower indentation level, we're outside any context
            if line_indent < current_indent - 4:  # Allow for some flexibility
                break

            # Check for tempfile.TemporaryDirectory() context
            if "TemporaryDirectory()" in line and "with" in line:
                # Verify it's at the right indentation level (parent context)
                if line_indent <= current_indent:
                    return True

            # Also check for the import pattern
            if "tempfile.TemporaryDirectory()" in line and "with" in line:
                if line_indent <= current_indent:
                    return True

        return False

    def _has_tmp_path_fixture(self, lines: list[str], line_num: int) -> bool:
        """Check if the current function has tmp_path fixture."""
        # Look backwards for any function definition (test function or fixture)
        for i in range(line_num - 1, max(0, line_num - 100), -1):
            line = lines[i].strip()

            # Check for function definitions
            if line.startswith("def "):
                if self._function_has_tmp_path(lines, i):
                    return True

            # Check for test class definitions
            if line.startswith("class ") and "Test" in line:
                if self._class_has_tmp_path_setup(lines, i):
                    return True
                break

        return False

    def _function_has_tmp_path(self, lines: list[str], func_line_idx: int) -> bool:
        """Check if a function definition includes tmp_path fixture."""
        line = lines[func_line_idx].strip()

        # Check if it's a fixture or test function
        is_fixture = self._is_pytest_fixture(lines, func_line_idx)
        is_test_or_method = (
            line.startswith("def test_") or
            is_fixture or
            line.startswith("def ")
        )

        if not is_test_or_method:
            return False

        # Get complete function definition (handle multi-line)
        full_def = self._get_full_function_def(lines, func_line_idx)
        return "tmp_path" in full_def or "temp_path" in full_def

    def _is_pytest_fixture(self, lines: list[str], func_line_idx: int) -> bool:
        """Check if function has @pytest.fixture decorator."""
        for j in range(max(0, func_line_idx - 5), func_line_idx):
            if "@pytest.fixture" in lines[j]:
                return True
        return False

    def _get_full_function_def(self, lines: list[str], start_idx: int) -> str:
        """Get complete function definition, handling multi-line definitions."""
        full_def = lines[start_idx].strip()
        j = start_idx

        while j < len(lines) - 1 and not full_def.rstrip().endswith(":"):
            j += 1
            full_def += " " + lines[j].strip()

        return full_def

    def _class_has_tmp_path_setup(self, lines: list[str], class_line_idx: int) -> bool:
        """Check if test class has setup method with tmp_path."""
        for j in range(class_line_idx, min(class_line_idx + 20, len(lines))):
            if "def setup" in lines[j] and "tmp_path" in lines[j]:
                return True
        return False

    def check_file(self, filepath: Path) -> bool:
        """
        Check a single test file for isolation violations.

        Returns True if violations found, False otherwise.
        """
        if not filepath.name.startswith("test_"):
            return False

        lines = self._read_file_lines(filepath)
        if lines is None:
            return False

        file_has_violations = False

        for line_num, line in enumerate(lines, 1):
            # Skip empty lines and comments
            if not line.strip() or line.strip().startswith("#"):
                continue

            # Get previous lines for context
            prev_lines = lines[max(0, line_num - 4) : line_num - 1]

            # Check each violation type
            if self._check_yaml_violation(filepath, line_num, line, prev_lines):
                file_has_violations = True

            if self._check_path_violation(filepath, line_num, line, prev_lines):
                file_has_violations = True

            if self._check_write_violation(filepath, line_num, line, lines):
                file_has_violations = True

            if self._check_chdir_violation(filepath, line_num, line, prev_lines):
                file_has_violations = True

        return file_has_violations

    def _read_file_lines(self, filepath: Path) -> list[str] | None:
        """Read and return file lines, or None on error."""
        try:
            content = filepath.read_text(encoding="utf-8")
            return content.splitlines()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return None

    def _check_yaml_violation(self, filepath: Path, line_num: int, line: str, prev_lines: list[str]) -> bool:
        """Check for YAML.Main/Settings/Game_Local usage violations."""
        if not re.search(r"YAML\.(Main|Settings|Game_Local)", line):
            return False

        if self._is_safe_yaml_usage(line, prev_lines):
            return False

        self._add_violation(
            filepath, line_num, line,
            "Using production YAML store - use YAML.TEST or mock",
            "Production YAML usage"
        )
        return True

    def _check_path_violation(self, filepath: Path, line_num: int, line: str, prev_lines: list[str]) -> bool:
        """Check for "CLASSIC Data" or "Crash Logs" path violations."""
        if not re.search(r'["\'](CLASSIC Data|Crash Logs)["\']', line):
            return False

        if self._is_safe_path_usage(line, prev_lines):
            return False

        self._add_violation(
            filepath, line_num, line,
            "Using production path - ensure it's under tmp_path",
            "Production path usage"
        )
        return True

    def _check_write_violation(self, filepath: Path, line_num: int, line: str, lines: list[str]) -> bool:
        """Check for file write operation violations."""
        if ".write_text(" not in line and ".write_bytes(" not in line:
            return False

        # Only check if NOT in a test with tmp_path fixture
        if self._has_tmp_path_fixture(lines, line_num):
            return False

        if self._is_safe_write_operation(line, lines, line_num):
            return False

        self._add_violation(
            filepath, line_num, line,
            "Writing files without tmp_path fixture",
            "File write without tmp_path"
        )
        return True

    def _check_chdir_violation(self, filepath: Path, line_num: int, line: str, prev_lines: list[str]) -> bool:
        """Check for os.chdir usage without monkeypatch."""
        if "os.chdir(" not in line:
            return False

        # Check if it's safe (has monkeypatch)
        if any(pattern in line for pattern in self.SAFE_TEST_PATTERNS):
            return False

        # Check previous lines for monkeypatch context
        has_monkeypatch = any("monkeypatch" in prev for prev in prev_lines[-3:])
        if has_monkeypatch:
            return False

        self._add_violation(
            filepath, line_num, line,
            "Using os.chdir without monkeypatch.chdir",
            "os.chdir without monkeypatch"
        )
        return True

    def _add_violation(self, filepath: Path, line_num: int, line: str,
                       violation_msg: str, verbose_type: str) -> None:
        """Add a violation to the list and optionally print verbose output."""
        self.violations.append((filepath, line_num, line.strip(), violation_msg))
        if self.verbose:
            print(f"{filepath}:{line_num}: {verbose_type}")
            print(f"  > {line.strip()}")

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
