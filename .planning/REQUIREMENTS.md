# Requirements: CLASSIC Codebase Cleanup

**Defined:** 2026-02-01
**Core Value:** Every piece of logic lives in exactly one place, and it's obvious where things belong -- so future Rust migration is straightforward rather than archaeological.

## v1 Requirements

Requirements for the cleanup milestone. Each maps to roadmap phases.

### Dead Code Removal

- [x] **DEAD-01**: Remove all files with DEPRECATED markers (11 files identified across ClassicLib/)
- [x] **DEAD-02**: Add vulture dead code detection to CI pipeline to prevent regression
- [x] **DEAD-03**: Audit all 39 Rust crates (21 business-logic + 18 python-bindings) and remove stub/empty crates
- [x] **DEAD-04**: Establish test coverage baseline with pytest --cov and identify 0% coverage modules as deletion candidates

### Global State Cleanup

- [x] **GLOB-01**: Replace mutable global flags (_VERSION_WARNING_LOGGED and similar) with instance variables or functools.lru_cache with cache_clear()
- [x] **GLOB-02**: Audit and categorize all 19 `global _*` instances: lazy-init caches (keep), mutable flags (replace with instance state), test-hostile (add reset methods)
- [x] **GLOB-03**: Add reset_all_singletons() autouse fixture for comprehensive test isolation across all singleton state

### Redundancy Removal

- [ ] **REDN-01**: Remove FormIDAnalyzer sync wrapper (156 lines wrapping FormIDAnalyzerCore with deprecated create_sync_wrapper)
- [ ] **REDN-02**: Consolidate YAML sync/async split -- merge parallel sync/ and async_/ cache implementations into async-only with sync wrappers at GUI entry points only
- [ ] **REDN-03**: Remove Python fallback implementations (8 files in ClassicLib/integration/python/) after verifying Rust wheel bundling and test coverage equivalence
- [ ] **REDN-04**: Remove all create_sync_wrapper usage and transitional bridge helpers (_async_utils/bridge_helpers.py, io/files/sync_adapters.py)

### Architecture Simplification

- [ ] **ARCH-01**: Simplify factory/detector/status three-layer indirection -- collapse to single-layer factory with try-import pattern, remove duplicate caching between _components_cache and _detection_cache
- [ ] **ARCH-02**: Remove or simplify RustAcceleration coordinator package (ClassicLib/acceleration/ -- coordinator.py, metrics.py, types.py, workload.py, ~400 lines) after auditing runtime usage
- [ ] **ARCH-03**: Type-narrow all factory function returns from Any to specific Rust types (~8 factory functions), enabling Pyright strict mode to catch errors
- [ ] **ARCH-04**: Thin out fat Python wrappers by moving business logic from ClassicLib/integration/rust/ wrappers into Rust -core crates (file_io_rust.py 39KB, parser 15KB, formid 16KB)

## v2 Requirements

Deferred to future Rust migration milestone. Tracked but not in current roadmap.

### Rust Migration

- **MIGR-01**: Migrate remaining Python business logic (scanning orchestration) to Rust -core crates
- **MIGR-02**: Flatten integration layer entirely -- direct Rust imports replacing factory pattern
- **MIGR-03**: Move GUI event handling to Rust (Slint or similar)

### Documentation

- **DOCS-01**: Document post-cleanup integration contract (single-page reference for how Python calls Rust)
- **DOCS-02**: Update all development guides to reflect simplified architecture

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| New feature development | This milestone is cleanup only |
| UI/UX changes | No user-visible changes unless simplification demands it |
| Performance optimization | Unless it falls out of removing redundancy |
| New Rust crates | No new crates, only cleaning existing ones |
| Remove CLASSIC_DISABLE_RUST env var | Still useful for debugging Rust loading issues -- change behavior to log error instead of silent fallback |
| Convert all singletons to dependency injection | Desktop app singletons (MessageHandler, GlobalRegistry) are legitimate -- fix problematic ones, keep architectural ones |
| Rewrite integration/factory from scratch | High regression risk -- simplify incrementally instead |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DEAD-01 | Phase 1 | Complete |
| DEAD-02 | Phase 1 | Complete |
| DEAD-03 | Phase 1 | Complete |
| DEAD-04 | Phase 1 | Complete |
| GLOB-01 | Phase 1 | Complete |
| GLOB-02 | Phase 1 | Complete |
| GLOB-03 | Phase 1 | Complete |
| REDN-01 | Phase 4 | Pending |
| REDN-02 | Phase 4 | Pending |
| REDN-03 | Phase 5 | Pending |
| REDN-04 | Phase 4 | Pending |
| ARCH-01 | Phase 2 | Pending |
| ARCH-02 | Phase 2 | Pending |
| ARCH-03 | Phase 2 | Pending |
| ARCH-04 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0

---
*Requirements defined: 2026-02-01*
*Last updated: 2026-02-01 after Phase 1 completion*
