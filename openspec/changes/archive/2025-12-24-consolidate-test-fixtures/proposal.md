# Proposal: Consolidate Test Fixtures

## Summary

Consolidate and reorganize the test fixture architecture to eliminate redundancy, reduce maintenance burden, and improve test suite organization. The current test suite has ~343 fixture definitions spread across 106 files, with significant duplication (notably `mock_yamldata` defined in 5+ locations with slight variations).

## Problem Statement

### Current Issues

1. **Fixture Duplication**: The same fixtures are defined multiple times with subtle differences:
   - `mock_yamldata` exists in `tests/fixtures/scanlog_fixtures.py`, `tests/async_tests/conftest.py`, `tests/rust_integration/conftest.py`, `tests/stress/stress_test_fixtures.py`
   - `crash_log_samples`/`sample_crash_log` variants exist in multiple locations
   - Database pool fixtures are duplicated between `tests/fixtures/database_pool_fixtures.py` and `tests/rust_integration/conftest.py`

2. **Inconsistent Fixture Quality**: Some fixtures provide Rust-compatible types, others use `MagicMock` which breaks PyO3 FFI boundaries, leading to runtime errors in Rust integration tests.

3. **Fixture Sprawl in conftest.py Files**: Large conftest.py files (e.g., `tests/rust_integration/conftest.py` at 385 lines) violate the 500-line guideline and mix concerns.

4. **Unclear Fixture Hierarchy**: Fixtures in `tests/fixtures/` are re-exported via root `conftest.py` but some directories have their own variants that shadow them.

5. **Test Directory Proliferation**: 30+ directories under `tests/` with some containing only 1-2 files, making navigation difficult.

## Proposed Solution

### Phase 1: Fixture Consolidation (High Priority)

**Goal**: Single source of truth for common fixtures

1. **Consolidate `mock_yamldata` variants** into a single parameterized fixture in `tests/fixtures/scanlog_fixtures.py`:
   - `mock_yamldata` - Default Rust-compatible mock
   - `mock_yamldata_minimal` - Minimal version for simple tests
   - `mock_yamldata_python_only` - For tests that explicitly need Mock objects

2. **Consolidate crash log fixtures** into `tests/fixtures/scanlog_fixtures.py`:
   - Merge `crash_log_samples`, `sample_crash_logs`, `sample_crash_log_content`, etc.
   - Provide clear naming: `crash_log_content`, `crash_log_file`, `crash_log_directory`

3. **Create `tests/fixtures/rust_fixtures.py`** for Rust-specific fixtures:
   - Move YAML file fixtures, Rust environment mocks from `rust_integration/conftest.py`
   - Centralize `parity_fixtures.py` content

4. **Slim down conftest.py files**:
   - Root `tests/conftest.py` only imports from `tests/fixtures/`
   - Domain conftest.py files only contain domain-specific fixtures

### Phase 2: Directory Consolidation (Medium Priority)

**Goal**: Reduce directory count while maintaining logical organization

1. **Merge small directories**:
   - `tests/api/` → `tests/core/` (if < 5 files)
   - `tests/edge_cases/` → `tests/core/` (error handling is core behavior)
   - `tests/entry_points/` → `tests/integration/`
   - `tests/tools/` → `tests/utils/`

2. **Consolidate scanning-related directories**:
   - Keep `tests/scanlog/` as the primary scanning test location
   - Consider merging `tests/scanning/` into `tests/scanlog/`

3. **Create subdirectory structure for large domains**:
   - `tests/rust_integration/` already has subdirectories - continue this pattern
   - `tests/async_tests/` could benefit from subdirectories

### Phase 3: Fixture Documentation (Lower Priority)

**Goal**: Clear documentation of fixture purposes and compatibility

1. **Add fixture documentation module**: `tests/fixtures/README.md`
2. **Add type hints to all fixtures** for IDE support
3. **Add docstrings explaining Rust compatibility requirements**

## Impact Analysis

### Benefits

- **Reduced Maintenance**: Single fixture definition to update
- **Faster Debugging**: Clear fixture hierarchy, no shadowing
- **Smaller conftest.py Files**: Better adherence to code organization standards
- **Fewer Test Failures**: Consistent Rust-compatible mocks prevent FFI errors

### Risks

- **Import Path Changes**: Tests importing fixtures directly need updates
- **Behavior Differences**: Consolidated fixtures may behave slightly differently
- **Migration Effort**: ~100+ test files may need fixture import updates

### Mitigation

- Maintain backward-compatible re-exports during transition
- Add deprecation warnings to old fixture locations
- Thorough test runs after each consolidation step

## Success Criteria

1. `mock_yamldata` defined in exactly 1 location (with variants)
2. No fixture duplication across `tests/fixtures/` and domain conftest.py files
3. All conftest.py files under 200 lines
4. Test suite passes with no new failures
5. Directory count reduced by at least 5

## Out of Scope

- Test logic refactoring (only fixture organization)
- New test coverage (separate initiative)
- CI/CD changes (no pipeline modifications needed)
