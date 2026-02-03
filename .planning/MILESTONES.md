# Project Milestones: CLASSIC

## v1.0 Codebase Cleanup (Shipped: 2026-02-02)

**Delivered:** Eliminated all redundancies across the Python-Rust hybrid codebase — every piece of logic now lives in exactly one place with clear ownership boundaries, ready for progressive Rust migration.

**Phases completed:** 1-5 (14 plans total)

**Key accomplishments:**

- Removed deprecated code, established 71% coverage baseline, Vulture CI enforcement, and comprehensive singleton reset fixture covering 19+ globals
- Collapsed 3-layer factory/detector/status into single flat factory.py with 13 Protocol types and zero pyright errors
- Reduced file_io/parser/formid wrappers by 60-75% using consistent thin delegation pattern
- Eliminated all sync wrappers and dual-interface patterns; AsyncBridge.run_async() is sole GUI sync mechanism
- Removed all 8 Python fallback implementations and CLASSIC_DISABLE_RUST mechanism; factory raises RuntimeError on missing Rust
- Added validate_rust_modules() startup validation for 6 required Rust modules; PyInstaller build verified

**Stats:**

- 252 files changed across 70 commits
- Net -11,993 lines (10,374 added / 22,367 removed)
- 48,342 lines Python (ClassicLib/)
- 5 phases, 14 plans
- ~23 hours wall clock, ~2.8 hours execution time

**Git range:** `feat(01-02)` → `docs(05)`

**What's next:** Rust migration milestone — migrate remaining Python business logic to Rust -core crates, flatten integration layer, progressive UI migration.

---
