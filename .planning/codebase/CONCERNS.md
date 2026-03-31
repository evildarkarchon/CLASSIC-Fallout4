# Codebase Concerns

**Analysis Date:** 2026-03-30

## Tech Debt

**Deprecated API Shims Awaiting Removal (scanlog-core parser):**
- Issue: Two deprecated methods `parse_segments` and `parse_segments_parallel` marked `#[deprecated(since = "9.0.0")]` remain in the public API as backward-compatibility shims over `parse_all_sections_arc`. Each has an explicit `# TODO: Remove once all callers have migrated` doc comment.
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/parser.rs` lines 459, 475
- Impact: Dead code surface, compile-time deprecation warnings suppressed with `#[allow(deprecated)]` in test files. Signals incomplete migration.
- Fix approach: Audit all binding and bridge callers. Both Python and C++ bridge do not currently call these methods; confirm Node binding does not call `parseLogSegments` via the deprecated path. Remove shims once confirmed.

**Deprecated `is_outdated` Method in scanlog-core version:**
- Issue: `is_outdated` marked deprecated on `CrashgenVersion`; callers in test files use `#[allow(deprecated)]`.
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/version.rs` line 200
- Impact: Minor — test-only concern. No known production callers.
- Fix approach: Remove the method once no callers remain.

**FormID Settings Split (Dual Representation):**
- Issue: There are two separate, incompatible representations for per-game FormID database paths. `ClassicConfig.formid_databases` (top-level YAML key `formid_databases`) is used by Rust config API and bindings. `CLASSIC_Settings.FormID Databases.{game}` (nested legacy key) is used by the C++ bridge at scan startup and the Qt GUI settings dialog. The two keys are never reconciled at runtime.
- Files: `ClassicLib-rs/business-logic/classic-config-core/src/config.rs`, `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` (lines 717, 754), `classic-gui/src/app/settingsdialog.cpp`
- Impact: A path saved through `ClassicConfig::save_to_yaml()` or the Python/Node binding is ignored by actual scan startup. A path saved through the GUI's settings dialog affects scanning but is invisible to the Rust config API. This is documented but unfixed in `docs/api/formid-settings-boundary.md`.
- Fix approach: Migrate `scanner.rs::build_full_scan_config` to read `ClassicConfig` using a bridge-side loader, or add a settings migration step that writes the Rust model key when saving through the GUI.

**`YamlFormatConfig` Dead Field in yaml-core:**
- Issue: `YamlOperations` holds a `format_config: YamlFormatConfig` field marked `#[allow(dead_code)]` with a comment "Reserved for future format preservation features." The field is allocated but never read.
- Files: `ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs` lines 507-509
- Impact: Unused struct memory per `YamlOperations` instance. Signals incomplete feature design.
- Fix approach: Either implement format preservation using the field or remove it entirely.

**`dead_code` Suppressions in plugin_analyzer:**
- Issue: A struct field in `plugin_analyzer.rs` is marked `#[allow(dead_code)]` with comment "Reserved for future case-insensitive matching optimization."
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/plugin_analyzer.rs` line 67
- Impact: Dormant field with no completion timeline.
- Fix approach: Implement or remove.

**`dead_code` Suppression in parser.rs:**
- Issue: Two `#[allow(dead_code)]` suppressions exist in `parser.rs` at lines 70 and 1208.
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/parser.rs`
- Impact: Unreachable or unused production code reduces clarity.
- Fix approach: Remove unused code or promote to active use.

**Python Binding Parity — Large Deferred Backlog:**
- Issue: Python parity tooling tracks 353 surfaces total. Only 66 are runtime-verified; 287 are "deferred." The `scanlog` module has 227 deferred surfaces and only 24 runtime-verified ones.
- Files: `ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.md`, `ClassicLib-rs/python-bindings/parity-artifacts/parity_diff_report.md`
- Impact: Tier-1 contract (59 rows) passes, but the large deferred backlog means regressions in Tier-2 `scanlog` surfaces go undetected by CI. Node bindings have better coverage (273/381 runtime-verified vs 66/353 for Python).
- Fix approach: Promote high-priority scanlog surfaces from deferred to runtime-verified in the parity governance backlog at `ClassicLib-rs/python-bindings/parity-artifacts/`.

**Node Binding Tier-2 Gaps:**
- Issue: Node parity report shows 120 total gaps (Tier-1 + Tier-2). Tier-2 breakdown: `scanlog` 71, `config` 29, `aux` 15, `version_registry` 5. All Tier-1 (261 rows) pass.
- Files: `ClassicLib-rs/node-bindings/classic-node/parity-artifacts/parity_diff_report.md`
- Impact: Tier-2 scanlog surfaces (71) and config surfaces (29) in Node bindings lack parity coverage. Regressions in these areas are not caught by the parity gate.
- Fix approach: Promote priority Tier-2 rows to Tier-1 contract in the Node parity baseline.

---

## Known Bugs

**`FCX` Global State Not Reset in C++ Bridge Scan Session:**
- Symptoms: `GLOBAL_FCX_HANDLER` is a process-wide `Lazy<Mutex<FcxModeHandler>>` singleton. The doc comment in `fcx_handler.rs` instructs callers to call `FcxModeHandler::reset_global_state()` at the start of each scan session. The Python binding exposes `reset_fcx_checks()`. However, the C++ bridge (`scanner.rs`) does not call `reset_global_state()` before starting a scan. In a multi-scan session via the C++ path, cached FCX check results from a prior scan will bleed into subsequent scans.
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs` lines 21-24, `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`
- Trigger: Run multiple scan sessions in the same process using the C++ bridge with `fcx_mode: true`. The second scan will reuse cached FCX results from the first.
- Workaround: None in the C++ path. Python callers must call `FcxModeHandler.reset_fcx_checks()` manually before each scan session.

---

## Security Considerations

**No security-specific concerns identified in application code.** The codebase handles local game files and YAML configuration; there are no network-exposed surfaces, credential storage, or privilege escalation paths.

**Relative Path Resolution for FormID DB (no existence check):**
- Risk: `scanner.rs::resolve_formid_db_paths` assembles DB paths from user-provided YAML without checking file existence at assembly time. Nonexistent relative paths are silently passed to `DatabasePool::initialize()`, which skips them with a warning rather than a hard error.
- Files: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` lines 679-754
- Current mitigation: `DatabasePool::initialize()` logs a warning for missing files.
- Recommendations: Add an optional path-existence pre-check step with a structured warning in the scan config build phase so callers receive feedback earlier.

---

## Performance Bottlenecks

**Per-Call `Regex::new` in `mod_detector.rs`:**
- Problem: `detect_mods_single`, `detect_mods_double`, `detect_mods_important`, and `detect_mods_batch` each call `Regex::new(&format!(...))` to compile a combined alternation pattern from the mod list on every invocation. Regex compilation is expensive.
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs` lines 160, 429, 520, 674
- Cause: The pattern is built dynamically from YAML-loaded mod data, which requires a fresh compile per call when the input set changes. However, for batch scanning the same YAML the pattern is identical across calls.
- Improvement path: Cache the compiled `Regex` keyed by the sorted mod name set, using a `DashMap` or `once_cell`-based memo. Alternatively, accept a pre-compiled pattern as a parameter from the orchestrator.

**Per-Call `Regex::new` in `classic-path-core` backup:**
- Problem: `extract_version_from_xse_log` compiles `Regex::new(r"(?i)(?:runtime )?version\s*[=:]\s*(\d+(?:\.\d+)+)").unwrap()` inside a non-`static`/`Lazy` function body on every call.
- Files: `ClassicLib-rs/business-logic/classic-path-core/src/backup.rs` line 205-206
- Cause: Regex not extracted to a `static Lazy<Regex>`.
- Improvement path: Move the regex to a `static Lazy<Regex>` at module level.

**`block_on` Wrapping for All Async Operations in C++ Bridge:**
- Problem: The C++ bridge wraps every async Rust operation with `get_runtime().block_on(...)`. There are 38 `block_on` calls across `config.rs`, `database.rs`, `files.rs`, `scangame.rs`, `scanner.rs`, and `yaml.rs`. Each call blocks a thread for the duration of the async operation.
- Files: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs`, `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs`, `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/files.rs`, `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`
- Cause: CXX FFI requires synchronous entry points; the bridge design uses a shared Tokio runtime with blocking callers.
- Improvement path: For scan-heavy operations, consider exposing async callbacks to C++ so the Qt worker thread does not block. This is a structural constraint documented in the bridge design.

---

## Fragile Areas

**`OrchestratorCore` in `orchestrator.rs` (3,139 Lines):**
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/orchestrator.rs`
- Why fragile: The file is 3,139 lines and contains all of `OrchestratorCore`'s construction, initialization, scan execution, batch logic, FCX handling, crashgen version checking, and helper factory methods (`create_report_generator`, `create_settings_validator`, `create_record_scanner`, `create_fcx_handler`). Changes to any one concern risk unintended cross-cutting effects.
- Safe modification: Read the full method list before adding new behavior. Changes to `process_log` or `process_logs_batch` affect both CLI and GUI paths through the C++ bridge. New helper methods belong at the bottom of the `impl` block; never add business logic inline in `process_log`.
- Test coverage: Inline `#[test]` block at the bottom of the file (tests section starting line 2088). Not exhaustive for all code paths.

**`yamldata.rs` (3,309 Lines):**
- Files: `ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs`
- Why fragile: The largest single file in the codebase at 3,309 lines. Contains `YamlDataCore` and all its accessors for Main, Game, and Ignore YAML sections. Very wide API surface.
- Safe modification: Use the Tier-1 parity contract before touching public accessors; any signature change triggers Node and Python parity failures. Run the parity gate locally after changes.

**`scanner.rs` Bridge (1,771 Lines) with `build_full_scan_config`:**
- Files: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`
- Why fragile: Contains both scan orchestration (30 `#[test]` inline tests) and FormID DB path resolution using the legacy `CLASSIC_Settings.FormID Databases.{game}` key. Settings changes to the Rust config model do not automatically propagate here due to the FormID split. Also contains hardcoded FOLON FormID DB path (line 683).
- Safe modification: Any change to FormID DB path resolution must be verified against both the `ClassicConfig` model and this bridge's resolution logic. The hardcoded FOLON path in `hardcoded_formid_db_relpaths` is not configurable.

**Test Current-Directory Mutation in `config-core`:**
- Files: `ClassicLib-rs/business-logic/classic-config-core/src/config.rs` lines 1079-1113
- Why fragile: `test_load_local_yaml_paths_merges_multiple_documents` mutates the process working directory using `std::env::set_current_dir`. It uses a custom `current_dir_lock()` `Mutex` to serialize against other config tests, but this lock is local to the config-core test module. If tests from `classic-file-io-core/src/generation.rs` run concurrently with config-core tests in the same process (possible under `cargo test --workspace`), both independently mutate the current directory without cross-crate coordination. `generation.rs` uses the `serial_test::serial` attribute but not the config-core lock.
- Safe modification: Do not add new `set_current_dir` tests to either crate without confirming cross-crate isolation. Prefer using absolute paths in tests over `set_current_dir`.

**`GLOBAL_FCX_HANDLER` Process-Wide Singleton:**
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs` lines 21-24
- Why fragile: Global mutable state shared across all scan sessions in the same process. `reset_global_state()` uses `try_lock()` (non-blocking), so if a scan session holds the lock during reset, the reset silently does nothing. This means stale FCX state can survive into subsequent scans.
- Safe modification: Any feature that adds new FCX check types must also update `reset_global_state` and verify callers reset before each session. The C++ bridge does not reset this state.
- Test coverage: Unit tests in `fcx_handler.rs` cover individual FcxModeHandler instances but not the global reset behavior under contention.

---

## Scaling Limits

**SQLite FormID Database Pool:**
- Current capacity: The `DatabasePool` in `classic-database-core` manages per-game SQLite connection pools. The default max connections setting is configurable; large FormID DBs (e.g., `Fallout4 FormIDs Main.db`) are loaded at scan startup and pooled for the scan duration.
- Limit: Each scan session initializes pools from scratch. For batch scans with many workers, the pool is shared via `Arc<DatabasePool>` but all workers share the same connection limit, which can become a bottleneck.
- Scaling path: Increase `max_connections` per pool or partition DB access by game type if Skyrim/Starfield support is added.

---

## Dependencies at Risk

**`once_cell` (process-wide static singletons):**
- Risk: `GLOBAL_FCX_HANDLER`, `METRICS` (in `classic-perf-core`), and `REGISTRY` (in `classic-registry-core`) all use `once_cell::sync::Lazy`. These are initialized once per process and cannot be re-initialized. In test scenarios with multiple test binaries (e.g., `--workspace`), each test binary gets its own singleton. However, within a single binary, any global state corruption or accumulation affects all tests.
- Impact: Test isolation issues if singletons are not reset between tests.
- Migration plan: `once_cell` is being merged into std (`std::sync::LazyLock` in Rust 1.80+). The codebase can migrate to `std::sync::OnceLock`/`LazyLock` when minimum Rust version allows.

---

## Missing Critical Features

**`macOS` Platform Support:**
- Problem: `classic-path-core/src/platform/` has only `windows.rs` and `linux.rs`. No `macos.rs`. The `get_system_documents_path()` function has `#[cfg(target_os = "windows")]` and `#[cfg(target_os = "linux")]` variants but no macOS variant. Compilation on macOS would fail to link `get_system_documents_path`.
- Blocks: Any macOS deployment.

---

## Test Coverage Gaps

**`formid_analyzer.rs` (991 Lines — No Test Module Header):**
- What's not tested: The file contains 8 public/pub(crate) functions and has inline `#[tokio::test]` blocks in a test helper section at the bottom (from line 764). However, `formid_match`, `formid_match_with_crashgen_name`, and `lookup_formid_value` are async database-touching paths that depend on test fixture DBs. If fixture setup is absent in CI or the SQLite DB is missing, these tests silently pass without coverage.
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/formid_analyzer.rs`
- Risk: Changes to FormID lookup logic may not be caught if test DB fixtures are missing.
- Priority: Medium

**C++ Bridge `scanner.rs` — FCX Mode Coverage:**
- What's not tested: The C++ bridge `scanner.rs` has 30 inline tests but none specifically test `fcx_mode: true` scan sessions or verify that `GLOBAL_FCX_HANDLER` state does not bleed between multiple orchestrator lifecycles created in the same test binary.
- Files: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`
- Risk: The FCX state bleed issue described above is not caught by existing bridge tests.
- Priority: High

**TUI Application (`classic-tui`) — Render and Event Tests:**
- What's not tested: The TUI has tests in `tests/event_tests.rs` and `tests/render_tests.rs` plus inline tests in `app.rs`, `results_markdown.rs`, and `tabs/main_tab.rs`. However, the TUI is not referenced in any CI workflow (confirmed absent from all `.github/workflows/*.yml` files by search). The workspace `cargo test --workspace` in `ci-rust.yml` does cover `classic-tui` since it is in `Cargo.toml`'s members list. No dedicated TUI CI job exists.
- Files: `ClassicLib-rs/ui-applications/classic-tui/`, `.github/workflows/ci-rust.yml`
- Risk: TUI test failures are reported alongside all other Rust tests under the generic `ci-rust.yml` test step. There is no targeted TUI CI job with TUI-specific setup or output capture.
- Priority: Low

**CI `rustfmt` Check is Non-Blocking:**
- What's not tested: The `format` job in `ci-rust.yml` sets `continue-on-error: true`. Rustfmt failures do not block the CI pipeline or prevent merging.
- Files: `.github/workflows/ci-rust.yml` line 19
- Risk: Formatting drift accumulates silently. Only `clippy` (with `-D warnings`) is blocking.
- Priority: Low

**Python Runtime Coverage Deferred Backlog (287/353 Surfaces):**
- What's not tested: 287 of 353 tracked Python API surfaces are marked "deferred" in the parity governance system. The `scanlog` module has 227 deferred surfaces. These are not covered by runtime tests.
- Files: `ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.md`
- Risk: Silent regressions in Python `classic_scanlog` behavior not caught by the Tier-1 gate.
- Priority: Medium

---

*Concerns audit: 2026-03-30*
