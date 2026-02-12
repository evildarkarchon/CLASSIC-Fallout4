# PRD: G-17 ClassicScanLogsInfo → Rust YamlData Unification

**Version**: 1.0
**Date**: 2026-02-12
**Status**: Draft
**Goal**: Unify Python's `ClassicScanLogsInfo` (345 lines) with Rust's `YamlDataCore`, eliminating the dual-loading redundancy and completing the last major Python-to-Rust migration gap.

---

## 1. Executive Summary

`ClassicScanLogsInfo` is the Python-side YAML configuration aggregator that loads 30 attributes from three YAML sources (Main, Game, Ignore) and serves them to the crash log scanning pipeline. It was **deferred from PRD v2.0** because of a VR dual-loading pattern that the Rust `YamlDataCore` doesn't support.

Today, YAML data is loaded **twice per scan** — once by Python (`ClassicScanLogsInfo`) and once by Rust (`YamlDataCore`) — because the bridge method `to_rust_config()` creates a separate Rust instance rather than converting the Python one. This is wasteful and creates a maintenance burden: every YAML schema change must be replicated in both implementations.

**This PRD proposes**:
1. Extending Rust `YamlDataCore` with 4 missing VR-parallel fields and accessor methods
2. Making `ClassicScanLogsInfo` a thin Python wrapper over the Rust `YamlDataCore`
3. Unifying the `YamlDataCore → AnalysisConfig` conversion into a single Rust function
4. Cleaning up dead code paths (non-existent field accesses, deprecated methods)

**Expected outcome**: ~300 lines of Python removed, single YAML loading path, and a cleaner cross-language boundary.

---

## 2. Background & Motivation

### 2.1 Why This Was Deferred

From PRD v2.0 (G-17 assessment):
> "30+ YAML attributes loaded via batch. Has `to_rust_config()` bridge. Could be unified with Rust `YamlData` but serves as Python-side config aggregator. **Deferred to dedicated porting session** due to complexity."

The core complexity is the **VR dual-loading pattern**: Python loads BOTH OG and VR variants of several fields simultaneously (enabling per-log VR detection without re-reading YAML), while Rust takes a `vr_mode: bool` at construction time and loads only one variant.

### 2.2 Current Architecture

```
YAML Files (3 sources: Main, Game, Ignore)
    │
    ├──→ Python Path: yaml_cache.batch_get_settings()
    │       → ClassicScanLogsInfo (dataclass, 30 fields, loads BOTH VR variants)
    │       → executor stores as self.yamldata
    │       → to_rust_config() creates SEPARATE Rust instance
    │
    └──→ Rust Path: YamlDataCore::load_from_yaml_files()
            → YamlDataCore (struct, 28 fields, loads ONE VR variant)
            → build_analysis_config() in scan.rs (GUI)
            → AnalysisConfig consumed by OrchestratorCore
```

### 2.3 Problems with Current State

1. **Dual loading**: YAML files read twice per scan (once Python, once Rust)
2. **Field parity gap**: Python has 5 fields Rust lacks (`crashgen_name_vr`, `crashgen_ignore_vr`, `game_root_name`, `game_root_name_vr`, `_skip_post_init`)
3. **Hardcoded values**: GUI's `build_analysis_config()` hardcodes `game: "Fallout4"` and `vr_mode: false`
4. **Dead code**: `FormIDAnalyzer` accesses 3 non-existent fields (`problematic_plugins`, `mods_single`, `mods_double`) that silently return empty dicts
5. **Deprecated methods**: `get_crashgen_latest()` marked deprecated but still present
6. **Type divergence**: Python uses `packaging.version.Version` for game versions; Rust uses `String`
7. **Unused parameter**: `AsyncCrashLogPipeline` stores `yamldata` but never reads it (calls `get_yamldata()` independently)

---

## 3. Current State Analysis

### 3.1 Python ClassicScanLogsInfo (345 lines)

**Location**: `ClassicLib/scanning/logs/scanloginfo/classic_scan_logs_info.py`

**Construction**: Two paths — sync (`__post_init__` via `batch_get_settings`) and async factory (`create_async` via `batch_get_settings_async`). Both load 30 values in a single batch from the YAML cache.

**30 Data Fields**:
- 11 string fields (versions, crashgen names, warnings, XSE acronym, autoscan text, game root names)
- 5 list fields (game hints, records, ignore lists)
- 2 set fields (crashgen ignore for OG and VR)
- 8 dict fields (mod databases, suspect patterns)
- 3 Version fields (game versions as `packaging.version.Version`)
- 1 internal flag (`_skip_post_init`)

**Key Methods**:
- `create_async()` — async factory classmethod
- `get_crashgen_name(is_vr)` — VR-aware accessor
- `get_crashgen_ignore(is_vr)` — VR-aware accessor
- `get_game_root_name(is_vr)` — VR-aware accessor
- `get_crashgen_latest(is_vr)` — deprecated
- `to_rust_config()` — bridge to Rust AnalysisConfig

**Immutability**: All fields set once during construction, never mutated afterward.

### 3.2 Rust YamlDataCore (28 fields)

**Location**: `rust/business-logic/classic-config-core/src/yamldata.rs`

**Construction**: `load_from_yaml_files()` (async, parallel `tokio::join!` over 3 YAML files) or `from_yaml_content()` (sync, for tests).

**Missing vs Python** (4 data fields):
| Field | Python | Rust | Gap |
|-------|--------|------|-----|
| `crashgen_name_vr` | Loads both OG+VR | Only loads one via `vr_mode` | VR dual-load |
| `crashgen_ignore_vr` | Loads both OG+VR | Only loads one via `vr_mode` | VR dual-load |
| `game_root_name` | Present | Missing entirely | Not extracted from YAML |
| `game_root_name_vr` | Present | Missing entirely | Not extracted from YAML |

### 3.3 AnalysisConfig (Rust, in classic-scanlog-core)

**Location**: `rust/business-logic/classic-scanlog-core/src/orchestrator.rs`

A **superset** of YamlDataCore with runtime config fields (`game`, `vr_mode`, `show_formid_values`, `fcx_mode`, `simplify_logs`, `game_root_name`, `remove_list`). Currently populated by:
- **GUI**: `build_analysis_config()` in `scan.rs` — manually maps YamlDataCore fields with hardcoded game/vr_mode
- **Python**: `AnalysisConfig.from_yamldata()` via PyO3 — extracts fields from Python object via `getattr()`

### 3.4 All Consumers (Read-Only)

| Consumer | Language | Key Fields Used |
|----------|----------|-----------------|
| ScanLogsExecutor | Python | `game_hints`, `autoscan_text`, `to_rust_config()` |
| ReportGeneratorFragments | Python | `classic_version`, `crashgen_name` |
| AsyncCrashLogPipeline | Python | Stored but **unused** (calls `get_yamldata()` independently) |
| RustPluginAnalyzer | Python | `ignore_plugins`, `ignore_list`, `crashgen_name`, game versions |
| RustRecordScanner | Python | `records_list`, `ignore_records`, `crashgen_name` |
| FormIDAnalyzer | Python | `crashgen_name` + 3 non-existent fields (dead code) |
| complete_scan_with_summary | Python | `game_hints`, `autoscan_text` |
| scan.rs (GUI) | Rust | ALL fields → AnalysisConfig |
| OrchestratorCore | Rust | Via AnalysisConfig (all fields) |
| Node bindings | NAPI-RS | ALL fields as getters |

**All consumers are strictly read-only.**

---

## 4. Proposed Solution

### 4.1 Approach: Extend Rust + Thin Python Wrapper (Option A+C Hybrid)

The cleanest approach combines extending Rust's `YamlDataCore` with the missing fields (Option A from research) while converting Python's `ClassicScanLogsInfo` to a thin wrapper (Option C). This avoids the complexity of maintaining two separate VR instances (Option B).

**Design principles**:
- Single source of truth: Rust `YamlDataCore` loads ALL data (both VR variants)
- Python wrapper: `ClassicScanLogsInfo` becomes a thin adapter over `PyYamlData`
- Unified conversion: A single `YamlDataCore::to_analysis_config()` method in Rust
- No dual loading: YAML files read once by Rust, consumed by both Python and Rust paths

### 4.2 Architectural Changes

```
YAML Files (3 sources)
    │
    └──→ Rust: YamlDataCore::load_from_yaml_files()
            → YamlDataCore (32 fields, loads BOTH VR variants)
            → to_analysis_config(game, vr_mode, config) → AnalysisConfig
            │
            ├──→ GUI scan.rs: calls to_analysis_config() directly
            ├──→ Python: PyYamlData wrapper exposes all fields + VR accessors
            │       → ClassicScanLogsInfo wraps PyYamlData (thin adapter)
            │       → executor.yamldata is now Rust-backed
            └──→ Node: JsYamlData wrapper (already complete)
```

---

## 5. Implementation Phases

### Phase 1: Extend YamlDataCore with VR Dual-Loading (~50 Rust LoC)

**Crate**: `classic-config-core`

**Changes to `yamldata.rs`**:
1. Add 4 new fields to `YamlDataCore`:
   - `crashgen_name_vr: String`
   - `crashgen_ignore_vr: Vec<String>`
   - `game_root_name: String`
   - `game_root_name_vr: String`
2. Update `load_from_yaml_files()` and `from_yaml_content()` to extract both OG and VR variants of crashgen/game_root fields simultaneously (no longer gated by `vr_mode`)
3. Add VR-aware accessor methods:
   - `get_crashgen_name(&self, is_vr: bool) -> &str`
   - `get_crashgen_ignore(&self, is_vr: bool) -> &[String]`
   - `get_game_root_name(&self, is_vr: bool) -> &str`
4. Keep existing fields (`crashgen_name`, `crashgen_ignore`) as the OG variants for backward compatibility
5. Update existing unit and integration tests; add tests for dual-loading

**Acceptance criteria**:
- All existing `classic-config-core` tests pass
- New tests verify both OG and VR fields are populated from a single `load_from_yaml_files()` call
- VR accessor methods return correct variant based on `is_vr` parameter

### Phase 2: Add `to_analysis_config()` to YamlDataCore (~40 Rust LoC)

**Crate**: `classic-scanlog-core` (or `classic-config-core` with feature flag)

**Changes**:
1. Add a method or free function that converts `YamlDataCore` + runtime settings → `AnalysisConfig`:
   ```rust
   pub fn build_analysis_config(
       yaml: &YamlDataCore,
       game: &str,
       vr_mode: bool,
       show_formid_values: bool,
       fcx_mode: bool,
       simplify_logs: bool,
       remove_list: Vec<String>,
   ) -> AnalysisConfig
   ```
2. Replace the manual `build_analysis_config()` in `scan.rs` (GUI) with a call to this shared function
3. Update `AnalysisConfig::from_yamldata()` in the PyO3 binding to use the same shared conversion

**Design decision**: This function likely belongs in `classic-scanlog-core` since `AnalysisConfig` is defined there. The `classic-config-core` crate should NOT depend on `classic-scanlog-core`. An alternative is a `From` trait impl or a builder pattern in `classic-scanlog-core`.

**Acceptance criteria**:
- GUI scan produces identical `AnalysisConfig` as before
- No code duplication between GUI and Python binding paths
- `game` and `vr_mode` are no longer hardcoded in GUI

### Phase 3: Update PyO3 Bindings (~30 Rust LoC)

**Crate**: `classic-config-py`

**Changes**:
1. Expose new fields as `#[getter]` on `PyYamlData`:
   - `crashgen_name_vr`, `crashgen_ignore_vr` (as `PySet`), `game_root_name`, `game_root_name_vr`
2. Add VR-aware accessor methods:
   - `get_crashgen_name(is_vr: bool) -> String`
   - `get_crashgen_ignore(is_vr: bool) -> HashSet<String>`
   - `get_game_root_name(is_vr: bool) -> String`
3. Update `classic_config.pyi` type stub

**Acceptance criteria**:
- Python can access all 32 fields on `classic_config.YamlData`
- VR accessor methods work correctly from Python
- Type stub matches runtime behavior

### Phase 4: Convert ClassicScanLogsInfo to Thin Wrapper (~200 Python LoC removed)

**File**: `ClassicLib/scanning/logs/scanloginfo/classic_scan_logs_info.py`

**Changes**:
1. Replace the dataclass with a thin wrapper class that delegates to `classic_config.YamlData`:
   ```python
   class ClassicScanLogsInfo:
       """Thin wrapper over Rust YamlData for backward compatibility."""

       def __init__(self) -> None:
           from ClassicLib.integration.factory import get_yamldata
           self._rust = get_yamldata()

       @classmethod
       async def create_async(cls) -> ClassicScanLogsInfo:
           # Same as sync — Rust loading is fast enough (~20ms)
           return cls()

       @property
       def crashgen_name(self) -> str:
           return self._rust.crashgen_name

       # ... property delegates for all 30+ fields ...

       def get_crashgen_name(self, is_vr: bool) -> str:
           return self._rust.get_crashgen_name(is_vr)

       def to_rust_config(self) -> AnalysisConfig:
           return AnalysisConfig.from_yamldata(self._rust)
   ```
2. Remove all YAML batch-loading logic (`_get_settings_requests`, `_assign_values`, `__post_init__`)
3. Remove `_skip_post_init` internal flag
4. Remove deprecated `get_crashgen_latest()` method (if no callers remain)
5. Keep `game_version` fields as strings (drop `packaging.version.Version` conversion — callers that need Version objects can convert themselves)

**Acceptance criteria**:
- All existing Python tests pass without modification to test assertions
- `ClassicScanLogsInfo` interface is backward-compatible (same properties and methods)
- YAML is loaded exactly once (by Rust), not twice

### Phase 5: Clean Up Dead Code and Consumers (~50 Python LoC removed)

**Changes**:
1. **FormIDAnalyzer** (`formid_rust.py`): Remove accesses to non-existent fields (`problematic_plugins`, `mods_single`, `mods_double`) that return empty dicts via `getattr` defaults
2. **AsyncCrashLogPipeline** (`async_crash_log_pipeline.py`): Remove unused `yamldata` parameter and stored reference (it calls `get_yamldata()` independently)
3. **Test fixtures**: Update `mock_yamldata` fixtures to reflect the new wrapper interface
4. **Factory cleanup**: Remove fallback path in `get_yamldata()` if Rust is now mandatory (aligns with PRD v2.0 direction)
5. Remove deprecated `get_crashgen_latest()` if all callers migrated to `VersionRegistry`

**Acceptance criteria**:
- No dead field accesses remain
- No unused parameters in function signatures
- All tests pass (fixture updates may change mock setup but not assertions)

### Phase 6: Parity Testing and Verification (~100 test LoC added)

**New tests**:
1. **Field parity test**: Verify Rust `YamlData` produces identical field values as the old Python `ClassicScanLogsInfo` for the same YAML input files
2. **VR dual-loading test**: Verify `get_crashgen_name(True)` vs `get_crashgen_name(False)` return different values from single instance
3. **AnalysisConfig conversion parity**: Verify the unified `build_analysis_config()` produces identical output as the old manual mapping
4. **End-to-end scan parity**: Run a full scan with old Python path vs new Rust-backed path, verify identical report output
5. **Performance regression**: Verify single-load is faster than dual-load (should be ~2x improvement)

**Acceptance criteria**:
- All parity tests pass
- No scan output regressions
- Performance is equal or better

---

## 6. Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| VR field extraction changes YAML parsing behavior | Medium | Low | Phase 1 tests validate both OG and VR extraction against known YAML content |
| `packaging.version.Version` removal breaks callers | Medium | Medium | Audit all callers of `game_version` fields; provide string→Version conversion utility if needed |
| Test fixture updates cascade to many test files | Low | High | Phase 5 updates fixtures; automated grep ensures no missed references |
| `create_async()` callers expect truly async behavior | Low | Low | Rust YamlData loads in ~20ms; sync-in-async is acceptable at this latency |
| GUI hardcoded game/vr_mode fix reveals other issues | Low | Medium | Phase 2 parameterizes these; GUI settings already track game selection |
| Node bindings need updating for new fields | Low | Low | Node bindings already wrap all YamlDataCore fields; 4 new fields auto-expose |

---

## 7. Success Metrics

| Metric | Before | After |
|--------|--------|-------|
| Python LoC in ClassicScanLogsInfo | 345 | ~80 (thin wrapper) |
| YAML loading per scan | 2x (Python + Rust) | 1x (Rust only) |
| Field parity gaps | 4 fields missing in Rust | 0 |
| Dead code accesses | 3 non-existent fields in FormIDAnalyzer | 0 |
| Hardcoded values in GUI | game="Fallout4", vr_mode=false | Parameterized from settings |
| Deprecated methods | 1 (get_crashgen_latest) | 0 |
| Unused parameters | 1 (AsyncCrashLogPipeline.yamldata) | 0 |

---

## 8. Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| `classic-config-core` crate | Exists | Phase 1 target — extend YamlDataCore |
| `classic-scanlog-core` crate | Exists | Phase 2 target — shared AnalysisConfig builder |
| `classic-config-py` bindings | Exists | Phase 3 target — expose new fields |
| YAML test fixtures | Exists | `tests/fixtures/yamldata_fixtures.py` and Rust test YAML |
| `classic_yaml` crate | Exists | Used by YamlDataCore for YAML parsing |
| VersionRegistry | Complete | Replaces deprecated `get_crashgen_latest()` |
| PRD v2.0 migration | Complete | All prerequisite Rust-mandatory transitions done |

---

## 9. Out of Scope

- **G-16 (ScanLogsExecutor)**: The executor's orchestration logic (file discovery, progress tracking, warm-up) stays in Python. Only the `yamldata` creation within the executor changes.
- **G-12/G-13 (Fragment collectors/composers)**: Thin Python wrappers that stay as-is.
- **YAML cache infrastructure**: `YamlSettingsCache` and `AsyncYamlSettingsCore` remain for other non-YamlData consumers.
- **Game detection logic**: Determining which game is active stays in `GlobalRegistry`; this PRD only parameterizes where the game string is passed to `AnalysisConfig`.
- **TUI/GUI Python code**: No changes to PySide6 or Textual UI layers.
- **Version type unification**: `packaging.version.Version` vs `String` is a broader concern; this PRD only affects the 3 game_version fields in ClassicScanLogsInfo.

---

## 10. Phase Dependency Graph

```
Phase 1 (Extend YamlDataCore)
    │
    ├──→ Phase 2 (Unified AnalysisConfig builder)
    │       │
    │       └──→ Phase 3 (PyO3 bindings update)
    │               │
    │               └──→ Phase 4 (Python thin wrapper)
    │                       │
    │                       └──→ Phase 5 (Dead code cleanup)
    │                               │
    │                               └──→ Phase 6 (Parity testing)
    │
    └──→ (Node bindings auto-benefit from Phase 1)
```

All phases are sequential — each builds on the previous. Estimated total: ~270 Rust LoC added/modified, ~300 Python LoC removed, ~100 test LoC added.

---

## 11. Appendix: Field Inventory

### A. Complete Field Map (Post-Migration)

| # | Field | Type (Rust) | YAML Source | VR Variant? |
|---|-------|-------------|-------------|-------------|
| 1 | `classic_version` | `String` | Main | No |
| 2 | `classic_version_date` | `String` | Main | No |
| 3 | `classic_game_hints` | `Vec<String>` | Game | No |
| 4 | `classic_records_list` | `Vec<String>` | Main | No |
| 5 | `autoscan_text` | `String` | Main | No |
| 6 | `crashgen_name` | `String` | Game | OG variant |
| 7 | `crashgen_name_vr` | `String` | Game | **VR variant (NEW)** |
| 8 | `crashgen_latest_og` | `String` | Game | OG variant |
| 9 | `crashgen_latest_vr` | `String` | Game | VR variant |
| 10 | `crashgen_ignore` | `Vec<String>` | Game | OG variant |
| 11 | `crashgen_ignore_vr` | `Vec<String>` | Game | **VR variant (NEW)** |
| 12 | `warn_noplugins` | `String` | Game | No |
| 13 | `warn_outdated` | `String` | Game | No |
| 14 | `xse_acronym` | `String` | Game | No |
| 15 | `game_ignore_plugins` | `Vec<String>` | Game | No |
| 16 | `game_ignore_records` | `Vec<String>` | Game | No |
| 17 | `ignore_list` | `Vec<String>` | Ignore | No |
| 18 | `suspects_error_list` | `IndexMap<String, String>` | Game | No |
| 19 | `suspects_stack_list` | `IndexMap<String, Vec<String>>` | Game | No |
| 20 | `game_mods_conf` | `IndexMap<String, String>` | Game | No |
| 21 | `game_mods_core` | `IndexMap<String, String>` | Game | No |
| 22 | `game_mods_core_folon` | `IndexMap<String, String>` | Game | No |
| 23 | `game_mods_freq` | `IndexMap<String, String>` | Game | No |
| 24 | `game_mods_opc2` | `IndexMap<String, String>` | Game | No |
| 25 | `game_mods_solu` | `IndexMap<String, String>` | Game | No |
| 26 | `game_version` | `String` | Game | No |
| 27 | `game_version_new` | `String` | Game | No |
| 28 | `game_version_vr` | `String` | Game | No |
| 29 | `game_root_name` | `String` | Game | **OG variant (NEW)** |
| 30 | `game_root_name_vr` | `String` | Game | **VR variant (NEW)** |

### B. Consumer → Field Access Matrix

| Consumer | crashgen_name | game_hints | autoscan_text | classic_version | ignore_* | game_versions | mods_* | suspects_* | records_list | game_root_name | crashgen_ignore |
|----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| ScanLogsExecutor | | X | X | | | | | | | | |
| ReportGeneratorFragments | X | | | X | | | | | | | |
| RustPluginAnalyzer | X | | | | X | X | | | | | |
| RustRecordScanner | X | | | | | | | | X | | |
| FormIDAnalyzer | X | | | | | | | | | | |
| scan.rs (GUI) | X | X | X | X | X | X | X | X | X | X | X |
| OrchestratorCore | X | | | X | X | X | X | X | X | | X |
