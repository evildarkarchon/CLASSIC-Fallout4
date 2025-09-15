# Test Reorganization Tools

This directory contains helper scripts to automate the test suite reorganization process for CLASSIC-Fallout4, ensuring compliance with the test organization rules defined in CLAUDE.md.

## Overview

The CLASSIC test suite follows these rules:
- **Maximum 300 lines per test file**
- **Separate test types**: Unit, Integration, and E2E tests in different files
- **Proper naming**: `test_<component>_<type>.py` format
- **Organized structure**: Tests in appropriate subdirectories

## Tools

### 1. `analyze_tests.py` - Test Analyzer

Analyzes test files to categorize tests as unit, integration, or E2E based on their characteristics.

#### Usage
```bash
# Analyze a single test file
python tests/tools/analyze_tests.py tests/core/test_formid_analyzer.py

# Analyze all test files in a directory
python tests/tools/analyze_tests.py tests/

# Analyze specific subdirectory
python tests/tools/analyze_tests.py tests/async_tests/
```

#### What it identifies

**Unit Tests:**
- ✅ Uses mocks (`MagicMock`, `patch`, etc.)
- ✅ No real file I/O operations
- ✅ No database calls
- ✅ Simple logic testing
- ✅ Tests single functions/methods

**Integration Tests:**
- ✅ Real file I/O operations (with `tmp_path`)
- ✅ Database interactions
- ✅ Multiple component interactions
- ✅ Tests component contracts

**E2E Tests:**
- ✅ Application entry points (`main`, `run`, `process`)
- ✅ Complete workflows
- ✅ GUI interactions
- ✅ Full stack testing

#### Example Output
```
============================================================
File: tests/core/test_formid_analyzer.py
============================================================
Total lines: 181
Total tests: 8

✅ Unit tests (3):
   • test_formid_extraction (line 45)
     - Uses mocks
     - No file I/O detected
     - Simple logic testing

🔗 Integration tests (4):
   • test_database_lookup (line 78)
     - Has database interactions
     - Uses temporary file fixtures

🔄 E2E tests (1):
   • test_full_crash_log_analysis (line 156)
     - Tests application entry points
     - Tests complete workflows

📊 Recommended action: SPLIT
```

### 2. `migrate_tests.py` - Migration Assistant

Automatically splits mixed test files into separate type-specific files while preserving all imports, fixtures, and test logic.

#### Usage
```bash
# Dry run to see what would happen (recommended first)
python tests/tools/migrate_tests.py tests/core/test_formid_analyzer.py --dry-run

# Actually perform the migration
python tests/tools/migrate_tests.py tests/core/test_formid_analyzer.py

# Skip creating backup
python tests/tools/migrate_tests.py tests/core/test_formid_analyzer.py --no-backup
```

#### What it does

1. **Analyzes** the file using the test analyzer
2. **Extracts** tests by category (unit/integration/e2e)
3. **Creates** new files with proper naming:
   - `test_formid_analyzer_unit.py`
   - `test_formid_analyzer_integration.py`
   - `test_formid_analyzer_e2e.py`
4. **Preserves** all imports and helper functions
5. **Adds** proper test markers (`@pytest.mark.unit`, etc.)
6. **Creates** backup of original file
7. **Removes** original file after successful split

#### Example Output
```
Test Migration Assistant
==================================================

🔄 Migrating tests/core/test_formid_analyzer.py
   📝 Creating test_formid_analyzer_unit.py with 3 tests
   📝 Creating test_formid_analyzer_integration.py with 4 tests
   📝 Creating test_formid_analyzer_e2e.py with 1 tests
   💾 Backup created: test_formid_analyzer.py.backup
   🗑️  Removed original file

✅ Migration completed!
Created 3 new test files:
   • test_formid_analyzer_unit.py (unit tests)
   • test_formid_analyzer_integration.py (integration tests)
   • test_formid_analyzer_e2e.py (e2e tests)

📋 Next steps:
   1. Run tests to ensure nothing broke: pytest tests/core/test_formid_analyzer_*.py
   2. Update any import statements in other files if needed
   3. Review the split and adjust test markers if necessary
```

### 3. `validate_structure.py` - Structure Validator

Validates that all test files comply with the test organization rules and provides a compliance report.

#### Usage
```bash
# Basic validation report
python tests/tools/validate_structure.py

# Verbose output showing each file checked
python tests/tools/validate_structure.py --verbose

# Get specific commands to fix violations
python tests/tools/validate_structure.py --suggest-fixes

# Validate specific directory
python tests/tools/validate_structure.py --test-dir tests/async_tests
```

#### What it checks

- **File sizes**: Identifies files over 300 lines
- **Mixed types**: Finds files with multiple test types
- **Naming conventions**: Checks for proper `test_*.py` naming
- **Directory placement**: Ensures files are in subdirectories
- **Compliance percentage**: Overall health metric

#### Example Output
```
============================================================
TEST SUITE STRUCTURE VALIDATION REPORT
============================================================
📊 Overview:
   Total test files: 103
   Compliant files: 53
   Non-compliant files: 50
   Compliance rate: 51.5%

❌ Files exceeding 300 lines (7):
   • async_tests\test_async_patterns.py (327 lines)
   • performance\test_async_performance.py (463 lines)

🔀 Files with mixed test types (47):
   • async_tests\test_async_patterns.py (contains: unit, e2e)
   • core\test_formid_analyzer.py (contains: unit, integration, e2e)

🎯 Priority Actions:
   1. Split largest files first:
      • performance\test_async_performance.py (463 lines)
      • async_tests\test_error_handling_patterns.py (362 lines)

🔧 Suggested fixes:
   Split oversized file:
   python tests/tools/migrate_tests.py performance\test_async_performance.py
```

## Workflow: Reorganizing the Test Suite

### Step 1: Assess Current State
```bash
# Get overall compliance report
python tests/tools/validate_structure.py --suggest-fixes
```

### Step 2: Analyze Problem Files
```bash
# Analyze the largest or most problematic files
python tests/tools/analyze_tests.py tests/performance/test_async_performance.py
```

### Step 3: Split Files (Dry Run First)
```bash
# Always dry run first to see what will happen
python tests/tools/migrate_tests.py tests/performance/test_async_performance.py --dry-run

# If the split looks good, do it for real
python tests/tools/migrate_tests.py tests/performance/test_async_performance.py
```

### Step 4: Verify Changes
```bash
# Run the newly created test files to ensure they work
poetry run pytest tests/performance/test_async_performance_*.py -v

# Check updated compliance
python tests/tools/validate_structure.py
```

### Step 5: Repeat
Continue with the next files identified by the validator until compliance reaches 100%.

## Tips for Success

### Priority Order
1. **Largest files first** (>400 lines) - Biggest impact
2. **Mixed type files** - Enables selective test execution
3. **Files over 300 lines** - Compliance requirement

### Test Execution Benefits
Once files are split, you can run tests selectively:
```bash
# Run only fast unit tests during development
poetry run pytest -m unit -n 4

# Skip slow tests for quick validation
poetry run pytest -m "not slow" -n 4

# Run only integration tests
poetry run pytest -m integration -n 4

# Run only async-related tests
poetry run pytest -m async_test -n 4
```

### Troubleshooting

**Import Errors After Migration:**
- Check if other test files import from the migrated file
- Update import statements to point to the new files
- The migration tool will warn about potential import issues

**Test Failures:**
- Verify all fixtures are properly imported
- Check that test logic wasn't altered during extraction
- Restore from backup if needed: `mv test_file.py.backup test_file.py`

**Wrong Categorization:**
- The analyzer uses heuristics and may occasionally miscategorize
- Review the generated files and move tests between them if needed
- Add proper markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`

## Exit Codes

All tools return appropriate exit codes for automation:
- **0**: Success (validation: 100% compliant)
- **1**: Issues found (validation: <100% compliant)

This makes them suitable for CI/CD integration and git hooks.

---

*These tools are part of the CLASSIC-Fallout4 test suite reorganization project. They help maintain clean, fast, and organized tests that follow the guidelines in CLAUDE.md.*
