#!/usr/bin/env python3
"""
Migration script to update test files to use standardized fixture system.

This script automates the migration from redundant custom fixtures to the
new standardized fixture system for MessageHandler, GlobalRegistry, and AsyncBridge.

Usage:
    python scripts/migrate_test_fixtures.py [--dry-run] [--verbose]
"""

import argparse
import re
from pathlib import Path


def find_test_files(base_dir: Path) -> list[Path]:
    """Find all Python test files in the tests directory."""
    tests_dir = base_dir / "tests"
    return list(tests_dir.rglob("test_*.py")) + list(tests_dir.rglob("conftest.py"))


class TestFileMigrator:
    """Handles migration of a single test file to standardized fixtures."""

    def __init__(self, file_path: Path, dry_run: bool = False, verbose: bool = False):
        self.file_path = file_path
        self.dry_run = dry_run
        self.verbose = verbose
        self.changes_made = []
        self.content = file_path.read_text(encoding="utf-8")
        self.original_content = self.content

    def migrate(self) -> bool:
        """Perform all migrations on the file."""
        # Skip our standardized fixture files
        if "fixtures/registry_fixtures.py" in str(self.file_path):
            return False
        if "fixtures/qt_fixtures.py" in str(self.file_path):
            # This file needs special handling for gui_message_handler
            return False

        self.remove_redundant_message_handler_fixtures()
        self.remove_direct_singleton_cleanup()
        self.update_fixture_usage_in_tests()
        self.remove_redundant_imports()
        self.add_fixture_imports_if_needed()

        if self.content != self.original_content:
            if not self.dry_run:
                self.file_path.write_text(self.content, encoding="utf-8")
            return True
        return False

    def remove_redundant_message_handler_fixtures(self):
        """Remove redundant MessageHandler fixture definitions."""
        # Pattern 1: autouse fixtures that just init and cleanup
        pattern1 = re.compile(
            r'@pytest\.fixture\(autouse=True\)\s*\n'
            r'def\s+\w+\([^)]*\)[^:]*:\s*\n'
            r'(?:\s*"""[^"]*"""\s*\n)?'
            r'(?:\s*import\s+ClassicLib\.MessageHandler\s*\n)?'
            r'(?:\s*from\s+ClassicLib\.MessageHandler\s+import\s+init_message_handler\s*\n)?'
            r'\s*(?:_handler\s*=\s*)?init_message_handler\([^)]*\)\s*\n'
            r'\s*yield\s*\n'
            r'\s*ClassicLib\.MessageHandler\._message_handler\s*=\s*None\s*\n',
            re.MULTILINE
        )

        if pattern1.search(self.content):
            self.content = pattern1.sub('', self.content)
            self.changes_made.append("Removed redundant autouse MessageHandler fixture")

        # Pattern 2: Regular fixtures that init MessageHandler
        pattern2 = re.compile(
            r'@pytest\.fixture\s*\n'
            r'def\s+(init_message_handler_\w+|message_handler_test)\([^)]*\)[^:]*:\s*\n'
            r'(?:\s*"""[^"]*"""\s*\n)?'
            r'(?:\s*import\s+ClassicLib\.MessageHandler\s*\n)?'
            r'(?:\s*from\s+ClassicLib\.MessageHandler\s+import\s+init_message_handler\s*\n)?'
            r'\s*(?:_?handler\s*=\s*)?init_message_handler\([^)]*\)\s*\n'
            r'\s*yield\s*(?:_?handler)?\s*\n'
            r'(?:\s*ClassicLib\.MessageHandler\._message_handler\s*=\s*None\s*)?\n',
            re.MULTILINE
        )

        matches = list(pattern2.finditer(self.content))
        for match in reversed(matches):  # Process in reverse to maintain positions
            fixture_name = match.group(1)
            self.content = self.content[:match.start()] + self.content[match.end():]
            self.changes_made.append(f"Removed redundant fixture: {fixture_name}")

    def remove_direct_singleton_cleanup(self):
        """Remove direct MessageHandler singleton cleanup lines."""
        # Remove standalone cleanup lines (not in fixtures we want to keep)
        pattern = re.compile(
            r'^\s*ClassicLib\.MessageHandler\._message_handler\s*=\s*None\s*$',
            re.MULTILINE
        )

        # Check if this is in a fixture we want to keep
        if "fixtures/" not in str(self.file_path):
            old_content = self.content
            self.content = pattern.sub('', self.content)
            if old_content != self.content:
                self.changes_made.append("Removed direct MessageHandler singleton cleanup")

    def update_fixture_usage_in_tests(self):
        """Update test functions to use standardized fixtures."""
        # Find test functions using custom fixtures
        test_pattern = re.compile(
            r'(def\s+test_\w+\([^)]*)'
            r'(init_message_handler_\w+|message_handler_test)'
            r'([^)]*\):)',
            re.MULTILINE
        )

        def replace_fixture(match):
            prefix = match.group(1)
            old_fixture = match.group(2)
            suffix = match.group(3)

            # Check if this test needs GUI mode
            if self._is_gui_test():
                new_fixture = "gui_message_handler"
            else:
                new_fixture = "message_handler"

            self.changes_made.append(f"Replaced fixture {old_fixture} with {new_fixture}")
            return f"{prefix}{new_fixture}{suffix}"

        self.content = test_pattern.sub(replace_fixture, self.content)

        # Handle tests that need fixture added (currently using autouse)
        if self._needs_message_handler_fixture():
            self._add_fixture_to_tests()

    def _is_gui_test(self) -> bool:
        """Check if this is a GUI test file."""
        return any(x in str(self.file_path) for x in ["gui", "qt", "pyside", "widget", "dialog"])

    def _needs_message_handler_fixture(self) -> bool:
        """Check if tests in this file need MessageHandler."""
        # Look for MessageHandler usage in the file
        patterns = [
            r'msg_info\(',
            r'msg_warning\(',
            r'msg_error\(',
            r'MessageHandler',
            r'init_message_handler\(',
        ]
        for pattern in patterns:
            if re.search(pattern, self.content):
                return True
        return False

    def _add_fixture_to_tests(self):
        """Add message_handler fixture to test functions that need it."""
        # Pattern for test functions without the fixture
        test_pattern = re.compile(
            r'(def\s+test_\w+\()([^)]*)(\):)',
            re.MULTILINE
        )

        def add_fixture_if_needed(match):
            func_def = match.group(0)
            params = match.group(2)

            # Skip if already has a message handler fixture
            if 'message_handler' in params or 'gui_message_handler' in params:
                return func_def

            # Check if this specific test uses MessageHandler
            # This is a simplified check - you might want to make it more sophisticated
            if 'message_handler' not in params.lower():
                fixture_name = 'gui_message_handler' if self._is_gui_test() else 'message_handler'

                if params.strip():
                    # Add to existing parameters
                    new_params = f"{params}, {fixture_name}"
                else:
                    # First parameter
                    new_params = fixture_name

                self.changes_made.append(f"Added {fixture_name} fixture to test function")
                return f"{match.group(1)}{new_params}{match.group(3)}"

            return func_def

        # Only modify if we found MessageHandler usage
        if self._needs_message_handler_fixture():
            self.content = test_pattern.sub(add_fixture_if_needed, self.content)

    def remove_redundant_imports(self):
        """Remove imports that are no longer needed."""
        # Remove import of init_message_handler if not used elsewhere
        if 'init_message_handler(' not in self.content:
            pattern = re.compile(
                r'^from\s+ClassicLib\.MessageHandler\s+import\s+init_message_handler\s*$',
                re.MULTILINE
            )
            old_content = self.content
            self.content = pattern.sub('', self.content)
            if old_content != self.content:
                self.changes_made.append("Removed unused init_message_handler import")

        # Clean up ClassicLib.MessageHandler import if only used for cleanup
        if '_message_handler' not in self.content:
            pattern = re.compile(
                r'^import\s+ClassicLib\.MessageHandler\s*$',
                re.MULTILINE
            )
            old_content = self.content
            self.content = pattern.sub('', self.content)
            if old_content != self.content:
                self.changes_made.append("Removed unused ClassicLib.MessageHandler import")

    def add_fixture_imports_if_needed(self):
        """Add note about standardized fixtures if needed."""
        if self.changes_made and 'standardized fixture' not in self.content:
            # Add a comment about the standardized fixtures after imports
            import_section_end = self._find_import_section_end()
            if import_section_end > 0:
                comment = (
                    "\n# Note: MessageHandler initialization is now handled by standardized\n"
                    "# fixtures in tests/fixtures/registry_fixtures.py which provide:\n"
                    "# - message_handler: For non-GUI tests\n"
                    "# - gui_message_handler: For GUI tests (from qt_fixtures.py)\n"
                    "# - Automatic cleanup via ensure_message_handler_cleanup\n"
                )
                self.content = self.content[:import_section_end] + comment + self.content[import_section_end:]
                self.changes_made.append("Added standardized fixture documentation")

    def _find_import_section_end(self) -> int:
        """Find the position after the last import statement."""
        lines = self.content.split('\n')
        last_import_idx = 0

        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                last_import_idx = i

        if last_import_idx > 0:
            # Return position after the last import line
            return sum(len(line) + 1 for line in lines[:last_import_idx + 1])
        return 0

    def report_changes(self):
        """Report what changes were made."""
        if self.changes_made:
            rel_path = self.file_path.relative_to(Path.cwd())
            print(f"\n{rel_path}:")
            for change in self.changes_made:
                print(f"  - {change}")


def main():
    """Main migration script."""
    parser = argparse.ArgumentParser(description="Migrate test fixtures to standardized system")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without modifying files")
    parser.add_argument("--verbose", action="store_true", help="Show detailed migration information")
    parser.add_argument("--file", type=str, help="Migrate a specific file only")
    args = parser.parse_args()

    base_dir = Path.cwd()

    if args.file:
        test_files = [Path(args.file)]
    else:
        test_files = find_test_files(base_dir)

    print(f"Found {len(test_files)} test files to check")
    if args.dry_run:
        print("DRY RUN MODE - No files will be modified\n")

    migrated_count = 0
    for test_file in test_files:
        migrator = TestFileMigrator(test_file, dry_run=args.dry_run, verbose=args.verbose)
        if migrator.migrate():
            migrator.report_changes()
            migrated_count += 1

    print(f"\n{'Would migrate' if args.dry_run else 'Migrated'} {migrated_count} files")

    if args.dry_run and migrated_count > 0:
        print("\nRun without --dry-run to apply these changes")


if __name__ == "__main__":
    main()
