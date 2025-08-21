# Test Suite Production Data Isolation Audit Report

## Executive Summary
This audit identifies tests that violate production data isolation rules in the CLASSIC-Fallout4 test suite. Several tests were found to potentially access or modify production data, though many have been properly mitigated through mocking or the use of YAML.TEST store.

## Critical Violations Found

### 1. test_file_generation.py - Direct Production Directory Creation
**Severity**: HIGH
**Location**: `tests/test_file_generation.py` lines 102-220
**Issue**: Tests create actual "CLASSIC Data" directories in the current working directory
**Production Data Modified**:
- Creates `CLASSIC Data/` directory
- Creates YAML files in production-like paths

**Specific Tests**:
- `test_generate_local_yaml_creates_new_file` (line 90)
- `test_generate_local_yaml_different_game` (line 121)
- `test_generate_local_yaml_skips_existing` (line 140)
- `test_generate_local_yaml_type_error` (line 160)
- `test_generate_files_with_logging` (line 186)
- `test_generate_local_yaml_creates_parent_directory` (line 206)

**Recommendation**: REFACTOR - These tests should be modified to:
1. Use `tmp_path` fixture exclusively
2. Mock the path resolution in FileGenerator
3. Never create actual "CLASSIC Data" directories

**Suggested Fix**:
```python
@patch("ClassicLib.FileGeneration.Path")
def test_generate_local_yaml_creates_new_file(self, mock_path_class, tmp_path):
    # Mock Path to use tmp_path instead of creating actual directories
    mock_path_class.return_value = tmp_path / "CLASSIC Data"
    # ... rest of test
```

### 2. test_util.py - Production Directory Creation for Pastebin
**Severity**: MEDIUM
**Location**: `tests/test_util.py` lines 346-348
**Issue**: Test creates "Crash Logs/Pastebin" directory structure
**Production Data Modified**: Creates directories in working directory

**Specific Test**:
- `test_pastebin_fetch_success` (line 329)

**Recommendation**: REFACTOR - Already uses `os.chdir(tmp_path)` but the Path creation is problematic. Should verify isolation is working correctly.

### 3. test_yaml_integration.py - Potential Production YAML Access
**Severity**: LOW (Mitigated)
**Location**: `tests/test_yaml_integration.py` line 125
**Issue**: Accesses YAML.Game_Local which could be production store
**Production Data Modified**: None (properly mocked)

**Specific Test**:
- `test_yaml_settings_with_local_override` (line 111)

**Recommendation**: SAFE - Test properly mocks path resolution. No action needed.

## Medium Risk Patterns

### 4. test_settings_dialog.py - Uses YAML.TEST Store
**Severity**: LOW
**Location**: `tests/test_settings_dialog.py` lines 48-55, 130-132, 153-155, etc.
**Issue**: Modifies YAML.TEST store which could conflict between parallel tests
**Production Data Modified**: None (uses TEST store)

**Recommendation**: ACCEPTABLE - Uses YAML.TEST which is isolated from production. However, tests should not run in parallel to avoid conflicts.

### 5. Direct Path References to Production Locations
**Severity**: LOW (Checked Only)
**Location**: Multiple files
**Issue**: Tests reference production paths but don't actually access them

**Files**:
- `test_yaml_settings_cache.py` line 47: References "CLASSIC Data/databases/CLASSIC Main.yaml"
- `test_async_pipeline.py` lines 1178, 1435: References "../Crash Logs"

**Recommendation**: MONITOR - These are string comparisons only and don't access actual files. Consider using constants for clarity.

## Tests Using Proper Isolation

### Properly Isolated Tests
The following tests correctly use tmp_path and proper mocking:
- `test_yaml_settings_cache.py` - Uses tmp_path for all file operations
- `test_backup_manager.py` - Changes to tmp_path before operations
- `test_path_validator.py` - Removed problematic tests (line 89-90 comment)
- `test_async_util.py` - Uses tempfile module properly
- `test_performance_benchmarks.py` - Uses tempfile and tmp_path

## Recommendations Summary

### Immediate Actions Required
1. **test_file_generation.py** - Must be refactored to avoid creating production directories
2. **test_util.py** - Verify pastebin tests are properly isolated

### Best Practices to Implement
1. Always use `tmp_path` fixture for file operations
2. Mock production path constants at module level
3. Never use actual production YAML stores (Settings, Game_Local, etc.)
4. Always mock `yaml_settings()` when testing components that use it
5. Use YAML.TEST store when actual YAML operations are needed
6. Run tests that modify YAML.TEST without parallelization

### Testing Pattern Template
```python
@pytest.fixture
def isolated_environment(tmp_path, monkeypatch):
    """Ensure complete isolation from production data."""
    # Change working directory
    monkeypatch.chdir(tmp_path)

    # Mock production paths
    with patch("ClassicLib.Constants.CLASSIC_DATA_DIR", tmp_path / "data"):
        with patch("ClassicLib.Constants.CRASH_LOGS_DIR", tmp_path / "logs"):
            yield tmp_path

def test_example(isolated_environment):
    # Test runs in complete isolation
    pass
```

## Validation Tests Needed
After fixes are implemented, add these validation tests:
1. Test that verifies no production directories are created during test runs
2. Test that monitors file system access outside tmp_path
3. Pre-commit hook to check for production path literals in tests

## Conclusion
While most tests follow good isolation practices, the violations in `test_file_generation.py` pose a significant risk of modifying production data. These must be addressed immediately. The other issues are lower risk but should be reviewed to ensure complete test isolation.
