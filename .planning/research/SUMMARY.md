# Project Research Summary

**Project:** CLASSIC Codebase Cleanup & Consolidation
**Domain:** Hybrid Python-Rust codebase maintenance and technical debt reduction
**Researched:** 2026-02-01
**Confidence:** HIGH

## Executive Summary

This research covers the cleanup and consolidation of CLASSIC, a mature hybrid Python 3.12+ / Rust desktop application for Bethesda game crash log analysis. The codebase has accumulated technical debt from progressive Rust migration: dual Python/Rust implementations, four-layer integration indirection, overlapping abstractions, and defensive detection infrastructure built for scenarios that no longer occur in production. The cleanup milestone aims to reduce what exists, not build new features.

The recommended approach is bottom-up incremental consolidation: start with low-risk dead code removal (deprecated modules, unused Rust stub crates), then simplify the integration layer (flatten four-layer factory/detector/wrapper stack to direct imports), thin out fat Python wrappers around Rust modules (move logic into Rust `-core` crates), and finally prune Python fallback implementations where Rust is proven stable. The tooling for this cleanup is already 80% installed (ruff, pyright, coverage, cargo clippy) with only vulture and cargo-machete needing to be added.

Key risks center on breaking hidden boundaries: removing "dead" Python fallbacks that are actually active in deployed PyInstaller builds (test with `CLASSIC_DISABLE_RUST=1`), breaking GUI async/sync boundaries when removing deprecated sync wrappers (requires manual GUI testing), breaking PyInstaller hidden imports when renaming modules (verify with test builds), singleton state leaks (requires comprehensive test fixture reset), and Rust crate dependency breakage (use `cargo tree --invert` before removal). The mitigation is phase gates: every structural change phase must pass full test suite, PyInstaller build verification, and GUI smoke testing before proceeding.

## Key Findings

### Recommended Stack

The project already has the core cleanup tooling installed. The main gaps are dedicated dead code detection tools and dependency analysis utilities that work on stable Rust.

**Core technologies:**
- **ruff 0.14.14** (installed): Unused imports (F401), unused variables (F841), unused arguments (ARG), commented-out code (ERA) — primary static analysis. Already configured and running in production.
- **vulture 2.14+** (needs install): Whole-program dead code detection — finds functions/classes/methods defined but never called across entire codebase. Ruff only catches unused within a single file; vulture performs cross-file analysis.
- **coverage 7.13.2** (installed): Branch coverage identifies untested/unreachable code paths — run comprehensive test suite with `--cov-report=html` to visually identify 0% coverage modules (prime deletion candidates).
- **pyright 1.1.408** (installed): Strict mode catches unreachable code after early returns and impossible type narrowings — complements static analysis with type-based dead code detection.
- **cargo clippy** (bundled): Rust dead code linting — workspace already has `unused = "deny"` which catches dead Rust code at compile time.
- **cargo-machete 0.7+** (needs install): Find unused Cargo dependencies on stable Rust — fast heuristic-based approach, works without nightly unlike cargo-udeps.

**Workflow integration:**
The cleanup uses tools in layers. Layer 1 (static analysis): vulture + ruff identify dead code candidates. Layer 2 (coverage): confirm candidates are truly dead by showing 0% test coverage. Layer 3 (cross-language audit): coverage-guided comparison of Python modules vs Rust equivalents identifies duplicate implementations. Layer 4 (validation): run full test suite + PyInstaller build + GUI smoke test after each removal to catch hidden dependencies.

### Expected Features

The cleanup milestone has clear deliverables measured by concrete metrics, not subjective code quality improvements. Features split into must-do (table stakes), should-do (high ROI for future migration), and anti-features (seem good but are harmful).

**Must have (table stakes):**
- **Remove FormIDAnalyzer sync wrapper** — 156 lines of dead code wrapping FormIDAnalyzerCore for a GUI mode that should use async directly. Documented as deprecated in its own docstring.
- **Remove Python fallback implementations** — 8 fallback files (`formid_py.py`, `parser_py.py`, `plugin_py.py`, etc.) exist for scenarios where Rust is unavailable, but Rust is always shipped in distribution. Creates double maintenance burden.
- **Eliminate global mutable state flags** — Module-level `global _VERSION_WARNING_LOGGED` and similar flags break test isolation. Already documented as fragile in CONCERNS.md.
- **Consolidate YAML sync/async split** — Parallel `ClassicLib/io/yaml/sync/` and `async_/` subdirectories with duplicate cache implementations. Two code paths for the same data.
- **Remove deprecated module references** — 11 files marked DEPRECATED. Deprecated code that remains becomes permanent.
- **Clean up global mutable state pattern** — 19 instances of `global _*` across ClassicLib. Categorize which are legitimate singletons, which are mutable flags to replace with instance state.
- **Simplify factory/detector/status layering** — Three overlapping abstraction layers for Rust detection with duplicate caching between `_components_cache` in factory and `_detection_cache` in detector.

**Should have (competitive):**
- **Establish clear module ownership boundaries** — After removing fallbacks, the three-layer indirection (rust/ wrappers + factory + detector) becomes unnecessary. Flatten to direct Rust imports with thin Python adapter.
- **Remove RustAcceleration coordinator singleton** — `ClassicLib/acceleration/` is an optimization framework (5 optimization levels, WorkloadCharacteristics, ComponentMetrics) that adds complexity without clear evidence of use.
- **Unify async entry patterns** — Remove `create_sync_wrapper` and transitional bridge helpers. Leave exactly two patterns: native async (CLI/TUI) and AsyncBridge (GUI).
- **Add dead code detection to CI** — Prevents regression. Without ongoing enforcement, deprecated/unused code will re-accumulate.
- **Type-narrow all `Any` returns from factory functions** — After removing fallbacks, factory return types can be narrowed to specific Rust types, enabling Pyright to catch errors.
- **Document post-cleanup integration contract** — Single-page reference for how Python calls Rust after cleanup: import pattern, error handling, type mapping. Prevents integration layer from re-growing organically.

**Defer (anti-features to avoid):**
- **Remove ALL Python fallbacks immediately** — Some fallback code serves as reference implementation and test oracle. Remove in phases: first for modules with comprehensive Rust tests (parser, formid, plugin), then modules needing verification (database, file_io).
- **Rewrite integration/factory layer from scratch** — Factory rewrite affects every import site simultaneously. High risk of subtle regressions. Simplify incrementally instead: remove fallback branches first, then inline simplified factories, then remove empty shell.
- **Convert all global state to dependency injection** — CLASSIC is a desktop app, not a web server. Some singletons (MessageHandler, GlobalRegistry, ThreadManager) are legitimate application-scoped singletons. Fix problematic globals (mutable flags, test-hostile caches) but keep legitimate singletons with `reset()` methods for test isolation.
- **Merge sync and async YAML into single module file** — Large merge creates massive diff that is hard to review and bisect. Consolidate cache implementations first, then remove sync convenience wrappers, then flatten directory structure. Three small PRs instead of one large one.
- **Remove `CLASSIC_DISABLE_RUST` environment variable** — Development and debugging still benefit from being able to disable Rust modules. Keep the env var but change behavior: instead of falling back to Python, log clear error and exit. Useful for diagnosing Rust loading issues.

### Architecture Approach

The current architecture has a four-layer integration stack between callers and Rust: Caller → factory (decides Rust/Python) → rust/ wrapper (Python class around PyO3 import) → -py crate (PyO3 adapter) → -core crate (pure Rust logic). Layers 1 and 2 are the consolidation target. The target state is direct imports: Caller → -py crate (thin PyO3 adapter) → -core crate (business logic).

**Major components:**
1. **Integration layer (ClassicLib/integration/)** — Four-layer stack with factory dispatch, detector caching, rust/ wrappers, and python/ fallbacks. Target: flatten to single-layer factory doing try-import with direct PyO3 class returns.
2. **Business logic (scanning/logs/, scanning/game/)** — Python orchestration calling Rust engines. Target: thin out Python wrappers, move logic into Rust `-core` crates.
3. **Data access (io/yaml, io/files, io/database)** — Already mostly Rust-accelerated and clean. Target: minimal changes, already well-architected.
4. **Rust engine (rust/business-logic/, rust/python-bindings/)** — 21 business-logic crates and 18 python-binding crates (39 total). Several appear to be stubs. Target: remove stub crates, audit for actual code vs. planning artifacts.

**Architectural patterns:**
- **Strangler Fig** — Gradually replace Python with Rust by routing through factory, then removing Python fallback once Rust is proven stable. Phase B (cleanup) identifies components where Rust always wins. Phase C removes Python fallback and simplifies factory.
- **Wrapper Thinning** — Move business logic OUT of `ClassicLib/integration/rust/` wrappers and INTO Rust `-core` crates. Several Rust wrappers are larger than the Python fallbacks they replace (file_io_rust.py at 39KB vs file_io_py.py at 18KB), indicating logic has leaked into wrong layer.
- **Interface Consolidation** — Remove sync wrappers and dual-interface patterns. Everything async. Wrap at entry points only (GUI uses AsyncBridge, CLI uses native async).
- **Factory Simplification Ladder** — Stage 1 (now): factory checks detection cache, imports conditionally. Stage 2 (cleanup target): factory imports Rust directly, catches ImportError only. Stage 3 (future): factory becomes re-export module. Stage 4 (end): factory removed, callers import Rust directly.

**Dual implementation inventory:**
Every component currently has both Rust and Python implementations. Key finding: several `rust/` wrappers have grown to contain significant Python business logic, defeating the purpose of Rust acceleration. Parser Rust wrapper is 15KB vs 8KB Python. FormID Rust wrapper is 16KB vs 12KB Python. FileIO Rust wrapper is 39KB vs 18KB Python (inverted). These fat wrappers should be thin adapters but have become a third location for business logic (alongside python/ fallbacks and -core crates).

### Critical Pitfalls

1. **Removing "dead" Python fallbacks that are active in deployed builds** — Python fallback appears dead because Rust is always available in dev. But in deployed PyInstaller builds, Rust extension loading can fail silently (DLL not found, ABI mismatch, missing redistributable). Factory returns fallback which no longer exists. App crashes for some users while working for developer. **Mitigation:** Run full test suite with `CLASSIC_DISABLE_RUST=1` before removing any fallback. For each factory function, explicitly decide "Is this fallback still needed?" and document. If fallback is removed, factory must raise clear error.

2. **Breaking PyInstaller hidden imports when renaming/moving modules** — Module moved, Python tests pass (pytest uses direct imports), but PyInstaller bundles based on `hiddenimports` in `CLASSIC.spec`. Renamed module not in bundle. App crashes at runtime with `ModuleNotFoundError` only in distributed executable. **Mitigation:** Maintain checklist for every module rename/move to update `CLASSIC.spec` hidden imports. Do test PyInstaller build after any cleanup phase. Treat spec file as first-class artifact updated in same commit as module restructuring.

3. **Singleton state leaks across cleanup boundaries** — Singletons (GlobalRegistry, MessageHandler, AsyncBridge, `_components_cache`) accumulate stale state references to removed/restructured code. Tests pass individually but fail in batch. `_VERSION_WARNING_LOGGED` already documented as fragile. **Mitigation:** Reset ALL singleton state between test runs. Add `reset_all_singletons()` test fixture that is `autouse=True`. When consolidating singletons, do it in single atomic step with all tests updated.

4. **Breaking async/sync boundary during sync wrapper removal** — Cleanup removes deprecated sync wrappers. But some call site deep in GUI layer was using sync wrapper from QThread worker context where `await` is not available and `asyncio.run()` would conflict with existing event loop. GUI freezes or deadlocks. **Mitigation:** Before removing any sync wrapper, trace ALL call sites using grep. For each, determine execution context (QThread? Qt main thread? async context?). Replace with appropriate async pattern. Test GUI functionality manually (deadlocks not caught by unit tests).

5. **Removing Rust crates that are depended on through Cargo workspace features** — Rust `-core` crate appears unused (no Python binding imports directly). Removed from `Cargo.toml` workspace members. But another `-core` crate depends on it via `[dependencies]`. Entire Rust workspace fails to build. **Mitigation:** Before removing any Rust crate, run `cargo tree -p classic-<name>-core --invert` to see what depends on it. Run `cargo build --workspace` after every crate removal. Check both -core and -py crate for each removal.

6. **Consolidating overlapping abstractions breaks integration layer contract** — Two abstractions (FileIOCore Python + classic_file_io Rust) merged into one. But factory expects specific interface (method names, parameter signatures, return types). Consolidated version has slightly different API. Python might return `pathlib.Path`, Rust returns `str`. Python might be async, Rust sync. **Mitigation:** Document interface contract for each factory function BEFORE consolidating. Use Protocol classes to define interface, verify both implementations satisfy it. Update factory and all callers in same PR.

7. **Lazy YAML import discipline breaks during module consolidation** — CLAUDE.md rule: "Import `yaml_settings`, `classic_settings` inside functions to avoid circular imports." During cleanup, developer adds top-level import of YAML settings because it looks cleaner. Circular import chain triggers at startup. **Mitigation:** Add comment on every lazy YAML import explaining circular dependency. During cleanup, keep lazy import pattern even if looks redundant. Test startup after any module consolidation to verify no circular imports.

## Implications for Roadmap

Based on combined research, cleanup should proceed bottom-up through dependency layers. Early phases are low-risk foundation work (dead code removal, tooling setup). Middle phases are core consolidation (integration layer simplification, wrapper thinning). Late phases are architecture changes (fallback removal, interface consolidation).

### Phase 1: Foundation Cleanup
**Rationale:** No dependencies, low risk. Sets up tooling and removes obvious dead code to reduce noise for later phases.
**Delivers:** Dead code detection in CI, deprecated modules removed, global mutable flags eliminated, singleton audit complete.
**Addresses:** Table stakes features (remove deprecated modules, clean global state). Establishes baseline metrics.
**Avoids:** Pitfall 3 (singleton state leaks) by cataloging all singletons upfront. Enables prevention in later phases.
**Research needs:** STANDARD — dead code removal is well-documented. No research-phase needed.

### Phase 2: Integration Layer Simplification
**Rationale:** After Phase 1 reduces noise, can safely simplify the factory/detector/status three-layer indirection. This is a prerequisite for Phase 3 (wrapper thinning) because it clarifies the integration boundary.
**Delivers:** Flattened `factory/` subpackage to single `factory.py`, replaced detector/cache with try-import pattern, removed `acceleration/` package.
**Uses:** Static analysis (ruff, vulture) to confirm removed code is unused. Coverage analysis to verify factory paths.
**Implements:** Factory Simplification Ladder (move from Stage 1 to Stage 2). Target: factory imports Rust directly, catches ImportError only.
**Avoids:** Pitfall 6 (factory contract breakage) by documenting interfaces with Protocol classes first. Pitfall 2 (PyInstaller breakage) by testing builds at phase gate.
**Research needs:** LOW — straightforward refactoring. May need `/gsd:research-phase` if factory interface contracts are unclear.

### Phase 3: Wrapper Thinning
**Rationale:** With integration layer simplified, can move Python logic from fat `rust/` wrappers into Rust `-core` crates. Requires Rust rebuilds. Most impactful phase for reducing maintenance burden.
**Delivers:** Python wrappers reduced to <50 lines each (type conversion only). Business logic moved to Rust. Rust test coverage expanded.
**Avoids:** Pitfall 1 (removing active fallbacks) by verifying Rust is stable before removing Python logic. Pitfall 5 (Rust dependency breakage) by using `cargo tree --invert` and running workspace builds.
**Research needs:** HIGH — this is where Python-to-Rust migration happens. Use `/gsd:research-phase` to research each component being migrated (parser, formid, plugin, etc.) for Rust implementation patterns.

### Phase 4: Interface Consolidation
**Rationale:** After wrappers are thin, can remove dual sync/async interfaces. Requires careful GUI testing.
**Delivers:** All `_sync` method variants removed. `FormIDAnalyzer.py` deprecated wrapper removed. Single orchestrator (hybrid with optional Rust batch).
**Implements:** Interface Consolidation pattern (async-only, wrap at entry points).
**Avoids:** Pitfall 4 (async/sync boundary breakage) by tracing all call sites and manual GUI testing. Pitfall 7 (lazy import breakage) by testing startup after module consolidation.
**Research needs:** MEDIUM — async patterns are known, but GUI integration points need verification. Consider `/gsd:research-phase` for QThread async patterns.

### Phase 5: Fallback Pruning
**Rationale:** After interfaces consolidated and wrappers thinned, can safely remove Python fallbacks where Rust is proven stable. Must be last major phase because it is irreversible without significant work.
**Delivers:** `integration/python/` reduced from 8 files to 2-3. Factory simplified to direct Rust imports. Type-narrowed factory returns (no more `Any`).
**Implements:** Strangler Fig pattern Phase C (removal). Policy: keep fallbacks only for components where Rust not proven stable on all platforms.
**Avoids:** Pitfall 1 (removing active fallbacks) by testing with `CLASSIC_DISABLE_RUST=1` and verifying Rust has been shipping reliably for 3+ months per component.
**Research needs:** LOW — by this phase, Rust stability is known from production data. No research needed.

### Phase Ordering Rationale

- **Phase 1 before all others:** Dead code removal reduces noise and establishes metrics. Tooling setup (vulture, cargo-machete, CI dead code detection) enables later phases.
- **Phase 2 before Phase 3:** Must simplify factory layer before thinning wrappers. The factory indirection makes it unclear where logic should live. Flatten factory first, then wrapper responsibilities become obvious.
- **Phase 3 before Phase 4:** Must move logic to Rust before removing sync wrappers. Sync wrappers often contain workarounds for Python logic that will disappear when moved to Rust.
- **Phase 4 before Phase 5:** Must consolidate interfaces before removing fallbacks. Dual interfaces (sync/async, old/new API) hide which code paths are actually active. Consolidate first, then fallback usage becomes visible.
- **Phase 5 last:** Removing fallbacks is irreversible. All previous phases prepare the codebase so fallback removal is safe. Rushing fallback removal risks Pitfall 1 (removing active code).

**Dependency chain:**
```
Phase 1 (Foundation)
  └─> Phase 2 (Integration Layer)
        └─> Phase 3 (Wrapper Thinning)
              └─> Phase 4 (Interface Consolidation)
                    └─> Phase 5 (Fallback Pruning)
```

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Wrapper Thinning):** Complex Python-to-Rust migration. Each component (parser, formid, plugin, database, file_io) may need dedicated `/gsd:research-phase` to research Rust implementation patterns, error handling, and PyO3 type mapping.
- **Phase 4 (Interface Consolidation):** QThread async patterns and AsyncBridge usage in GUI workers need verification. Consider lightweight `/gsd:research-phase` for Qt async integration if team is unfamiliar.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** Dead code removal and tooling setup are well-documented. Ruff, vulture, coverage usage is standard.
- **Phase 2 (Integration Layer):** Factory simplification is straightforward Python refactoring. Protocol classes and try-import patterns are known.
- **Phase 5 (Fallback Pruning):** By this phase, Rust stability is proven from production. Removal is mechanical (delete files, update factories).

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Tools verified from `uv pip list` output. Ruff, pyright, coverage already configured. Vulture and cargo-machete are mature tools with stable APIs. |
| Features | HIGH | Derived from direct codebase analysis of CLASSIC repository. All findings verified against actual source files. Metrics are concrete (file counts, line counts). |
| Architecture | HIGH | Based on direct reading of CLASSIC codebase structure, architecture docs, and Rust workspace manifest. Four-layer integration stack confirmed by tracing imports. |
| Pitfalls | HIGH | Sourced from CONCERNS.md (existing known issues), CLAUDE.md rules (project conventions), and architectural analysis. Each pitfall grounded in actual codebase patterns. |

**Overall confidence:** HIGH

This research is based on direct codebase analysis with all findings verified against actual source files. The confidence is not from external sources or training data, but from reading the CLASSIC repository structure, documentation, and code. Tool recommendations (vulture, cargo-machete) are the only MEDIUM confidence items (versions from training data, but tools are mature and stable).

### Gaps to Address

**Rust crate maturity:** Research identified 39 Rust crates (21 business-logic, 18 python-bindings) but could not determine which are stubs vs. have real code without auditing each crate's source. **During planning:** Phase 1 should include "Rust crate audit" task to categorize stubs (remove) vs. mature crates (keep).

**Python fallback usage in production:** Research assumes Python fallbacks are rarely/never exercised in production (Rust always ships), but this is not verified with telemetry or user reports. **During planning:** Before Phase 5, add task to verify Rust availability in deployed builds (check PyInstaller bundle contents, review user crash reports for ImportError patterns).

**GUI async boundary call sites:** Research identified sync wrapper removal as Pitfall 4 but did not trace actual GUI call sites. **During planning:** Phase 4 should include "Map GUI async call sites" task to grep for sync wrapper usage in `ClassicLib/Interface/workers/` and `ClassicLib/Interface/controllers/`.

**Factory function interface contracts:** Research noted factory contract breakage as Pitfall 6 but did not document existing contracts. **During planning:** Phase 2 should include "Document factory interfaces with Protocol classes" task before any consolidation.

**Test coverage baseline:** Research recommends coverage-guided audit but did not establish current coverage metrics. **During planning:** Phase 1 should include "Establish coverage baseline" task to run `pytest --cov` and record starting metrics for comparison.

## Sources

### Primary (HIGH confidence)
- `J:/CLASSIC-Fallout4/.planning/codebase/CONCERNS.md` — Known bugs, tech debt, fragile areas, test gaps
- `J:/CLASSIC-Fallout4/.planning/codebase/ARCHITECTURE.md` — Data flow, async patterns, factory pattern
- `J:/CLASSIC-Fallout4/.planning/codebase/STRUCTURE.md` — Module layout, Rust crate inventory
- `J:/CLASSIC-Fallout4/.planning/codebase/CONVENTIONS.md` — Code organization standards
- `J:/CLASSIC-Fallout4/.planning/codebase/INTEGRATIONS.md` — Python-Rust boundary patterns
- `J:/CLASSIC-Fallout4/.planning/PROJECT.md` — Cleanup scope, constraints, key decisions
- `J:/CLASSIC-Fallout4/.claude/rules/` — Project conventions (lazy imports, ONE RUNTIME, TDD)
- `J:/CLASSIC-Fallout4/CLASSIC.spec` — PyInstaller configuration with hardcoded module paths
- `J:/CLASSIC-Fallout4/rust/Cargo.toml` — Workspace manifest
- `J:/CLASSIC-Fallout4/pyproject.toml` — Installed tool versions verified via `uv pip list`
- Direct codebase grep for patterns: `global _*`, `DEPRECATED`, `create_sync_wrapper`

### Secondary (MEDIUM confidence)
- vulture capabilities and version (2.14+) — Known from training data. Core functionality (whole-program dead code detection) is stable and well-established.
- cargo-machete vs cargo-udeps tradeoffs — Known from training data. Machete's stable-Rust advantage and speed are well-documented in Rust ecosystem.
- PyO3 patterns — Based on training data for version-specific claims. Core PyO3 concepts (GIL handling, exception mapping) are stable.

### Tertiary (LOW confidence)
- None. All recommendations based on direct codebase analysis or mature tool capabilities.

---
*Research completed: 2026-02-01*
*Ready for roadmap: yes*
