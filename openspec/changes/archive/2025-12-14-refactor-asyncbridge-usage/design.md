# Design: AsyncBridge Usage Refactoring

## Context

CLASSIC is a hybrid Python-Rust application with three interfaces: GUI (PySide6/Qt), CLI (Python), and TUI (Rust/Ratatui). The AsyncBridge was designed to bridge sync Qt callbacks to async Python code, but has been misused in production CLI paths.

**Stakeholders**: Core developers, CLI users (performance impact), GUI maintainers

**Key Constraint**: `08-memories.md` explicitly states:
> AsyncBridge and `create_sync_wrapper()` are ONLY for GUI workers (Qt threads) and testing. Production CLI code MUST use async-first pattern with single `asyncio.run()` at entry point.

## Goals / Non-Goals

### Goals
- Establish clear specification for AsyncBridge usage boundaries
- Provide migration path for non-compliant code
- Improve CLI performance by eliminating unnecessary event loops
- Enforce async-first pattern in production CLI code

### Non-Goals
- Removing AsyncBridge entirely (it's essential for GUI)
- Changing how GUI workers operate
- Modifying the Rust async integration patterns
- Breaking test utilities that legitimately use AsyncBridge

## Decisions

### Decision 1: Three-Tier Usage Classification

**What**: Classify all AsyncBridge usage into three tiers:
1. **Tier 1 - Core** (Never refactor): AsyncBridge implementation, helper modules
2. **Tier 2 - Legitimate** (Keep): GUI workers, test utilities, sync adapters for GUI
3. **Tier 3 - Violation** (Refactor): Production CLI paths, non-GUI modules

**Why**: Clear classification enables systematic refactoring without breaking legitimate use cases.

**Alternatives considered**:
- Runtime detection (rejected: adds overhead)
- Separate modules for GUI/CLI (rejected: too much duplication)

### Decision 2: Dual Interface Pattern

**What**: Modules used by both GUI and CLI SHALL provide:
- Async methods as primary API (for CLI)
- Sync wrappers explicitly marked for GUI-only use

```python
# Primary async API (CLI uses this)
async def generate_game_result_async() -> str:
    ...

# GUI-only sync wrapper
def generate_game_result() -> str:
    """Sync wrapper for GUI workers. NOT for CLI use."""
    bridge = AsyncBridge.get_instance()
    return bridge.run_async(generate_game_result_async())
```

**Why**: Maintains backward compatibility for GUI while enforcing async-first for CLI.

### Decision 3: Entry Point Pattern Enforcement

**What**: CLI entry points MUST follow the async-first pattern:
```python
async def main() -> None:
    # All async operations here
    result = await async_operation()

if __name__ == "__main__":
    asyncio.run(main())
```

**Why**: Single event loop is more efficient than creating/destroying loops per operation.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Breaking GUI functionality | Tier 2 classification protects legitimate usage |
| Large refactoring scope | Phased approach with clear task ordering |
| Test failures during migration | Tests are valid AsyncBridge users, no change needed |
| Incomplete migration | Specification enables future enforcement/linting |

## Migration Plan

### Step 1: Specification (This Change)
- Create `async-patterns` spec
- Document all requirements and scenarios

### Step 2: Audit & Classification
- Run grep analysis to find all AsyncBridge imports
- Classify each usage into tiers
- Document in migration guide

### Step 3: Refactor by Module Priority
Priority order based on usage frequency and CLI impact:
1. `ClassicLib/ScanGame/` modules (highest CLI usage)
2. `ClassicLib/ScanLog/` modules
3. `ClassicLib/rust/` wrappers
4. `ClassicLib/FileGeneration.py`

### Step 4: Validation
- Run full test suite
- Performance benchmark CLI operations
- Verify GUI still works correctly

### Rollback
Each module refactoring is independent. If a module refactoring causes issues:
1. Revert that specific module
2. Document the blocker
3. Continue with other modules

## Open Questions

1. **Q**: Should we add a runtime check that warns when AsyncBridge is used outside GUI context?
   **A**: Defer to implementation phase - may add development-only warnings.

2. **Q**: Should sync wrappers be removed entirely or kept as GUI-only APIs?
   **A**: Keep as GUI-only APIs to avoid breaking GUI workers.
