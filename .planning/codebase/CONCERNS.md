# Codebase Concerns

**Analysis Date:** 2026-04-04

## Tech Debt

**Deprecated Parser API Not Fully Removed:**
- Issue: Two deprecated shim methods (`parse_segments`, `parse_segments_parallel`) in the core `LogParser` remain in production code marked with `#[deprecated(since = "9.0.0")]`. The Python binding (`classic-scanlog-py/src/parser.rs`) still calls `parse_segments_parallel` with `#[allow(deprecated)]`, keeping these shims alive.
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/parser.rs:459,475`, `ClassicLib-rs/python-bindings/classic-scanlog-py/src/parser.rs:98`
- Impact: Cannot remove deprecated API until all Python callers migrate to `parse_all_sections_arc`. Both TODO comments note pending removal.
- Fix approach: Replace `parse_segments_parallel` in Python bindings with a wrapper over `parse_all_sections_arc`, then delete the two deprecated methods.

**Deprecated `is_outdated` Version Check Still Has Callers:**
- Issue: `CrashgenVersion::is_outdated` is marked `#[deprecated(since = "0.2.0")]` but tests use `#[allow(deprecated)]`. The Python binding re-exposes the equivalent API (`generate_suspect_section` legacy method in `report.rs:651`) without deprecation marking.
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/version.rs:200`, `ClassicLib-rs/python-bindings/classic-scanlog-py/src/report.rs:307`
- Impact: Callers remain coupled to a single-version comparison that doesn't support multi-version checking. Migration path is `check_version_status()`.
- Fix approach: Migrate Python binding `generate_suspect_section` to call `generate_suspect_section_header` + `generate_suspect_found_footer` separately; then remove the legacy method.

**Legacy Settings Validator Fallback Path:**
- Issue: `SettingsValidator::scan_all_settings` falls back to `scan_all_settings_legacy_bucketed` for crashgen configs that lack structured `CrashgenEntry` rules. This legacy path is not deprecated but is structurally separate code.
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/settings_validator.rs:192,195`
- Impact: Two distinct validation code paths for settings checks; inconsistent results depending on whether `CrashgenEntry` is populated.
- Fix approach: Migrate all crashgen configs to use structured rules and eliminate the legacy bucketed path.

**Python FormID Analyzer Accepts Legacy Map Format:**
- Issue: Python binding's `PyFormIDAnalyzerCore::new` still accepts `mods_single` as a plain `PyDict` (key→value string map) via `legacy_mod_map_to_entries()`. The Rust-native API uses structured `ModSolutionEntry` sequences (as mandated by docs/api/README.md).
- Files: `ClassicLib-rs/python-bindings/classic-scanlog-py/src/formid_analyzer.rs:11,102`
- Impact: Binding silently converts old-format input, hiding the migration boundary. Python callers can pass legacy maps indefinitely.
- Fix approach: Add a deprecation warning when `mods_single` dict is detected; document expected `mods_double`-style sequence; reject or warn on legacy map in a future release.

**`SEGMENT_BOUNDARIES` Static Is Dead Code:**
- Issue: `static SEGMENT_BOUNDARIES` in the parser is kept for "backward compat" but marked `#[allow(dead_code)]`. Nothing references it.
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/parser.rs:70`
- Impact: Clutters the parser crate. No functional impact but masks future dead code warnings.
- Fix approach: Remove the static; the named section approach via `parse_all_sections_arc` is the canonical path.

**`YamlFormatConfig` Field Reserved But Unused:**
- Issue: `YamlOperations.format_config` field is `#[allow(dead_code)]` and marked "reserved for future format preservation features." The feature has never shipped.
- Files: `ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs:507`
- Impact: Empty struct field adds confusion. No runtime cost.
- Fix approach: Either implement YAML format preservation or remove the field and the `YamlFormatConfig` struct.

**`PluginAnalyzer.case_cache` Allocated But Never Written:**
- Issue: `PluginAnalyzer` holds an `Arc<DashMap<String, String>>` for `case_cache` marked `#[allow(dead_code)] // Reserved for future case-insensitive matching optimization`. The cache is allocated on each `PluginAnalyzer::new` call but never populated or read.
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/plugin_analyzer.rs:67`
- Impact: Small heap allocation per orchestrator construction; no functional effect. If batch scanning creates many orchestrators, the cost accumulates.
- Fix approach: Remove the field or implement the optimization.

**`PyGpuDetector.inner` Field Allocated But Unused:**
- Issue: Python binding `PyGpuDetector` holds an `inner: GpuDetector` field that is explicitly unused (the `GpuDetector` methods are static). Marked `#[allow(dead_code)]`.
- Files: `ClassicLib-rs/python-bindings/classic-scanlog-py/src/gpu_detector.rs:118`
- Impact: Cosmetic / slight allocation waste per Python `GpuDetector` instance.
- Fix approach: Remove the `inner` field; convert to a pure-methods Python class with no state.

**`construct_proton_docs_path` Linux Function Is Dead Code:**
- Issue: `construct_proton_docs_path` in the Linux platform module is `#[allow(dead_code)]`. It is not used by any code path.
- Files: `ClassicLib-rs/business-logic/classic-path-core/src/platform/linux.rs:170`
- Impact: Linux path detection is incomplete; Proton path support is partially implemented.
- Fix approach: Either wire up `construct_proton_docs_path` to the docs-path discovery workflow or remove it.

**Node `index.d.ts` Is Not Pre-Generated:**
- Issue: `package.json` declares `"types": "index.d.ts"` but no `index.d.ts` exists in the repository. It is only generated post-build via `napi build`. The TypeScript type system for consumers is not source-controlled.
- Files: `ClassicLib-rs/node-bindings/classic-node/package.json`
- Impact: Contributors cloning the repo have no type definitions until they run a full build. CI freshness tooling (`dts:freshness:check`) checks this but the file itself is gitignored.
- Fix approach: Either commit a generated `index.d.ts` snapshot or document the build-first requirement explicitly in the Node binding README.

**`ratatui`, `arboard`, and `crossterm` Not in Workspace Dependencies:**
- Issue: The TUI application pins `ratatui = "0.30"`, `arboard = "3"`, `crossterm = "0.28"`, and `open = "5"` as crate-local deps, not declared in the root workspace `[workspace.dependencies]`.
- Files: `ClassicLib-rs/ui-applications/classic-tui/Cargo.toml:15,37-42`
- Impact: Version updates require editing the crate's Cargo.toml separately; not centrally managed like all other deps.
- Fix approach: Promote to workspace dependencies if the TUI is expected to grow.

**`zerovec` Workaround Dep in `classic-shared-core`:**
- Issue: `classic-shared-core` has a dev-dependency `zerovec = { version = "0.11", features = ["alloc"] }` documented as a "workaround: icu_properties (transitive via slint) requires zerovec/alloc when building with gui-bridge in isolation."
- Files: `ClassicLib-rs/foundation/classic-shared-core/Cargo.toml:50-52`
- Impact: Fragile workaround that may break on Slint or zerovec upgrades. Undocumented in workspace-level docs.
- Fix approach: Track the upstream Slint/icu_properties issue; remove when resolved.

---

## Performance Bottlenecks

**Dynamic Regex Compilation in Hot Scan Paths:**
- Problem: `detect_mods_single`, `detect_mods_double`, `detect_mods_batch`, and `detect_mods_important` all call `Regex::new(...)` at runtime during each scan invocation, building combined alternation patterns from YAML-loaded mod lists.
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs:160,429,524,678`
- Cause: Mod lists are loaded at runtime from config and vary per user, preventing static compilation.
- Improvement path: Cache compiled patterns keyed by a hash of the mod list contents (similar to the existing pattern cache in `LogParser`). Reset cache on config reload.

**`detect_crash_pattern` in C++ Bridge Creates New Parser Per Call:**
- Problem: `detect_crash_pattern` in the C++ bridge function calls `classic_scanlog_core::LogParser::new(None).unwrap()` on every invocation, rebuilding all compiled patterns each time.
- Files: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs:671`
- Cause: No parser instance is cached at the bridge level.
- Improvement path: Make `detect_crash_pattern` a method on a bridge-owned `Orchestrator` or hold a `Lazy<LogParser>` at module level.

**`detect_mods_important` Compiles One Regex Per Entry:**
- Problem: Unlike `detect_mods_single`/`detect_mods_double` which build a single combined alternation pattern, `detect_mods_important` compiles a separate `Regex::new` for every entry in the list on each call.
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs:524`
- Cause: Entries need individual match semantics (gpu checks, exclusions).
- Improvement path: Pre-compile all patterns into an `AhoCorasick` automaton or build a combined pattern with named capture groups; check exclusions after matching.

**`detect_mods_important` Joins All Plugin Strings on Each Call:**
- Problem: The function joins all plugin names into a concatenated string (`plugins_text`, `modules_text`, `all_text`) on every invocation.
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs:512-517`
- Cause: Pattern matching against a full joined string rather than per-item lookup.
- Improvement path: Match against a `HashSet` using individual `contains` checks, or use `AhoCorasick` to search a flat byte slice.

---

## Fragile Areas

**`GLOBAL_FCX_HANDLER` Singleton - Silent Drop on Contention:**
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs:23,296`
- Why fragile: `reset_global_state()` uses `try_lock()` — if the mutex is held (e.g., concurrent batch scan), the reset silently does nothing. The next scan session may inherit stale FCX state.
- Safe modification: Always call `FcxModeHandler::reset_global_state()` from a single coordinating thread before scan initiation. Do not call from concurrent workers.
- Test coverage: No test covers the contention-drop case.

**`VersionRegistry` Singleton Cannot Be Reloaded:**
- Files: `ClassicLib-rs/business-logic/classic-version-registry-core/src/registry.rs:22`
- Why fragile: Uses `OnceLock` — the registry is initialized once on first access and cannot be refreshed at runtime. Any YAML-backed customization or test isolation requires a process restart.
- Safe modification: Tests that touch registry-dependent code must run in separate processes or accept the default initialized state.
- Test coverage: Registry-dependent tests are isolated via process restart or accept defaults; direct registry mutation in tests is absent.

**FCX Global State Not Accessible from C++ Bridge or Node Bindings:**
- Files: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`, `ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs`
- Why fragile: The C++ bridge and Node bindings expose `fcx_mode` as a config flag but never call `FcxModeHandler::reset_global_state()`. If fcx mode is used in a scan, the global handler state from that scan persists for subsequent scans in the same process.
- Safe modification: Add explicit reset calls in bridge/binding scan entry points before each scan session.
- Test coverage: Not tested across the bridge or Node binding layer.

**`scan_all_settings_legacy_bucketed` Has No Clear Deprecation Path:**
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/settings_validator.rs:195`
- Why fragile: The function is reachable whenever a `CrashgenEntry` is `None`, which happens silently. No warning is emitted; callers may not know they are hitting the legacy path.
- Safe modification: Add tracing/logging at the entry point to indicate legacy path activation. Add a test asserting the legacy path is not hit for standard configs.
- Test coverage: The legacy path is tested implicitly; no explicit "legacy path is not hit for known configs" assertion exists.

**`read_file_mmap` Assumes File Stability:**
- Files: `ClassicLib-rs/business-logic/classic-file-io-core/src/core.rs:1029-1050`
- Why fragile: The memory-mapped read path explicitly warns callers that concurrent file modification during the map window is unsafe. This is a correctness guarantee that relies on external (caller) enforcement.
- Safe modification: Only call `read_file_mmap` on files that are fully written before scanning (archived crash logs). Use `read_file_with_encoding` for any file that may still be appended (active Papyrus logs).
- Test coverage: No test verifies behavior when a file is modified during a mmap read.

---

## Security Considerations

**`unsafe` Memory Map in File I/O:**
- Risk: Memory-mapped file read (`Mmap::map`) in `read_file_mmap` is marked safe by the author's reasoning (read-only, file handle held, dropped before return) but the underlying OS allows another process to modify the file during the map window on Windows.
- Files: `ClassicLib-rs/business-logic/classic-file-io-core/src/core.rs:1050`
- Current mitigation: `#[allow(unsafe_code)]` with documented safety invariants. Only used for files >1MB.
- Recommendations: Consider using `MmapOptions::map_copy()` (copy-on-write) to avoid TOCTOU issues, or confine `read_file_mmap` to read-only opened file handles.

**`unsafe extern "C++"` CXX Bridge Block:**
- Risk: The CXX bridge declares `unsafe extern "C++"` for the `ScanBatchProgressCallback` type. Misuse of the C++ callback (e.g., passing a dangling pointer) would be undefined behavior.
- Files: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs:888`
- Current mitigation: CXX provides pinning/lifetime enforcement for opaque C++ types. The callback is C++-owned and passed by reference.
- Recommendations: No immediate action required; maintain CXX version upgrades promptly to pick up safety fixes.

---

## Test Coverage Gaps

**FCX Global Handler Contention Reset:**
- What's not tested: Silent drop of reset when mutex is held during concurrent scan.
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs:295-298`
- Risk: Stale FCX state persists across scan sessions in long-running batch operations.
- Priority: Medium

**Legacy Fallback Path in `SettingsValidator`:**
- What's not tested: No assertion that standard production configs do NOT hit `scan_all_settings_legacy_bucketed`.
- Files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/settings_validator.rs:195`
- Risk: Regressions in `CrashgenEntry` population silently fall back to legacy behavior with no warning.
- Priority: Medium

**`detect_crash_pattern` in C++ Bridge with Parser Allocation:**
- What's not tested: Performance regression of re-allocating `LogParser` per bridge call in realistic scan workloads.
- Files: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs:671`
- Risk: No latency regression detection for high-throughput C++ scan paths.
- Priority: Low

**Linux Proton Path Discovery:**
- What's not tested: `construct_proton_docs_path` is dead code with no test coverage; the Linux docs-path workflow has no integration tests against a real Proton prefix structure.
- Files: `ClassicLib-rs/business-logic/classic-path-core/src/platform/linux.rs:170`
- Risk: Linux support for Proton-based game installs may be silently broken.
- Priority: Medium

**Node Binding FCX State Reset:**
- What's not tested: `GLOBAL_FCX_HANDLER` state carryover between Node binding scan calls in a single process.
- Files: `ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs`
- Risk: Node consumers running multiple scans in one process may see FCX state from a prior scan.
- Priority: Low

---

## Dependencies at Risk

**`winreg = "0.52"` Not in Workspace:**
- Risk: Version pinned only in `classic-path-core/Cargo.toml`, not the root workspace. Future contributors adding registry access to another crate may pin a different version.
- Impact: Duplicate `winreg` versions in the dependency graph, inflating binary size.
- Migration plan: Promote to `[workspace.dependencies]`.

**`phf = "0.13.1"` Not in Workspace:**
- Risk: Pinned only in `classic-constants-core/Cargo.toml`. If PHF is needed elsewhere a version mismatch is possible.
- Impact: Inconsistent PHF version across potential future consumers.
- Migration plan: Promote to `[workspace.dependencies]`.

**`slint = "1.15.0"` Transitive Dep Workaround:**
- Risk: `zerovec` workaround in `classic-shared-core` dev-deps is tied to the current Slint/icu_properties ABI. Slint upgrades that change the zerovec requirement will silently break the `gui-bridge` feature build.
- Impact: `gui-bridge` feature may fail to compile after Slint updates without noticing the root cause.
- Migration plan: Add a CI check or comment referencing the upstream Slint issue tracker item.

---

## Scaling Limits

**`YAML_CACHE` and `SETTINGS_CACHE` Are Global Process-Wide:**
- Current capacity: Unbounded `DashMap` in `classic-yaml-core` (`YAML_CACHE`) and `classic-settings-core` (`SETTINGS_CACHE`).
- Limit: In long-running server or batch processes that load many distinct YAML files, memory grows without bound.
- Scaling path: Apply the same TTL/LRU eviction strategy used by `DatabasePool` to `YAML_CACHE` and `SETTINGS_CACHE`. A `clear_global_yaml_cache` function already exists but must be called manually.

**`HASH_CACHE` Is Unbounded:**
- Current capacity: Global `Arc<DashMap<PathBuf, String>>` in `classic-file-io-core/src/hash.rs:51`.
- Limit: Grows with the number of unique file paths hashed across a session; never evicted.
- Scaling path: Add TTL or capacity eviction similar to `DatabasePool`.

---

## Missing Critical Features

**Node Binding FCX Handler Exposure:**
- Problem: The Node binding exposes `fcx_mode` as a config bool but has no way to call `FcxModeHandler::reset_global_state()` or access the detected issues list (`ConfigIssue` list). The FCX result surface is Python-only.
- Blocks: Node consumers cannot use FCX mode effectively in multi-scan sessions.

**C++ Bridge FCX State Reset:**
- Problem: The C++ bridge does not expose a reset for `GLOBAL_FCX_HANDLER`. Batch scans via the bridge that use `fcx_mode: true` accumulate state.
- Blocks: C++ bridge callers cannot safely re-use the same process for multiple independent scan sessions with FCX enabled.

---

*Concerns audit: 2026-04-04*
