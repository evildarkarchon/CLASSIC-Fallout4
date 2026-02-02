# Feature Research: Codebase Cleanup and Consolidation

**Domain:** Hybrid Python-Rust codebase cleanup (CLASSIC)
**Researched:** 2026-02-01
**Confidence:** HIGH (derived from direct codebase analysis, not external sources)

## Feature Landscape

### Table Stakes (Must-Do or Milestone Fails)

Cleanup activities where failure to execute means the codebase remains in a confused state with unclear ownership. These are the minimum to call the milestone "done."

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Remove `FormIDAnalyzer` sync wrapper | Dead code: wraps `FormIDAnalyzerCore` with `create_sync_wrapper` for a GUI mode that should use async directly. Documented as deprecated in its own docstring. | LOW | `ClassicLib/scanning/logs/analyzers/FormIDAnalyzer.py` -- 156 lines wrapping the real implementation. All callers should use `FormIDAnalyzerCore` directly. |
| Remove Python fallback implementations where Rust is always shipped | 8 fallback files in `ClassicLib/integration/python/` exist for a scenario (Rust unavailable) that never occurs in distribution. They create maintenance burden: every Rust API change requires updating two implementations. | MEDIUM | `formid_py.py`, `parser_py.py`, `plugin_py.py`, `record_py.py`, `report_py.py`, `database_py.py`, `file_io_py.py`, `mod_detector_py.py`. Verify Rust wheels are always bundled before removing. |
| Eliminate `_VERSION_WARNING_LOGGED` global mutable state | Module-level `global` flag in `game_path.py` that breaks test isolation. Already documented as fragile in CONCERNS.md. | LOW | Replace with instance variable on `GamePath` class or `functools.lru_cache` with `cache_clear()` in test fixtures. |
| Consolidate YAML sync/async split | `ClassicLib/io/yaml/` has parallel `sync/` and `async_/` subdirectories with overlapping cache implementations. Two code paths to maintain for the same data. | MEDIUM | Collapse to async-only with sync wrappers at entry points (GUI). The sync dir has `cache.py`, `convenience.py`; async dir has `cache.py`, `core.py`, `file_operations.py`. |
| Remove deprecated module references | 11 files across `ClassicLib/` contain DEPRECATED markers. Deprecated code that remains becomes permanent. | LOW | Audit each of the 11 files from grep results. Remove deprecated paths, update callers to current API. |
| Clean up global mutable state pattern | 19 instances of `global _*` across ClassicLib (grep results above). Each is a singleton/lazy-init that complicates testing and creates hidden coupling. | HIGH | Not all can be removed (some are legitimate singletons like `_message_handler`). Categorize: which are lazy-init caches (acceptable), which are mutable flags (replace with instance state), which are test-hostile (add reset fixtures). |
| Simplify factory/detector/status layering | Three overlapping abstraction layers for Rust component detection: `detector.py` (import-based detection + caching), `factory/core.py` (additional cache layer over detector), `status.py` (yet another layer with `RUST_AVAILABLE` dict and `RUST_STATUS` dict). | MEDIUM | Collapse to: detector does detection, factory uses detector directly, status is a read-only view. Remove duplicate caching between `_components_cache` in factory/core.py and `_detection_cache` in detector.py. |

### Differentiators (Makes Future Rust Migration Significantly Easier)

These go beyond "cleaning up the mess" to actively preparing the codebase for the next phase of Rust migration. Not required for the cleanup milestone, but high ROI.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Establish clear module ownership boundaries | Currently, `ClassicLib/integration/rust/` wraps Rust modules, `ClassicLib/integration/python/` provides fallbacks, and `ClassicLib/integration/factory/` selects between them. After removing fallbacks, this three-layer indirection becomes two layers of indirection for no reason. Flatten to direct Rust imports with thin Python adapter. | HIGH | Major refactor of the integration layer. Sets the pattern for how all future Rust modules are consumed. Do this once, correctly. |
| Remove `RustAcceleration` coordinator singleton | `ClassicLib/acceleration/` (coordinator.py, metrics.py, types.py, workload.py) is an elaborate optimization framework (OptimizationLevel enum with 5 levels, WorkloadCharacteristics, ComponentMetrics) that adds complexity without clear evidence of use. If Rust is always available, the "coordination" and "fallback" logic is dead weight. | MEDIUM | 4 files, ~400 lines. Verify no runtime code depends on `RustAcceleration` instance. If metrics are needed, they belong in the Rust layer, not a Python wrapper. |
| Unify async entry patterns | Three different async-entry patterns exist: `AsyncBridge.run_async()` for GUI, `asyncio.run()` for CLI, and `create_sync_wrapper()` for transitional code. After cleanup, there should be exactly two: native async (CLI/TUI) and `AsyncBridge` (GUI). Remove `create_sync_wrapper` and all `_async_utils/bridge_helpers.py` transitional code. | MEDIUM | `ClassicLib/_async_utils/bridge_helpers.py`, `ClassicLib/_async_utils/__init__.py`, `ClassicLib/io/files/sync_adapters.py`, plus 4 files using `create_sync_wrapper`. |
| Add dead code detection to CI | A cleanup milestone without ongoing enforcement means code will re-accumulate. Add `vulture` or equivalent dead code detection to CI pipeline so deprecated/unused code is flagged automatically. | LOW | One-time CI configuration. Prevents regression. |
| Type-narrow all `Any` returns from factory functions | Factory functions like `get_parser()`, `get_formid_analyzer()` return `Any` because they could return Rust or Python implementations. After removing fallbacks, return types can be narrowed to specific Rust types, enabling Pyright to catch errors. | MEDIUM | Requires updating ~8 factory functions in `ClassicLib/integration/factory/` and all type stubs. |
| Document the post-cleanup integration contract | Write a single-page reference for how Python calls Rust after cleanup: import pattern, error handling, type mapping. This replaces the current scattered documentation across 5+ doc files. | LOW | Documentation deliverable. Prevents the integration layer from re-growing organically. |

### Anti-Features (Cleanup Activities That Seem Good but Are Actually Harmful)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Remove ALL Python fallbacks immediately | "If Rust is always shipped, why keep any Python?" | Some fallback code serves as the reference implementation and test oracle. Removing it before Rust implementations are fully tested removes the safety net. Specifically `database_py.py` and `file_io_py.py` exercise paths that Rust might not cover in edge cases. | Remove fallbacks in phases: first for modules with comprehensive Rust tests (parser, formid, plugin), then for modules where Rust test coverage needs verification (database, file_io). |
| Rewrite the integration/factory layer from scratch | "It's three layers deep, just rebuild it cleanly" | Factory pattern rewrite affects every import site in the codebase simultaneously. High risk of introducing subtle regressions in component selection. | Simplify incrementally: first remove fallback branches (making factories trivially "always Rust"), then inline the simplified factories, then remove the empty shell. |
| Convert all global state to dependency injection | "Global mutable state is bad, inject everything" | CLASSIC is a desktop app, not a web server. Some singletons (MessageHandler, GlobalRegistry, ThreadManager) are legitimate application-scoped singletons. Converting them to DI adds constructor parameter proliferation without benefit. | Fix the problematic globals (mutable flags, test-hostile caches) but keep legitimate singletons. Add `reset()` methods for test isolation instead of removing the pattern. |
| Remove the entire `ClassicLib/acceleration/` package now | "It's premature optimization infrastructure" | While the optimization levels and workload characteristics are likely unused, the ComponentMetrics tracking may have diagnostic value. Removing it without checking runtime usage could break status reporting. | Audit actual usage first. If `RustAcceleration` is only instantiated in status reporting, simplify rather than remove. If never instantiated at runtime, safe to remove entirely. |
| Merge sync and async YAML into a single module file | "Why have directories when one file would do?" | The YAML subsystem is actively used by dozens of callers. A large merge-and-restructure creates a massive diff that is hard to review and hard to bisect if something breaks. | Consolidate the cache implementations first (two `cache.py` files into one). Then remove the sync convenience wrappers. Then flatten the directory structure. Three small PRs instead of one large one. |
| Remove `CLASSIC_DISABLE_RUST` environment variable | "If fallbacks are removed, the env var is meaningless" | Development and debugging still benefit from being able to disable Rust modules. Even without fallbacks, the env var can trigger graceful degradation messaging rather than hard crashes. | Keep the env var but change its behavior: instead of falling back to Python, it logs a clear error and exits. Useful for diagnosing Rust loading issues. |

## Feature Dependencies

```
[Remove Python fallbacks]
    |
    |--requires--> [Verify Rust wheels always bundled in distribution]
    |--requires--> [Verify Rust test coverage for each removed fallback]
    |
    +--enables--> [Simplify factory layer]
                      |
                      +--enables--> [Type-narrow factory returns]
                      +--enables--> [Remove acceleration coordinator]
                      +--enables--> [Flatten integration layers]

[Remove FormIDAnalyzer sync wrapper]
    |--requires--> [Audit all callers to confirm none use sync API]
    +--enables--> [Unify async entry patterns]

[Consolidate YAML sync/async]
    |--requires--> [Audit all YAML callers for sync vs async usage]
    +--independent of--> [Remove Python fallbacks]

[Clean up global mutable state]
    |--independent of--> [All other items]
    +--benefits from--> [Improved test fixtures]

[Remove deprecated modules]
    |--independent of--> [All other items]
    |--should precede--> [Remove Python fallbacks] (reduces noise in diffs)

[Add dead code detection to CI]
    |--independent of--> [All other items]
    +--should be first--> (catches things the manual audit misses)
```

### Dependency Notes

- **Remove Python fallbacks requires Rust verification:** The fallbacks exist because Rust modules might not be available. Before removing them, must confirm that (a) all distribution channels bundle Rust wheels, and (b) each Rust module has equivalent test coverage to its Python fallback.
- **Simplify factory layer requires fallback removal:** The factory's entire purpose is selecting between Rust and Python. With only Rust, factories become trivial pass-throughs that can be inlined.
- **Type-narrowing requires simplified factories:** You cannot narrow `Any` to a specific Rust type while the factory might return either implementation.
- **FormIDAnalyzer removal requires caller audit:** The sync wrapper is marked deprecated but may still be imported somewhere in GUI code.
- **YAML consolidation is independent:** Can proceed in parallel with fallback removal since the sync/async split is a Python-only concern unrelated to Rust.

## MVP Definition

### Phase 1: Foundation Cleanup (Do First)

Minimum viable cleanup -- the activities with no dependencies and low risk.

- [ ] Add dead code detection to CI -- catches things humans miss, prevents regression
- [ ] Remove deprecated module references -- 11 files, low risk, reduces noise
- [ ] Eliminate `_VERSION_WARNING_LOGGED` and similar mutable global flags -- LOW complexity, improves test isolation
- [ ] Audit and categorize all 19 `global _*` instances -- decide which to fix, which to keep

### Phase 2: Core Consolidation (Do After Phase 1)

The main cleanup work. Removes the largest sources of redundancy.

- [ ] Verify Rust wheel bundling and test coverage -- prerequisite gate
- [ ] Remove FormIDAnalyzer sync wrapper -- after confirming no callers
- [ ] Remove Python fallback implementations (parser, formid, plugin, record first) -- after verification
- [ ] Consolidate YAML sync/async split -- parallel with above

### Phase 3: Architecture Simplification (Do After Phase 2)

Restructuring that depends on the core cleanup being done.

- [ ] Simplify factory/detector/status three-layer indirection -- enabled by fallback removal
- [ ] Remove or simplify RustAcceleration coordinator -- after auditing usage
- [ ] Unify async entry patterns, remove transitional `create_sync_wrapper` -- after sync wrappers gone
- [ ] Type-narrow factory function returns -- after factories simplified

### Future Consideration (Post-Milestone)

- [ ] Flatten integration layer entirely (direct Rust imports) -- too large for cleanup milestone
- [ ] Document post-cleanup integration contract -- after new patterns stabilize
- [ ] Migrate remaining Python business logic to Rust -- separate milestone entirely

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Risk | Priority |
|---------|------------|---------------------|------|----------|
| Remove deprecated modules | MEDIUM | LOW | LOW | P1 |
| Fix global mutable state flags | MEDIUM | LOW | LOW | P1 |
| Add dead code detection to CI | HIGH | LOW | LOW | P1 |
| Remove FormIDAnalyzer sync wrapper | MEDIUM | LOW | LOW | P1 |
| Remove Python fallbacks (verified) | HIGH | MEDIUM | MEDIUM | P1 |
| Consolidate YAML sync/async | HIGH | MEDIUM | MEDIUM | P1 |
| Simplify factory/detector/status | HIGH | MEDIUM | MEDIUM | P2 |
| Remove RustAcceleration coordinator | MEDIUM | MEDIUM | LOW | P2 |
| Unify async entry patterns | MEDIUM | MEDIUM | MEDIUM | P2 |
| Type-narrow factory returns | HIGH | MEDIUM | LOW | P2 |
| Flatten integration layers entirely | HIGH | HIGH | HIGH | P3 |
| Document integration contract | MEDIUM | LOW | LOW | P3 |

**Priority key:**
- P1: Must complete for cleanup milestone
- P2: Should complete if time allows, high ROI for future migration
- P3: Defer to post-milestone or next milestone

## Measurable Outcomes

A successful cleanup is measurable by these concrete metrics:

| Metric | Before (Estimated) | Target After | How to Measure |
|--------|---------------------|-------------|----------------|
| Python fallback files | 8 files | 0 files | `ls ClassicLib/integration/python/` |
| Deprecated markers in prod code | 11 files | 0 files | `grep -r DEPRECATED ClassicLib/` |
| Global mutable state flags | ~6 problematic | 0 problematic | `grep -r "global _" ClassicLib/` audit |
| Integration layer depth | 3 layers (detector + factory + status) | 2 layers (detector + factory) | Code review |
| Duplicate cache implementations | 2 (YAML sync + async caches) | 1 | File count in `io/yaml/` |
| Sync wrapper files | 3+ (FormIDAnalyzer, sync_adapters, bridge_helpers) | 0 transitional | `grep -r create_sync_wrapper ClassicLib/` |
| Dead code in CI | Not checked | 0 violations | CI pipeline green |
| Factory return types using `Any` | ~8 functions | 0 functions | Pyright strict mode |

## Sources

- Direct codebase analysis of `J:\CLASSIC-Fallout4\ClassicLib\` (HIGH confidence)
- `J:\CLASSIC-Fallout4\.planning\codebase\CONCERNS.md` (HIGH confidence -- recent audit)
- `J:\CLASSIC-Fallout4\.planning\codebase\ARCHITECTURE.md` (HIGH confidence)
- `J:\CLASSIC-Fallout4\.planning\codebase\STRUCTURE.md` (HIGH confidence)
- `J:\CLASSIC-Fallout4\.planning\codebase\CONVENTIONS.md` (HIGH confidence)
- `J:\CLASSIC-Fallout4\.planning\codebase\INTEGRATIONS.md` (HIGH confidence)
- Grep results across codebase for patterns: `global _*`, `DEPRECATED`, `create_sync_wrapper` (HIGH confidence)

---
*Feature research for: CLASSIC codebase cleanup and consolidation*
*Researched: 2026-02-01*
