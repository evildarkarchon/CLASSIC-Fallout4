# Design: Expand Rust Acceleration Usage

## Context

CLASSIC has a well-designed hybrid Python-Rust architecture with:
- 25+ Rust modules providing 10-150x speedups
- Factory pattern (`ClassicLib/integration/factory.py`) for transparent Rust/Python selection
- Automatic fallback to Python when Rust is unavailable
- Environment variable (`CLASSIC_DISABLE_RUST`) for testing/debugging

However, investigation reveals underutilization:
- RecordScanner (40x) exists but OrchestratorCore uses Python directly
- Path operations (10-50x) factory returns None (no fallback implemented)
- Phase 4 utility modules integrated but not consumed

## Goals / Non-Goals

**Goals:**
- Maximize performance by utilizing existing Rust acceleration
- Maintain backward compatibility with Python-only environments
- Follow established factory pattern consistently
- Add tests to verify Rust usage and parity

**Non-Goals:**
- Writing new Rust crates (use existing)
- Changing the factory pattern architecture
- Breaking API compatibility

## Decisions

### Decision 1: Use Factory Pattern Exclusively

**What**: All component instantiation MUST use factory functions (e.g., `get_record_scanner()`) instead of direct class instantiation (e.g., `RecordScanner()`).

**Why**:
- Ensures Rust acceleration is used when available
- Maintains singleton patterns where appropriate
- Provides consistent fallback behavior
- Enables performance monitoring via factory

**Implementation**:
```python
# Before (bypasses Rust)
self.record_scanner = RecordScanner(yamldata)

# After (uses Rust if available)
self.record_scanner = get_record_scanner(yamldata)
if self.record_scanner is None:
    # Factory returned None = both Rust and Python unavailable
    raise RuntimeError("RecordScanner not available")
```

### Decision 2: Implement Missing Python Fallbacks

**What**: Factory functions that return `None` should have Python fallbacks implemented.

**Why**:
- `get_path_operations()` currently returns `None` when Rust unavailable
- This prevents graceful degradation
- Python implementations may be slower but functional

**Implementation**:
- Create Python fallback classes in `ClassicLib/python/`
- Update factory to instantiate Python class when Rust unavailable
- Document performance difference in status output

### Decision 3: Phase 4 Selective Integration

**What**: Only integrate Phase 4 modules where measurable benefit exists.

**Why**:
- Constants, version, web utilities may have minimal performance impact
- Integration effort should be proportional to benefit
- Some utilities are called infrequently (startup only)

**Implementation**:
- Profile current usage to identify hot paths
- Integrate modules in hot paths first
- Skip integration for cold/infrequent code paths

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Factory returns None breaks code | Add explicit None checks with clear error messages |
| Performance regression if Rust unavailable | Python fallbacks must exist and be tested |
| Test complexity increases | Group tests in `rust_integration/` with clear naming |
| CI time increases | Use pytest markers to run Rust tests selectively |

## Migration Plan

1. **Phase 1** (Low risk): RecordScanner factory integration
   - Single file change
   - Existing tests verify parity
   - Rollback: revert to direct instantiation

2. **Phase 2** (Low risk): File I/O audit
   - Identify and update direct instantiations
   - No functional change, just routing
   - Rollback: N/A (factory already works)

3. **Phase 3** (Medium risk): Path operations
   - Requires Python fallback implementation
   - New tests needed
   - Rollback: return None from factory (current behavior)

4. **Phase 4** (Low risk): Utility integration
   - Optional, based on profiling
   - Individual module integration
   - Rollback: don't call factory

## Open Questions

1. **Q**: Should `get_path_operations()` Python fallback use existing `ClassicLib/Utils/` code or new implementation?
   - **Proposed**: Use existing code, wrap in factory-compatible interface

2. **Q**: Which Phase 4 utilities have measurable performance impact?
   - **Proposed**: Profile before integrating, start with `get_version_utils()` for version checking
