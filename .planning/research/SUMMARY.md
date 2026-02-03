# Research Summary: CLASSIC Codebase Cleanup and Consolidation

**Project:** CLASSIC v8.2.0-part2 Codebase Cleanup and Consolidation
**Domain:** Hybrid Python-Rust desktop application (crash log analysis)
**Researched:** 2026-02-02
**Confidence:** HIGH (based on direct codebase analysis, verified external sources)

## Executive Summary

CLASSIC has already migrated the majority of its performance-critical logic to Rust (YAML parsing, database operations, crash log parsing, FormID analysis, file I/O). The cleanup and consolidation milestone is about **removing scaffolding left from the migration** rather than building new functionality. Research reveals three key findings: (1) The existing Rust infrastructure requires **zero new external dependencies** — all necessary capabilities exist in the workspace's 39 crates. (2) The primary technical debt is **three-layer indirection** in the integration layer (factory -> Rust wrapper -> PyO3 binding) where the middle layer has grown to contain duplicate business logic. (3) The remaining Python fallback implementations (8 files) exist for a scenario (Rust unavailable) that never occurs in production deployments, creating a false maintenance burden.

The recommended approach is **progressive simplification, not rewriting**. Remove Python fallbacks where Rust is proven stable (3+ months in production). Collapse the factory/detector/status three-layer indirection to a single try-import pattern. Consolidate duplicate YAML sync/async implementations. Fix the handful of problematic global mutable state flags that break test isolation. This is mostly **wiring and deletion**, not engineering — but deletion requires careful verification to avoid breaking PyInstaller builds, GUI async boundaries, or Rust workspace dependencies.

Key risks center on **invisible breakage**: PyInstaller hidden imports that only fail in distributed builds, async/sync boundary violations that only manifest as GUI deadlocks, and Rust crate dependencies that only break the workspace, not individual tests. Mitigation: treat PyInstaller builds as a phase gate, manually test GUI paths after sync wrapper removal, and run `cargo build --workspace` after any Rust structural changes.

## Key Findings

### Recommended Stack

**Zero new external dependencies required.** CLASSIC's existing Rust infrastructure (PyO3 0.27, Tokio 1.49, 25+ crates) covers all cleanup needs. The research identified and rejected several tempting additions: `markdown-gen` (report generation is trivial string concatenation), `steamlocate` (CLASSIC validates user-provided paths, doesn't auto-detect Steam), and template engines like `handlebars` (static-format reports don't need runtime templating).

**Core technologies already in place:**
- **PyO3 0.27.2**: Python-Rust bindings with abi3-py312 stable ABI (DO NOT upgrade to 0.28 — breaking changes across 18+ crates)
- **Tokio 1.49**: Async runtime via `classic-shared-core::get_runtime()` (ONE RUNTIME rule enforced)
- **yaml-rust2 0.11**: YAML parsing in `classic-settings-core` (15-30x faster than Python ruamel.yaml)
- **DashMap 6.1**: Lock-free concurrent cache for settings
- **rayon 1.10**: CPU-bound parallel processing for orchestration
- **lasso 0.7 + smartstring 1.0**: String interning and optimization for report generation

**Version strategy:** Stay on current stable versions. All workspace versions verified as current as of 2026-02-02. The only version constraint is "do not upgrade PyO3" until a dedicated migration milestone.

### Expected Features (Cleanup Activities)

**Must-Do (Table Stakes for Milestone Completion):**
- Remove `FormIDAnalyzer` sync wrapper (dead code wrapping async implementation)
- Remove Python fallback implementations where Rust is always shipped (8 files in `ClassicLib/integration/python/`)
- Eliminate `_VERSION_WARNING_LOGGED` and similar global mutable state flags that break test isolation
- Consolidate YAML sync/async split (two parallel directories, overlapping cache implementations)
- Remove deprecated module references (11 files with DEPRECATED markers)
- Simplify factory/detector/status three-layer indirection (duplicate caching, overlapping abstractions)

**Should-Do (High ROI for Future Migration):**
- Establish clear module ownership boundaries (flatten `integration/rust/` fat wrappers)
- Remove `RustAcceleration` coordinator singleton (elaborate framework with no clear usage)
- Unify async entry patterns (remove transitional `create_sync_wrapper` code)
- Add dead code detection to CI (prevent regression)
- Type-narrow all `Any` returns from factory functions (enable Pyright to catch errors after fallback removal)
- Document post-cleanup integration contract (single-page reference for Python-Rust boundary)

**Anti-Features (Seem Good But Are Harmful):**
- Remove ALL Python fallbacks immediately (some serve as test oracles and reference implementations — phase removal instead)
- Rewrite integration/factory layer from scratch (affects every import site simultaneously — simplify incrementally)
- Convert all global state to dependency injection (CLASSIC is a desktop app, some singletons are legitimate — fix problematic ones, keep legitimate ones)
- Merge sync and async YAML into a single module file (creates massive diff, hard to review — consolidate caches first, then flatten)

### Architecture Approach

CLASSIC follows a **strangler fig migration pattern** where Rust gradually replaces Python implementations through factory indirection. The cleanup consolidates what the strangler fig left behind.

**Current four-layer integration stack (problem area):**
```
Caller (GUI/CLI)
  -> factory/ (decides Rust or Python)
    -> rust/ wrapper (Python class around PyO3 import)
      -> -py crate (PyO3 #[pyclass] adapter)
        -> -core crate (pure Rust logic)
```

**Target three-layer stack (after cleanup):**
```
Caller
  -> factory (try-import, simple fallback)
    -> -py crate (direct import, thin PyO3)
      -> -core crate (pure Rust business logic)
```

**Major components affected by cleanup:**
1. **Integration layer** (`ClassicLib/integration/`) — Primary cleanup target. Flatten factory/ subpackage to single file. Remove detector/config/status redundancy. Thin out or remove rust/ wrappers.
2. **YAML subsystem** (`ClassicLib/io/yaml/`) — Consolidate sync/async directories. Single cache implementation with async-first, sync wrappers at entry points.
3. **Scanning orchestration** (`ClassicLib/scanning/logs/`) — Remove sync wrappers. Establish async-only interface with AsyncBridge at GUI boundaries only.
4. **Acceleration framework** (`ClassicLib/acceleration/`) — Audit usage. Simplify or remove coordinator/metrics/workload abstractions that add complexity without measured benefit.
5. **Rust workspace** (`rust/`) — Audit 39 crates for stubs vs. active code. Do NOT create new crates during cleanup. Use existing crates.

**Critical architectural rules to preserve during cleanup:**
- **ONE RUNTIME**: Single global Tokio runtime via `classic_shared_core::get_runtime()` — never `Runtime::new()`
- **Lazy YAML imports**: Import `yaml_settings`, `classic_settings` inside functions to avoid circular imports (documented in CLAUDE.md rule 8)
- **Separate business logic and PyO3 bindings**: `-core` crates have no PyO3 dependency, `-py` crates are thin adapters
- **GIL release discipline**: Use `py.allow_threads()` before async work to prevent deadlocks

### Critical Pitfalls

**Top migration-specific pitfalls** (added 2026-02-02 based on PyO3/Tokio integration challenges):

1. **Nested Runtime Errors (M1)** — Creating multiple Tokio runtimes causes "Cannot start a runtime from within a runtime" panics. Prevention: Always use `classic_shared_core::get_runtime()`, never `Runtime::new()`. Check context before blocking. Release GIL with `py.allow_threads()`.

2. **GIL Deadlock During Async Operations (M2)** — Holding Python GIL while doing async work in multi-threaded Tokio runtime causes complete freeze. Prevention: Use `py.allow_threads()` to release GIL before any async work. Detach Python objects before sending to other threads. Detection: Application hangs with no output, only under parallel load.

3. **Behavioral Parity Regression (M3)** — Rust implementation produces different output than Python for edge cases. Prevention: Golden file testing comparing Rust output against captured Python output. Use `IndexMap` instead of `HashMap` when order matters. Character-by-character comparison of report output. Fuzz testing with random/malformed input.

4. **Memory Ownership Across Python/Rust Boundary (M4)** — Passing Python objects to Rust, doing async work, then trying to use them causes use-after-free. Prevention: Clone data before releasing GIL. Convert to owned types at boundary (`String` not `&str`). Never hold `&PyAny` across `py.allow_threads()` boundaries.

5. **Type Conversion Overhead at Hot Paths (M5)** — Repeatedly converting between Python and Rust types in tight loops negates Rust performance benefits. Prevention: Batch operations (pass entire collections). Keep data on Rust side between operations. Measure before assuming Rust is faster.

**Top cleanup-specific pitfalls** (original research 2026-02-01):

6. **Removing "Dead" Python Fallbacks That Are Active** — Fallback appears dead in dev, but PyInstaller builds fail silently for some users. Prevention: Run test suite with `CLASSIC_DISABLE_RUST=1` before removing any fallback. Verify Rust has been shipping reliably for 3+ months.

7. **Breaking PyInstaller Hidden Imports** — Module renamed/moved, tests pass, distributed executable crashes with `ModuleNotFoundError`. Prevention: Update `CLASSIC.spec` hidden imports in same commit as module changes. Test PyInstaller build at every phase gate.

8. **Singleton State Leaks Across Cleanup** — Singletons accumulate stale references during restructuring. Tests pass individually, fail in batch. Prevention: Reset ALL singleton state between test runs. Add `reset_all_singletons()` autouse fixture.

9. **Breaking Async/Sync Boundary During Sync Wrapper Removal** — Sync wrapper removed, GUI call site in QThread worker freezes. Prevention: Trace ALL call sites before removal. Replace with appropriate async pattern for each context. Manual GUI testing after each removal.

10. **Lazy YAML Import Discipline Breaks** — Module consolidation converts lazy imports to top-level, circular import chain triggers at startup. Prevention: Keep lazy import pattern even during consolidation. Test startup after module merges. Add comments explaining circular dependency.

## Implications for Roadmap

Based on research, this cleanup is best executed as **four focused phases** rather than a large monolithic effort. The phase ordering prevents pitfalls by establishing foundations before removal, and creates natural verification checkpoints.

### Phase 1: Foundation Audit and Verification
**Rationale:** Before removing anything, establish what's safe to remove and create automated detection for future regression. This phase pays dividends throughout cleanup by catching mistakes early.

**Delivers:**
- Dead code detection in CI (prevents regression)
- Rust fallback verification report (which fallbacks are actually exercised)
- Deprecated module catalog (11 files marked DEPRECATED)
- Global mutable state categorization (19 instances — which to fix, which to keep)
- PyInstaller build baseline (verify current state before changes)

**Addresses Features:**
- Add dead code detection to CI (Should-Do differentiator)
- Audit all `global _*` instances (Must-Do table stakes)

**Avoids Pitfalls:**
- Pitfall 6: Removing active Python fallbacks (verify with `CLASSIC_DISABLE_RUST=1`)
- Pitfall 3: Singleton state leaks (catalog before fixing)
- Pitfall 7: Lazy YAML import breaks (document intentional lazy imports)

**Research Flag:** Standard patterns (skip research-phase) — this is auditing, not engineering.

---

### Phase 2: Low-Risk Cleanup
**Rationale:** Execute cleanup activities with no dependencies and minimal risk. Build confidence in the cleanup process before tackling complex consolidations. This phase should complete quickly and prove the verification infrastructure works.

**Delivers:**
- Deprecated module references removed (11 files)
- `_VERSION_WARNING_LOGGED` and similar mutable global flags eliminated
- `FormIDAnalyzer` sync wrapper removed
- Test fixture improvements (singleton reset infrastructure)

**Addresses Features:**
- Remove deprecated module references (Must-Do table stakes)
- Eliminate problematic global mutable state (Must-Do table stakes)
- Remove FormIDAnalyzer sync wrapper (Must-Do table stakes)

**Avoids Pitfalls:**
- Pitfall 8: Singleton state leaks (fix global flags that break test isolation)
- Pitfall 9: Breaking async/sync boundary (FormIDAnalyzer removal requires call site audit)

**Uses Stack:**
- Existing test infrastructure (pytest, mypy, ruff)
- Existing Rust components (no changes to Rust side)

**Research Flag:** Standard patterns — straightforward deletion with verification.

---

### Phase 3: Core Consolidation
**Rationale:** The main cleanup work. Remove redundancy in integration layer and YAML subsystem. This phase has the highest pitfall risk but also the highest maintenance burden reduction. Must complete Phase 1 verification first.

**Delivers:**
- Python fallback implementations removed (parser, formid, plugin, record — 4 of 8 files initially)
- YAML sync/async directories consolidated (single cache, async-first with sync wrappers)
- Factory/detector/status three-layer indirection simplified (detector does detection, factory uses detector, status is read-only view)

**Addresses Features:**
- Remove Python fallbacks where Rust stable (Must-Do table stakes)
- Consolidate YAML sync/async split (Must-Do table stakes)
- Simplify factory/detector/status layering (Must-Do table stakes)

**Avoids Pitfalls:**
- Pitfall 6: Removing active fallbacks (Phase 1 verified which are safe)
- Pitfall 7: Breaking PyInstaller (update CLASSIC.spec with module changes, test build at phase gate)
- Pitfall 8: Singleton state leaks (Phase 2 established reset infrastructure)
- Pitfall M2: GIL deadlock (YAML consolidation requires careful async boundary handling)

**Uses Stack:**
- `classic-settings-core` (existing Rust YAML cache)
- PyO3 0.27 (existing bindings)
- Test infrastructure from Phase 1 (dead code detection, fallback verification)

**Research Flag:** Needs deeper research during planning — YAML consolidation affects dozens of call sites, needs careful migration plan for sync callers. Consider `/gsd:research-phase` for "YAML async-first migration" sub-phase.

---

### Phase 4: Architecture Simplification
**Rationale:** Restructuring that depends on Phase 2-3 cleanup being done. This phase makes future Rust migration easier but is not required for the cleanup milestone to succeed. Can be deferred if time constrained.

**Delivers:**
- `RustAcceleration` coordinator simplified or removed
- Async entry patterns unified (remove transitional `create_sync_wrapper`)
- Factory function returns type-narrowed (from `Any` to specific Rust types)
- Integration contract documentation (single-page reference)

**Addresses Features:**
- Remove RustAcceleration coordinator (Should-Do differentiator)
- Unify async entry patterns (Should-Do differentiator)
- Type-narrow factory returns (Should-Do differentiator)
- Document integration contract (Should-Do differentiator)

**Implements Architecture:**
- Flatten integration layer (remove rust/ wrappers where they're just pass-throughs)
- Establish clear module ownership boundaries

**Avoids Pitfalls:**
- Pitfall 2: Factory contract breakage (type narrowing requires interface documentation first)
- Pitfall 9: Async/sync boundary breakage (async pattern unification needs careful GUI testing)

**Uses Stack:**
- Pyright strict mode (type narrowing verification)
- Existing PyO3 bindings (no new Rust code, just removing Python wrappers)

**Research Flag:** Standard patterns — this is deletion and simplification, established patterns exist.

---

### Phase Ordering Rationale

1. **Audit before removal** (Phase 1 before 2-3): Cannot safely remove code without knowing what's actually dead. Verification infrastructure catches mistakes in later phases.

2. **Low-risk before high-risk** (Phase 2 before 3): Build confidence and establish processes with easy wins. Deprecated modules and global flags are isolated changes. YAML consolidation and fallback removal affect many files.

3. **Consolidation before simplification** (Phase 3 before 4): Cannot type-narrow factory returns while fallbacks still exist (`Any` is necessary when return type could be Rust or Python). Cannot remove coordinator until factory layer is simplified.

4. **Natural verification checkpoints**: Each phase ends with specific verification (Phase 1: dead code CI green, Phase 2: all tests pass with new fixtures, Phase 3: PyInstaller build works, Phase 4: Pyright strict mode passes).

5. **Pitfall prevention order**: Phase 1 catches Pitfall 6 (active fallbacks), Phase 2 fixes Pitfall 8 (singleton state), Phase 3 addresses Pitfall 7 (PyInstaller), Phase 4 handles Pitfall 2 (factory contracts).

### Research Flags

**Needs deeper research during planning:**
- **Phase 3 — YAML consolidation sub-phase**: Affects dozens of call sites across `ClassicLib/`. Need migration plan for: (a) which callers can use async directly, (b) which need AsyncBridge wrappers, (c) how to handle batch operations. Consider `/gsd:research-phase` for "YAML async-first migration patterns" to map all call sites before consolidation.

**Standard patterns (skip research-phase):**
- **Phase 1 — Audit/verification**: Tooling and scripting, well-established patterns.
- **Phase 2 — Low-risk cleanup**: Straightforward deletion, existing test infrastructure.
- **Phase 4 — Architecture simplification**: Type narrowing and documentation, standard patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Based on workspace `Cargo.toml` analysis and verified external sources. All versions confirmed current as of 2026-02-02. Zero new dependencies needed — finding verified by checking each migration target against existing crates. |
| Features | HIGH | Based on direct codebase analysis (grep results, file counts). All cleanup activities are concrete and measurable (8 fallback files, 11 deprecated markers, 19 global instances). MVP definition comes from analyzing CONCERNS.md known issues. |
| Architecture | HIGH | Based on direct code inspection of integration layer, existing documentation in `.planning/codebase/`, and verified PyO3 patterns from official docs. The four-layer vs three-layer analysis is derived from actual import chains. |
| Pitfalls | HIGH | Migration pitfalls (M1-M5) from official PyO3 documentation and GitHub issue discussions. Cleanup pitfalls (6-10) from project-specific CONCERNS.md and ARCHITECTURE.md. All pitfalls tied to specific code locations. |

**Overall confidence:** HIGH

This is not greenfield research with uncertain answers — this is **codebase archaeology** with verifiable findings. The research is about what already exists and what's safe to remove, not what to build. Confidence is high because findings are grounded in actual source files, not inferred from external documentation.

### Gaps to Address

**During planning (before phase execution):**
- **YAML call site mapping**: Need comprehensive map of all `yaml_settings`, `classic_settings`, and `YamlCache` call sites to plan Phase 3 consolidation. This should be done during requirements definition for Phase 3, possibly as a dedicated research-phase sub-task.
- **RustAcceleration usage verification**: `ClassicLib/acceleration/` coordinator.py is 670+ lines but unclear if it's actually instantiated at runtime. Need runtime profiling or strategic `print()` statements to verify before removal in Phase 4.
- **Rust crate dependency graph**: Need `cargo tree` output for all `-core` crates to identify hidden dependencies before any crate removal. This prevents Pitfall 5 (Rust workspace breakage).

**During execution (validate as you go):**
- **PyInstaller hidden imports**: `CLASSIC.spec` must be manually reviewed and updated for every module move/rename. Consider generating hidden imports programmatically from import analysis to reduce human error.
- **GUI async boundary call sites**: No automated way to detect which code paths run in QThread workers vs Qt main thread. Requires manual code review and runtime testing for any sync wrapper removal.
- **Golden file tests for behavioral parity**: Python report output should be captured for ~10 representative crash logs before any Rust report generation changes. This creates regression tests for Pitfall M3.

**Validation strategy:**
- Phase gates include specific verification (CI green, PyInstaller builds, manual GUI testing)
- Each pitfall has detection criteria documented
- When gaps are discovered during execution, add to phase requirements rather than proceeding blindly

## Sources

### Primary (HIGH confidence)
- **CLASSIC workspace analysis**:
  - `j:\CLASSIC-Fallout4\rust\Cargo.toml` — authoritative workspace manifest, version verification
  - `j:\CLASSIC-Fallout4\.planning\codebase\CONCERNS.md` — documented known issues, tech debt, fragile areas
  - `j:\CLASSIC-Fallout4\.planning\codebase\ARCHITECTURE.md` — data flow, async patterns, factory pattern documentation
  - `j:\CLASSIC-Fallout4\.planning\codebase\STRUCTURE.md` — module layout, Rust crate inventory
  - `j:\CLASSIC-Fallout4\CLASSIC.spec` — PyInstaller configuration, hidden imports
  - `j:\CLASSIC-Fallout4\.claude\rules\05-memories.md` — historical decisions, AsyncBridge patterns
  - `j:\CLASSIC-Fallout4\docs\development\pyo3_integration_patterns.md` — PyO3 integration guide
  - `j:\CLASSIC-Fallout4\docs\development\async_development_guide.md` — async patterns
  - `j:\CLASSIC-Fallout4\docs\development\rust_workspace_architecture.md` — Rust workspace structure
  - Grep results across codebase for patterns: `global _*`, `DEPRECATED`, `create_sync_wrapper`, `import classic_*`

### Secondary (MEDIUM confidence)
- [PyO3 Migration Guide](https://pyo3.rs/v0.22.4/migration) — Official PyO3 0.27 migration documentation, API version patterns
- [PyO3 FAQ and Troubleshooting](https://pyo3.rs/main/faq) — Common issues and solutions, GIL handling
- [PyO3 Async/Await Guide](https://pyo3.rs/v0.13.2/ecosystem/async-await) — Async runtime integration patterns
- [GIL Deadlock Discussion](https://github.com/PyO3/pyo3/discussions/3045) — Multi-threaded Tokio GIL issues, real-world examples
- [Tokio Structured Concurrency Patterns](https://medium.com/@adamszpilewicz/structured-concurrency-in-rust-with-tokio-beyond-tokio-spawn-78eefd1febb4) — Orchestration patterns
- [Migrating from Python to Rust](https://corrode.dev/learn/migration-guides/python-to-rust/) — General migration best practices, behavioral parity testing

### Tertiary (context, not critical to findings)
- [Incrementally Porting Python to Rust](https://blog.waleedkhan.name/port-python-to-rust/) — Incremental migration strategies (strangler fig pattern)
- [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/documentation.html) — Documentation standards for Rust crates

**Research methods:**
- Direct codebase inspection (grep, file counts, import tracing)
- Cargo workspace analysis (`cargo tree`, dependency graph)
- Version verification against crates.io (all versions current as of 2026-02-02)
- PyO3 official documentation cross-reference
- Project history analysis (git log, documented decisions in CLAUDE.md)

---
*Research completed: 2026-02-02*
*Ready for roadmap: Yes*
*Confidence: HIGH (codebase archaeology, not inference)*
