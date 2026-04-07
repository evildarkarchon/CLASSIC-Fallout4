# Requirements: CLASSIC Codebase Health Milestone

**Defined:** 2026-04-04
**Core Value:** Every concern identified in the codebase audit is resolved -- no silent legacy paths, no dead code, no unbounded caches, and all binding surfaces expose consistent, complete APIs.

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Tech Debt Cleanup

- [x] **DEBT-01**: Remove `SEGMENT_BOUNDARIES` static from `classic-scanlog-core/src/parser.rs` (dead code, `#[allow(dead_code)]`)
- [x] **DEBT-02**: Remove `YamlFormatConfig` struct and `format_config` field from `YamlOperations` in `classic-yaml-core/src/lib.rs` (dead code, never shipped)
- [x] **DEBT-03**: Remove `PluginAnalyzer.case_cache` field from `classic-scanlog-core/src/plugin_analyzer.rs` (allocated per orchestrator but never written or read)
- [x] **DEBT-04**: Remove `PyGpuDetector.inner` field from `classic-scanlog-py/src/gpu_detector.rs` and convert to stateless Python class
- [x] **DEBT-05**: Migrate Python binding `parse_segments_parallel` caller to wrapper over `parse_all_sections_arc`, update `.pyi` contract
- [x] **DEBT-06**: Migrate Python `generate_suspect_section` legacy method to call `generate_suspect_section_header` + `generate_suspect_found_footer` separately
- [x] **DEBT-07**: Rewrite tests using `#[allow(deprecated)]` on `CrashgenVersion::is_outdated` to exercise `check_version_status()` instead
- [x] **DEBT-08**: Delete deprecated `parse_segments`, `parse_segments_parallel`, and `is_outdated` methods after all callers migrated
- [x] **DEBT-09**: Eliminate `scan_all_settings_legacy_bucketed` fallback path with tracing warning, assertion test, and removal
- [x] **DEBT-10**: Add deprecation warning via `PyErr::warn` when `PyFormIDAnalyzerCore::new` receives legacy `PyDict` format for `mods_single`

### Correctness and Safety

- [x] **SAFE-01**: Fix `GLOBAL_FCX_HANDLER.reset_global_state()` silent drop -- replace `try_lock()` with `lock()` (parking_lot non-poisoning)
- [x] **SAFE-02**: Expose `reset_fcx_global_state()` in C++ bridge CXX extern block, called before each scan session
- [x] **SAFE-03**: Expose `resetFcxState()` NAPI function in Node bindings, called before each scan session
- [x] **SAFE-04**: Expose `ConfigIssue` list in Node bindings via `JsConfigIssue` NAPI struct and `getFcxIssues()` function
- [x] **SAFE-05**: Switch `read_file_mmap` from `Mmap::map()` to `MmapOptions::map_copy_read_only()` for TOCTOU safety on Windows

### Performance

- [x] **PERF-01**: Cache compiled regex patterns in `detect_mods_single`, `detect_mods_double`, `detect_mods_batch` keyed by hash of mod list contents
- [x] **PERF-02**: Replace per-entry `Regex::new` in `detect_mods_important` with `str::contains` (patterns are escaped literals) or AhoCorasick for large lists
- [x] **PERF-03**: Replace per-call `LogParser::new(None)` in C++ bridge `detect_crash_pattern` with module-level `LazyLock<LogParser>`
- [x] **PERF-04**: Add criterion benchmarks and committed proof for `detect_mods_important`, `detect_mods_single`/`batch`, and `detect_crash_pattern` hotspot measurements; mmap throughput benchmarking is owned by **SAFE-05** / Phase 6

### Cache Eviction

- [x] **CACHE-01**: Replace unbounded `DashMap` in `YAML_CACHE` with `quick_cache::sync::Cache` (capacity 128)
- [x] **CACHE-02**: Replace unbounded `DashMap` in `SETTINGS_CACHE` with `quick_cache::sync::Cache` (capacity 64)
- [x] **CACHE-03**: Replace unbounded `DashMap` in `HASH_CACHE` with `quick_cache::sync::Cache` (capacity 1024)

### Workspace and Infrastructure

- [x] **INFRA-01**: Promote `winreg` to `[workspace.dependencies]` in root `Cargo.toml`
- [x] **INFRA-02**: Promote `phf` to `[workspace.dependencies]` in root `Cargo.toml`
- [x] **INFRA-03**: Wire `construct_proton_docs_path` into Linux docs-path discovery workflow with unit tests using mock Proton prefix
- [x] **INFRA-04**: Document or resolve `zerovec` workaround dependency in `classic-shared-core` (check if Slint 1.15+ resolved it)
- [x] **INFRA-05**: Commit generated `index.d.ts` snapshot for Node bindings with CI freshness check

### Test Coverage

- [x] **TEST-01**: Add test for FCX contention reset (concurrent scan scenario where mutex is held during reset)
- [x] **TEST-02**: Add assertion test that standard production crashgen configs do NOT hit `scan_all_settings_legacy_bucketed`
- [x] **TEST-03**: Add integration test for Linux Proton docs-path discovery with mock Proton prefix structure
- [x] **TEST-04**: Add test for Node binding FCX state carryover between scan calls in a single process

### Codebase Consistency (Differentiators)

- [x] **CONS-01**: Replace `once_cell::sync::Lazy` with `std::sync::LazyLock` across all crates still using `once_cell`
- [x] **CONS-02**: Return `Result<(), FcxResetError>` from `reset_global_state()` so callers can distinguish success, unnecessary, and failure
- [x] **CONS-03**: Expose consistent `CacheStats` struct (hits, misses, hit rate, size, capacity) on all three bounded caches
- [x] **CONS-04**: Use `LazyLock` with `Regex::new().unwrap()` for static patterns in `mod_detector` to move compilation failure to startup

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| TUI dependency workspace promotion (ratatui, arboard, crossterm, open) | Local to classic-tui, not shared -- management overhead for no benefit |
| VersionRegistry singleton reload | OnceLock design is intentional; process-restart isolation is acceptable |
| CXX bridge `unsafe extern "C++"` restructuring | CXX framework manages safety boundary; no action beyond version upgrades |
| Major binding API redesigns | Fixes parity gaps and deprecations only, not wholesale API changes |
| New user-facing features | Purely a health/hardening milestone |
| Python FormID legacy map removal | Deprecation warning first (this milestone); removal in a future milestone |
| Bulk error handling refactoring | Error handling works; no audit-driven justification for migration |
| Singleton architecture redesign | Fixes specific bugs (silent reset, unbounded growth) not structural rewrites |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DEBT-01 | Phase 2 | Complete |
| DEBT-02 | Phase 2 | Complete |
| DEBT-03 | Phase 2 | Complete |
| DEBT-04 | Phase 2 | Complete |
| DEBT-05 | Phase 9 | Complete |
| DEBT-06 | Phase 9 | Complete |
| DEBT-07 | Phase 9 | Complete |
| DEBT-08 | Phase 2 | Complete |
| DEBT-09 | Phase 2 | Complete |
| DEBT-10 | Phase 9 | Complete |
| SAFE-01 | Phase 3 | Complete |
| SAFE-02 | Phase 3 | Complete |
| SAFE-03 | Phase 3 | Complete |
| SAFE-04 | Phase 3 | Complete |
| SAFE-05 | Phase 6 | Complete |
| PERF-01 | Phase 5 | Complete |
| PERF-02 | Phase 5 | Complete |
| PERF-03 | Phase 10 | Complete |
| PERF-04 | Phase 5 | Complete |
| CACHE-01 | Phase 4 | Complete |
| CACHE-02 | Phase 4 | Complete |
| CACHE-03 | Phase 4 | Complete |
| INFRA-01 | Phase 11 | Complete |
| INFRA-02 | Phase 11 | Complete |
| INFRA-03 | Phase 11 | Complete |
| INFRA-04 | Phase 11 | Complete |
| INFRA-05 | Phase 11 | Complete |
| TEST-01 | Phase 3 | Complete |
| TEST-02 | Phase 2 | Complete |
| TEST-03 | Phase 11 | Complete |
| TEST-04 | Phase 3 | Complete |
| CONS-01 | Phase 7 | Complete |
| CONS-02 | Phase 3 | Complete |
| CONS-03 | Phase 4 | Complete |
| CONS-04 | Phase 10 | Complete |

**Coverage:**
- v1 requirements: 35 total
- Mapped to phases: 35
- Unmapped: 0

---
*Requirements defined: 2026-04-04*
*Last updated: 2026-04-07 after Phase 11 workspace/infra verification closure*
