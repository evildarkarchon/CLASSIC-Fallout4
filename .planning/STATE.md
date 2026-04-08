---
gsd_state_version: 1.0
milestone: v9.1.0
milestone_name: milestone
current_plan: 1
status: executing
stopped_at: Completed 03-03-scanlog-wave2-detection-and-analysis-PLAN.md
last_updated: "2026-04-08T22:43:59.121Z"
last_activity: 2026-04-08
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 21
  completed_plans: 14
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-06)

**Core value:** Every shared Rust crate is exposed at full fidelity through C++, Node, and Python — no Tier-2 deferrals, no narrowing, with parity gates that prevent future drift on all three surfaces.
**Current focus:** Phase 03 — python-tier-collapse

## Current Position

Phase: 03 (python-tier-collapse) — EXECUTING
Plan: 4 of 10
Current Plan: 1
Status: Ready to execute
Last activity: 2026-04-08

Progress: [          ] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 31
- Average duration: 15min
- Total execution time: 7.75 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 08-workspace-and-infrastructure | 3 | 43min | 14min |

**Recent Trend:**

- Last 5 plans: 08-01 (13min), 08-02 (19min), 08-03 (11min), 09-01 (3min), 10-01 (12min)
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
| Phase quick-260406-syy-resolve-the-newly-uncovered-python-parit P01 | 8min | 2 tasks | 6 files |
| Phase 11-workspace-infra-verification-completion P01 | 5min | 2 tasks | 2 files |
| Phase 01-cxx-parity-gate-tooling P01 | 6min | 2 tasks | 11 files |
| Phase 01-cxx-parity-gate-tooling P02 | 8min | 2 tasks | 8 files |
| Phase 01-cxx-parity-gate-tooling P03 | 4min | 2 tasks | 5 files |
| Phase 02-cxx-bridge-surface-expansion P01 | 27min | 2 tasks | 9 files |
| Phase 02-cxx-bridge-surface-expansion P02 | 27min | 2 tasks | 12 files |
| Phase 02-cxx-bridge-surface-expansion P03 | 13min | 2 tasks | 11 files |
| Phase 02 P04 | 27 | 3 tasks | 11 files |
| Phase 02-cxx-bridge-surface-expansion P05 | 8min | 2 tasks | 7 files |
| Phase 02 P06 | 9 | 2 tasks | 8 files |
| Phase 02 P07 | 562 | 3 tasks | 7 files |
| Phase 02 P08 | 1860 | 3 tasks | 7 files |
| Phase 03-python-tier-collapse P01 | 13min | 5 tasks | 20 files |
| Phase 03-python-tier-collapse P02 | 11min | 4 tasks | 19 files |
| Phase 03-python-tier-collapse P03 | 12min | 5 tasks | 18 files |

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
- [Phase 10-pattern-caching-verification-backfill]: Refreshed the original Phase 5 verification artifact in place so PERF-03 and CONS-04 now have current explicit evidence without creating a parallel closure file
- [Phase 10-pattern-caching-verification-backfill]: Verified CONS-04 against the accepted bounded-cache plus true-constant LazyLock rule instead of inventing a fake static-regex refactor in mod_detector
- [Phase quick-260406-syy-resolve-the-newly-uncovered-python-parit]: Kept FcxResetError as a deferred Tier-2 Python gap and refreshed only the required runtime coverage summaries.
- [Phase 11-workspace-infra-verification-completion]: Created the missing authoritative report in the original Phase 8 folder instead of inventing a Phase 11-only verification artifact.
- [Phase 11-workspace-infra-verification-completion]: Kept Phase 8 summaries as provenance only and promoted the exact validation commands into direct requirement evidence rows.
- [Phase 11-workspace-infra-verification-completion]: Recorded INFRA-05 as one Node governance bundle covering the tracked snapshot, freshness script, local gates, and CI workflow together.
- [Roadmap v9.1.0-bindings]: Phase numbering reset to 1 for new milestone (--reset-phase-numbers applied at /gsd:new-milestone)
- [Roadmap v9.1.0-bindings]: CXX gate tooling (Phase 1) must precede CXX bridge expansion (Phase 2) — gate is the acceptance criterion for bridge surface changes
- [Roadmap v9.1.0-bindings]: Python collapse (Phase 3) and Node collapse (Phase 4) are independent — can run in parallel with each other and with CXX work
- [Roadmap v9.1.0-bindings]: HARM-01/02 (PE-version) bundled with Node collapse Phase 4; HARM-03/04 (classic_shared) bundled with Python collapse Phase 3; HARM-05 (error-contract doc) in Phase 6
- [Roadmap v9.1.0-bindings]: CI enforcement (Phase 5) depends on all three gate phases (1, 3, 4) being complete before branch protection is wired
- [Roadmap v9.1.0-bindings]: Documentation reset (Phase 6) is last — governance file deletion MUST follow gate green status and CI enforcement
- [Phase 01-cxx-parity-gate-tooling]: Use regex+balanced-brace counter hybrid for CXX bridge parser; pure regex cannot handle nested struct/extern blocks.
- [Phase 01-cxx-parity-gate-tooling]: Skip struct/enum names that fall inside extern blocks via pre-computed extern spans to avoid cross-attribution between cxx shared types and extern items.
- [Phase 01-cxx-parity-gate-tooling]: Sort entries by (bridgeModule, kind, rustSymbol) and use sha256[:16] of f'{rustSymbol}:{kind}:{bridgeModule}' for deterministic id field.
- [Phase 01-cxx-parity-gate-tooling]: When fixture filename and intended bridgeModule differ in synthetic test layouts, install the fixture file at src/<bridgeModule>.rs so the documented filename-stem rule keeps holding.
- [Phase 01-cxx-parity-gate-tooling]: Compare contract rows by sha256 id and exclude sourceFile from semantic comparison so file moves do not register as drift
- [Phase 01-cxx-parity-gate-tooling]: Bootstrap writes a placeholder cxx_gate_report.md and reconciliation requires one --update-baseline run; this sequence is baked into _bootstrap_synthetic_gate
- [Phase 01-cxx-parity-gate-tooling]: Lock schema_version=1 in parity_contract.json so future schema migrations have a discriminator
- [Phase 01-cxx-parity-gate-tooling]: Use synthetic single-file _SIMPLE_BRIDGE under tmp_path for hermetic drift integration tests
- [Phase 01-cxx-parity-gate-tooling]: CXX parity gate contributor doc (docs/api/cxx-parity-gate.md) follows a 7-section structure: Overview, Local Run, Refresh Workflow, Bootstrap From Scratch, Contract Row Schema, build.rs Relationship, Ephemeral vs Committed Artifacts, CI Integration
- [Phase 01-cxx-parity-gate-tooling]: Bridge crate .gitignore hides parity-artifacts/ with a trailing-slash directory pattern and an inline comment referencing D-08 and the regeneration command so future contributors find the rationale in-source
- [Phase 01-cxx-parity-gate-tooling]: VALIDATION.md task IDs use pytest ClassName::test_method form (e.g., TestParseExternRust::test_parse_extern_rust_functions) to match Plan 01's actual test layout so every automated command is runnable as-is
- [Phase 02-cxx-bridge-surface-expansion]: Adapted bridge wrappers to REAL classic-path-core API signatures (Path-taking functions, instance-based BackupManager, GamePathFinder method instead of free fn for find_game_path)
- [Phase 02-cxx-bridge-surface-expansion]: GUI D-10 clean build uses system-fallback Qt from main repo vcpkg_installed -- worktree lacks pre-built Qt, main repo has it at J:/CLASSIC-Fallout4/classic-gui/build/vcpkg_installed
- [Phase 02-cxx-bridge-surface-expansion]: parity_contract.json requires generate_baseline.py --write-baseline (not just --update-baseline) to refresh the contract entries; --update-baseline only syncs diff/gate reports
- [Phase 02-cxx-bridge-surface-expansion]: Added constants.rs to corrosion_add_cxxbridge FILES lists in both CMakeLists.txt — Corrosion requires explicit enumeration to generate cxxbridge headers, same pattern as path.rs in 02-01
- [Phase 02-cxx-bridge-surface-expansion]: WebGameId declared as a second shared enum in web.rs bridge block because CXX shared enums cannot cross bridge module boundaries — same repr(u8) discriminants as classic::constants::GameId for direct integer cast
- [Phase 02-cxx-bridge-surface-expansion]: xse.rs typed API uses real classic-xse-core &Path-taking signatures — Path::new(s) conversion at bridge boundary (Codex LOW correction)
- [Phase 02-cxx-bridge-surface-expansion]: version_registry_get_all_for_game uses get_all() iteration with manual filter — equivalent to registry.get_all_for_game but avoids coupling to that optional helper
- [Phase 02-cxx-bridge-surface-expansion]: D-08 shims in game.rs call core crates directly — no cross-bridge-module calls; duplication intentional per D-08
- [Phase 02-cxx-bridge-surface-expansion]: BA2 free-fn wrappers use internal BA2Scanner::new() + scan_archive() per call - acceptable since per-archive scans are bounded
- [Phase 02-cxx-bridge-surface-expansion]: CXX shared enum types generated by cxx-build do not derive Debug; test assertions must use matches! without {:?} format specifiers
- [Phase 02]: WryeSeverity uses 3 real variants (Info/Warning/Error) not 4 — no Note variant in classic-scangame-core
- [Phase 02]: CXXS-04 complete: scangame bridge parity baseline at 305 entries (was 288) with 0 drift
- [Phase 02]: Suspect-stack rules flattened (SuspectStackRuleMetadataDto + separate count getter) to clear Pitfall 6 per Codex HIGH
- [Phase 02]: FormIdEntryDto.found derived from Ok(Some(_)) semantics for accurate miss detection
- [Phase 02]: D-11 N/A justified with grep evidence: no current call sites for typed FormID or suspect-rule readers in C++ frontends
- [Phase 02]: Pre-existing FCX global-state tests annotated with serial_test::serial to fix test isolation race (Rule 2 auto-fix)
- [Phase 02]: GUI D-10 final verification used system-fallback Qt preset because worktree vcpkg lacks pre-built Qt
- [Phase 02]: FINAL Phase 2 parity baseline at 316 entries (314+2 for FcxIssueDto+get_fcx_config_issues); CXXS-01..CXXS-10 all satisfied
- [Phase 03-python-tier-collapse]: Pitfall 4 audit walks pub mod reachability graph and classifies orphan files as Known Exclusions (dead code), not blocking failures
- [Phase 03-python-tier-collapse]: _OWNER_RENDER_ORDER derives from RUST_OWNER_BY_CRATE.values() + ('aux',) so new crates propagate automatically to rendered gap tables
- [Phase 03-python-tier-collapse]: Pitfall 2 guard runs between parse_rust_surface and generate_diff_report in check_parity_gate.py::main(); prints actionable remediation to stderr and exits 1
- [Phase 03-python-tier-collapse]: Expanded generate_wave_manifest.py WAVE_BY_OWNER to 20 owners and added SQUAD_BY_OWNER dict replacing the hard-coded Squad A/Squad B ternary
- [Phase 03-python-tier-collapse]: Deferred backlog expanded from 285 to 1202 entries via generate_wave_manifest.py regeneration; gate now green with 1212 total tier-2 gaps tracked across 19 owners
- [Phase 03-python-tier-collapse]: Wave 1 ID scheme: dotted scanlog.<sub_module>.<symbol> for Wave 1 promoted rows; legacy kebab-case preserved for original 20 scanlog rows
- [Phase 03-python-tier-collapse]: Rust-only deferred symbols (Streaming*, module markers, unwrapped FormIDAnalyzer/FormIDAnalyzerCore/PluginAnalyzer/RecordScanner) routed via @rust-suffixed proxy-paired contract rows; eliminates rust-side gap without requiring new PyO3 wrappers
- [Phase 03-python-tier-collapse]: Plan R8 fix: single python-tier1-scanlog selector entry bumped count 20->94 + new hash; new python-tier1-scanlog-wave1-promoted aux entry uses bindingIdentifiers (not selector) since selector matching only honors ownerModule+tier
- [Phase 03-python-tier-collapse]: Python FormIDAnalyzer wraps RustFormIDAnalyzer (NOT the parallel unwrapped formid::FormIDAnalyzer); contract rows pair pythonExportPath=FormIDAnalyzer with rustSymbol=RustFormIDAnalyzer
- [Phase 03-python-tier-collapse]: Promoted FcxResetError as a real Python exception via pyo3::create_exception! instead of a proxy row, closing the quick-260406-syy deferred gap
- [Phase 03-python-tier-collapse]: R9 exclusion: GLOBAL_FCX_HANDLER LazyLock static is not tier1-promotable; Wave 2 lands 57 rows not 58
- [Phase 03-python-tier-collapse]: Wrapped create_exception! in #[allow(missing_docs)] sub-module to scope the lint allowance to exactly one macro-generated struct

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1]: The CXX gate regex parser must handle all 14 bridge source file patterns correctly — test against all modules in `classic-cpp-bridge/build.rs` enumeration before committing baseline
- [Phase 2]: CXXS-04 (scangame widening) requires DTO design review — CXX shared-struct rules restrict which Rust types can cross the FFI boundary; review before implementing all orchestration entry points
- [Phase 3]: The 289 deferred Python entries include many sub-module symbols not re-exported at `lib.rs` — each promotion requires a `pub use` addition before the parity parser can see it (Pitfall 2)
- [Phase 4]: All 109 Node contract rows must use camelCase `nodeExport` values — validate against `index.d.ts` TypeScript identifiers, not Rust snake_case names (Pitfall 3)
- [Phase 6]: Gate scripts must be made deferred-registry-tolerant BEFORE governance files are deleted (Pitfall 1); DOC-01 must land in the same commit as file deletions
- Phase 3 Plan 09a residual cleanup needs re-planning: Plan 01 A10 sizing reveals ~913 tier-2 gaps across 13 owners (scangame=218, path=85, constants=59, message=53, database=46, resource=40, xse=40, registry=39, settings=39, yaml=37, web=29, version=28, perf=16, update=16) that the current plan sequence does not explicitly budget. Plan 08 shared scope needs to grow from estimated 11 rows to 66 actual rows.

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 260406-syy | Resolve the newly uncovered Python parity surface for FcxResetError so the Python parity gate no longer reports uncovered runtime metadata. | 2026-04-07 | 8f4a9324 | Verified | [260406-syy-resolve-the-newly-uncovered-python-parit](./quick/260406-syy-resolve-the-newly-uncovered-python-parit/) |
| 260407-rg3 | Fix lying Game Files scan banner in Qt GUI — GameFilesWorker now computes combinedHasErrors/combinedTotalChecks from orchestrator + ENB + Crashgen instead of forwarding raw result fields that excluded ENB and Crashgen. | 2026-04-07 | 5fa8345e | Verified | [260407-rg3-fix-lying-game-files-scan-banner-in-qt-g](./quick/260407-rg3-fix-lying-game-files-scan-banner-in-qt-g/) |
| 260407-rvj | Make DocsPathFinder Steam App ID opt-in for Linux Proton lookup — removed hard-coded 377160 constant, added with_steam_app_id consuming builder; CXX bridge and TUI opt in via Fallout4Version; Python/Node bindings get set_steam_app_id setter. | 2026-04-08 | 7363ff55 | Verified | [260407-rvj-docspathfinder-steam-id-opt-in-for-linux](./quick/260407-rvj-docspathfinder-steam-id-opt-in-for-linux/) |

## Session Continuity

Last session: 2026-04-08T22:43:31.385Z
Stopped at: Completed 03-03-scanlog-wave2-detection-and-analysis-PLAN.md
Resume file: None
Next action: `/gsd:plan-phase 1` to plan Phase 1: CXX Parity Gate Tooling
