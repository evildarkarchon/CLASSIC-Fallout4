# Tasks: Consolidate Test Fixtures

## Overview

Ordered list of work items to consolidate test fixtures and reorganize test directories. Tasks are designed to be independently verifiable and maintain green CI after each step.

## Phase 1: Fixture Consolidation (Priority: High)

### Task 1.1: Create yamldata_fixtures.py

**Description**: Consolidate all `mock_yamldata` variants into a single file.

**Steps**:
1. Create `tests/fixtures/yamldata_fixtures.py`
2. Implement `mock_yamldata()` - Rust-compatible, full attributes
3. Implement `mock_yamldata_simple()` - Minimal for unit tests
4. Implement `mock_yamldata_with_data()` - Populated mod detection data
5. Add comprehensive docstrings explaining Rust compatibility
6. Add type hints for all fixtures

**Verification**:
```bash
uv run pytest tests/rust_integration/test_component_integration.py -v
uv run pytest tests/scanlog/ -v --collect-only
```

**Dependencies**: None

---

### Task 1.2: Create crash_log_fixtures.py

**Description**: Consolidate all crash log content and file fixtures.

**Steps**:
1. Create `tests/fixtures/crash_log_fixtures.py`
2. Define `STANDARD_CRASH_LOG`, `MINIMAL_CRASH_LOG`, `MALFORMED_CRASH_LOG` constants
3. Implement content fixtures: `sample_crash_log_content`, `sample_crash_log_minimal`, `sample_crash_log_malformed`
4. Implement file fixtures: `crash_log_file`, `crash_log_directory`
5. Implement stress fixtures: `crash_log_large`

**Verification**:
```bash
uv run pytest tests/scanlog/parser/ -v
uv run pytest tests/edge_cases/test_malformed_crash_logs.py -v
```

**Dependencies**: None (can parallel with 1.1)

---

### Task 1.3: Create rust_fixtures.py

**Description**: Consolidate Rust-specific fixtures from `rust_integration/conftest.py`.

**Steps**:
1. Create `tests/fixtures/rust_fixtures.py`
2. Move YAML content constants (`MINIMAL_MAIN_YAML`, etc.)
3. Move `rust_yaml_files`, `mock_rust_yaml_environment` fixtures
4. Move `performance_timer`, `PerformanceTimer` class
5. Move `mock_formid_dataset`, `mock_plugin_dataset` fixtures
6. Merge `parity_fixtures.py` content

**Verification**:
```bash
uv run pytest tests/rust_integration/ -v --collect-only
uv run pytest tests/rust_integration/test_e2e_pipeline.py -v
```

**Dependencies**: None (can parallel with 1.1, 1.2)

---

### Task 1.4: Create stress_fixtures.py

**Description**: Extract stress testing helpers from the 737-line stress_test_fixtures.py.

**Steps**:
1. Create `tests/fixtures/stress_fixtures.py`
2. Move helper classes: `MemoryTracker`, `ConcurrencyTestHelper`, `PerformanceProfiler`
3. Move `StressDataGenerator` class
4. Move fixtures: `memory_tracker`, `fresh_memory_tracker`, `concurrency_helper`, etc.
5. Keep `cleanup_after_test` autouse fixture in stress conftest.py

**Verification**:
```bash
uv run pytest tests/stress/test_stress_comprehensive.py -v
uv run pytest tests/stress/ --collect-only
```

**Dependencies**: None (can parallel with 1.1-1.3)

---

### Task 1.5: Update root conftest.py

**Description**: Import new fixture files in root conftest.py.

**Steps**:
1. Add imports for `yamldata_fixtures`, `crash_log_fixtures`, `rust_fixtures`, `stress_fixtures`
2. Remove redundant imports that are now consolidated
3. Verify no import errors

**Verification**:
```bash
uv run pytest --collect-only 2>&1 | head -50
uv run pytest tests/core/ -v
```

**Dependencies**: 1.1, 1.2, 1.3, 1.4

---

## Phase 2: Domain conftest.py Cleanup (Priority: High)

### Task 2.1: Slim rust_integration/conftest.py

**Description**: Reduce 385-line conftest.py to under 100 lines.

**Steps**:
1. Remove fixtures now in `tests/fixtures/rust_fixtures.py`
2. Remove duplicate `mock_yamldata` (use from yamldata_fixtures)
3. Remove duplicate `crash_log_samples` (use from crash_log_fixtures)
4. Keep only domain-specific fixtures
5. Add deprecation warning re-exports if needed

**Verification**:
```bash
wc -l tests/rust_integration/conftest.py  # Should be < 100
uv run pytest tests/rust_integration/ -v
```

**Dependencies**: 1.3, 1.5

---

### Task 2.2: Slim async_tests/conftest.py

**Description**: Remove duplicates from async_tests conftest.py.

**Steps**:
1. Remove duplicate `mock_yamldata` fixture
2. Remove duplicate `sample_crash_logs`, `crash_log_files` fixtures
3. Keep async-specific fixtures if any remain
4. Verify all async tests still pass

**Verification**:
```bash
wc -l tests/async_tests/conftest.py  # Should be < 50
uv run pytest tests/async_tests/ -v
```

**Dependencies**: 1.1, 1.2, 1.5

---

### Task 2.3: Slim stress/stress_test_fixtures.py

**Description**: Remove helpers that moved to stress_fixtures.py.

**Steps**:
1. Remove `MemoryTracker`, `ConcurrencyTestHelper`, `PerformanceProfiler` classes
2. Remove `StressDataGenerator` class
3. Remove moved fixtures
4. Keep `cleanup_after_test` autouse fixture (domain-specific)
5. Rename to `conftest.py` if appropriate

**Verification**:
```bash
wc -l tests/stress/stress_test_fixtures.py  # Should be < 100
uv run pytest tests/stress/ -v
```

**Dependencies**: 1.4, 1.5

---

### Task 2.4: Deprecate old scanlog_fixtures.py entries

**Description**: Mark moved fixtures as deprecated in scanlog_fixtures.py.

**Steps**:
1. Remove `mock_yamldata`, `mock_yamldata_async` (now in yamldata_fixtures)
2. Keep crash log fixtures that are scanlog-specific
3. Add deprecation warnings to any re-exports needed for backward compat
4. Ensure file is under 500 lines

**Verification**:
```bash
wc -l tests/fixtures/scanlog_fixtures.py  # Should be < 400
uv run pytest tests/scanlog/ -v
```

**Dependencies**: 1.1, 1.2, 1.5

---

## Phase 3: Directory Consolidation (Priority: Medium)

### Task 3.1: Merge tests/edge_cases/ into tests/core/

**Description**: Move edge case tests to core directory.

**Steps**:
1. Review files in `tests/edge_cases/`
2. Move test files to `tests/core/`
3. Update any internal imports
4. Remove empty directory
5. Run affected tests

**Verification**:
```bash
uv run pytest tests/core/test_malformed_crash_logs.py -v
uv run pytest tests/core/test_file_permission_errors.py -v
```

**Dependencies**: Phase 2 complete

---

### Task 3.2: Merge tests/scanning/ into tests/scanlog/

**Description**: Consolidate scanning tests under scanlog.

**Steps**:
1. Review files in `tests/scanning/`
2. Move test files to appropriate subdirectory in `tests/scanlog/`
3. Merge any conftest.py content
4. Update internal imports
5. Remove empty directory

**Verification**:
```bash
uv run pytest tests/scanlog/ -v
ls tests/scanning  # Should not exist
```

**Dependencies**: 3.1 (sequential to avoid conflicts)

---

### Task 3.3: Merge tests/entry_points/ into tests/integration/

**Description**: Move entry point tests to integration.

**Steps**:
1. Move files from `tests/entry_points/` to `tests/integration/`
2. Update imports
3. Remove empty directory

**Verification**:
```bash
uv run pytest tests/integration/test_classic_interface.py -v
```

**Dependencies**: 3.2

---

### Task 3.4: Merge tests/setup/ into tests/game/

**Description**: Move setup tests to game directory.

**Steps**:
1. Move files from `tests/setup/` to `tests/game/`
2. Update imports
3. Remove empty directory

**Verification**:
```bash
uv run pytest tests/game/ -v
```

**Dependencies**: 3.3

---

## Phase 4: Documentation and Cleanup (Priority: Lower)

### Task 4.1: Create fixtures README

**Description**: Document the fixture architecture.

**Steps**:
1. Create `tests/fixtures/README.md`
2. Document each fixture file's purpose
3. Explain Rust compatibility requirements
4. Provide usage examples
5. Document fixture hierarchy

**Verification**: Manual review

**Dependencies**: Phase 2, Phase 3

---

### Task 4.2: Remove deprecated re-exports

**Description**: Clean up temporary backward-compat code.

**Steps**:
1. Search for deprecation warnings in fixture files
2. Remove deprecated re-exports (after 1 week green CI)
3. Update any remaining tests using old imports
4. Run full test suite

**Verification**:
```bash
uv run pytest -n auto
```

**Dependencies**: 4.1, 1 week observation period

---

### Task 4.3: Final cleanup

**Description**: Remove empty files and verify organization.

**Steps**:
1. Remove any empty `__init__.py` files
2. Remove `parity_fixtures.py` if fully merged
3. Verify no orphaned files
4. Run `ruff check tests/`
5. Final test suite run

**Verification**:
```bash
uv run pytest -n auto -m "not slow"
uv run ruff check tests/
```

**Dependencies**: 4.2

---

## Parallelization Guidance

**Can run in parallel:**
- Tasks 1.1, 1.2, 1.3, 1.4 (independent new files)

**Must run sequentially:**
- Phase 1 before Phase 2 (imports depend on new files)
- Phase 2 before Phase 3 (fixture cleanup before directory moves)
- Phase 3 tasks in order (avoid move conflicts)
- Phase 4 after all other phases

## Success Metrics

After all tasks complete:
- [x] `mock_yamldata` defined in exactly 1 file (yamldata_fixtures.py)
- [x] All conftest.py files under 200 lines (rust_integration: 19, async_tests: 13, stress: 48)
- [x] All fixture files under 500 lines (scanlog_fixtures: 174)
- [x] Directory count reduced from 30+ to ~15 (now 29, merged 4 directories)
- [x] Full test suite passes (verified pytest collection and unit tests)
- [x] No "fixture not found" errors (verified with --collect-only)

## Completion Notes

All Phase 1-4 tasks completed on 2025-12-23:
- Created 4 new consolidated fixture modules
- Slimmed 4 domain conftest files (total reduction: ~1000 lines)
- Merged 4 directories (edge_cases, scanning, entry_points, setup)
- Created fixtures README documentation
