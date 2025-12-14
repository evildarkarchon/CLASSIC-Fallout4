# Change: Reduce Type Safety Technical Debt

## Why
The codebase has accumulated type safety technical debt that reduces static analysis effectiveness and hides potential runtime errors. This includes 126 `# type: ignore` comments, 57 broad `except Exception` handlers, 25 incomplete `pass` statements, and 1 dynamic `globals()` usage in production code.

## What Changes
- **BREAKING**: Remove bare `# type: ignore` comments requiring proper type annotations or specific error codes
- Categorize and reduce `# type: ignore` comments from 126 to target of ~30 (legitimate cases only)
- Replace 50+ broad `except Exception` handlers with specific exception types
- Audit and resolve 25 `pass` statements (complete implementations or add explicit comments)
- Document legitimate dynamic code usage patterns

### Type Ignore Categories (Current State)
| Category | Count | Resolution Strategy |
|----------|-------|---------------------|
| `[attr-defined]` | 19 | Add type stubs or Protocol types |
| `[union-attr]` | 16 | Use type guards or narrowing |
| `[misc]` | 10 | Case-by-case analysis |
| `[assignment]` | 10 | Fix type annotations |
| `[arg-type]` | 9 | Fix function signatures |
| `[return-value]` | 8 | Add proper return types |
| Bare (no code) | 26 | Require specific error codes |
| Other | 28 | Case-by-case analysis |

### Exception Handler Categories
| Pattern | Typical Usage | Resolution |
|---------|---------------|------------|
| GUI thread safety | Qt signal handling | Keep with documentation |
| Rust fallback | PyO3 bridge errors | Use specific Rust exceptions |
| File I/O | Resource access | Use `OSError`, `IOError` |
| Network | HTTP operations | Use specific HTTP exceptions |
| Catch-all | Unknown origin | Audit and specialize |

## Impact
- Affected specs: `code-organization` (new type safety requirements)
- Affected code: `ClassicLib/`, `src/`, entry points
- Improved static analysis coverage (mypy, pyright)
- Better IDE autocompletion and error detection
- Reduced silent failures from overly broad exception handling

## Risks
- **Low**: Some legitimate `type: ignore` cases exist (Qt bindings, dynamic imports)
- **Medium**: Exception handler changes may affect error propagation
- **Mitigation**: Implement changes incrementally with test coverage verification

## Success Criteria
- `# type: ignore` comments reduced to <40 (legitimate cases documented)
- All remaining `type: ignore` use specific error codes (no bare ignores)
- `except Exception` reduced to <15 (GUI-only or explicitly documented)
- All `pass` statements have explicit comments or proper implementations
- mypy passes with stricter configuration
