#!/usr/bin/env python
"""
Pre-commit hook to check for test isolation violations.

This script scans test files for patterns that indicate potential
production data access or modification.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple


class TestIsolationChecker:
    """Check test files for isolation violations."""
    
    # Patterns that indicate production data access
    VIOLATION_PATTERNS = [
        # Direct use of production YAML stores
        (r'YAML\.Settings(?!\s*==\s*YAML\.TEST)', 
         "Using YAML.Settings in tests - use YAML.TEST or mock instead"),
        (r'YAML\.Game_Local(?!\s*==\s*YAML\.TEST)', 
         "Using YAML.Game_Local in tests - use YAML.TEST or mock instead"),
        (r'YAML\.Main(?!\s*==\s*YAML\.TEST)', 
         "Using YAML.Main in tests - use YAML.TEST or mock instead"),
        
        # Creating production-like directories without proper isolation
        (r'Path\(["\']CLASSIC Data["\']\)(?!.*mock|.*patch|.*tmp_path)', 
         "Creating 'CLASSIC Data' directory - use tmp_path fixture"),
        (r'mkdir.*CLASSIC Data(?!.*tmp_path|.*test)', 
         "Creating production directory - use tmp_path"),
        
        # Direct file writes without tmp_path
        (r'\.write_text\(.*\)(?!.*tmp_path|.*test_|.*mock)', 
         "Writing files without tmp_path - ensure proper isolation"),
        
        # Modifying production settings
        (r'yaml_settings\(.*YAML\.Settings.*new_value', 
         "Modifying production settings - use YAML.TEST"),
        
        # Direct access to production paths
        (r'["\']Crash Logs["\'](?!.*test_|.*tmp_path|.*mock)', 
         "Accessing production 'Crash Logs' directory"),
        (r'["\']Documents["\'].*["\']My Games["\'](?!.*mock|.*patch)', 
         "Accessing user Documents folder - mock this path"),
        
        # Using os.chdir without proper isolation
        (r'os\.chdir\((?!.*tmp_path|.*monkeypatch)', 
         "Using os.chdir without tmp_path or monkeypatch"),
    ]
    
    # Patterns to whitelist (legitimate uses)
    WHITELIST_PATTERNS = [
        r'#.*YAML\.Settings',  # Comments
        r'["\'"].*YAML\.Settings.*["\'"]',  # String literals
        r'mock.*YAML\.Settings',  # Mocked usage
        r'patch.*YAML\.Settings',  # Patched usage
        r'assert.*not.*YAML\.Settings',  # Negative assertions
    ]
    
    def __init__(self, verbose: bool = False):
        """Initialize the checker."""
        self.verbose = verbose
        self.violations: List[Tuple[Path, int, str, str]] = []
    
    def check_file(self, filepath: Path) -> bool:
        """
        Check a single test file for isolation violations.
        
        Returns True if violations found, False otherwise.
        """
        if not filepath.name.startswith('test_'):
            return False
            
        try:
            content = filepath.read_text(encoding='utf-8')
            lines = content.splitlines()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return False
        
        file_has_violations = False
        
        for line_num, line in enumerate(lines, 1):
            # Skip empty lines and comments
            if not line.strip() or line.strip().startswith('#'):
                continue
                
            # Check against whitelist patterns
            if any(re.search(pattern, line) for pattern in self.WHITELIST_PATTERNS):
                continue
            
            # Check for violations
            for pattern, message in self.VIOLATION_PATTERNS:
                if re.search(pattern, line):
                    self.violations.append((filepath, line_num, line.strip(), message))
                    file_has_violations = True
                    
                    if self.verbose:
                        print(f"{filepath}:{line_num}: {message}")
                        print(f"  > {line.strip()}")
                    break
        
        return file_has_violations
    
    def check_directory(self, directory: Path) -> int:
        """
        Check all test files in a directory.
        
        Returns the number of files with violations.
        """
        test_files = list(directory.rglob('test_*.py'))
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
    parser = argparse.ArgumentParser(
        description="Check test files for isolation violations"
    )
    parser.add_argument(
        'files', 
        nargs='*', 
        help='Test files to check (if empty, checks all test files)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output'
    )
    parser.add_argument(
        '--directory', '-d',
        default='tests',
        help='Directory to scan for test files (default: tests)'
    )
    
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


if __name__ == '__main__':
    sys.exit(main())