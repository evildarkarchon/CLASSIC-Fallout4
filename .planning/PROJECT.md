# CLASSIC

## Current Milestone: v9.1.0-consolidation Crate Consolidation

**Goal:** Reduce workspace granularity by merging 3 pairs of crates (19 → 16), updating all binding surfaces and parity gates, with zero functional changes.

**Status:** Phase 5 complete — remaining consolidation audit debt is closed, and the docs, verification artifacts, and Node parity contract surfaces now match the live one-tier baseline.

**Target features:**
- Merge `classic-yaml-core` into `classic-settings-core` (unify YAML loading/caching)
- Merge `classic-crashgen-settings-core` into `classic-config-core` (absorb single-consumer rule model)
- Redistribute constants ownership across `classic-version-registry-core` (Fallout4Version, NULL_VERSION), `classic-settings-core` (YamlFile, settings constants), and `classic-shared-core` (GameId) by semantic domain
- Update all binding crates (C++, Node, Python) for changed import paths
- All three parity gates (CXX, Python, Node) pass at zero drift after consolidation

## What This Is

The CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) codebase: a Rust-core / multi-binding (C++, Python, Node) workspace with native CLI/GUI/TUI frontends for analyzing Fallout 4 / Bethesda crash logs.

## Core Value

The Rust workspace has minimal, well-bounded crates with no redundant boundaries — every crate earns its compilation unit, and all binding surfaces remain at full parity with zero drift.

## Requirements

### Validated

- ✓ Layered Rust core with thin multi-language adapter surfaces — existing
- ✓ Single shared Tokio runtime (ONE RUNTIME RULE) — existing
- ✓ C++, Python, and Node.js binding surfaces delegating to `-core` crates — existing
- ✓ Windows-native C++ frontends (CLI + Qt GUI) via CXX bridge — existing
- ✓ 16 business-logic `-core` crates with no PyO3 dependencies — v9.1.0-consolidation Phases 1-3 (started at 19, yaml-core merged in Phase 1 -> 18, crashgen-settings-core merged in Phase 2 -> 17, constants-core redistributed in Phase 3 -> 16)
- ✓ Parity tooling for Node and Python bindings — existing
- ✓ All deprecated API callers migrated with deprecation warnings — v9.1.0-bugfixes Phase 1
- ✓ Phase 1 deprecated API migration closure evidence refreshed — v9.1.0-bugfixes Phase 9
- ✓ All deprecated APIs removed (parse_segments, parse_segments_parallel, is_outdated) — v9.1.0-bugfixes Phase 2
- ✓ Dead code removed (SEGMENT_BOUNDARIES, YamlFormatConfig, PluginAnalyzer.case_cache, PyGpuDetector.inner) — v9.1.0-bugfixes Phase 2
- ✓ Legacy `scan_all_settings_legacy_bucketed` fallback eliminated with assertion test — v9.1.0-bugfixes Phase 2
- ✓ FCX global state reset is blocking, typed, and contention-tested — v9.1.0-bugfixes Phase 3
- ✓ C++ bridge exposes explicit FCX reset and auto-resets before scan sessions — v9.1.0-bugfixes Phase 3
- ✓ Node bindings expose FCX reset plus structured issue inspection — v9.1.0-bugfixes Phase 3
- ✓ YAML, settings, and hash caches use bounded `quick_cache` eviction (128/64/1024) — v9.1.0-bugfixes Phase 4
- ✓ YAML, settings, and hash cache stats expose canonical five-field contract across all bindings — v9.1.0-bugfixes Phase 4
- ✓ Large-file mmap reads use `MmapOptions::map_copy_read_only()` — v9.1.0-bugfixes Phase 6
- ✓ Owned workspace lazy statics use `std::sync::LazyLock`/`OnceLock` — v9.1.0-bugfixes Phase 7
- ✓ Wire up `construct_proton_docs_path` to Linux docs-path discovery — v9.1.0-bugfixes Phase 8/11
- ✓ Promote `winreg` and `phf` to workspace dependencies — v9.1.0-bugfixes Phase 8/11
- ✓ Document or remove `zerovec` workaround dependency — v9.1.0-bugfixes Phase 8/11
- ✓ Commit or document Node `index.d.ts` build-first requirement — v9.1.0-bugfixes Phase 8/11
- ✓ Add test coverage: Linux Proton path — v9.1.0-bugfixes Phase 8/11
- ✓ Migrate Python FormID analyzer away from legacy map format with deprecation warnings — v9.1.0-bugfixes Phase 1/9
- ✓ Cache compiled regex patterns in mod detector hot paths — v9.1.0-bugfixes Phase 5
- ✓ Replace per-call `LogParser::new` in C++ bridge with cached parser — v9.1.0-bugfixes Phase 5/10
- ✓ Replace per-entry regex in `detect_mods_important` with AhoCorasick — v9.1.0-bugfixes Phase 5
- ✓ Add before/after criterion benchmarks for performance improvements — v9.1.0-bugfixes Phase 5/6
- ✓ Python Tier-1/Tier-2 collapsed into the current one-tier parity contract (historical v9.1.0-bindings note: the old `deferred_total == 0` target was achieved during Phase 3)
- ✓ Node Tier-1/Tier-2 collapsed into one enforced contract with no deferred owners remaining — v9.1.0-bindings Phase 4
- ✓ First-class C++ bridge parity gate with baseline + diff + CI enforcement — v9.1.0-bindings Phases 1+5
- ✓ C++ bridge exposes full surface of every shared Rust crate (316 entries across 19 modules) — v9.1.0-bindings Phase 2
- ✓ Node binding gains PE-version extraction parity — v9.1.0-bindings Phase 4
- ✓ Python binding gains explicit `classic_shared` runtime helpers — v9.1.0-bindings Phase 3
- ✓ Per-binding error-contract conventions documented — v9.1.0-bindings Phase 6
- ✓ CI runs Python, Node, and C++ parity gates on every PR — v9.1.0-bindings Phase 5
- ✓ `binding-parity-overview.md` rewritten as harmony-achieved reference — v9.1.0-bindings Phase 6
- ✓ Tier-2 backlog/governance/manifest files deleted — v9.1.0-bindings Phase 6
- ✓ Single source-of-truth parity policy doc added — v9.1.0-bindings Phase 6
- ✓ Merge classic-yaml-core into classic-settings-core — v9.1.0-consolidation Phase 1
- ✓ Merge classic-crashgen-settings-core into classic-config-core — v9.1.0-consolidation Phase 2
- ✓ Redistribute constants ownership across version-registry-core, settings-core, and shared-core — v9.1.0-consolidation Phase 3
- ✓ Update all binding crates for changed import paths — v9.1.0-consolidation Phases 1-3
- ✓ All three parity gates pass at zero drift after consolidation, with closure evidence recorded in `04-VERIFICATION.md` — v9.1.0-consolidation Phase 4

### Active

- None for the active v9.1.0-consolidation milestone scope.

### Out of Scope

- TUI-specific dependencies (ratatui, arboard, crossterm, open) workspace promotion — local to classic-tui, not shared
- VersionRegistry singleton reload — OnceLock design is intentional; process-restart isolation is acceptable
- CXX bridge `unsafe extern "C++"` — CXX framework manages this; no action needed beyond version upgrades
- Major binding API redesigns — parity is achieved; future redesigns would be a new initiative
- CI-04 branch protection — user-deferred; can be configured manually when needed

## Context

- All business logic lives in Rust `-core` crates under `ClassicLib-rs/business-logic/`
- Three binding surfaces: C++ (CXX), Python (PyO3), Node (NAPI-RS) — all at full parity
- Three CI-enforced parity gates prevent drift on all binding surfaces
- CXX bridge surface: 316 entries across 19 modules
- Python parity contract: one enforced tier with zero drift and no stale tracked artifacts accepted at closure
- Node parity contract: one enforced tier; verify with `bun run parity:gate` and refresh only with `bun run parity:gate:update-baseline` when drift is intentional
- Codebase map from 2026-04-04 at `.planning/codebase/CONCERNS.md` — all actionable concerns resolved across v9.1.0-bugfixes and v9.1.0-bindings
- v9.1.0-consolidation Phase 4 closed with green docs, parity, workspace, and native wrapper evidence in `.planning/phases/04-gate-validation-documentation/04-VERIFICATION.md`
- v9.1.0-consolidation Phase 5 closed the remaining audit debt: top-level docs routing, Phase 3 verification bookkeeping, and Node parity contract artifacts now agree with the live 705-row one-tier baseline

## Constraints

- **Platform**: Native C++ targets are Windows-only (MSVC x64); Rust workspace is cross-platform at source level
- **Runtime**: Single shared Tokio runtime — no new runtimes
- **Bindings**: All binding changes must pass existing parity gates (`check_parity_gate.py` for Python, `bun run parity:gate` for Node, `check_parity_gate.py` for CXX); only use refresh commands when source-backed drift is intentional
- **Testing**: Use PowerShell build wrappers for C++ tests, never raw ctest
- **Parity**: One-tier policy — new public Rust APIs must be exposed in all three bindings before CI passes

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Switch mmap to map_copy_read_only() | TOCTOU safety outweighs potential perf cost | ✓ v9.1.0-bugfixes Phase 6 |
| Keep Proton path code, wire it up | Linux support is planned; don't delete partial work | ✓ v9.1.0-bugfixes Phase 8/11 |
| Bounded `quick_cache` eviction for caches | Bounded memory for long-running processes | ✓ v9.1.0-bugfixes Phase 4 |
| Standardize owned lazy init on std primitives | `LazyLock`/`OnceLock` stable in MSRV | ✓ v9.1.0-bugfixes Phase 7 |
| Promote only shared deps to workspace | TUI deps are local; workspace promotion adds overhead for no benefit | ✓ v9.1.0-bugfixes Phase 8 |
| Before/after benchmarks for perf work | Criterion benchmarks become regression guards | ✓ v9.1.0-bugfixes Phase 5/6 |
| Use bounded `LazyLock<quick_cache::Cache>` for input-derived regexes | Repo-standard pattern; bounded caches own input-derived regexes | ✓ v9.1.0-bugfixes Phase 5/10 |
| Treat FCX `Unnecessary` as success across bindings | No-op reset stays benign without breaking failure handling | ✓ v9.1.0-bugfixes Phase 3 |
| In-place verification refresh for gap-closure phases | Parent phase verification stays the single source of truth | ✓ v9.1.0-bugfixes Phase 9/10/11 |
| Full bindings parity: collapse Tier-1/Tier-2 and add C++ gate | Tier-2 deferral was tactical; user goal is harmony with drift prevention | ✓ v9.1.0-bindings Phases 1-6 |
| Delete (not empty) Tier-2 governance files | Active files would leak back into discussions | ✓ v9.1.0-bindings Phase 6 |

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
*Last updated: 2026-04-12 after Phase 5 milestone cleanup closure*
