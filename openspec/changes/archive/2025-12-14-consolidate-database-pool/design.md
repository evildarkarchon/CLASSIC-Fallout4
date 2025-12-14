# Design: consolidate-database-pool

## Current Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Current State (Duplicated)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ClassicLib/ScanLog/AsyncUtil.py (492 lines)                    │
│  ├── DatabasePoolManager (tries Rust, falls back to Python)     │
│  ├── AsyncDatabasePool (Python aiosqlite implementation)        │
│  └── File operations (read_file_async, write_file_async, etc.)  │
│                                                                  │
│  ClassicLib/rust/database_rust.py (495 lines)                   │
│  ├── DatabasePoolManager (Rust-only singleton)                  │
│  ├── RustAsyncDatabasePool (Rust wrapper)                       │
│  └── AsyncDatabasePool = RustAsyncDatabasePool (alias)          │
│                                                                  │
│  ClassicLib/integration/factory/database.py                     │
│  └── get_database_pool() - selects between implementations      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Problems:**
1. Two `DatabasePoolManager` classes with different selection logic
2. Confusing `AsyncDatabasePool` name overloaded for different implementations
3. Callers bypass factory and import directly, leading to inconsistent behavior
4. Both files near 500-line limit, mixing concerns

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Proposed State (Consolidated)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ClassicLib/Database/                                            │
│  ├── __init__.py (re-exports public API)                        │
│  ├── pool_manager.py                                             │
│  │   └── DatabasePoolManager (unified singleton)                 │
│  ├── async_pool.py                                               │
│  │   └── AsyncDatabasePool (Python fallback)                     │
│  └── rust_pool.py                                                │
│      └── RustAsyncDatabasePool (Rust wrapper)                    │
│                                                                  │
│  ClassicLib/integration/factory/database.py                     │
│  └── get_database_pool() - uses ClassicLib.Database             │
│                                                                  │
│  ClassicLib/ScanLog/AsyncUtil.py (~150 lines, file ops only)    │
│  └── read_file_async, write_file_async, batch_file_operations   │
│                                                                  │
│  ClassicLib/rust/database_rust.py (removed or minimal shim)     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Single DatabasePoolManager Location

**Decision:** Place the unified `DatabasePoolManager` in `ClassicLib/Database/pool_manager.py`.

**Rationale:**
- Database concerns are distinct from ScanLog operations
- Follows Single Responsibility principle
- Consistent with existing patterns (e.g., `ClassicLib/FileIO/`, `ClassicLib/YamlSettings/`)

**Behavior:**
```python
class DatabasePoolManager:
    """Unified singleton manager for database pool instances."""

    async def get_pool(self) -> AsyncDatabasePool | RustAsyncDatabasePool:
        """Get pool, preferring Rust when available."""
        if is_rust_accelerated("database_pool"):
            return RustAsyncDatabasePool(...)
        return AsyncDatabasePool(...)
```

### 2. Clear Naming Convention

**Decision:** Keep distinct class names:
- `AsyncDatabasePool` - Pure Python implementation (aiosqlite)
- `RustAsyncDatabasePool` - Rust wrapper implementation

**Rationale:**
- Eliminates confusion from aliasing
- Makes it clear which implementation is in use
- Type hints remain accurate

### 3. Factory as Primary Interface

**Decision:** All production code should use `get_database_pool()` factory.

**Rationale:**
- Single point of selection logic
- Easier to modify acceleration behavior
- Consistent with existing factory patterns for YAML, parsers, etc.

```python
# Preferred usage
from ClassicLib.integration.factory import get_database_pool
pool = get_database_pool()

# NOT recommended (direct imports)
from ClassicLib.Database import DatabasePoolManager  # Only for singleton access
```

### 4. Backward Compatibility Strategy

**Decision:** Two-phase migration with deprecation warnings.

**Phase 1 (this change):**
- Old import paths work with `DeprecationWarning`
- New canonical paths available

**Phase 2 (future change):**
- Remove old import paths
- Document in migration guide

```python
# ClassicLib/rust/database_rust.py (transitional)
import warnings
from ClassicLib.Database import RustAsyncDatabasePool, DatabasePoolManager

warnings.warn(
    "Import from ClassicLib.Database instead of ClassicLib.rust.database_rust",
    DeprecationWarning,
    stacklevel=2
)
```

## Module Structure

### ClassicLib/Database/__init__.py
```python
"""Database connection pool management.

Public API:
    DatabasePoolManager: Singleton for pool lifecycle management
    AsyncDatabasePool: Pure Python implementation (fallback)
    RustAsyncDatabasePool: Rust-accelerated implementation
"""
from ClassicLib.Database.pool_manager import DatabasePoolManager
from ClassicLib.Database.async_pool import AsyncDatabasePool
from ClassicLib.Database.rust_pool import RustAsyncDatabasePool

__all__ = ["DatabasePoolManager", "AsyncDatabasePool", "RustAsyncDatabasePool"]
```

### ClassicLib/Database/pool_manager.py
- Single `DatabasePoolManager` class
- Thread-safe singleton pattern (matches existing implementation)
- Uses factory logic internally for implementation selection
- ~80 lines

### ClassicLib/Database/async_pool.py
- `AsyncDatabasePool` class (from AsyncUtil.py)
- Pure Python, aiosqlite-based
- Context manager support
- ~150 lines

### ClassicLib/Database/rust_pool.py
- `RustAsyncDatabasePool` class (from database_rust.py)
- Wraps Rust `DatabasePool`
- Exception mapping
- ~200 lines

## Import Path Changes

| Old Path | New Canonical Path |
|----------|-------------------|
| `ClassicLib.ScanLog.AsyncUtil.DatabasePoolManager` | `ClassicLib.Database.DatabasePoolManager` |
| `ClassicLib.ScanLog.AsyncUtil.AsyncDatabasePool` | `ClassicLib.Database.AsyncDatabasePool` |
| `ClassicLib.rust.database_rust.DatabasePoolManager` | `ClassicLib.Database.DatabasePoolManager` |
| `ClassicLib.rust.database_rust.RustAsyncDatabasePool` | `ClassicLib.Database.RustAsyncDatabasePool` |
| `ClassicLib.rust.database_rust.AsyncDatabasePool` | `ClassicLib.Database.RustAsyncDatabasePool` |

## Testing Strategy

1. **Unit tests**: Test each pool implementation in isolation
2. **Integration tests**: Test pool manager selection logic
3. **Parity tests**: Verify Python and Rust implementations have same behavior
4. **Migration tests**: Verify old import paths work during transition

## Alternatives Considered

### Alternative 1: Keep in AsyncUtil.py, remove database_rust.py
**Rejected:** AsyncUtil.py would still be large and mix concerns (file I/O + database)

### Alternative 2: Merge into database_rust.py only
**Rejected:** Conflates Rust wrapper module with general database concerns; what happens when Rust isn't available?

### Alternative 3: Keep both files, just deduplicate DatabasePoolManager
**Rejected:** Doesn't address the dual-location issue or the 500-line problem

## Compatibility Notes

- Rust crate interface unchanged (`classic_database.DatabasePool`)
- Factory function signature unchanged
- Pool instance API unchanged
- Only import paths change (with deprecation shims)
