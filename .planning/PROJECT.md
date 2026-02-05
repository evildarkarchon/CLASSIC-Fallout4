# CLASSIC

## Current Milestone: (None — milestone complete)

**Previous:** v8.3.0 Performance & Polish — shipped 2026-02-05

---

# CLASSIC Rust Migration

## What This Is

A Rust-first desktop application (CLASSIC — Crash Log Auto Scanner & Setup Integrity Checker) that analyzes crash logs from Bethesda games (Fallout 4, Skyrim). Python serves as a thin UI shell (PySide6/Qt GUI) while Rust owns ALL business logic through PyO3 bindings. Performance is systematically measured via Criterion benchmarks with CI regression detection.

## Core Value

Python is the UI, Rust is the engine — every piece of business logic lives in Rust `-core` crates, Python only handles presentation and user interaction.

## Current State (After v8.3.0)

**Architecture achieved:**
- All scanning orchestration routes through Rust OrchestratorCore
- All game detection routes through Rust GamePathFinder
- All report generation routes through Rust ReportGenerator/ReportComposer
- All settings loading routes through Rust classic-settings with DashMap cache
- 7 Python analyzer files deleted, factory returns Rust components directly
- 19 Rust modules bundled in PyInstaller build
- 77+ Criterion benchmarks with statistical analysis
- CI automatically detects performance regressions (>10% threshold)

**Codebase metrics:**
- Python: ~88,594 LOC (ClassicLib/ - UI shell, integration layer)
- Rust: ~65,277+ LOC (rust/ - all business logic)
- Benchmarks: 77+ Criterion benchmarks across yaml-core, scanlog-core, file-io-core
- Tests: 3,849 passing with Rust as primary code path

**Tech stack:** Python 3.12+, PySide6/Qt, Rust (PyO3 0.27), tokio async runtime, DashMap, Criterion

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
- ✓ Migrate scanning orchestration to Rust — v8.2.0-part2
- ✓ Migrate game detection to Rust — v8.2.0-part2
- ✓ Migrate report generation to Rust — v8.2.0-part2
- ✓ Migrate settings management to Rust — v8.2.0-part2
- ✓ Reduce Python to UI-only code — v8.2.0-part2
- ✓ Benchmarks execute in release mode with statistical aggregation — v8.3.0
- ✓ CI pipeline detects performance regressions (>10% threshold) — v8.3.0
- ✓ Rust operations >1ms release Python GIL — v8.3.0
- ✓ Flamegraph and py-spy profiling available — v8.3.0
- ✓ DashMap cache hit rates instrumented — v8.3.0
- ✓ test_clear_cache parallel test pollution fixed — v8.3.0
- ✓ classic_settings() path resolution fixed — v8.3.0

### Active

(None — milestone complete, next milestone not yet started)

### Out of Scope

- GUI framework migration — Keep PySide6/Qt, don't migrate to Rust GUI (egui/iced)
- New user-facing features — Migration only, no new capabilities
- TUI migration — Ratatui TUI is already Rust-native
- i18n/localization — Future scope, stick to English strings
- HTML/RTF report output — Markdown is standard
- Steam API integration — Rely on registry/XSE log

## Context

**Shipped v8.3.0** with comprehensive performance infrastructure:
- 77+ Criterion benchmarks with statistical output
- CI regression detection (10% threshold, PR comments)
- GIL release audit (65 without_gil occurrences)
- Profiling tooling (flamegraph, py-spy, dhat)
- O(1) membership optimization in Python

**Known issues:**
- py-spy 0.4.1 incompatible with Python 3.14 (limits native frame profiling)

**Tech debt:**
- Report parity: 20 tests identify true Rust-Python differences (by design)

## Constraints

- **Behavioral parity**: App must work identically after migration (achieved)
- **Test coverage**: Existing tests must pass; add Rust integration tests for migrated logic
- **TDD required**: All changes follow red-green-refactor per project standards
- **GUI stays Python**: PySide6/Qt remains, only business logic migrates
- **Incremental migration**: Each component migrates fully before next (no half-migrated state)
- **PyO3 patterns**: Business logic in `-core` crates, PyO3 adapters in `-py` crates
- **Performance baselines**: Optimizations must be validated against benchmarks

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Clean up before migrating to Rust | Can't migrate cleanly if you don't know what's live vs. dead | ✓ Good — removed 11,993 net lines, clear ownership |
| Full-stack cleanup (Python + Rust) | Redundancies exist on both sides of the boundary | ✓ Good — 960-line acceleration pkg removed, Rust crates audited |
| Improvements welcome during cleanup | Rigid "identical behavior" would prevent simplification | ✓ Good — enabled fallback removal, DISABLE_RUST elimination |
| Future end state: Rust as engine, Python as GUI/glue | Informs which direction ownership should consolidate toward | ✓ Good — v8.2.0-part2 achieved this |
| 5-phase bottom-up approach (v1.0) | Dead code first, fallback pruning last (irreversible) | ✓ Good — each phase unblocked the next safely |
| lru_cache(maxsize=1) for global flags | Testable via cache_clear(), no mutable state | ✓ Good — 19+ globals test-friendly |
| 13 Protocol types for factory contracts | Static analysis catches errors at type-check time | ✓ Good — pyright 0 errors |
| Thin delegation pattern for wrappers | convert args → call Rust → convert return | ✓ Good — 60-75% wrapper reduction |
| RuntimeError for missing Rust | Fail-fast, no silent degradation | ✓ Good — clear errors vs silent fallback |
| validate_rust_modules() at startup | Early failure detection before user interaction | ✓ Good — catches missing modules immediately |
| Rust-only, hard fail | No Python fallback for any migrated component | ✓ Good — clean architecture |
| VR indicator removal | VR detection still works, just no display text | ✓ Good — simplified reports |
| Delete Python orchestrators entirely | Not deprecate-first, immediate removal | ✓ Good — 1,223 lines removed cleanly |
| asyncio.to_thread() for Rust batch processing | Avoid blocking event loop in async Python | ✓ Good — smooth async integration |
| Arc<AtomicBool> for cancellation | Simpler than CancellationToken for between-logs checking | ✓ Good — clean Rust async pattern |
| 1ms threshold for GIL release | Operations >1ms benefit from parallelism; faster ones don't justify overhead | ✓ Good — clear guideline |
| Quick/thorough benchmark modes | BENCH_MODE env var controls depth (50 vs 200 samples) | ✓ Good — flexible for dev vs CI |
| Shared benchmark config via #[path] | Benchmark utilities shared without crate dependency | ✓ Good — standard Rust pattern |
| serial_test for cache-touching tests | Prevents parallel test pollution in global state tests | ✓ Good — BUG-01 fixed |
| ResourceLoader.get_data_directory().parent as root | CWD-independent path resolution | ✓ Good — BUG-02 fixed |
| Python-first optimization focus | Profiling showed 86% threading overhead, 0.3% Rust FFI | ✓ Good — right ROI |
| ready_for_review trigger for CI benchmarks | Reduces noise vs all PR events | ✓ Good — less CI churn |
| 5% warning / 10% failure thresholds | Balance sensitivity with noise tolerance | ✓ Good — actionable feedback |

---
*Last updated: 2026-02-05 after v8.3.0 milestone*
