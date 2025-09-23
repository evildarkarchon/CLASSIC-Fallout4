#!/usr/bin/env python
"""
Test Migration Assistant for CLASSIC-Fallout4

Automatically splits mixed test files into separate unit, integration, and E2E files.
Preserves all imports, fixtures, and test logic while adding proper markers.

Usage:
    python tests/tools/migrate_tests.py path/to/test_file.py [--dry-run] [--backup]
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Any

from analyze_tests import TestInfo, analyze_file


class TestExtractor(ast.NodeVisitor):
    """Extracts specific test functions and their dependencies."""

    def __init__(self, test_names_to_extract: set[str]):
        self.test_names_to_extract = test_names_to_extract
        self.extracted_nodes = []
        self.helper_functions = []
        self.class_nodes = {}
        self.current_class = None

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        """Handle test classes."""
        old_class = self.current_class
        self.current_class = node.name

        # Check if this class contains any tests we want
        class_has_target_tests = False
        for child in ast.walk(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if child.name.startswith('test_'):
                    test_name = f"{self.current_class}.{child.name}"
                    if test_name in self.test_names_to_extract:
                        class_has_target_tests = True
                        break

        if class_has_target_tests:
            # Create a new class with only the methods we want
            new_class = ast.ClassDef(
                name=node.name,
                bases=node.bases,
                keywords=node.keywords,
                decorator_list=node.decorator_list,
                body=[],
                lineno=node.lineno,
                col_offset=node.col_offset
            )

            # Extract only the methods we want
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if child.name.startswith('test_'):
                        test_name = f"{self.current_class}.{child.name}"
                        if test_name in self.test_names_to_extract:
                            new_class.body.append(child)
                    elif not child.name.startswith('test_'):
                        # Include helper methods
                        new_class.body.append(child)
                else:
                    # Include class variables, docstrings, etc.
                    new_class.body.append(child)

            if new_class.body:
                self.extracted_nodes.append(new_class)

        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        """Handle standalone test functions."""
        if node.name.startswith('test_'):
            test_name = node.name
            if test_name in self.test_names_to_extract:
                self.extracted_nodes.append(node)
        elif not node.name.startswith('_'):
            # Potential helper function
            self.helper_functions.append(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        """Handle async test functions."""
        self.visit_FunctionDef(node)


def extract_imports_and_constants(file_content: str) -> tuple[list[str], list[str]]:
    """Extract import statements and module-level constants."""
    tree = ast.parse(file_content)

    imports = []
    constants = []

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(ast.unparse(node))
        elif isinstance(node, ast.Assign):
            # Module-level constants
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if node.targets[0].id.isupper():
                    constants.append(ast.unparse(node))

    return imports, constants


def create_file_content(
    tests: list[TestInfo],
    test_type: str,
    original_file_path: Path,
    imports: list[str],
    constants: list[str],
    extracted_code: list[ast.AST]
) -> str:
    """Create the content for a new test file."""

    # Determine component name from file path
    component_name = original_file_path.stem.replace('test_', '')

    # Create file header
    header = f'''"""
{test_type.title()} tests for {component_name} - {test_type} logic testing.

This file contains {test_type} tests that {'test individual functions with mocked dependencies' if test_type == 'unit' else 'test interactions between components' if test_type == 'integration' else 'test complete workflows from entry to output'}.
"""

'''

    # Add imports
    content_parts = [header]

    if imports:
        content_parts.append('\n'.join(imports))
        content_parts.append('\n')

    # Add pytest import if not present
    if not any('pytest' in imp for imp in imports):
        content_parts.append('import pytest\n')

    # Add constants
    if constants:
        content_parts.append('\n')
        content_parts.append('\n'.join(constants))
        content_parts.append('\n')

    # Add marker for the test type
    content_parts.append(f'\npytestmark = pytest.mark.{test_type}\n\n')

    # Add extracted test code
    if extracted_code:
        for node in extracted_code:
            content_parts.append(ast.unparse(node))
            content_parts.append('\n\n')

    return ''.join(content_parts)


def _print_migration_header(file_path: Path) -> None:
    """Print migration header."""
    try:
        relative_path = file_path.relative_to(Path.cwd())
        print(f"\n🔄 Migrating {relative_path}")
    except ValueError:
        print(f"\n🔄 Migrating {file_path}")


def _handle_performance_file() -> dict[str, Path]:
    """Handle performance file migration."""
    print("   ⚡ Performance file detected - requires manual functional scope splitting")
    print("   📋 Suggested approach:")
    print("      • Split by functional areas (comparisons, baselines, benchmarks)")
    print("      • Group related performance tests together")
    print("      • Consider: test_<component>_performance_<scope>.py naming")
    print("   ❌ Automatic migration not recommended for performance files")
    return {}


def _get_component_name(file_path: Path) -> str:
    """Extract component name from file path."""
    base_name = file_path.stem
    if base_name.startswith('test_'):
        return base_name[5:]  # Remove 'test_' prefix
    return base_name


def _create_test_file(file_path: Path, test_type: str, tests: list[TestInfo],
                     imports: list[str], constants: list[str], original_content: str,
                     dry_run: bool) -> Path | None:
    """Create a single test file for a specific test type."""
    component_name = _get_component_name(file_path)
    new_filename = f"test_{component_name}_{test_type}.py"
    new_file_path = file_path.parent / new_filename

    print(f"   📝 Creating {new_filename} with {len(tests)} tests")

    # Extract the test code for this type
    test_names = {test.name for test in tests}
    extractor = TestExtractor(test_names)

    tree = ast.parse(original_content)
    extractor.visit(tree)

    # Create file content
    content = create_file_content(
        tests, test_type, file_path, imports, constants, extractor.extracted_nodes
    )

    if not dry_run:
        new_file_path.write_text(content, encoding='utf-8')
        return new_file_path
    return None


def _handle_post_migration(file_path: Path, original_content: str, created_files: dict[str, Path],
                         create_backup: bool, dry_run: bool, test_groups: dict[str, list]) -> None:
    """Handle post-migration tasks."""
    if not dry_run and created_files:
        if create_backup:
            backup_path = file_path.with_suffix('.py.backup')
            backup_path.write_text(original_content, encoding='utf-8')
            print(f"   💾 Backup created: {backup_path.name}")

        # Remove original file
        file_path.unlink()
        print("   🗑️  Removed original file")

    if dry_run:
        print("   🔍 DRY RUN - No files were actually created")
        component_name = _get_component_name(file_path)
        for test_type in test_groups:
            new_filename = f"test_{component_name}_{test_type}.py"
            print(f"   📝 Would create: {new_filename}")


def migrate_test_file(
    file_path: Path,
    dry_run: bool = False,
    create_backup: bool = True
) -> dict[str, Path]:
    """Migrate a test file by splitting it into separate files by test type."""
    _print_migration_header(file_path)

    # Analyze the file first
    analysis = analyze_file(file_path)

    if not analysis.needs_split:
        print("   ✅ File doesn't need splitting")
        return {}

    # Handle performance files specially
    if analysis.is_performance_file:
        return _handle_performance_file()

    # Read original content
    original_content = file_path.read_text(encoding='utf-8')
    imports, constants = extract_imports_and_constants(original_content)

    # Group tests by type
    test_groups = {
        'unit': analysis.unit_tests,
        'integration': analysis.integration_tests,
        'e2e': analysis.e2e_tests
    }

    # Remove empty groups
    test_groups = {k: v for k, v in test_groups.items() if v}

    if len(test_groups) <= 1:
        print("   ✅ File contains only one test type, no split needed")
        return {}

    created_files = {}

    # Create new files for each test type
    for test_type, tests in test_groups.items():
        if tests:
            new_file = _create_test_file(
                file_path, test_type, tests, imports, constants, original_content, dry_run
            )
            if new_file:
                created_files[test_type] = new_file

    # Handle post-migration tasks
    _handle_post_migration(file_path, original_content, created_files, create_backup, dry_run, test_groups)

    return created_files


def update_imports_in_other_files(original_file: Path, created_files: dict[str, Path]) -> None:
    """Update any imports in other test files that reference the migrated file."""
    test_dir = original_file.parent

    # Find files that might import from the original file
    module_name = original_file.stem
    import_pattern = re.compile(rf'from\s+.*{re.escape(module_name)}\s+import|import\s+.*{re.escape(module_name)}')

    for test_file in test_dir.rglob('test_*.py'):
        if test_file == original_file or test_file in created_files.values():
            continue

        try:
            content = test_file.read_text(encoding='utf-8')
            if import_pattern.search(content):
                print(f"   ⚠️  {test_file.name} may need import updates")
        except Exception:
            continue


def main():
    """Main script entry point."""
    parser = argparse.ArgumentParser(description='Migrate mixed test files into separate type-specific files')
    parser.add_argument('file_path', help='Path to the test file to migrate')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--no-backup', action='store_true', help='Do not create backup of original file')

    args = parser.parse_args()

    file_path = Path(args.file_path)

    if not file_path.exists():
        print(f"Error: {file_path} does not exist")
        sys.exit(1)

    if not file_path.name.startswith('test_') or file_path.suffix != '.py':
        print(f"Error: {file_path} is not a test file")
        sys.exit(1)

    print("Test Migration Assistant")
    print(f"{'='*50}")

    created_files = migrate_test_file(
        file_path,
        dry_run=args.dry_run,
        create_backup=not args.no_backup
    )

    if created_files and not args.dry_run:
        print("\n✅ Migration completed!")
        print(f"Created {len(created_files)} new test files:")
        for test_type, path in created_files.items():
            print(f"   • {path.name} ({test_type} tests)")

        # Check for import dependencies
        update_imports_in_other_files(file_path, created_files)

        print("\n📋 Next steps:")
        print(f"   1. Run tests to ensure nothing broke: pytest {' '.join(str(p) for p in created_files.values())}")
        print("   2. Update any import statements in other files if needed")
        print("   3. Review the split and adjust test markers if necessary")

    elif args.dry_run:
        print("\n🔍 Dry run completed - no files were modified")


if __name__ == "__main__":
    main()
