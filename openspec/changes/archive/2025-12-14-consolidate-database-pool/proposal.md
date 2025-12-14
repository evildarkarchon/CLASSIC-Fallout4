# consolidate-database-pool

## Summary
Eliminate duplicate `DatabasePoolManager` and `AsyncDatabasePool` implementations across `ClassicLib/ScanLog/AsyncUtil.py` and `ClassicLib/rust/database_rust.py` by consolidating into a single canonical location with clear separation between Rust wrapper and Python fallback.

## Motivation
**Current State:**
- `ClassicLib/ScanLog/AsyncUtil.py` (492 lines) contains:
  - `DatabasePoolManager` class (lines 21-106) - Singleton that tries Rust, falls back to Python
  - `AsyncDatabasePool` class (lines 109-349) - Pure Python implementation using aiosqlite

- `ClassicLib/rust/database_rust.py` (495 lines) contains:
  - `DatabasePoolManager` class (lines 113-185) - Singleton for Rust pool only
  - `RustAsyncDatabasePool` class (lines 188-465) - Wrapper around Rust DatabasePool
  - `AsyncDatabasePool` alias (line 468) pointing to `RustAsyncDatabasePool`

**Problems:**
1. Two `DatabasePoolManager` singletons with nearly identical patterns but different behaviors
2. Confusing `AsyncDatabasePool` name used for both Python and Rust implementations
3. Bug fixes require updating 2 locations (estimated 4 hours overhead per bug)
4. Risk of behavioral drift between implementations
5. Both files exceed 490 lines, violating the 500-line guideline in code-organization spec

**Impact:**
- Maintenance burden doubles for database pool code
- Developers must understand which implementation to use in each context
- Factory in `ClassicLib/integration/factory/database.py` already handles selection but internal code bypasses it

## Scope
- **In scope:**
  - Consolidating `DatabasePoolManager` into a single implementation
  - Separating Python fallback (`AsyncDatabasePool`) from Rust wrapper (`RustAsyncDatabasePool`)
  - Updating imports across the codebase to use canonical paths
  - Updating test fixtures and mocks

- **Out of scope:**
  - Changes to Rust crate implementations
  - API changes to the pool interface
  - Performance optimizations

## Approach
1. **Create canonical location**: `ClassicLib/Database/` package with:
   - `pool_manager.py` - Single `DatabasePoolManager` singleton
   - `async_pool.py` - Pure Python `AsyncDatabasePool` (moved from AsyncUtil.py)
   - `rust_pool.py` - `RustAsyncDatabasePool` wrapper (moved from database_rust.py)
   - `__init__.py` - Re-exports for backward compatibility

2. **Update factory**: `ClassicLib/integration/factory/database.py` imports from new location

3. **Migrate callers**: Update all imports to use factory or new canonical paths

4. **Remove duplicates**: Delete duplicate code from AsyncUtil.py and database_rust.py

5. **Maintain backward compatibility**: Re-exports from old locations during transition

## Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Import breakage | Medium | High | Backward compat re-exports, comprehensive test coverage |
| Singleton behavior change | Low | High | Preserve exact behavior in consolidated implementation |
| Circular imports | Medium | Medium | Use TYPE_CHECKING pattern, careful dependency ordering |

## Success Criteria
- [ ] Single `DatabasePoolManager` implementation
- [ ] Clear separation: Python fallback vs Rust wrapper
- [ ] All existing tests pass without modification
- [ ] No duplicate class definitions for database pool
- [ ] Factory remains the public interface for pool selection

## Related
- **Spec**: `code-organization` - Single Responsibility File Organization, Rust Wrapper Module Organization
- **Spec**: `rust-orchestrator` - Database Pool Support
