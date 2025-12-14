# Tasks: Reduce Type Safety Technical Debt

## 1. Inventory and Analysis
- [ ] 1.1 Generate inventory of all `# type: ignore` comments with file paths and line numbers
- [ ] 1.2 Categorize type ignores by error code (bare, attr-defined, union-attr, etc.)
- [ ] 1.3 Generate inventory of all `except Exception` handlers
- [ ] 1.4 Categorize exception handlers by context (GUI, entry point, business logic)
- [ ] 1.5 Generate inventory of all `pass` statements
- [ ] 1.6 Categorize pass statements (abstract, no-op, incomplete)

## 2. Fix Bare Type Ignores (26 instances)
- [ ] 2.1 Audit bare `# type: ignore` in `ClassicLib/Interface/` (Qt-related)
- [ ] 2.2 Add specific error codes to bare ignores in `ClassicLib/FileIO/`
- [ ] 2.3 Add specific error codes to bare ignores in `ClassicLib/Database/`
- [ ] 2.4 Add specific error codes to remaining bare ignores
- [ ] 2.5 Update mypy configuration to require error codes (`warn_unused_ignores = true`)

## 3. Reduce Fixable Type Ignores
- [ ] 3.1 Fix `[assignment]` issues in conditional imports (10 instances)
- [ ] 3.2 Fix `[return-value]` issues with proper return type annotations (8 instances)
- [ ] 3.3 Fix `[arg-type]` issues with correct function signatures (9 instances)
- [ ] 3.4 Add type guards for `[union-attr]` issues (16 instances)
- [ ] 3.5 Evaluate `[attr-defined]` issues - add stubs or protocols (19 instances)
- [ ] 3.6 Add explanatory comments to remaining legitimate ignores

## 4. Exception Handler Audit
- [ ] 4.1 Review and document GUI worker exception handlers (keep with noqa)
- [ ] 4.2 Review and document top-level entry point handlers
- [ ] 4.3 Replace broad handlers in `ClassicLib/Database/` with specific types
- [ ] 4.4 Replace broad handlers in `ClassicLib/Interface/` non-worker code
- [ ] 4.5 Replace broad handlers in `ClassicLib/rust/` with Rust exception types
- [ ] 4.6 Add `# noqa: BLE001` comments to legitimate broad handlers

## 5. Pass Statement Cleanup
- [ ] 5.1 Audit abstract-like methods - replace with `raise NotImplementedError`
- [ ] 5.2 Audit empty exception handlers - add logging or comments
- [ ] 5.3 Audit placeholder implementations - complete or add TODO
- [ ] 5.4 Add comments to intentional no-op pass statements

## 6. Dynamic Code Audit
- [ ] 6.1 Review `globals()` usage in `ClassicLib/rust/__init__.py`
- [ ] 6.2 Document or refactor dynamic feature detection pattern
- [ ] 6.3 Verify no `eval()` or `exec()` in production code

## 7. Validation
- [ ] 7.1 Run full mypy check with updated configuration
- [ ] 7.2 Run ruff check for BLE001 violations
- [ ] 7.3 Run full pytest suite to verify no behavioral changes
- [ ] 7.4 Update CI configuration if mypy strictness changes

## Dependencies
- Tasks in Phase 2-6 can be done in parallel
- Phase 7 validation depends on all other phases

## Verification Commands
```bash
# Count remaining type ignores
grep -rn "# type: ignore" --include="*.py" ClassicLib/ src/ CLASSIC_*.py | wc -l

# Count bare type ignores (target: 0)
grep -rn "# type: ignore$" --include="*.py" ClassicLib/ src/ CLASSIC_*.py | wc -l

# Count except Exception (target: <15)
grep -rn "except Exception" --include="*.py" ClassicLib/ src/ CLASSIC_*.py | wc -l

# Run mypy
uv run mypy ClassicLib/ src/

# Run tests
uv run pytest -n auto -m "unit and not slow"
```
