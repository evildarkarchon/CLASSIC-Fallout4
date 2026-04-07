# CLASSIC

## Current State

**Latest shipped milestone:** v9.1.0-bugfixes CLASSIC Codebase Health (2026-04-07)

The codebase is now in a healthier, audit-clean state: no dead code, no silent legacy fallbacks, no unbounded caches, hot-path regex/parser caching with Criterion proof, mmap TOCTOU safety, FCX state hardening across all bindings, canonical CacheStats contract, LazyLock consistency sweep, workspace dependency promotion, Linux Proton docs-path wiring, and committed Node `index.d.ts` governance with CI freshness gating.

## Next Milestone Goals

No phases planned yet. Use `/gsd:new-milestone` to start the next milestone cycle.

## What This Is

The CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) codebase: a Rust-core / multi-binding (C++, Python, Node) workspace with native CLI/GUI/TUI frontends for analyzing Fallout 4 / Bethesda crash logs.

## Core Value

Every concern identified in the codebase audit is resolved — no silent legacy paths, no dead code, no unbounded caches, and all binding surfaces expose consistent, complete APIs.

## Requirements

### Validated

- ✓ Layered Rust core with thin multi-language adapter surfaces — existing
- ✓ Single shared Tokio runtime (ONE RUNTIME RULE) — existing
- ✓ C++, Python, and Node.js binding surfaces delegating to `-core` crates — existing
- ✓ Windows-native C++ frontends (CLI + Qt GUI) via CXX bridge — existing
- ✓ 19 business-logic `-core` crates with no PyO3 dependencies — existing
- ✓ Parity tooling for Node and Python bindings — existing
- ✓ All deprecated API callers migrated with deprecation warnings — Validated in Phase 1: Deprecated API Migration
- ✓ Phase 1 deprecated API migration closure evidence refreshed and audit traceability reconciled — Validated in Phase 9: Deprecated API Verification Closure
- ✓ All deprecated APIs removed (parse_segments, parse_segments_parallel, is_outdated) — Validated in Phase 2: Dead Code Removal
- ✓ Dead code removed (SEGMENT_BOUNDARIES, YamlFormatConfig, PluginAnalyzer.case_cache, PyGpuDetector.inner) — Validated in Phase 2: Dead Code Removal
- ✓ Legacy `scan_all_settings_legacy_bucketed` fallback path eliminated with assertion test — Validated in Phase 2: Dead Code Removal
- ✓ FCX global state reset is blocking, typed, and contention-tested — Validated in Phase 3: FCX State Hardening
- ✓ C++ bridge exposes explicit FCX reset and auto-resets before scan sessions — Validated in Phase 3: FCX State Hardening
- ✓ Node bindings expose FCX reset plus structured issue inspection without same-process carryover — Validated in Phase 3: FCX State Hardening
- ✓ YAML, settings, and hash caches now use bounded `quick_cache` eviction with capacities 128/64/1024 — Validated in Phase 4: Bounded Cache Replacement
- ✓ YAML, settings, and hash cache stats now expose one canonical five-field contract across Rust, Node, Python, and C++ — Validated in Phase 4: Bounded Cache Replacement
- ✓ Large-file mmap reads use `MmapOptions::map_copy_read_only()` with validated Windows benchmark proof — Validated in Phase 6: mmap TOCTOU Safety
- ✓ Owned workspace lazy statics now use `std::sync::LazyLock`, and the remaining scanlog `OnceCell` cache uses `std::sync::OnceLock` with direct `once_cell` manifests removed — Validated in Phase 7: Consistency Sweep
- ✓ Wire up `construct_proton_docs_path` to Linux docs-path discovery workflow (not delete) — Validated in Phase 8 / Phase 11
- ✓ Promote `winreg` and `phf` to workspace dependencies — Validated in Phase 8 / Phase 11
- ✓ Document or remove `zerovec` workaround dependency — Validated in Phase 8 / Phase 11
- ✓ Commit or document Node `index.d.ts` build-first requirement — Validated in Phase 8 / Phase 11
- ✓ Add test coverage: Linux Proton path — Validated in Phase 8 / Phase 11
- ✓ Migrate Python FormID analyzer away from legacy map format with deprecation warnings — Validated in Phase 1 / Phase 9
- ✓ Cache compiled regex patterns in mod detector hot paths (detect_mods_single/double/batch/important) — Validated in Phase 5
- ✓ Replace per-call `LogParser::new` in C++ bridge `detect_crash_pattern` with cached parser — Validated in Phase 5 / Phase 10
- ✓ Replace per-entry regex in `detect_mods_important` with AhoCorasick — Validated in Phase 5
- ✓ Add before/after criterion benchmarks for performance improvements — Validated in Phase 5 / Phase 6

### Active

(None — all v9.1.0-bugfixes requirements shipped. Run `/gsd:new-milestone` to define the next cycle.)

### Out of Scope

- TUI-specific dependencies (ratatui, arboard, crossterm, open) workspace promotion — these are local to classic-tui and not shared
- VersionRegistry singleton reload — OnceLock design is intentional; process-restart isolation is acceptable
- CXX bridge `unsafe extern "C++"` — CXX framework manages this; no action needed beyond version upgrades
- Major binding API redesigns — this milestone fixes parity gaps and deprecations, not wholesale API changes
- New feature development — this is purely a health/hardening milestone

## Context

- All business logic lives in Rust `-core` crates under `ClassicLib-rs/business-logic/`
- Three binding surfaces: C++ (CXX), Python (PyO3), Node (NAPI-RS)
- Codebase map completed 2026-04-04 with detailed CONCERNS.md at `.planning/codebase/CONCERNS.md`
- Performance concerns center on `classic-scanlog-core` mod_detector and the C++ bridge scanner
- FCX (FormID Cross-reference) handler is a process-wide singleton with state management issues across binding boundaries
- The `detect_mods_important` function is the most performance-critical path — compiles one regex per entry per call
- Proton/Linux path support is partially implemented; should be wired up rather than removed

## Constraints

- **Platform**: Native C++ targets are Windows-only (MSVC x64); Rust workspace is cross-platform at source level
- **Runtime**: Single shared Tokio runtime — no new runtimes
- **Bindings**: All binding changes must pass existing parity gates (`check_parity_gate.py` for Python, `parity:gate:local` for Node)
- **Testing**: Use PowerShell build wrappers for C++ tests, never raw ctest
- **Backwards compat**: Python FormID legacy map format gets deprecation warning first, not immediate removal

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Switch mmap to map_copy_read_only() | TOCTOU safety outweighs potential perf cost for >1MB files while preserving a conservative snapshot-style large-file read path | ✓ Validated in Phase 6 |
| Keep Proton path code, wire it up | Linux support is planned; don't delete partial work | ✓ Validated in Phase 8 / Phase 11 |
| Bounded `quick_cache` eviction for caches | Bounded memory is more important than unlimited cache hits for long-running processes, and Phase 4 standardizes on the repo's existing `quick_cache` implementation | ✓ Validated in Phase 4 |
| Standardize owned lazy initialization on std primitives | `LazyLock`/`OnceLock` are stable in the repo MSRV and remove the need for direct `once_cell` ownership in workspace code | ✓ Validated in Phase 7 |
| Promote only shared deps to workspace | TUI deps are local to one crate; workspace promotion adds management overhead for no benefit | ✓ Validated in Phase 8 (winreg + phf only) |
| Before/after benchmarks for perf work | Prove improvements with data; criterion benchmarks become regression guards | ✓ Validated in Phase 5 / Phase 6 |
| Binding parity in-scope | FCX and deprecated API issues span core + bindings; splitting would leave incomplete fixes | ✓ Validated in Phases 1, 3, 4, 8 |
| Use bounded `LazyLock<quick_cache::Cache>` for input-derived alternation regexes (CONS-04 interpretation) | Repo-standard pattern; bounded caches own input-derived regexes while only true constants belong on dedicated `LazyLock` statics | ✓ Validated in Phase 5 / Phase 10 |
| Treat FCX `Unnecessary` as success across bindings | Lets binding code keep the no-op reset path benign without breaking explicit-failure handling | ✓ Validated in Phase 3 |
| In-place verification refresh for gap-closure phases (9/10/11) | Avoids parallel verification artifacts; the parent phase verification stays the single source of truth | ✓ Validated in Phase 9, 10, 11 |
| Internal milestone label `v1.0` renamed to `v9.1.0-bugfixes` at ship time | Keeps the project's existing v8.x version progression contiguous and avoids the duplicate v1.0 entry that would otherwise collide with the 2026-02 "Codebase Cleanup" milestone | ✓ Applied at v9.1.0-bugfixes ship 2026-04-07 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check -- still the right priority?
3. Audit Out of Scope -- reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-07 after v9.1.0-bugfixes milestone completion*
