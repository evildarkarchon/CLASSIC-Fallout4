# Design: Type Safety Debt Reduction

## Context
CLASSIC uses mypy for static type checking but has accumulated 126 `# type: ignore` comments and 57 broad exception handlers in production code. This reduces the effectiveness of static analysis and can hide runtime errors.

**Stakeholders**: All Python developers, CI/CD pipeline, IDE users
**Constraints**: Must maintain backward compatibility; some ignores are legitimate (Qt bindings, PyO3)

## Goals / Non-Goals

### Goals
- Reduce `# type: ignore` comments to legitimate cases only (~30)
- Require specific error codes for all remaining type ignores
- Replace broad `except Exception` with specific exception types
- Improve mypy/pyright coverage and accuracy
- Document legitimate exception patterns

### Non-Goals
- Achieve 100% type coverage (some dynamic patterns are necessary)
- Change public API signatures (backward compatibility required)
- Modify exception handling in Rust code (separate concern)
- Refactor exception hierarchies (scope creep)

## Decisions

### Decision 1: Categorize Type Ignores by Resolution Strategy
Each `# type: ignore` will be classified:

| Category | Action | Example |
|----------|--------|---------|
| **Fix** | Add proper type annotations | Bare ignores, missing return types |
| **Stub** | Create/update `.pyi` stubs | Qt signal types, PyO3 bindings |
| **Guard** | Add type narrowing | Union types, optional handling |
| **Keep** | Document with specific code | Dynamic imports, metaprogramming |

**Rationale**: Not all type ignores are equal; some require code changes, others require stubs.

### Decision 2: Bare Type Ignores Become Errors
All `# type: ignore` comments without specific error codes will be treated as errors.

**Rationale**: Bare ignores suppress all type errors at a location, potentially hiding real bugs.

**Implementation**:
```python
# BAD - suppresses all errors
result = some_call()  # type: ignore

# GOOD - documents specific issue
result = some_call()  # type: ignore[arg-type]
```

### Decision 3: Exception Handler Tiers
Define three tiers for exception handling:

| Tier | Pattern | When to Use |
|------|---------|-------------|
| **Specific** | `except ValueError, TypeError` | Always preferred |
| **Category** | `except OSError` | File/network operations |
| **Broad** | `except Exception` | GUI workers, top-level handlers only |

**Rationale**: Broad handlers hide bugs; specific handlers enable targeted recovery.

### Decision 4: Legitimate Broad Exception Cases
Document and allow `except Exception` only for:

1. **GUI thread workers** - Qt requires catching all to prevent crashes
2. **Top-level entry points** - Graceful shutdown on unexpected errors
3. **Rust fallback code** - After trying specific Rust exceptions
4. **Cleanup operations** - Ensure resources are released

All such cases MUST include:
- `# noqa: BLE001` comment (intentional broad exception)
- Brief documentation of why broad catch is necessary

### Decision 5: Pass Statement Audit
Each `pass` statement will be reviewed:

| Category | Action |
|----------|--------|
| Abstract methods | Replace with `raise NotImplementedError` |
| Placeholder implementations | Complete or add `# TODO` with issue link |
| Intentional no-op | Add comment explaining why |
| Exception handlers | Add logging or re-raise |

## Risks / Trade-offs

### Risk: Breaking Changes from Type Fixes
Some type annotation fixes may reveal actual bugs or require API changes.

**Mitigation**: Run full test suite after each category of changes; document any behavioral changes.

### Risk: Exception Handler Changes Affect Error Propagation
Changing exception types may cause previously-caught exceptions to propagate.

**Mitigation**:
1. Map current exception usage before changes
2. Ensure specific exceptions are subclasses of currently-caught types where appropriate
3. Add tests for error handling paths

### Trade-off: Maintenance Burden of Type Stubs
Creating `.pyi` stubs for Qt bindings adds maintenance overhead.

**Decision**: Use inline type hints where possible; only create stubs for external dependencies.

## Migration Plan

### Phase 1: Inventory and Categorize (No Code Changes)
1. Generate full inventory of type ignores with file locations
2. Categorize each by resolution strategy
3. Identify legitimate vs. fixable cases

### Phase 2: Fix Bare Type Ignores
1. Add specific error codes to all bare `# type: ignore` comments
2. Update mypy configuration to require error codes

### Phase 3: Reduce Fixable Type Ignores
1. Fix `[assignment]` and `[return-value]` issues (type annotation fixes)
2. Fix `[arg-type]` issues (signature corrections)
3. Add type guards for `[union-attr]` issues

### Phase 4: Exception Handler Audit
1. Inventory all `except Exception` handlers
2. Categorize by tier (GUI/top-level/fixable)
3. Replace fixable handlers with specific types
4. Document legitimate broad handlers

### Phase 5: Pass Statement Cleanup
1. Audit all `pass` statements
2. Complete implementations or add documentation
3. Replace abstract methods with `raise NotImplementedError`

## Open Questions

1. **Q**: Should we create a central exception hierarchy for CLASSIC-specific errors?
   **A**: Out of scope for this proposal; consider for future work.

2. **Q**: What mypy strictness level should we target?
   **A**: Current settings with `warn_unused_ignores = true` and `no_implicit_optional = true`.

3. **Q**: Should Qt stub packages be added as dependencies?
   **A**: Evaluate `types-PySide6` or similar packages; may reduce Qt-related ignores.
