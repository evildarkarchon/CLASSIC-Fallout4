# CLASSIC Codebase Cleanup

## What This Is

A cleanup and consolidation milestone for CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker), a hybrid Python-Rust desktop application that analyzes crash logs from Bethesda games. The goal is to remove redundancies — duplicate logic, dead code, and overlapping abstractions — across both Python and Rust layers, producing a codebase with clear ownership, smaller surface area, and clean separation that's ready for progressive Rust migration.

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
- ✓ Automatic Rust-to-Python fallback via factory pattern — existing
- ✓ Async-first architecture with AsyncBridge for GUI sync contexts — existing
- ✓ FormID analysis and mod conflict detection — existing
- ✓ Settings/INI scanning and duplicate config detection — existing
- ✓ Game path detection and XSE/ENB integrity checking — existing
- ✓ Report generation in markdown format — existing
- ✓ PyInstaller executable bundling for Windows distribution — existing

### Active

- [ ] Remove duplicate logic (Python/Rust parallel implementations where only one is needed)
- [ ] Eliminate dead code (unused modules, functions, files that have been superseded)
- [ ] Flatten overlapping abstractions (wrappers around wrappers, unnecessary indirection)
- [ ] Consolidate dual sync/async interfaces (remove deprecated sync wrappers)
- [ ] Clean up Python-Rust boundary (stubs, bindings, fallback patterns)
- [ ] Ensure clear single-owner for every piece of business logic
- [ ] Reduce overall code surface area
- [ ] Prepare clean separation points for future Rust migration

### Out of Scope

- New feature development — this milestone is cleanup only
- Rust migration of business logic — deferred to subsequent milestone
- UI/UX changes — no user-visible changes unless simplification demands it
- Performance optimization — unless it falls out of removing redundancy
- New Rust crates — no new crates, only cleaning existing ones

## Context

- CLASSIC has evolved organically with Rust acceleration layered in over time, creating parallel implementations
- The codebase map (`.planning/codebase/`) identifies specific concerns: dual interface patterns in FormIDAnalyzer, global mutable state, overlapping abstractions
- Known fragile areas: ConfigFileCache duplicate detection, AsyncBridge in GUI workers, global `_VERSION_WARNING_LOGGED` flag
- Existing tech debt: ConfigFileCache error handling, incomplete YAML cache path in Rust, sync wrappers documented as "GUI-only" but callable from anywhere
- Three-layer Rust architecture (foundation → business logic → python bindings) is sound but may have unused crates or stale bindings
- Python fallback implementations may be dead code where Rust equivalents are always available

## Constraints

- **Behavioral parity**: App must work identically after cleanup (improvements welcome where they simplify code)
- **Test coverage**: Existing tests must continue to pass; update tests to match new APIs rather than preserving old ones
- **Both languages**: Cleanup spans Python and Rust — neither is exempt
- **TDD required**: All changes follow red-green-refactor per project standards
- **No backward compatibility hacks**: If something is unused, delete it completely

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Clean up before migrating to Rust | Can't migrate cleanly if you don't know what's live vs. dead | — Pending |
| Full-stack cleanup (Python + Rust) | Redundancies exist on both sides of the boundary | — Pending |
| Improvements welcome during cleanup | Rigid "identical behavior" would prevent simplification | — Pending |
| Future end state: Rust as engine, Python as GUI/glue | Informs which direction ownership should consolidate toward | — Pending |

---
*Last updated: 2026-02-01 after initialization*
