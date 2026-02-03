# CLASSIC Codebase Cleanup

## What This Is

A hybrid Python-Rust desktop application (CLASSIC — Crash Log Auto Scanner & Setup Integrity Checker) that analyzes crash logs from Bethesda games (Fallout 4, Skyrim). After the v1.0 cleanup milestone, the codebase has clear single-ownership for every piece of business logic: Rust owns computation, Python owns UI and orchestration, with thin adapter wrappers at the boundary and fail-fast validation at startup.

## Core Value

Every piece of logic lives in exactly one place, and it's obvious where things belong — so future Rust migration is straightforward rather than archaeological.

## Requirements

### Validated

- ✓ Crash log scanning and analysis for Fallout 4 and Skyrim — existing
- ✓ GUI interface via PySide6/Qt with tabbed layout — existing
- ✓ CLI interface for headless/server operation — existing
- ✓ TUI interface via Textual (in development) — existing
- ✓ Rust acceleration for YAML parsing (15-30x speedup) — existing
- ✓ Rust acceleration for database operations (25x speedup) — existing
- ✓ Rust acceleration for crash log parsing (10-50x speedup) — existing
- ✓ Async-first architecture with AsyncBridge for GUI sync contexts — existing
- ✓ FormID analysis and mod conflict detection — existing
- ✓ Settings/INI scanning and duplicate config detection — existing
- ✓ Game path detection and XSE/ENB integrity checking — existing
- ✓ Report generation in markdown format — existing
- ✓ PyInstaller executable bundling for Windows distribution — existing
- ✓ Remove duplicate logic (Python/Rust parallel implementations) — v1.0
- ✓ Eliminate dead code (unused modules, functions, files) — v1.0
- ✓ Flatten overlapping abstractions (wrappers around wrappers) — v1.0
- ✓ Consolidate dual sync/async interfaces (remove deprecated sync wrappers) — v1.0
- ✓ Clean up Python-Rust boundary (stubs, bindings, fallback patterns) — v1.0
- ✓ Ensure clear single-owner for every piece of business logic — v1.0
- ✓ Reduce overall code surface area — v1.0
- ✓ Prepare clean separation points for future Rust migration — v1.0

### Active

(None — next milestone requirements defined via `/gsd:new-milestone`)

### Out of Scope

- New feature development during cleanup — cleanup only (completed)
- Rust migration of business logic — deferred to v2.0 milestone
- UI/UX changes — no user-visible changes unless simplification demands it
- Performance optimization — unless it falls out of removing redundancy

## Context

**Shipped v1.0** with 48,342 lines Python (ClassicLib/), ~23 hours wall clock.
**Tech stack:** Python 3.12+, PySide6, Rust (PyO3 0.27), uv package manager.
**Architecture:** Single flat factory.py with 13 Protocol types, thin adapter wrappers (60-75% reduced), fail-fast RuntimeError on missing Rust, validate_rust_modules() at startup.
**Known issues:**
- Pre-existing classic-yaml-core test_clear_cache failure (cache size assertion)
- Pre-existing GUI file path resolution bug in classic_settings() (relative path)
- cache.py line 431: return {} metrics placeholder (not implemented)
- _async_utils package kept for backward compatibility re-exports

## Constraints

- **Behavioral parity**: App must work identically after cleanup (improvements welcome where they simplify code)
- **Test coverage**: Existing tests must continue to pass; update tests to match new APIs rather than preserving old ones
- **Both languages**: Cleanup spans Python and Rust — neither is exempt
- **TDD required**: All changes follow red-green-refactor per project standards
- **No backward compatibility hacks**: If something is unused, delete it completely
- **Rust required**: No Python fallbacks — Rust modules must be present (fail-fast at startup)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Clean up before migrating to Rust | Can't migrate cleanly if you don't know what's live vs. dead | ✓ Good — removed 11,993 net lines, clear ownership |
| Full-stack cleanup (Python + Rust) | Redundancies exist on both sides of the boundary | ✓ Good — 960-line acceleration pkg removed, Rust crates audited |
| Improvements welcome during cleanup | Rigid "identical behavior" would prevent simplification | ✓ Good — enabled fallback removal, DISABLE_RUST elimination |
| Future end state: Rust as engine, Python as GUI/glue | Informs which direction ownership should consolidate toward | ✓ Good — v1.0 established clean separation points |
| 5-phase bottom-up approach | Dead code first, fallback pruning last (irreversible) | ✓ Good — each phase unblocked the next safely |
| lru_cache(maxsize=1) for global flags | Testable via cache_clear(), no mutable state | ✓ Good — 19+ globals test-friendly |
| 13 Protocol types for factory contracts | Static analysis catches errors at type-check time | ✓ Good — pyright 0 errors |
| Thin delegation pattern for wrappers | convert args → call Rust → convert return | ✓ Good — 60-75% wrapper reduction |
| RuntimeError for missing Rust | Fail-fast, no silent degradation | ✓ Good — clear errors vs silent fallback |
| validate_rust_modules() at startup | Early failure detection before user interaction | ✓ Good — catches missing modules immediately |

---
*Last updated: 2026-02-02 after v1.0 milestone*
