# Phase 2: Integration Layer Simplification - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Flatten the Python-Rust integration boundary: collapse the multi-layer factory/detector/status subpackage into a single `factory.py` module using try-import, remove the entire acceleration coordinator package, and narrow factory return types from `Any` to specific Protocol-based interfaces. This phase does NOT add new Rust components or change fallback behavior — it simplifies the existing integration layer's structure and type contracts.

</domain>

<decisions>
## Implementation Decisions

### Factory collapse strategy
- Collapse `factory/` subpackage (detector, status, etc.) into a single `factory.py` module
- Protocol classes kept as inline documentation in factory.py — documents what each Rust component must provide
- No caching: each factory function does a fresh try-import on every call (Python's module cache handles performance)
- Detection functions (is_rust_available, has_yaml_support, etc.) removed — callers use try-get pattern: call the factory function, handle failure
- `print_rust_status()` diagnostic utility removed entirely — not needed in production
- Old import paths updated immediately at all call sites — no temporary re-export shims or deprecation wrappers

### Acceleration removal scope
- Clean full delete of entire `ClassicLib/acceleration/` directory (coordinator, metrics, types, workload)
- No concepts from acceleration need to survive or be preserved elsewhere
- Full caller audit required before deletion — systematically trace every import and reference
- If callers depend on acceleration types/coordinator, refactor those callers in this phase to remove the dependency
- No workload-aware routing logic preserved — factory simply returns what's available

### Type narrowing approach
- Factory return types use Protocol classes — both Rust and Python fallback implementations satisfy the same Protocol
- Protocol classes live in a separate `integration/types.py` module, not in factory.py
- When neither Rust nor Python fallback is available, factory raises `ImportError` (fail loud, not Optional/None)
- Pyright enforcement on `factory.py` only (as success criteria requires) — don't expand to entire integration/ package

### Migration safety
- Two separate plans as roadmap suggests: 02-01 (factory collapse) then 02-02 (acceleration removal + type narrowing)
- Full test suite run after each plan for verification — run synchronously (`uv run pytest`) since parallel is currently unstable
- Fix-forward policy on test failures: keep the restructure, fix the failing test (most failures will be import path issues)
- All callers updated immediately — no intermediate compatibility states

</decisions>

<specifics>
## Specific Ideas

- Protocol classes serve dual purpose: type contracts for pyright AND documentation of what Rust components provide (decided to keep them earlier for "inline docs" value)
- The try-import-every-call pattern is intentionally simple — Python's `sys.modules` cache means repeated imports are essentially dict lookups, so custom caching adds complexity without meaningful performance gain
- Synchronous test runs (`uv run pytest` without `-n auto`) for verification — parallel execution is unstable at this time

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-integration-layer-simplification*
*Context gathered: 2026-02-01*
