# Project Milestones: CLASSIC

## v9.1.0-root Move Crates to Project Root (Shipped: 2026-04-15)

**Delivered:** Moved the Rust workspace out of `ClassicLib-rs/` into repo-root layer directories, kept wrapper/parity/CI/doc flows working against the new layout, and closed the remaining relocation and integration verification gaps.

**Phases completed:** 7 phases, 33 plans, 44 tasks

**Stats:**

- 735 files changed
- 57,539 insertions / 11,750 deletions
- 3 days from first execution commit to ship
- Audit: `.planning/milestones/v9.1.0-root-MILESTONE-AUDIT.md`

**Git range:** `fdf9ee9d` -> `a04f871d`

**Key accomplishments:**

- Moved the Cargo contract fully to the repo root, including CI, benchmark workflow assumptions, clean proof, and active contributor guidance.
- Relocated the crate tree out of `ClassicLib-rs/` and closed Phase 7 with a 37-crate relocation audit plus repo-root cargo proof.
- Rewired wrapper, native, and parity flows for the moved workspace and refreshed checked-in Python/Node parity artifacts to repo-root paths.
- Proved clean-state replay end to end, including parity gates and GUI packaging, without relying on stale legacy outputs.
- Rewrote active docs, migration guidance, codebase maps, and tripwires so contributors are taught the repo-root layout instead of `ClassicLib-rs`.
- Closed the lingering verification gaps with canonical `07-VERIFICATION.md`, `08-VERIFICATION.md`, and `09-VERIFICATION.md`, so all 11 milestone requirements now trace to current evidence.

**Known Gaps:**

- Non-active and historical docs outside the Phase 10 audited surface still contain some legacy `ClassicLib-rs` references.
- `12-VALIDATION.md` is still missing, so Nyquist coverage for the final gap-closure phase is partial.

**What's next:** Define the next milestone and create a fresh `.planning/REQUIREMENTS.md` with `/gsd-new-milestone`.

---

## v9.1.0 Crate Consolidation (Shipped: 2026-04-12)

**Delivered:** Consolidated the Rust workspace from 19 to 16 business-logic crates while preserving C++/Python/Node parity, green workspace/native validation, and aligned documentation for the surviving owners.

**Phases completed:** 5 phases, 16 plans, 38 tasks

**Stats:**

- 237 files changed
- 64,721 insertions / 25,574 deletions
- 3 days from first execution commit to ship
- Audit: `.planning/milestones/v9.1.0-MILESTONE-AUDIT.md`

**Git range:** `3276fd20` -> `fe4a2ba6`

**Key accomplishments:**

- Merged `classic-yaml-core` into `classic-settings-core`, migrated all bindings and consumers, and taught the parity generators to scan Rust sub-modules so the merged surface stays visible to the gates.
- Merged `classic-crashgen-settings-core` into `classic-config-core`, consolidated its docs into `classic-config-core.md`, and reparented Node parity ownership without introducing drift.
- Redistributed `classic-constants-core` into semantic owners across Rust, Python, Node, CXX, GUI, docs, and refreshed parity artifacts.
- Closed Phase 4 with green workspace tests, CLI/GUI wrapper validation, and plain CXX/Python/Node parity reruns recorded in a single verification artifact.
- Closed milestone cleanup debt by aligning top-level docs routing, Phase 3 verification bookkeeping, and all Node parity contract artifacts to the live one-tier 705-row baseline with durable audit and tripwire checks.

**What's next:** Define the next milestone and create a fresh `.planning/REQUIREMENTS.md` with `/gsd-new-milestone`.

---

## v9.1.0-bindings Full Bindings Parity (Shipped: 2026-04-10)

**Delivered:** Full binding parity across C++, Node, and Python with drift-preventing parity gates on all three surfaces. Every shared Rust crate is now exposed at full fidelity through all three bindings with zero Tier-2 deferrals.

**Phases completed:** 7 phases, 32 plans, 90 tasks

**Stats:**

- ~192 commits over 4 days (2026-04-07 to 2026-04-10)
- 44/45 v1 requirements satisfied (CI-04 branch protection user-deferred)
- 7/7 phases verified passed (all Nyquist-compliant)
- 10/12 cross-phase integration points wired (2 cosmetic issues closed by Phase 7)
- 2/2 end-to-end flows complete
- Audit: `.planning/milestones/v9.1.0-bindings-MILESTONE-AUDIT.md`

**Git range:** v9.1.0-bugfixes tag to `3a08b27c` on main

**Key accomplishments:**

- Built a first-class C++ bridge parity gate (source-only, no build required) with born-green baseline expanding from 202 to 316 entries across 19 modules as the bridge surface widened (Phases 1-2)
- Collapsed Python Tier-1/Tier-2 into a single enforced tier — 1098 tier1Mappings, `deferred_total == 0`, `classic_shared` wired as a gate-enrolled build target with 61 contract rows (Phase 3)
- Collapsed Node Tier-1/Tier-2 into a single enforced tier — all 109 deferred entries promoted, `extractPeVersion`/`isValidPePath` added for PE-version extraction parity (Phase 4)
- Wired all three parity gates (CXX, Python, Node) into CI with triple-gate canary assertion proving new public Rust APIs fail CI until all three bindings cover them (Phase 5)
- Deleted all Tier-2 governance files, rewrote `binding-parity-overview.md` as the harmony-achieved reference, created `binding-parity-policy.md` and `error-contract.md` as new single-source-of-truth docs (Phase 6)
- Closed all cosmetic audit gaps: traceability corrections, CXX baseline path fix, vestigial tier2 label removal from generators, stale comment cleanup (Phase 7)

**Known Gaps:**

- CI-04: Branch protection not configured for CXX parity gate (user-deferred)

---

## v9.1.0-bugfixes CLASSIC Codebase Health (Shipped: 2026-04-07)

**Delivered:** Resolved every concern from the codebase audit — deprecated API removal, dead code elimination, FCX state hardening across bindings, bounded cache replacement with canonical CacheStats, hot-path regex/parser caching with Criterion proof, mmap TOCTOU safety, LazyLock consistency sweep, workspace dependency promotion, Linux Proton docs-path wiring, and committed Node `index.d.ts` governance.

**Phases completed:** 11 phases, 32 plans, 61 tasks (Phases 1-8 planned work plus Phases 9-11 verification gap-closure)

**Internal milestone label during execution:** v1.0 (renamed to v9.1.0-bugfixes at ship time to continue the v8.x project version progression).

**Stats:**

- 154 commits over 4 days (2026-04-04 → 2026-04-07)
- 35/35 v1 requirements satisfied
- 11/11 phases verified passed (all Nyquist-compliant)
- 13/13 cross-phase wiring claims verified
- 8/8 end-to-end flows complete
- Audit: `.planning/milestones/v9.1.0-bugfixes-MILESTONE-AUDIT.md`

**Git range:** `6604979b` (`docs: complete project research`) → `87d3f551` (`Docs: refresh v1.0 milestone audit after Phase 9/10/11 closure`) on `gsd/v1.0-milestone`

**Key accomplishments:**

- Three Python binding methods migrated off deprecated scanlog-core APIs with DeprecationWarning emission via PyO3 PyErr::warn, pytest coverage, and updated .pyi/API docs
- Migrated 3 deprecated shim tests to parse_all_sections_arc, then deleted parse_segments, parse_segments_parallel, is_outdated, SEGMENT_BOUNDARIES, fast_contains, and named_sections_to_positional from scanlog-core
- Assertion test proving production configs never hit legacy fallback, then scan_all_settings_legacy_bucketed method and fallback branch deleted
- Blocking FCX singleton reset with a typed unnecessary outcome and contention-tested stale-state cleanup for downstream bindings.
- C++ bridge FCX reset helper plus automatic pre-scan state cleanup on every public scan session entrypoint.
- Node scanlog bindings now expose flat FCX reset/issue APIs, isolate FCX state across sequential scans, and publish refreshed parity metadata for the new contract.
- 128-entry quick_cache-backed YAML caching with preserved mtime freshness and canonical five-field cache stats
- 64-entry quick_cache-backed settings caching with canonical stats and separate cache_keys helper documentation
- Bounded SHA256 path-hash caching with canonical hits/misses observability via quick_cache
- Node now ships one canonical cache stats contract for YAML, settings, and hash helpers with committed snake_case TypeScript declarations and refreshed parity coverage metadata.
- Python now exposes the Phase 4 cache stats contract for YAML, settings, and hashes, with typed stubs, hash-cache smoke coverage, and parity metadata that tracks the new helper surface.
- C++ bridge cache stats entrypoints for YAML, settings, and hashes with matching parity docs across the active binding surfaces.
- Bounded xxh3-keyed regex matcher caches for mod_detector single/double/batch paths with contributor-facing LazyLock guidance
- Important-mod detection now uses a LeftmostLongest Aho-Corasick literal matcher with fixture-backed parity tests and a retained legacy regex helper for semantic proof.
- Cached `detect_crash_pattern` on one shared `LogParser` while adding positive bridge coverage and documenting the unchanged fail-soft contract.
- Criterion proof coverage for cached regex matchers, important-mod Aho-Corasick scans, and bridge-style crash-pattern parser reuse with a documented local baseline workflow
- Deterministic double-matcher cache reuse proof using scoped compile deltas and grouped-run-safe detector tests
- Shareable Phase 5 benchmark proof with paired hotspot deltas, focused `phase5_` reproduction commands, and mmap ownership clarified for Phase 6
- Important-mod detection now reuses a bounded cached Aho-Corasick matcher, trims real-fixture haystack setup cost, and has proof showing both tracked surfaces beat the legacy regex comparator.
- Large-file reads now use `map_copy_read_only()` with unchanged text decoding and aligned Phase 6 safety documentation.
- Criterion now benchmarks `map`, `map_copy`, and `map_copy_read_only()` in `classic-file-io-core`, with a committed Windows proof showing the safer mapping stays acceptable.
- The Phase 6 mmap benchmark now keeps `map`, `map_copy`, and `map_copy_read_only` coverage intact while isolating benchmark-only unsafe constructors behind explicit helper functions that pass crate clippy validation.
- classic-scanlog-core now uses std::sync::LazyLock and OnceLock for its remaining lazy state, with matching crate-manifest cleanup and updated contributor docs.
- Registry and perf global stores now use std::sync::LazyLock, and the remaining owned direct once_cell manifest/docs references were removed from the Phase 7 target set.
- Workspace-owned `winreg`/`phf` pins plus removal of the `classic-shared-core` `zerovec` workaround with validated `gui-bridge` docs.
- Shared Linux documents-path discovery now prefers a valid Fallout 4 Proton documents path before falling back to the legacy local-share path, with crate-level integration proof and aligned docs.
- The committed Node declaration snapshot is now the documented first-class contract artifact, the `.gitignore` policy no longer contradicts that, and the existing local Node gates passed without needing a declaration diff.
- Phase 1 deprecated API migration now has fresh Rust, Python, and Node closure proof recorded in `01-VERIFICATION.md`, with DEBT-05/06/07/10 traceability synchronized in `REQUIREMENTS.md`.
- Phase 5 now has one coherent verification artifact again: `05-VERIFICATION.md` explicitly covers PERF-03 and CONS-04 with current source, docs, test, and benchmark-backed evidence, and Phase 10 traceability is closed in the planning files.
- Authoritative Phase 8 verification coverage for workspace-owned deps, Proton docs-path proof, gui-bridge cleanup, and Node declaration freshness governance.

---

## v8.3.0 Performance & Polish (Shipped: 2026-02-05)

**Delivered:** Established comprehensive performance infrastructure — Criterion benchmarks across all Rust crates, GIL release audit, profiling tooling, hot path optimization based on data, and CI-based regression detection.

**Phases completed:** 12-18 (15 plans total)

**Key accomplishments:**

- Comprehensive GIL release audit with 65 without_gil occurrences, enabling true Python thread parallelism for CPU-bound Rust operations (GIL-01, GIL-02)
- Criterion benchmark infrastructure with quick/thorough modes, statistical output, and PowerShell runner scripts (BENCH-01 to BENCH-06)
- Profiling tooling: Flamegraph, py-spy (Python+Rust combined stacks), dhat memory profiling, DashMap cache instrumentation (PROF-01 to PROF-03, GIL-03)
- Fixed test_clear_cache parallel pollution with #[serial] and classic_settings() path resolution bug (BUG-01, BUG-02)
- Data-driven optimization: Profiling revealed 86% time in Python threading (not Rust FFI at 0.3%); implemented O(1) membership via set-backed lists
- CI regression detection: GitHub Actions workflow with 10% threshold, PR comments, bypass labels, and branch protection documentation

**Stats:**

- 80 commits over 2 days (2026-02-04 → 2026-02-05)
- 111 files changed, +18,578 / -175 lines
- 7 phases, 15 plans, 14 requirements satisfied
- 77+ Criterion benchmarks across yaml-core, scanlog-core, file-io-core crates
- All tech debt from milestone audit addressed in Phase 18

**Git range:** `feat(12-01)` → `docs(18)`

**What's next:** New milestone — user-facing features, additional Rust acceleration, or maintenance work now that performance infrastructure is in place.

---

## v8.2.0-part2 Rust Migration (Shipped: 2026-02-04)

**Delivered:** Completed Rust migration — Python is now a thin UI shell while Rust owns all business logic (settings, game detection, report generation, orchestration, analysis).

**Phases completed:** 6-11 (14 plans total)

**Key accomplishments:**

- Migrated settings cache to Rust DashMap-based lock-free caching via classic_settings module (SETT-01 to SETT-05)
- Created golden file parity infrastructure with 16 crash logs captured (32 files) for Python-Rust comparison (VAL-01)
- Game detection fully delegated to Rust GamePathFinder with no Python fallback, GlobalRegistry integration (GAME-01 to GAME-04)
- Removed Python orchestrators (1,223 lines); all scanning via Rust OrchestratorCore with parallel processing (ORCH-01 to ORCH-05)
- Report generation through Rust ReportGenerator/ReportComposer for all markdown output (REPT-01 to REPT-04)
- Deleted 7 Python analyzer files; factory returns Rust components directly (INTG-01 to INTG-05)

**Stats:**

- 143 commits over 3 days (2026-02-02 → 2026-02-04)
- 88,594 lines Python, 65,277 lines Rust
- 6 phases, 14 plans, 23 requirements satisfied
- 3,849 tests passing with Rust as primary code path
- PyInstaller build verified with 19 Rust modules bundled

**Git range:** `feat(06-01)` → `feat(11-02)`

**What's next:** Performance benchmarking milestone (PERF-01 to PERF-03) or new features now that Rust foundation is complete.

---

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
