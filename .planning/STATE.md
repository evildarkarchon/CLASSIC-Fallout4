---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_plan: 1
status: verifying
stopped_at: Completed 09-deprecated-api-verification-closure-01-PLAN.md
last_updated: "2026-04-07T03:17:11.276Z"
last_activity: 2026-04-07
progress:
  total_phases: 11
  completed_phases: 9
  total_plans: 30
  completed_plans: 30
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-04)

**Core value:** Every concern identified in the codebase audit is resolved -- no silent legacy paths, no dead code, no unbounded caches, and all binding surfaces expose consistent, complete APIs.
**Current focus:** Phase 09 — deprecated-api-verification-closure

## Current Position

Phase: 09 (deprecated-api-verification-closure) — EXECUTING
Plan: 1 of 1
Current Plan: 1
Status: Phase complete — ready for verification
Last activity: 2026-04-07

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**

- Total plans completed: 29
- Average duration: 15min
- Total execution time: 7.75 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 08-workspace-and-infrastructure | 3 | 43min | 14min |

**Recent Trend:**

- Last 5 plans: 07-02 (5min), 08-01 (13min), 08-02 (19min), 08-03 (11min)
- Trend: completed

*Updated after each plan completion*
| Phase 02 P02 | 9min | 2 tasks | 5 files |
| Phase 02 P01 | 11min | 2 tasks | 2 files |
| Phase 02 P03 | 6min | 2 tasks | 1 files |
| Phase 03 P01 | 0 min | 2 tasks | 3 files |
| Phase 03 P02 | 6 min | 2 tasks | 2 files |
| Phase 03 P03 | 8 min | 3 tasks | 10 files |
| Phase 04 P02 | 3 | 2 tasks | 3 files |
| Phase 04-bounded-cache-replacement P03 | 4min | 2 tasks | 2 files |
| Phase 04-bounded-cache-replacement P01 | 7min | 2 tasks | 4 files |
| Phase 04-bounded-cache-replacement P06 | 11min | 2 tasks | 6 files |
| Phase 04-bounded-cache-replacement P04 | 8 min | 2 tasks | 12 files |
| Phase 04-bounded-cache-replacement P05 | 15min | 2 tasks | 13 files |
| Phase 05-pattern-caching-and-performance P03 | 4min | 2 tasks | 2 files |
| Phase 05-pattern-caching-and-performance P01 | 8min | 2 tasks | 3 files |
| Phase 05-pattern-caching-and-performance P02 | 9min | 2 tasks | 1 files |
| Phase 05-pattern-caching-and-performance P04 | 12min | 2 tasks | 3 files |
| Phase 05-pattern-caching-and-performance P05 | 18min | 2 tasks | 2 files |
| Phase 05-pattern-caching-and-performance P06 | 43min | 2 tasks | 5 files |
| Phase 05-pattern-caching-and-performance P07 | 17min | 3 tasks | 3 files |
| Phase 06 P01 | 1 min | 2 tasks | 4 files |
| Phase 06 P02 | 6 min | 2 tasks | 3 files |
| Phase 06 P03 | 1 min | 1 tasks | 1 files |
| Phase 07 P01 | 7h 8m | 2 tasks | 13 files |
| Phase 07 P02 | 5 min | 2 tasks | 11 files |
| Phase 08-workspace-and-infrastructure P01 | 13min | 2 tasks | 5 files |
| Phase 08-workspace-and-infrastructure P02 | 19min | 2 tasks | 7 files |
| Phase 08-workspace-and-infrastructure P03 | 11min | 2 tasks | 4 files |
| Phase 09-deprecated-api-verification-closure P01 | 3min | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: TS-2 (deprecated API migration) must complete before TS-1 (dead code removal) -- `deprecated = "deny"` lint constraint
- [Roadmap]: Tests and benchmarks accompany their feature phases, not in a separate test phase
- [Roadmap]: CONS-02 (FCX error returns) paired with SAFE-01 (FCX fix) in Phase 3
- [Roadmap]: CONS-03 (CacheStats) paired with CACHE-01/02/03 in Phase 4
- [Roadmap]: Phase 7 (LazyLock sweep) depends on Phases 4 and 5 since both introduce new LazyLock usage
- [01-01]: Followed D-05 -- expanded check_version_status test coverage beyond minimal equivalents to include VR-specific edge cases
- [Phase 02]: Renamed yaml_config_benchmarks to yaml_operations_benchmarks since config variants no longer exist
- [Phase 02]: Removed unused memchr imports after fast_contains deletion (only consumer of those symbols)
- [Phase 02]: Kept once_cell::sync::Lazy import in parser.rs -- still used by COMMON_PATTERNS and CRASHGEN_HEADER_PATTERN
- [Phase 02]: Removed orphaned has_real_buffout_module from settings_validator.rs -- orchestrator.rs retains its own copy
- [Phase 03]: Use blocking GLOBAL_FCX_HANDLER.lock() for FCX reset so contention cannot silently skip cleanup.
- [Phase 03]: Treat an already-clean FCX singleton as Err(FcxResetError::Unnecessary) so bindings can keep the no-op path benign.
- [Phase 03]: Keep the C++ FCX surface reset-only in Phase 3
- [Phase 03]: Preserve existing C++ batch signatures by short-circuiting with failed batch DTOs on reset failure
- [Phase 03]: Keep Node FCX diagnostics behind resetFcxGlobalState() and getFcxConfigIssues() instead of extending JsAnalysisResult.
- [Phase 03]: Populate FCX issue state in the Node adapter from existing ClassicConfig/scangame helpers so binding code stays thin.
- [Phase 03]: Track FcxResetError as deferred Tier-2 parity while runtime-verifying the new Node-only FCX exports.
- [Phase 04]: Use LazyLock<quick_cache::sync::Cache<...>> with capacity 64 for SETTINGS_CACHE.
- [Phase 04]: Keep cache_keys() as the only public key-listing helper while CacheStats stays canonical.
- [Phase 04]: Validate bounded quick_cache behavior by capacity and stats, not exact eviction victim order.
- [Phase 04]: Keep cache_size() as a compatibility adapter over the canonical hash cache stats.
- [Phase 04]: Validate hash cache boundedness through quick_cache capacity and stats behavior instead of strict victim-order assertions.
- [Phase 04]: Use quick_cache::sync::Cache with fixed capacity 128 while keeping YAML mtime validation and custom hit/miss counters.
- [Phase 04]: Keep legacy get_cache_stats() as an adapter over canonical stats plus YAML-specific total_bytes detail.
- [Phase 04]: Serialize YAML integration cache tests so clear/reset helpers remain deterministic without cache-internal assertions.
- [Phase 04-bounded-cache-replacement]: Keep the bridge layer adapter-only: cache stats are computed in Rust core crates and only reshaped for CXX transport.
- [Phase 04-bounded-cache-replacement]: Keep legacy *_cache_size helpers as compatibility shims over the canonical stats DTO instead of removing them mid-phase.
- [Phase 04-bounded-cache-replacement]: Preserve exact snake_case cache stat names in Node by using explicit NAPI naming overrides and typed return annotations.
- [Phase 04-bounded-cache-replacement]: Classify the new hash cache helpers as runtime-verified Tier-2 aux coverage in the Node registry.
- [Phase 04-bounded-cache-replacement]: Validate bounded hash cache behavior through capacity and stats counters instead of eviction-victim order assertions.
- [Phase 04-bounded-cache-replacement]: Use explicit TypedDict cache stats aliases in Python stubs so the canonical five-field contract is visible to static tooling.
- [Phase 04-bounded-cache-replacement]: Track Python hash cache helpers as registry-only Tier-2 runtime coverage instead of broadening the Python parity parser to every aux module.
- [Phase 04-bounded-cache-replacement]: Keep FileHasher.cache_size() as a deferred compatibility adapter while cache_stats/reset_cache_stats own the Phase 4 runtime smoke contract.
- [Phase 05-pattern-caching-and-performance]: Kept bridge regression coverage focused on observable main_error output instead of parser internals.
- [Phase 05-pattern-caching-and-performance]: Reused one module-level default LogParser with LazyLock while preserving empty-string fail-soft behavior for parse failures.
- [Phase 05-pattern-caching-and-performance]: Keep single, double, and batch matcher caches separate while sharing normalization and compile helpers.
- [Phase 05-pattern-caching-and-performance]: Validate bounded matcher caches by reuse and capacity behavior instead of eviction-victim order.
- [Phase 05-pattern-caching-and-performance]: Kept the legacy regex path as a private helper so fixture-backed parity stays executable while detect_mods_important uses Aho-Corasick.
- [Phase 05-pattern-caching-and-performance]: Used the large crash-log fixture for important-mod parity because the smaller fixture lacks a plugin section.
- [Phase 05-pattern-caching-and-performance]: Kept the Aho-Corasick automaton one-per-call in PERF-02 and deferred cache reuse to later performance proof work.
- [Phase 05-pattern-caching-and-performance]: Kept Phase 5 performance proof in the existing scanlog Criterion harness and mirrored bridge crash-pattern behavior with a Rust helper instead of an FFI benchmark.
- [Phase 05-pattern-caching-and-performance]: Primed cached single and batch matchers before timed loops and used Criterion iter_batched to avoid timing benchmark input setup.
- [Phase 05-pattern-caching-and-performance]: Scoped the legacy important-mod regex helper to tests after bench verification exposed a dead-code lint failure in non-test builds.
- [Phase 05-pattern-caching-and-performance]: Measured the double-matcher reuse proof with a scoped compile-count snapshot instead of an absolute global counter.
- [Phase 05-pattern-caching-and-performance]: Serialized detect_mods_double regression tests so grouped runs cannot pollute the shared double-matcher compile counter.
- [Phase 05-pattern-caching-and-performance]: Focused the save/compare workflow on the phase5_ benchmark groups so proof runs stay bounded to the locked hotspots.
- [Phase 05-pattern-caching-and-performance]: Added paired before/after benchmark variants in the existing harness because same-revision Criterion baseline comparisons alone cannot prove hotspot deltas.
- [Phase 05-pattern-caching-and-performance]: Moved mmap throughput ownership out of PERF-04 and into SAFE-05 / Phase 6 to match the roadmap and actual harness scope.
- [Phase 05-pattern-caching-and-performance]: Reused the repo-standard LazyLock + quick_cache bounded cache pattern for important-mod matcher reuse once the synthetic compile-only slice proved per-call automaton construction was the main regression source.
- [Phase 05-pattern-caching-and-performance]: Preserved the existing Aho-Corasick, LeftmostLongest, and combined plugin/XSE haystack semantics while optimizing setup cost instead of parity-sensitive matching behavior.
- [Phase 05-pattern-caching-and-performance]: Skipped plugin-name set construction unless an important-mod entry actually uses exclude_when because the real-fixture slices showed haystack preparation dominated the remaining cost.
- [Phase 06]: Use MmapOptions::map_copy_read_only() on all platforms for the 1 MB+ read_file_mmap branch.
- [Phase 06]: Document the mmap change conservatively as a safer snapshot-style mitigation rather than a blanket upstream safety guarantee.
- [Phase 06]: Keep the Phase 6 throughput proof in classic-file-io-core's existing file_io_benchmarks harness instead of creating a new benchmark target.
- [Phase 06]: Treat map_copy_read_only() as acceptable for Windows validation because it wins at 1 MiB+4 KiB and 4 MiB and stays below a 10% slowdown even when 16 MiB crosses the 5% warning bar.
- [Phase 06]: Keep the Phase 6 benchmark contract unchanged and move the three unsafe mmap constructors into narrowly allowed helper functions instead of weakening lint policy.
- [Phase 07]: Used TDD audit tests to lock the std LazyLock/OnceLock migration contract before implementation.
- [Phase 07]: Kept RecordScanner on per-instance get_or_init semantics by swapping OnceCell to OnceLock instead of redesigning construction flow.
- [Phase 07]: Use std::sync::LazyLock with DashMap::new for registry and perf globals to match the Phase 4/5 repo pattern without API churn.
- [Phase 07]: Treat Phase 7 success as removal of owned direct once_cell usage and manifest declarations, while allowing transitive lockfile once_cell entries to remain.
- [Phase 08-workspace-and-infrastructure]: Promoted winreg and phf into ClassicLib-rs/Cargo.toml without changing pinned versions so member crates only inherit ownership.
- [Phase 08-workspace-and-infrastructure]: Removed the classic-shared-core zerovec workaround outright and documented gui-bridge as building directly from workspace Slint dependencies after build proof passed.
- [Phase 08-workspace-and-infrastructure]: Kept Linux documents-path ownership in DocsPathFinder and reused the existing Proton helpers instead of duplicating logic in bindings.
- [Phase 08-workspace-and-infrastructure]: Treated classic-node/index.d.ts as the tracked generated Node contract artifact and kept the existing freshness/parity workflow as the only enforcement path.
- [Phase 09-deprecated-api-verification-closure]: Closed Phase 1 by rewriting the existing verification artifact in repo-standard re-verification form instead of adding a separate Phase 09 verification file
- [Phase 09-deprecated-api-verification-closure]: Recorded fresh Rust, Python, and Node command results directly in the verification artifact and treated prior summaries as provenance only

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1]: The `deprecated = "deny"` lint requires careful sequencing -- temporarily relax to `warn`, migrate, then restore
- [Phase 5]: AhoCorasick semantic parity must be verified against test fixtures before removing regex path
- [Phase 6]: Windows `map_copy_read_only()` behavior must be empirically validated, not inferred from Linux

## Session Continuity

Last session: 2026-04-07T03:17:11.272Z
Stopped at: Completed 09-deprecated-api-verification-closure-01-PLAN.md
Resume file: None
