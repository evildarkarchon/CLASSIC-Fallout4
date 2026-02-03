# CLASSIC Rust Migration

## What This Is

A Rust-first desktop application (CLASSIC — Crash Log Auto Scanner & Setup Integrity Checker) that analyzes crash logs from Bethesda games (Fallout 4, Skyrim). Python serves as a thin UI shell (PySide6/Qt GUI) while Rust owns ALL business logic through PyO3 bindings. The v1.0 cleanup established clear ownership boundaries; v8.2.0-part2 completes the migration.

## Core Value

Python is the UI, Rust is the engine — every piece of business logic lives in Rust `-core` crates, Python only handles presentation and user interaction.

## Current Milestone: v8.2.0-part2 Rust Migration

**Goal:** Migrate all remaining Python business logic to Rust, making Python a thin UI shell.

**Target features:**
- Scanning orchestration moved to Rust (OrchestratorCore replacement)
- Game detection migrated to Rust (path detection, XSE/ENB checking)
- Report generation in Rust (markdown output)
- Settings management in Rust (configuration loading/saving)
- Python reduced to: GUI widgets, event handling, PyO3 call sites

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

- [ ] Migrate scanning orchestration to Rust — v8.2.0-part2
- [ ] Migrate game detection to Rust — v8.2.0-part2
- [ ] Migrate report generation to Rust — v8.2.0-part2
- [ ] Migrate settings management to Rust — v8.2.0-part2
- [ ] Reduce Python to UI-only code — v8.2.0-part2

### Out of Scope

- GUI framework migration — Keep PySide6/Qt, don't migrate to Rust GUI (egui/iced)
- New user-facing features — Migration only, no new capabilities
- TUI migration — Ratatui TUI is already Rust-native
- Performance benchmarking — Migration correctness first, optimization later

## Context

**Starting point:** 48,342 lines Python (ClassicLib/) after v1.0 cleanup.
**Tech stack:** Python 3.12+, PySide6, Rust (PyO3 0.27), uv package manager.
**Architecture:** Single flat factory.py with 13 Protocol types, thin adapter wrappers, fail-fast RuntimeError on missing Rust.
**Migration targets:**
- `ClassicLib/ScanGame/` — Game detection, path finding, integrity checks
- `ClassicLib/ScanLog/` — Crash log orchestration (Parser already Rust)
- `ClassicLib/Report/` — Markdown report generation
- `ClassicLib/io/yaml/` — Settings loading (YAML parsing already Rust)
**Known issues (pre-existing):**
- classic-yaml-core test_clear_cache failure (cache size assertion)
- GUI file path resolution bug in classic_settings() (relative path)
- cache.py line 431: return {} metrics placeholder

## Constraints

- **Behavioral parity**: App must work identically after migration
- **Test coverage**: Existing tests must pass; add Rust integration tests for migrated logic
- **TDD required**: All changes follow red-green-refactor per project standards
- **GUI stays Python**: PySide6/Qt remains, only business logic migrates
- **Incremental migration**: Each component migrates fully before next (no half-migrated state)
- **PyO3 patterns**: Business logic in `-core` crates, PyO3 adapters in `-py` crates

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
*Last updated: 2026-02-02 after v8.2.0-part2 milestone started*
