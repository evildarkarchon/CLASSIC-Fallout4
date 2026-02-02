# Roadmap: CLASSIC Codebase Cleanup

## Overview

This cleanup milestone proceeds bottom-up through dependency layers: remove dead code and fix global state (low risk, high noise reduction), simplify the integration layer (clarify ownership boundaries), thin out fat Python wrappers by moving logic to Rust (highest impact), consolidate dual sync/async interfaces (remove deprecated patterns), and finally prune Python fallback files (irreversible, requires proven Rust stability). Each phase unblocks the next by reducing ambiguity about what is live, what is dead, and where logic belongs.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation Cleanup** - Remove dead code, fix global state, establish tooling baselines
- [x] **Phase 2: Integration Layer Simplification** - Flatten factory/detector/status indirection and remove acceleration coordinator
- [x] **Phase 3: Wrapper Thinning** - Move business logic from fat Python wrappers into Rust -core crates
- [x] **Phase 4: Interface Consolidation** - Remove sync wrappers and dual-interface patterns
- [ ] **Phase 5: Fallback Pruning** - Remove Python fallback implementations and type-narrow factory returns

## Phase Details

### Phase 1: Foundation Cleanup
**Goal**: The codebase contains only live code, global state is test-friendly, and CI prevents dead code regression
**Depends on**: Nothing (first phase)
**Requirements**: DEAD-01, DEAD-02, DEAD-03, DEAD-04, GLOB-01, GLOB-02, GLOB-03
**Success Criteria** (what must be TRUE):
  1. `grep -r "DEPRECATED" ClassicLib/ --include="*.py" -l` returns only files with Phase 4+ deprecation notices (FormIDAnalyzer.py sync wrappers); no Phase 1 deprecated modules (database_rust.py, _DeprecatedVersion) remain
  2. `uv run vulture ClassicLib/` runs in CI and reports 0 violations (dead code detection enforced)
  3. `cargo build --workspace` succeeds with no stub/empty crates remaining (all audited, stubs removed)
  4. `uv run pytest --cov=ClassicLib --cov-report=term` produces a baseline report and all 0%-coverage modules have been evaluated for deletion
  5. No `global _*` mutable flags remain in ClassicLib/ -- all replaced with instance variables, lru_cache, or singletons with reset() methods; `reset_all_singletons()` autouse fixture exists and passes
**Plans**: 4 plans

Plans:
- [x] 01-01-PLAN.md -- Dead code removal (remove deprecated files, verify Rust crates, establish coverage baseline)
- [x] 01-02-PLAN.md -- CI tooling setup (install vulture, curate whitelist, add to CI pipeline)
- [x] 01-03-PLAN.md -- Global state cleanup (replace mutable flags, audit globals, add reset fixture)
- [x] 01-04-PLAN.md -- Gap closure (fix test MessageHandler init, refine DEPRECATED criterion scope)

### Phase 2: Integration Layer Simplification
**Goal**: The Python-Rust integration boundary uses a single-layer factory with direct try-import, no redundant detection/caching layers
**Depends on**: Phase 1
**Requirements**: ARCH-01, ARCH-02, ARCH-03
**Success Criteria** (what must be TRUE):
  1. `ClassicLib/integration/factory/` is a single `factory.py` module (not a subpackage) using try-import pattern with no `_components_cache` or `_detection_cache` dictionaries
  2. `ClassicLib/acceleration/` directory does not exist (coordinator, metrics, types, workload removed after usage audit)
  3. All factory function return types are specific Rust types (no `Any` annotations remain in factory signatures); `uv run pyright ClassicLib/integration/factory.py` passes with 0 errors
  4. `uv run pytest -n auto` passes with no regressions from integration layer changes
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md -- Factory flattening (collapse factory/ subpackage + detector.py + status.py into single flat factory.py, update all caller import paths)
- [x] 02-02-PLAN.md -- Acceleration removal and type narrowing (delete acceleration/ package, create Protocol types, narrow factory return types, pass pyright)

### Phase 3: Wrapper Thinning
**Goal**: Python wrappers in ClassicLib/integration/rust/ are thin adapters (type conversion only), with business logic living in Rust -core crates
**Depends on**: Phase 2
**Requirements**: ARCH-04
**Success Criteria** (what must be TRUE):
  1. `file_io_rust.py` is under 200 lines (down from 39KB/~1000+ lines), containing only type conversion and PyO3 call delegation
  2. `parser` and `formid` Rust wrappers are each under 150 lines, with business logic moved to corresponding Rust `-core` crates
  3. `cargo test --workspace` passes with expanded Rust test coverage for migrated logic
  4. `uv run pytest -n auto` passes with no regressions; application behavior identical
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md -- FileIO wrapper thinning (937 lines -> 230, removed SyncWrapper and convenience functions)
- [x] 03-02-PLAN.md -- Parser and FormID wrapper thinning (321 + 326 lines -> 122 + 128, removed hasattr/legacy patterns)

### Phase 4: Interface Consolidation
**Goal**: The codebase has exactly two async patterns -- native async (CLI/TUI) and AsyncBridge (GUI) -- with no deprecated sync wrappers
**Depends on**: Phase 3
**Requirements**: REDN-01, REDN-02, REDN-04
**Success Criteria** (what must be TRUE):
  1. `FormIDAnalyzer.py` sync wrapper file does not exist (156-line deprecated wrapper removed); all callers use FormIDAnalyzerCore directly
  2. `ClassicLib/io/yaml/sync/` directory does not exist; YAML access is async-only with sync wrappers at GUI entry points only
  3. `grep -r "create_sync_wrapper" ClassicLib/` returns 0 results; `_async_utils/bridge_helpers.py` and `io/files/sync_adapters.py` do not exist
  4. GUI launches and performs crash log scan without freezing or deadlocking (manual smoke test)
**Plans**: 3 plans

Plans:
- [x] 04-01-PLAN.md -- FormID sync wrapper removal (REDN-01 -- delete FormIDAnalyzer.py, update callers to FormIDAnalyzerCore)
- [x] 04-02-PLAN.md -- Bridge helper + sync adapter removal (REDN-04 -- remove create_sync_wrapper, delete bridge_helpers.py and sync_adapters.py, migrate callers)
- [x] 04-03-PLAN.md -- YAML sync/ directory consolidation (REDN-02 -- move sync/ files to parent yaml/, delete sync/ directory, GUI smoke test)

### Phase 5: Fallback Pruning
**Goal**: Python fallback implementations are removed where Rust is proven stable, and factory returns typed Rust objects directly
**Depends on**: Phase 4
**Requirements**: REDN-03
**Success Criteria** (what must be TRUE):
  1. `ClassicLib/integration/python/` contains at most 2-3 files (down from 8), only for components where Rust stability is not yet proven on all platforms
  2. Factory functions that previously returned fallback Python implementations now raise clear errors (not silent fallback) when Rust is unavailable
  3. PyInstaller build succeeds and the resulting executable runs crash log scan correctly (no ModuleNotFoundError from removed fallbacks)
  4. `CLASSIC.spec` hiddenimports list is updated to remove references to deleted Python fallback modules
**Plans**: 3 plans

Plans:
- [ ] 05-01-PLAN.md -- Remove 5 easy fallbacks (database, file_io, formid, record, report) + remove CLASSIC_DISABLE_RUST mechanism
- [ ] 05-02-PLAN.md -- Remove 3 hard fallbacks (parser, mod_detector, plugin) with rust wrapper cleanup + delete integration/python/ directory
- [ ] 05-03-PLAN.md -- Add startup Rust validation, clean spec files, PyInstaller build verification

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation Cleanup | 4/4 | Complete | 2026-02-02 |
| 2. Integration Layer Simplification | 2/2 | Complete | 2026-02-02 |
| 3. Wrapper Thinning | 2/2 | Complete (accepted deviations) | 2026-02-02 |
| 4. Interface Consolidation | 3/3 | Complete | 2026-02-02 |
| 5. Fallback Pruning | 0/3 | Not started | - |
