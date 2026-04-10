# Phase 2: CXX Bridge Surface Expansion - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Close every C++ bridge narrowing gap currently flagged in REQUIREMENTS.md (CXXS-04..CXXS-09) and add first-time C++ bridge surfaces for `classic-constants-core`, `classic-web-core`, and the FCX issue getter (CXXS-01..CXXS-03). The CXX parity gate baseline created in Phase 1 is refreshed via `--update-baseline` so the single-tier contract reflects the complete widened surface, and `classic-cli` / `classic-gui` continue to build clean (CXXS-10).

**In scope:**
- New bridge files: `src/constants.rs`, `src/web.rs`, `src/xse.rs`, `src/version_registry.rs`
- Promote `src/path.rs` from source-only to a `build.rs`-listed bridge module
- Widen `src/scangame.rs` from 2 entry points to the full `classic-scangame-core` orchestration surface (BA2, INI, ENB, crashgen TOML, Wrye, integrity, setup orchestrator)
- Add `get_fcx_config_issues()` to `src/scanner.rs`
- Widen `src/database.rs` typed result API (FormID lookup typed results, batch query results) per CXXS-05
- Widen `src/config.rs` suspect-rule subset per CXXS-07
- Migrate `classic-cli` / `classic-gui` call sites that currently hand-roll behavior because the bridge was too narrow (D-11)
- Refresh `tools/cxx_api_parity` baseline JSON + reports per plan, in the same commit as the surface change

**Out of scope:**
- CI wiring of the CXX gate (Phase 5)
- Python and Node tier collapse (Phases 3 and 4)
- Tier-2 governance file deletion and harmony-doc rewrite (Phase 6)
- HARM-05 error-contract documentation (Phase 6)
- Any classic-cli/classic-gui rewrite that is not directly proving a new bridge entry point

</domain>

<decisions>
## Implementation Decisions

### Module / File Layout

- **D-01:** XSE helpers move to a NEW `src/xse.rs` file under `#[cxx::bridge(namespace = "classic::xse")]`. The existing string-based XSE helpers in `game.rs` (`detect_xse_version_string`, `is_xse_installed_check`, `xse_type_from_str`) move into the new file. This matches CXXS-09 wording literally and gives `classic-xse-core` its own clean namespace. Pitfall 5 clean `-Test` build cycle is required immediately after the file lands.
- **D-02:** Version-registry helpers move to a NEW `src/version_registry.rs` file under `#[cxx::bridge(namespace = "classic::version_registry")]`. Existing `version_registry_*` and `parse_game_version` helpers in `game.rs` move there. The current `src/registry.rs` is UNCHANGED — it stays as the `classic-registry-core` typed key/value singleton bridge. CXXS-06's "registry" wording is interpreted as the `classic::version_registry` namespace; the `classic::registry` namespace continues to mean classic-registry-core.
- **D-03:** `src/path.rs` is added to `build.rs::cxx_build::bridges` AS-IS in an early Phase 2 plan, then widened in subsequent plans within the same phase to cover the full `classic-path-core` surface (validation helpers, backup helpers, restricted-path checks, `DocsPathFinder` INI variants per CXXS-08). This gives smaller atomic commits and gates against the real source state earlier.
- **D-04:** `classic-constants-core` enums (`GameId`, `YamlFile`, `Fallout4Version`) are exposed as CXX shared enums declared inside `#[cxx::bridge(namespace = "classic::constants")]` blocks. Type-safe across the boundary, matches what `classic-web-core::ModSite::game_url` expects, and the parity gate locks the variant set so silent additions cannot drift the contract.
- **What is left in `game.rs` after D-01/D-02:** PE-version extraction (`extract_pe_version_string`) and the legacy `find_game_path` / `validate_path` / `check_restricted_path` helpers that are duplicated in `path.rs`. The Phase 2 planner decides whether to leave them as compatibility shims or move them into `path.rs` during the path-widening plan; both options remain inside this phase scope.

### Scangame DTO Design (CXXS-04)

- **D-05:** The default DTO shape for "list of issues" results (`BA2Issues`, `ConfigIssue` from `ini.rs`, `EnbValidationResult`, `TomlConfigIssue`, `WryeIssue`, etc.) is **flat CXX shared structs per issue type**. Each domain gets a `#[cxx::bridge]` shared struct with flat scalar/`String` fields only — for example `Ba2IssueDto { archive_path: String, issue_kind: String, severity: Severity, message: String }` — returned as `Vec<Ba2IssueDto>`. All fields stay flat (no nested `Vec`) so Pitfall 6 (`rust::Vec<T>` ABI restriction) cannot be triggered.
- **D-06:** Nested orchestrator results (`GameScanResult`, `ModScanResult`, `IntegrityCheckResult`, etc.) are flattened across the FFI boundary by exposing **one bridge fn per sub-domain** rather than one fn returning a nested aggregate. The bridge surface is `scangame_run_ba2_check(...) -> Vec<Ba2IssueDto>`, `scangame_run_ini_check(...) -> Vec<IniIssueDto>`, `scangame_run_integrity_check(...) -> IntegrityResultDto`, `scangame_run_setup_orchestrator(...) -> ScanGameSetupDto` (flat counts only), and so on. The C++ caller composes them. This avoids `Vec<StructWithVec>` entirely and matches the codebase-health Phase 4 "bridge layer is adapter-only" rule.
- **D-07:** Severity / category enums (`IssueSeverity`, `WryeSeverity`, `EnbResult`, `EnbConfigResult`, `IntegrityCheckResult.kind`) cross the boundary as CXX shared enums declared inside `#[cxx::bridge]`. Consistent with D-04. Variants are exhaustive in C++ `switch` statements; the parity gate locks the variant list so adding a new severity requires a coordinated Rust+C++ update (which is correct).
- **D-08:** The bridge keeps core-side combined-output summary helpers (`SetupCheckResults.combined()`-style fail-soft text strings) ALONGSIDE the new structured DTOs. Existing GUI code paths that just dump text continue to work without modification; new code paths use the structured DTOs. Slightly larger surface, but preserves the CXXS-10 "no API breakage in existing C++ frontend code" promise without forcing every consumer migration into the same plan as the DTO addition.

### Baseline Refresh Cadence

- **D-09:** `python tools/cxx_api_parity/check_parity_gate.py --update-baseline` runs **per plan, in the same commit as the surface change**. Each Phase 2 plan that lands new bridge surface refreshes `docs/implementation/cxx_api_parity/baseline/parity_contract.json` plus the committed `cxx_diff_report.{json,md}` and `cxx_gate_report.md` artifacts in the same commit. The repository is gate-green after every commit; bisects work; this matches the Python/Node parity-artifact commit pattern from earlier codebase-health phases.
- **D-10:** Clean MSVC builds (`pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test` AND `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test`) are MANDATORY before committing any plan that adds a new `src/*.rs` to `build.rs::cxx_build::bridges`. This catches Pitfall 5 (CXX header generation order / "incomplete type" errors) at the source. Phase 2 has at least 5 new `build.rs` entries — `constants.rs`, `web.rs`, `xse.rs`, `version_registry.rs`, `path.rs` — so this is at least 5 mandatory clean-build cycles, on top of incremental builds during plan work. AGENTS.md "never run raw `ctest`" rule applies; only the PowerShell wrappers are valid.

### Frontend Migration Scope (CXXS-10)

- **D-11:** Phase 2 MIGRATES classic-cli / classic-gui call sites that **currently hand-roll scangame, path, xse, or version-registry logic in C++ specifically because the bridge was too narrow**. New bridge functions land with at least one production caller; the "thin adapter" pattern is enforced end-to-end. This is a deliberate scope expansion beyond the safer surface-only default — the user wants the widening proven by real callers, not just compile-clean. The Phase 2 researcher MUST enumerate which classic-cli/classic-gui paths qualify before the planner decomposes this into tasks; the plans should pair each bridge addition with its consumer migration so the build proof is meaningful. Hand-rolled paths that the new bridge does NOT directly replace (e.g., Qt-specific UI helpers) are OUT OF SCOPE.

### Testing Strategy

- **D-12:** Every new bridge function gets a Rust-side `#[cfg(test)] mod tests` block in its bridge file, mirroring the existing pattern in `scangame.rs` / `database.rs` / `registry.rs` / `game.rs`. Tests call the Rust-side helper directly (not through the CXX-generated C++ side); they run via `cargo test` from `ClassicLib-rs/cpp-bindings/classic-cpp-bridge` and stay hermetic / fast / no-MSVC. C++-side validation comes from the D-10 mandatory clean `-Test` build cycle, which exercises the generated headers. C++ Catch2 tests in `classic-cli` / `classic-gui` are added only if a Rust-side test cannot exercise the code path (e.g., shared-enum exhaustiveness on the C++ `switch` side).

### Claude's Discretion

- The exact field names and ordering inside each new shared struct DTO. The planner picks names that are idiomatic for both Rust and C++ consumers; the parity gate locks them once committed.
- Whether `extract_pe_version_string`, `find_game_path`, `validate_path`, and `check_restricted_path` from `game.rs` move into `path.rs` during the path-widening plan or stay as compatibility shims (see D-04 closing note). Both options stay inside Phase 2 scope.
- The internal organisation of the new `src/scangame.rs` file once widened — single large module vs. logical sub-sections with `// ──` dividers.
- Whether `classic::web::ModSite::game_url(GameId)` is exposed as one bridge fn or split per `ModSite` variant. CXX shared enums per D-04 enable either shape.
- Whether the FCX issue getter (CXXS-03) returns `Vec<FcxIssueDto>` or a single combined-output string. Default to `Vec<FcxIssueDto>` to match D-05 unless the planner finds a CXX shared-struct constraint.
- Whether the database typed result API (CXXS-05) keeps the existing tab-delimited fail-soft batch path AND adds a typed `Vec<FormIdEntryDto>` path (additive), or replaces the tab-delimited helper outright. Default is additive, matching D-08's "keep both" pattern.

### Folded Todos

None — `gsd-tools todo match-phase 2` returned 0 matches.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements

- `.planning/REQUIREMENTS.md` §"CXX Bridge Surface (CXXS)" — CXXS-01..CXXS-10 are this phase's complete requirement set
- `.planning/ROADMAP.md` §"Phase 2: CXX Bridge Surface Expansion" — phase goal + 5 success criteria
- `.planning/phases/01-cxx-parity-gate-tooling/01-CONTEXT.md` — Phase 1 decisions that constrain Phase 2 (D-07 build.rs source-of-truth, D-09/D-10 baseline acceptance flow, D-11 no sibling coverage, D-12 no deferred-registry concept)

### Research (this milestone)

- `.planning/research/SUMMARY.md` — synthesized cross-cutting findings (no new Cargo deps; phase ordering)
- `.planning/research/STACK.md` §"C++ parity gate" — rejects generated-header parsing as the gate's source of truth
- `.planning/research/ARCHITECTURE.md` §"New CXX Bridge Modules", §"Component Boundaries" — lists every new and modified bridge file, the namespace each one gets, and the integration points for `classic-cli` / `classic-gui`
- `.planning/research/FEATURES.md` §"C++ parity gate" — anti-feature: binary ABI checks
- `.planning/research/PITFALLS.md` §"Pitfall 5: CXX Header Generation Order" — the clean-build requirement that drives D-10
- `.planning/research/PITFALLS.md` §"Pitfall 6: rust::Vec<T> ABI Type Restriction" — the constraint that drives D-05/D-06 DTO flattening
- `.planning/research/PITFALLS.md` §"Pitfall 7: Cross-Binding Error-Contract Standardization" — the rule that error shapes stay per-binding (do NOT normalize during this phase)

### Source-of-truth Rust crates that the bridge must mirror

- `ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs` — `GameId`, `YamlFile`, `Fallout4Version` enums; `NULL_VERSION`, `SETTINGS_IGNORE_NONE`; `must_not_be_none`
- `ClassicLib-rs/business-logic/classic-web-core/src/lib.rs` — `validate_url`, `is_valid_url`, `extract_domain`, `get_user_agent[_with_suffix]`, `ModSite` enum + methods, `join_url`, `build_url_with_query`, `WebError`
- `ClassicLib-rs/business-logic/classic-scangame-core/src/lib.rs` — re-exports for `ba2`, `config`, `crashgen_orchestrator`, `enb`, `game_report`, `integrity`, `ini`, `logs`, `mod_ini`, `orchestrator`, `setup`, `toml`, `unpacked`, `wrye`, `xse`
- `ClassicLib-rs/business-logic/classic-scangame-core/src/orchestrator.rs` — `GameScanOrchestrator`, `GameScanConfig`, `GameScanResult`, `ModScanResult`, `CheckResult`, `detect_config_issues`
- `ClassicLib-rs/business-logic/classic-scangame-core/src/setup.rs` — `SetupCheckConfig`, `SetupCheckResults`, `run_combined_checks`, `migrate_game_version_setting`, `resolve_effective_game_version`, `needs_path_detection`
- `ClassicLib-rs/business-logic/classic-scangame-core/src/{ba2,ini,enb,toml,wrye,unpacked,integrity,config,config_cache,mod_ini,xse,logs}.rs` — per-domain check structs and DTOs that need shared-struct mirrors in the bridge
- `ClassicLib-rs/business-logic/classic-database-core/src/pool_sqlx.rs` — typed FormID entry shape that drives CXXS-05
- `ClassicLib-rs/business-logic/classic-version-registry-core/src/registry.rs` — full OG/NG/AE/VR variant + crashgen-rule resolution surface for CXXS-06
- `ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs` — suspect-rule subset for CXXS-07
- `ClassicLib-rs/business-logic/classic-path-core/src/lib.rs` (and submodules) — full validation/backup helper surface for CXXS-08
- `ClassicLib-rs/business-logic/classic-xse-core/src/lib.rs` — full XSE detection surface for CXXS-09
- `ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs` (and `fcx_handler.rs`) — FCX issue getter source for CXXS-03

### Current bridge crate state (mirror baseline)

- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs` — the current 14-file list; `path.rs`, `constants.rs`, `web.rs`, `xse.rs`, `version_registry.rs` will be added by Phase 2 plans
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs` — module re-exports; new modules also need `#[cfg(windows)] pub mod` entries here
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` — currently 2 entry points (the narrow baseline this phase widens)
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs` — current home of XSE / version-registry / PE-version / path helpers; D-01 / D-02 split it
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs` — exists as source but not yet in `build.rs`; D-03 adds it
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs` — STAYS as classic-registry-core KV bridge per D-02
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/{config,database,scanner}.rs` — recipients of CXXS-07, CXXS-05, CXXS-03 widening
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/` — generated header output directory; clean-build cadence (D-10) validates header generation order

### Parity gate produced by Phase 1

- `tools/cxx_api_parity/check_parity_gate.py` — `--update-baseline` flag (D-09 cadence) and the freshness check that fails CI on uncommitted drift
- `tools/cxx_api_parity/generate_baseline.py` — re-bootstrap path; called by `check_parity_gate.py --update-baseline`
- `docs/implementation/cxx_api_parity/baseline/parity_contract.json` — the committed baseline that this phase refreshes per plan
- `docs/api/cxx-parity-gate.md` — contributor doc explaining the refresh workflow that Phase 2 actually uses

### Existing API docs that describe the bridge surface (background reading)

- `docs/api/classic-cpp-bridge-game-entrypoints.md` — current path/game/scangame entry points; this doc will need a follow-up update as Phase 2 widens the surface (out of scope for Phase 2 itself; Phase 6 owns doc rewrites)
- `docs/api/classic-cpp-bridge-data-entrypoints.md` — current config/file/database/scanner entry points; same follow-up note
- `docs/api/binding-parity-overview.md` — current cross-binding comparison; rewritten in Phase 6 once all three gates are green

### Architectural rules

- `AGENTS.md` §"Always-On Repository Rules" — single Tokio runtime; never raw `ctest`; the PowerShell wrapper requirement that drives D-10
- `CLAUDE.md` §"Build Commands" — exact `build_cli.ps1` and `build_gui.ps1` invocations Phase 2 must use
- `CLAUDE.md` §"Key Gotchas" — `VCPKG_ROOT`, `tools/use_msvc_from_git_bash.sh` for Git Bash sessions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs`** — Current 2-entry-point file. Reuses the `block_on()` pattern that all widened scangame entry points should follow. The `SetupCheckResult` shared struct (`combined_output`, `has_errors`, `total_checks`) is the working template for D-08-style "summary plus structured" pairs.
- **`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs`** — `db_pool_get_entries_batch` shows the existing tab-delimited batch pattern. CXXS-05 widening adds a typed alternative alongside it (D-08 additive rule).
- **`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs`** — `YamlDataModSolutionEntry` / `YamlDataModSolutionCriteria` are working examples of nested-but-flat CXX shared structs (the inner `criteria` field is itself a flat shared struct with two `Vec<String>` fields). Use the same nesting depth for new scangame DTOs and DO NOT exceed it.
- **`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs`** — The current pattern for fail-soft fallback DTOs (e.g., `VersionInfoDto.found: bool`, `XseConfigDto.found: bool`). Mirror this for the new XSE / version-registry split files.
- **`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs`** — Reference implementation of a small, single-purpose bridge module under one namespace. New `xse.rs` / `version_registry.rs` / `constants.rs` / `web.rs` follow the same shape.
- **`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs`** — Already exists as an unbridged source file with a working `#[cxx::bridge(namespace = "classic::path")]` block; D-03 simply promotes it into `build.rs`.

### Established Patterns

- **One file per domain, one `#[cxx::bridge]` block per file.** ARCHITECTURE.md research §"Pattern: Flat Module per Domain" confirms this. Phase 2 keeps the flat layout — no `meta` grouping module, no per-namespace sub-directories.
- **`block_on()` at the bridge boundary.** Every async core call is wrapped in `classic_shared_core::get_runtime().block_on(...)` (one runtime rule). New scangame async helpers follow this exactly.
- **`Result<T, String>` for explicit failure, fail-soft primitives for misses.** `db_pool_get_entry` returns `""` on miss, `db_pool_initialize` returns `Result<(), String>`. New bridge functions follow the same split: predicates and getters fail soft, mutations and validations return `Result<_, String>`.
- **`#[cfg(test)] mod tests` per bridge file with `serial_test::serial` when touching global state.** `registry.rs` shows the serial pattern for the DashMap singleton; new bridge tests use the same approach when needed.
- **Bridge cache stats are reshaped, not recomputed.** `config.rs::settings_cache_stats()` shows the codebase-health Phase 4 rule: cache stats are computed in core crates and only flattened to a CXX shared `CacheStats` here. Any new cache surfaces from CXXS-05 follow the same shape.

### Integration Points

- **`build.rs::cxx_build::bridges([...])`** — single source of truth for bridge files. Phase 1 D-07 says the parity gate parses this dynamically. Every Phase 2 plan that adds a file must update this list and run the gate `--update-baseline` in the same commit (D-09).
- **`include/classic_cxx_bridge/`** — CXX-generated header output directory. New modules produce new headers here. Pitfall 5 / D-10 requires a clean MSVC build to validate that header generation order is correct (no incomplete-type errors when shared structs cross modules).
- **`classic-cli/CMakeLists.txt` and `classic-gui/CMakeLists.txt`** — these CMake projects link against the bridge static library produced by Corrosion. Adding new bridge headers may require a CMake configure refresh; the `build_cli.ps1 -Clean -Test` and `build_gui.ps1 -Clean -Test` cycles handle that automatically.
- **D-11 consumer migration call sites** — the Phase 2 researcher must enumerate which classic-cli / classic-gui `.cpp` / `.h` files currently hand-roll scangame, path, xse, or version-registry logic. The planner pairs each bridge addition with its consumer migration so the build proof is meaningful. This enumeration is the single biggest research task for Phase 2.
- **`docs/implementation/cxx_api_parity/baseline/`** — Phase 1 created this directory; Phase 2 plans commit refreshed JSON + report files here per D-09.

</code_context>

<specifics>
## Specific Ideas

- **The widening must be visible to real callers.** D-11 is a deliberate scope choice — the user explicitly chose "migrate currently-narrowed call sites" over the safer "surface-only" default. New bridge functions land with at least one production consumer; phases that add surface without callers do not satisfy CXXS-10 by the user's standard.
- **Every plan in Phase 2 commits both code and refreshed parity artifacts together.** D-09 makes the repository gate-green after every commit; bisects work; this is non-negotiable.
- **No deferred Tier-2 concept.** Phase 1 D-12 established this for the CXX gate. Phase 2 inherits it: any bridge function added must appear in the parity contract immediately, not on a "promote later" backlog.
- **Pitfall 6 is the hard constraint on every DTO design choice.** No `Vec<StructWithVec>`. The planner verifies every shared struct against this rule before writing the `#[cxx::bridge]` block. Existing `YamlDataModSolutionEntry` / `YamlDataModSolutionCriteria` (nested but flat) is the maximum acceptable nesting depth.
- **The clean-build cadence (D-10) is at least 5 mandatory cycles minimum** — `constants.rs`, `web.rs`, `xse.rs`, `version_registry.rs`, `path.rs` each trigger a required `build_cli.ps1 -Clean -Test` AND `build_gui.ps1 -Clean -Test` pair before commit. Plans should batch related additions to keep this manageable but never skip the cycle.
- **`classic-cli/build_cli.ps1 -Test` and `classic-gui/build_gui.ps1 -Test` are the ONLY valid C++ test invocations.** Raw `ctest` is forbidden by AGENTS.md. The planner uses `-CTestName "<name>"` or `-IntegrationTestName "<csv>"` for narrow test runs.
- **Phase 6 owns the doc rewrite.** Phase 2 does NOT update `docs/api/classic-cpp-bridge-*.md` or `docs/api/binding-parity-overview.md`. Those rewrites happen in Phase 6 after all three gates are green. Phase 2 may add inline `///` doc comments to new bridge functions.

</specifics>

<deferred>
## Deferred Ideas

- **FCX issue getter DTO shape (CXXS-03 detail)** — The default is `Vec<FcxIssueDto>` per D-05 (flat shared struct), but the planner validates the FCX core surface before locking the field set. If `classic-config-core::fcx_handler` returns nested data the planner falls back to the D-08 "summary string + structured side channel" pattern.
- **Database typed result API additive vs replacement (CXXS-05 detail)** — Default is additive (D-08 pattern), keeping the existing `db_pool_get_entries_batch` tab-delimited path. Replacing the tab-delimited path is deferred unless the planner finds it has zero callers in `classic-cli` / `classic-gui`.
- **`game.rs` leftover surface after D-01 / D-02 split** — PE-version extraction (`extract_pe_version_string`), `find_game_path`, `validate_path`, `check_restricted_path` may stay as compatibility shims OR move into `path.rs`. The planner decides during the path-widening plan; both options stay in Phase 2 scope.
- **Error contract standardization across bindings** — Pitfall 7 says NO. Documentation of per-binding error contracts is HARM-05, owned by Phase 6. Phase 2 follows existing per-domain conventions and does NOT introduce a structured `BridgeError` shared struct.
- **`classic-web-core::ModSite::game_url(GameId)` exposure shape** — One bridge fn returning `String` vs one fn per `ModSite` variant. CXX shared enums per D-04 enable either; planner picks during the `web.rs` plan.
- **`docs/api/classic-cpp-bridge-*.md` rewrite** — Phase 6 owns this. Phase 2 leaves the docs as-is and adds inline `///` doc comments to new bridge functions.
- **`docs/api/binding-parity-overview.md` rewrite** — Phase 6 owns this; "harmony achieved" reframing depends on all three gates being green, which only happens after Phases 3 + 4.
- **C++ Catch2 tests in classic-cli/classic-gui for new bridge functions** — D-12 says Rust-side tests are the default. C++ Catch2 tests are added only if a Rust-side test cannot exercise the code path (e.g., shared-enum exhaustiveness on the C++ `switch` side).
- **Full classic-cli/classic-gui sweep replacing any C++ helper that has a Rust counterpart** — D-11 explicitly limits migration to call sites currently narrowed by bridge gaps. Broader sweeps belong in a separate cleanup phase.
- **Tier-2 governance file deletion** — Phase 6 owns this. Phase 2 does NOT touch `docs/implementation/{python,node}_api_parity/governance/`.

### Reviewed Todos (not folded)

None — `gsd-tools todo match-phase 2` returned 0 matches.

</deferred>

---

*Phase: 02-cxx-bridge-surface-expansion*
*Context gathered: 2026-04-07*
