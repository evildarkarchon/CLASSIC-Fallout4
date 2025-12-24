# Design: Consolidate Test Fixtures

## Architectural Overview

### Current State

```
tests/
├── conftest.py                    # 120 lines - imports from fixtures/
├── fixtures/                      # Centralized fixtures (good)
│   ├── async_fixtures.py          # 93 lines
│   ├── data_fixtures.py           # ~100 lines
│   ├── database_pool_fixtures.py  # ~150 lines
│   ├── mock_fixtures.py           # 177 lines
│   ├── qt_fixtures.py             # ~100 lines
│   ├── registry_fixtures.py       # ~300 lines
│   ├── scanlog_fixtures.py        # 562 lines (over limit)
│   └── version_cache_fixtures.py  # ~100 lines
├── async_tests/conftest.py        # 98 lines - DUPLICATES mock_yamldata
├── rust_integration/
│   ├── conftest.py                # 385 lines (OVER LIMIT)
│   ├── parity_fixtures.py         # ~150 lines
│   └── fixtures/                  # Nested fixtures dir
├── stress/
│   └── stress_test_fixtures.py    # 737 lines (SEVERELY OVER LIMIT)
└── ... 25+ more directories
```

### Target State

```
tests/
├── conftest.py                    # <100 lines - only imports
├── fixtures/                      # ALL common fixtures
│   ├── __init__.py               # Re-exports for backward compat
│   ├── async_fixtures.py         # Event loop, cleanup helpers
│   ├── crash_log_fixtures.py     # All crash log variants (NEW)
│   ├── data_fixtures.py          # Test files, temp structures
│   ├── database_fixtures.py      # Pool, connection fixtures
│   ├── mock_fixtures.py          # Network, registry mocks
│   ├── qt_fixtures.py            # Qt/PySide6 fixtures
│   ├── registry_fixtures.py      # Singleton management
│   ├── rust_fixtures.py          # Rust-specific (NEW)
│   ├── stress_fixtures.py        # Memory, concurrency helpers (MOVED)
│   └── yamldata_fixtures.py      # All yamldata variants (NEW)
├── async_tests/conftest.py        # <50 lines - domain-specific only
├── rust_integration/conftest.py   # <100 lines - domain-specific only
├── stress/conftest.py             # <50 lines - imports from fixtures/
└── ... consolidated directories
```

## Fixture Consolidation Strategy

### 1. YamlData Fixtures (`tests/fixtures/yamldata_fixtures.py`)

**Current Duplication:**
- `tests/fixtures/scanlog_fixtures.py`: `mock_yamldata`, `mock_yamldata_async`
- `tests/async_tests/conftest.py`: `mock_yamldata`
- `tests/rust_integration/conftest.py`: `mock_yamldata`, `mock_scanlog_info`
- `tests/stress/stress_test_fixtures.py`: `mock_yamldata`, `mock_yamldata_python_only`

**Consolidated Design:**

```python
# tests/fixtures/yamldata_fixtures.py
"""YamlData and ScanLogInfo test fixtures.

This module provides all yamldata-related fixtures for testing.
Fixtures are designed to be Rust-compatible by default.

IMPORTANT: Use `mock_yamldata` for Rust integration tests.
Use `mock_yamldata_simple` for unit tests that don't call Rust.
"""

import pytest
from unittest.mock import MagicMock, Mock

@pytest.fixture
def mock_yamldata() -> MagicMock:
    """Create Rust-compatible yamldata mock.

    All attributes are proper Python types (not Mock objects)
    to ensure PyO3 type conversion works correctly.

    Use for: Rust integration, parity tests, orchestrator tests
    """
    mock = MagicMock(spec=False)
    # ... full Rust-compatible implementation
    return mock

@pytest.fixture
def mock_yamldata_simple() -> MagicMock:
    """Create minimal yamldata mock for simple unit tests.

    Use for: Unit tests that don't call Rust FFI
    """
    mock = MagicMock()
    mock.crashgen_name = "Buffout 4"
    # ... minimal implementation
    return mock

@pytest.fixture
def mock_yamldata_with_data() -> MagicMock:
    """Create yamldata mock with populated mod detection data.

    Use for: Mod detection, suspect scanning tests
    """
    # ... implementation with game_mods_* populated
    return mock
```

### 2. Crash Log Fixtures (`tests/fixtures/crash_log_fixtures.py`)

**Current Duplication:**
- `tests/fixtures/scanlog_fixtures.py`: `sample_crash_log_content`, `crash_log_file`, etc.
- `tests/async_tests/conftest.py`: `sample_crash_logs`, `crash_log_files`
- `tests/rust_integration/conftest.py`: `crash_log_samples`
- `tests/stress/stress_test_fixtures.py`: `large_crash_log`, `temp_crash_logs_dir`

**Consolidated Design:**

```python
# tests/fixtures/crash_log_fixtures.py
"""Crash log test fixtures.

This module provides all crash log-related fixtures with clear naming:
- `crash_log_*` for file-based fixtures
- `sample_*_content` for string content
"""

# Content fixtures
@pytest.fixture
def sample_crash_log_content() -> str:
    """Standard crash log content for parsing tests."""
    return STANDARD_CRASH_LOG

@pytest.fixture
def sample_crash_log_minimal() -> str:
    """Minimal valid crash log for edge case tests."""
    return MINIMAL_CRASH_LOG

@pytest.fixture
def sample_crash_log_malformed() -> str:
    """Malformed crash log for error handling tests."""
    return MALFORMED_CRASH_LOG

# File fixtures
@pytest.fixture
def crash_log_file(tmp_path, sample_crash_log_content) -> Path:
    """Single crash log file."""

@pytest.fixture
def crash_log_directory(tmp_path) -> Path:
    """Directory with multiple crash logs."""

# Stress fixtures (large data)
@pytest.fixture
def crash_log_large(tmp_path, stress_data_generator) -> Path:
    """Large crash log (50MB) for stress testing."""
```

### 3. Rust Fixtures (`tests/fixtures/rust_fixtures.py`)

**Moved from:** `tests/rust_integration/conftest.py`, `tests/rust_integration/parity_fixtures.py`

```python
# tests/fixtures/rust_fixtures.py
"""Rust-specific test fixtures.

Fixtures for Rust integration testing including:
- YAML environment setup
- Rust extension availability checks
- Parity test infrastructure
"""

# YAML file fixtures for Rust YamlData initialization
MINIMAL_MAIN_YAML = """..."""
MINIMAL_GAME_YAML = """..."""

@pytest.fixture
def rust_yaml_files(tmp_path) -> dict[str, Path]:
    """Create minimal YAML files for Rust YamlData."""

@pytest.fixture
def mock_rust_yaml_environment(rust_yaml_files):
    """Mock environment for Rust YamlData initialization."""

@pytest.fixture
def performance_timer():
    """Context manager for timing Rust vs Python operations."""

# Parity testing infrastructure
@pytest.fixture
def parity_crash_generator():
    """Generate crash logs for Rust/Python parity comparison."""
```

### 4. Stress Fixtures (`tests/fixtures/stress_fixtures.py`)

**Moved from:** `tests/stress/stress_test_fixtures.py`

Split the 737-line file into focused modules:
- Core helpers (MemoryTracker, ConcurrencyTestHelper, etc.) → `stress_fixtures.py`
- Data generators remain as class, imported where needed
- Domain-specific stress fixtures stay in `tests/stress/conftest.py`

## Directory Consolidation Plan

### Directories to Merge

| Source | Target | Rationale |
|--------|--------|-----------|
| `tests/api/` | `tests/core/` | Only 1-2 files, API is core behavior |
| `tests/edge_cases/` | `tests/core/` | Error handling is core behavior |
| `tests/entry_points/` | `tests/integration/` | Entry points are integration tests |
| `tests/tools/` | `tests/utils/` | Same domain |
| `tests/scanning/` | `tests/scanlog/` | Same domain, consolidate scanning |
| `tests/setup/` | `tests/game/` | Setup relates to game configuration |
| `tests/unit/` | Domain directories | Distribute to relevant domains |

### Directories to Keep

- `tests/async_tests/` - Large enough, distinct concern
- `tests/async_resources/` - Distinct from async patterns
- `tests/core/` - Central tests
- `tests/fixtures/` - Fixture home
- `tests/gui/` - GUI-specific tests
- `tests/integration/` - Cross-component tests
- `tests/performance/` - Benchmarks
- `tests/rust_integration/` - Rust FFI tests
- `tests/scanlog/` - Core parsing domain
- `tests/settings/` - Configuration tests
- `tests/stress/` - Stress testing
- `tests/test_data/` - Static test data

**Target: Reduce from 30+ to ~15 directories**

## Migration Strategy

### Phase 1: Create New Fixture Files (Non-Breaking)

1. Create `tests/fixtures/yamldata_fixtures.py` with consolidated fixtures
2. Create `tests/fixtures/crash_log_fixtures.py` with consolidated fixtures
3. Create `tests/fixtures/rust_fixtures.py` with moved fixtures
4. Create `tests/fixtures/stress_fixtures.py` with moved helpers

### Phase 2: Update Root conftest.py

```python
# tests/conftest.py
from tests.fixtures.async_fixtures import *
from tests.fixtures.crash_log_fixtures import *
from tests.fixtures.data_fixtures import *
from tests.fixtures.database_fixtures import *
from tests.fixtures.mock_fixtures import *
from tests.fixtures.qt_fixtures import *
from tests.fixtures.registry_fixtures import *
from tests.fixtures.rust_fixtures import *
from tests.fixtures.stress_fixtures import *
from tests.fixtures.yamldata_fixtures import *
```

### Phase 3: Update Domain conftest.py Files

For each domain conftest.py:
1. Remove duplicate fixtures that now exist in `tests/fixtures/`
2. Keep only domain-specific fixtures
3. Add deprecation warnings for any re-exports

### Phase 4: Update Test Imports

Run tests and fix any import errors:
```bash
uv run pytest -x 2>&1 | grep "fixture .* not found"
```

### Phase 5: Directory Consolidation

1. Move files from source to target directories
2. Update any absolute imports
3. Remove empty directories

## Backward Compatibility

### Re-export Strategy

```python
# tests/fixtures/scanlog_fixtures.py (old location)
"""DEPRECATED: Import from yamldata_fixtures instead."""
import warnings
from tests.fixtures.yamldata_fixtures import mock_yamldata as _mock_yamldata

@pytest.fixture
def mock_yamldata():
    warnings.warn(
        "mock_yamldata from scanlog_fixtures is deprecated. "
        "Import from tests.fixtures.yamldata_fixtures",
        DeprecationWarning,
        stacklevel=2
    )
    return _mock_yamldata()
```

### Removal Timeline

- Phase 1-4: Keep deprecated re-exports
- After 1 week of green CI: Remove deprecated fixtures
- Final cleanup: Remove empty old fixture files

## Risk Mitigation

### Testing Strategy

1. Run full test suite after each phase
2. Use `pytest --collect-only` to verify fixture availability
3. Check for shadowed fixtures with custom pytest plugin

### Rollback Plan

Each phase can be reverted independently:
- Phase 1: Delete new fixture files
- Phase 2: Revert conftest.py
- Phase 3: Revert domain conftest.py files
- Phase 4: Revert test imports
- Phase 5: Move files back

## Definition of Done

1. No fixture defined in more than one location (except re-exports)
2. All conftest.py files under 200 lines
3. All fixture files under 500 lines
4. Test suite passes with no new failures
5. CI green on all checks
6. Documentation updated in `tests/fixtures/README.md`
