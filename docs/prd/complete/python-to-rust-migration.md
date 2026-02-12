# PRD: Python-to-Rust Business Logic Migration

**Version**: 2.0
**Date**: 2026-02-11
**Status**: Active
**Goal**: Complete the migration of Python business logic to Rust, eliminating feature gaps

---

## 1. Executive Summary

Since PRD v1.0 was drafted, **massive progress** has been made. Of the original 23 feature gaps, **17 are now fully implemented in Rust** with PyO3 bindings, and the corresponding Python modules have been converted to thin wrappers. The remaining gaps are concentrated in two areas:

1. **Report Composition Pipeline** — Python composition/orchestration logic around already-Rust report fragments
2. **Application-Level Orchestration** — Python async coordinators and data loaders that call Rust-backed functions

**Current coverage**: ~85% of business logic delegates to Rust (up from ~60% at PRD v1.0). An additional ~7% has Rust equivalents built but not yet wired up on the Python side.

**What remains**: ~13 targeted gaps totaling ~4,800 lines of Python business logic. Of these, ~3,100 lines have existing Rust implementations that just need Python-side delegation wiring. The rest need cleanup of deprecated code and Python fallback paths.

**End state** (unchanged from v1.0): Python should contain only:
- UI code (PySide6 GUI, Textual TUI)
- Thin orchestration wrappers calling Rust (<50 lines each)
- Python-specific glue (factory imports, AsyncBridge, logging config)
- Entry points (CLI/GUI launchers)

---

## 2. Progress Summary

### 2.1 Completed Gaps (17 of 23)

All of these have Rust implementations in their respective core crates with PyO3 bindings exposed, and their Python counterparts have been converted to thin wrappers.

| # | Gap | Rust Module | Crate | Python Wrapper |
|---|-----|------------|-------|----------------|
| G-01 | Game Scanning Orchestrator | `orchestrator.rs` (819 lines) | classic-scangame-core | `orchestrator.py` still uses own async coordinator (see G-NEW-01) |
| G-02 | ScanGameCore (Mod Scanning) | `orchestrator.rs` (GameScanOrchestrator) | classic-scangame-core | Included with G-01 |
| G-03 | ConfigFileCache | `config_cache.rs` (657 lines) | classic-scangame-core | `config.py` (~187 lines) wraps `RustConfigFileCache` |
| G-04 | Mod INI Scanning | `mod_ini.rs` (526 lines) | classic-scangame-core | `scan_mod_inis.py` (~97 lines) delegates to `RustModIniScanner` |
| G-05 | Wrye Bash Parser | `wrye.rs` (445 lines) | classic-scangame-core | `wrye_check.py` (~73 lines) delegates to `WryeBashParser` |
| G-06 | XSE Plugin Checking | `xse.rs` (pre-existing) | classic-scangame-core | `check_xse_plugins.py` (~193 lines) delegates to `XseChecker` |
| G-07 | Crashgen Settings Check | `crashgen_orchestrator.rs` (357 lines) | classic-scangame-core | `check_crashgen.py` (~70 lines) delegates to `CrashgenCheckOrchestrator` |
| G-08 | DDS Processing Pipeline | `dds.rs` + `dds_analyzer.rs` binding | classic-file-io-core | `dds_analyzer.py` via `PyDDSAnalyzer` binding |
| G-09 | Game Report Builder | `game_report.rs` (536 lines) | classic-scangame-core | Exposed via `classic-scangame-py` |
| G-10 | Scan Validators | `game_report.rs` (ScanValidators) | classic-scangame-core | Exposed via `classic-scangame-py` |
| G-11 | Report Fragment System | `ReportFragment` in classic-scanlog-core | classic-scanlog-core | Python uses Rust `ReportFragment` exclusively via `report_rust.py` |
| G-18 | Setup Coordinator | `setup.rs` (506 lines) | classic-scangame-core | Functions exposed via `classic-scangame-py` |
| G-19 | Papyrus Log Analysis | `papyrus_logging()` in classic-scanlog-core | classic-scanlog-core | `papyrus.py` (~47 lines) delegates to Rust |
| G-20 | YAML Validators | `validators.rs` (568 lines) | classic-settings-core | Exposed via `classic-settings-py` |
| G-21 | PE Version Extraction | `pe_version.rs` (246 lines) | classic-version-core | `version_utils.py` tries Rust first, Python fallback |
| G-22 | File Similarity | `similarity.rs` (307 lines) | classic-file-io-core | `file_utils.py` tries Rust first, Python fallback |
| G-23 | Path Validation | `validator.rs` in classic-path-core | classic-path-core | `path_utils.py` tries Rust first, Python fallback |

### 2.2 Current Architecture State

| Layer | Python LoC | Rust Coverage | Status |
|-------|-----------|---------------|--------|
| Crash Log Scanning | ~500 (executor + orchestration) | 97% | Rust does all analysis; Python handles config and file discovery |
| Game File Scanning | ~600 (orchestrator + wrappers) | 95% | All individual checks delegate to Rust; Python orchestrator remains |
| Report Composition | ~440 (composers + conditionals) | 60% | Fragments are Rust; composition logic is Python |
| File I/O & YAML | ~300 (wrappers + fallbacks) | 92% | Rust-first with Python fallbacks |
| Support & Setup | ~100 (wrappers) | 95% | Nearly all delegated to Rust |
| Utilities | ~600 (version + file + path) | 80% | Rust-first with significant Python fallback code |
| Game Files Manager | ~565 | 0% | Pure Python file operations |
| UI (PySide6+Textual) | ~7,000 | N/A | Stays Python |

---

## 3. Remaining Feature Gaps

### 3.1 Report Composition & Orchestration (Priority: MEDIUM)

These gaps involve Python composition logic that wraps already-Rust report fragments. The business logic is modest — these are builder patterns and conditional inclusion logic.

| # | Gap | Python Source | Lines | Assessment |
|---|-----|-------------|-------|------------|
| G-12 | FragmentCollector | `scanning/logs/reporting/fragment_collector.py` | 55 | **THIN WRAPPER** — List-like interface over Rust `ReportFragment`. Minimal business logic. Consider keeping as-is. |
| G-13 | ReportComposer (fragment) | `scanning/logs/reporting/fragment_composer.py` | 63 | **THIN WRAPPER** — Static `compose()` and `conditional_section()` using Rust `ReportFragment`. Consider keeping as-is. |
| G-14 | ReportComposer (section) | `scanning/logs/reporting/section_composer.py` | 143 | **BUILDER PATTERN** — Accumulates Rust fragments with conditional sections. Pure Python orchestration around Rust types. |
| G-15 | ConditionalSection | `scanning/logs/reporting/conditional_section.py` | 109 | **BUSINESS LOGIC** — Evaluates `has_content` on Rust fragments, conditionally prepends headers. Could be a Rust utility. |
| G-24 | Mod Detection Logic | `scanning/logs/reporting/mod_detection.py` | 70 | **NEW GAP** — Pipe-delimited multi-plugin matching (`"modA|modB"`) and fragment generation. Pure business logic suitable for Rust. |

### 3.2 Application Orchestration (Priority: LOW)

These are Python coordination layers that call Rust-backed functions. They're closer to "glue" than "business logic" but contain non-trivial orchestration.

| # | Gap | Python Source | Lines | Assessment |
|---|-----|-------------|-------|------------|
| G-16 | Scan Logs Executor | `scanning/logs/executor.py` | 449 | **ORCHESTRATION** — Config loading from YAML, crash log file discovery, resource warm-up, progress tracking, summary generation. Calls Rust Orchestrator for analysis. Config loading and summary generation could move to Rust. |
| G-17 | ClassicScanLogsInfo | `scanning/logs/scanloginfo/classic_scan_logs_info.py` | 345 | **DATA CONTAINER** — 30+ YAML attributes loaded via batch. Has `to_rust_config()` bridge. Could be unified with Rust `YamlData` but serves as Python-side config aggregator. **Deferred to dedicated porting session** due to complexity. |
| G-25 | Game Integrity Orchestrator | `scanning/game/orchestrator.py` | 456 | **NEW GAP** — Python `GameIntegrityOrchestratorCore` runs XSE/crashgen/wrye/INI checks via `asyncio.TaskGroup`. All individual checks already delegate to Rust. This coordinator could call the Rust `GameScanOrchestrator` directly instead of coordinating individual Rust-backed Python functions. |
| G-26 | Game Files Manager | `scanning/game/game_files_manager.py` | 565 | **NEW GAP** — Async file backup/restore/remove with semaphored I/O. The existing Rust `BackupManager` in `classic-file-io-core` handles 4 hardcoded `BackupType` variants but lacks the generic, list-driven approach. A Rust `GameFilesManager` should be created for cross-language benefit (Slint GUI, Node bindings, etc.); **Python stays as-is** since it's I/O-bound with no delegation benefit. |

### 3.3 Undelegated Python Logic (Priority: HIGH)

These Python files have **Rust equivalents that already exist** but the Python side has NOT been updated to delegate to them. They contain no `from classic_*` imports. Wiring them to Rust is straightforward because the Rust APIs and PyO3 bindings are already built.

| # | Gap | Python Source | Lines | Rust Equivalent | Assessment |
|---|-----|-------------|-------|----------------|------------|
| G-30 | VersionRegistry | `support/versions/core.py` | 933 | `classic-version-registry-core` (3,168 LOC) | **CRITICAL** — Thread-safe YAML-driven version registry. Rust `VersionRegistry` has identical API. Python should delegate via `classic_constants` bindings. |
| G-31 | Version Data Models | `support/versions/models.py` | 457 | `classic-version-registry-core` | Frozen dataclasses (`VersionInfo`, `CrashgenConfig`, `XseConfig`, etc.). Rust has matching types. Python models could become thin wrappers around Rust types. |
| G-32 | Version Matching | `support/versions/matching.py` | 297 | `classic-version-registry-core::VersionMatcher` | 4-tier matching (exact→range→nearest→default). Rust `VersionMatcher` already implements this. |
| G-33 | Crashgen Version Checker | `support/versions/crashgen_checker.py` | 348 | `classic-scanlog-core::CrashgenVersion` | Crashgen version validation logic. Rust has `check_crashgen_version_status()`, `crashgen_version_gen()`. |
| G-34 | Game Integrity Checker | `support/integrity.py` | 230 | `classic-scangame-core::integrity` | SHA256 hash validation, installation location check. Rust `GameIntegrityChecker` has `run_full_check()`. |
| G-35 | GitHub Update Checker | `support/update.py` | 549 | `classic-update-core` (1,212 LOC) | `aiohttp`-based GitHub API client. Rust `GithubClient` has `get_latest_release()`, `has_update()`. |
| G-36 | Crash Log Mod Detection | `scanning/logs/detect_mods.py` | 287 | `classic-scanlog-core::mod_detector` | `detect_mods_single()`, `detect_mods_double()`, `detect_mods_important()`. Rust has all three functions with batch variants. |

**Total undelegated Python business logic**: ~3,101 lines across 7 files, all with existing Rust equivalents.

### 3.4 Utility Fallback Cleanup (Priority: LOW)

These Python files already delegate to Rust but retain fallback code paths. Cleanup removes dead code.

| # | Gap | Python Source | Lines | Assessment |
|---|-----|-------------|-------|------------|
| G-27 | Version Utils Fallback | `Utils/version_utils.py` | 327 | Has 4 fallback strategies (pywin32, pefile, regex) after Rust PE extraction. With Rust `pelite` always available, fallbacks are dead code. |
| G-28 | File Utils Fallback | `Utils/file_utils.py` | 121 | Python `SequenceMatcher` fallback after Rust `calculate_similarity`. |
| G-29 | Path Utils Fallback | `Utils/path_utils.py` | 168 | Python drive/permission checks after Rust `PathValidator`. |

---

## 4. Recommended Migration Phases

### Phase A0: Wire Undelegated Python to Existing Rust (~3,100 lines converted)

**Gaps**: G-30, G-31, G-32, G-33, G-34, G-35, G-36
**Rationale**: **Highest ROI phase.** These 7 Python files have complete Rust equivalents with PyO3 bindings already built and tested, but the Python side hasn't been updated to call them. No new Rust code is needed — only Python-side wiring changes.

**Actions**:
1. `support/versions/core.py` (G-30, 933 lines) → Import `classic_constants.VersionRegistry` (or `classic_version`) and delegate `get_version_registry()`, `get_by_id()`, `match_version()`, etc.
2. `support/versions/models.py` (G-31, 457 lines) → Replace frozen dataclasses with Rust-backed types from `classic_constants`
3. `support/versions/matching.py` (G-32, 297 lines) → Delegate to Rust `VersionMatcher`
4. `support/versions/crashgen_checker.py` (G-33, 348 lines) → Delegate to Rust `check_crashgen_version_status()`, `crashgen_version_gen()`
5. `support/integrity.py` (G-34, 230 lines) → Delegate to Rust `GameIntegrityChecker.run_full_check()`
6. `support/update.py` (G-35, 549 lines) → Delegate to Rust `GithubClient` for API calls ~~(keep `aiohttp` as async transport if needed, or use Rust's reqwest)~~ (Rust implementation should already be async, if it is not, it needs an async version)
7. `scanning/logs/detect_mods.py` (G-36, 287 lines) → Delegate to Rust `detect_mods_single()`, `detect_mods_double()`, `detect_mods_important()`

**Python LoC Converted**: ~3,100 → ~400 (thin wrappers)
**Rust LoC Added**: 0 (already exists)
**Estimated Effort**: Medium (3-5 sessions) — mostly mechanical wiring work
**Risk**: Low — Rust APIs are already tested; only changing Python call sites

---

### Phase A1: Cleanup & Dead Code Removal (~600 lines removed)

**Gaps**: G-27, G-28, G-29 + deprecated files
**Rationale**: Zero-risk removal of fallback code that can never execute when Rust bindings are present (which they always are in production). Also removes already-deprecated files.

**Actions**:
1. Remove Python fallback paths in `version_utils.py`, `file_utils.py`, `path_utils.py` — keep only Rust delegation
2. Delete deprecated `report_generator_functional.py` (already marked deprecated)
3. Delete `*_fallback.py` files in `scanning/game/checks/`:
   - `ba2_fallback.py`
   - `config_duplicate_fallback.py`
   - `ini_fallback.py`
   - `log_fallback.py`
   - `unpacked_fallback.py`
   - `xse_fallback.py`
4. Remove `classic_scan_logs_info.py` Python fallback logic if Rust `YamlData` covers all attributes (verify first)

**Python LoC Removed**: ~600
**Rust LoC Added**: 0
**Estimated Effort**: Small (1-2 sessions)
**Risk**: Very low — only removing code paths gated behind `except ImportError`

---

### Phase B: Report Composition in Rust (~380 lines migrated)

**Gaps**: G-14, G-15, G-24
**Rationale**: The section composer, conditional section, and mod detection logic are pure business logic that operates on Rust `ReportFragment` types. Moving them to Rust enables complete report generation without Python round-trips.

**New Rust Additions to `classic-scanlog-core`**:
1. `SectionComposer` — Builder for accumulating fragments with conditional headers
2. `ConditionalSection` — Evaluates `has_content` and conditionally prepends headers
3. `ModDetector` — Pipe-delimited multi-plugin matching with fragment generation

**New PyO3 Bindings** in `classic-scanlog-py`:
- Expose `SectionComposer`, `ConditionalSection`, `detect_mods_single()`

**Python Changes**:
- `section_composer.py` → Thin wrapper or removed
- `conditional_section.py` → Thin wrapper or removed
- `mod_detection.py` → Delegate to Rust `detect_mods_single()`

**Python LoC Removed**: ~280 (keep ~100 as thin wrappers)
**Rust LoC Added**: ~500-700
**Estimated Effort**: Medium-Small (2-3 sessions)

---

### Phase C: Orchestrator Consolidation (~900 lines simplified)

**Gaps**: G-16, G-25
**Rationale**: The Python game integrity orchestrator (`orchestrator.py`) coordinates 6 checks that all individually delegate to Rust. The Rust `GameScanOrchestrator` already runs these same checks concurrently via `tokio::JoinSet`. Wiring the Python side to call the Rust orchestrator directly eliminates redundant async coordination.

Similarly, the scan logs executor (`executor.py`) orchestrates the Rust crash log `Orchestrator` but adds config loading, file discovery, and summary generation in Python.

**Option A (Recommended): Minimal consolidation**
- `orchestrator.py` → Replace `GameIntegrityOrchestratorCore` internals with a single call to Rust `GameScanOrchestrator` (eliminating 6 individual `_run_*_async` methods)
- `executor.py` → Move summary generation and config loading into Rust `ScanExecutor` extensions
- Keep Python files as thin wrappers (~50 lines each)

**Option B: Full Rust orchestration**
- Build a Rust `FullScanOrchestrator` that takes YAML settings and returns a complete report
- Python reduces to: `result = FullScanOrchestrator.run(yaml_settings_dict)`
- Higher effort, bigger payoff

**Python LoC Removed**: ~700 (keep ~200 as wrappers)
**Rust LoC Added**: ~800-1,200 (Option A) or ~2,000-3,000 (Option B)
**Estimated Effort**: Medium (Option A) or Large (Option B)

---

### Phase D: Low-Priority Items (~1,000 lines, mixed)

**Gaps**: G-12, G-13, G-17 (keep), G-26 (Rust-only implementation)
**Rationale**: `FragmentCollector` and `ReportComposer` (fragment) are already <65 lines each and are essentially type adapters. `ClassicScanLogsInfo` is a YAML data aggregator that bridges Python settings to Rust config. These three are acceptable as Python-side glue.

`GameFilesManager` is I/O-bound and provides no Python-side migration benefit, **but** a Rust implementation is needed so other consumers (Slint GUI, Node bindings, future Rust-only tools) can use it without reimplementing. The Python version remains as-is.

| Gap | Recommendation |
|-----|---------------|
| G-12 FragmentCollector (55 lines) | **Keep** — Backwards-compatible adapter, minimal logic |
| G-13 ReportComposer (63 lines) | **Keep** — Two static methods using Rust types |
| G-17 ClassicScanLogsInfo (345 lines) | **Deferred** — Python YAML aggregator with 30+ attributes and `to_rust_config()` bridge; requires dedicated porting session due to complexity |
| G-26 GameFilesManager (565 lines) | **Rust-only** — Create generic `GameFilesManager` in `classic-file-io-core` for cross-language use; Python stays as-is |

#### G-26 Implementation Details

**Problem**: The existing Rust `BackupManager` in `classic-file-io-core/src/backup.rs` is limited to 4 hardcoded `BackupType` enum variants (XSE, ReShade, Vulkan, ENB) with predefined glob patterns. The Python `GameFilesManagerCore` supports arbitrary YAML-configured file lists with case-insensitive substring matching, file+directory handling, and semaphore-limited concurrency.

**New Rust additions to `classic-file-io-core`** (new `game_files.rs` module):
1. `GameFilesManager` — Generic game file backup/restore/remove manager
   - Takes `game_root: PathBuf`, `backup_root: PathBuf`
   - Operations accept a list label (string) and a `Vec<String>` of file name patterns
   - Case-insensitive substring matching (matching Python's `item.lower() in name.lower()`)
   - Supports both files and directories (copy/copytree, remove/rmtree)
   - Async with `tokio::fs`, concurrent operations via `JoinSet` or `FuturesUnordered`
2. `FileOperation` — Enum: Backup / Restore / Remove
3. `FileOperationResult` — Summary struct (files_affected, errors, operation type)

**New PyO3 bindings** in `classic-file-io-py` (optional, for Python consumers who want it):
- Expose `GameFilesManager` — but Python is NOT required to delegate to it

**Python changes**: None — `game_files_manager.py` remains as-is

**Rust LoC Added**: ~300-500
**Python LoC Changed**: 0
**Estimated Effort**: Small (1-2 sessions)

---

## 5. Updated Dependency Order

```
Phase A0 ─── Wire undelegated Python to existing Rust (highest ROI)
             ├─ G-36 detect_mods.py (independent, simple delegation)
             ├─ G-34 integrity.py (independent, simple delegation)
             ├─ G-33 crashgen_checker.py (independent)
             ├─ G-35 update.py (independent, needs async consideration)
             ├─ G-31 models.py (foundation for G-30, G-32)
             ├─ G-32 matching.py (depends on G-31)
             └─ G-30 core.py (depends on G-31, G-32)

Phase A1 ─── Cleanup tasks (all parallel, can run alongside Phase A0)
             ├─ Remove fallback paths in Utils/
             ├─ Delete *_fallback.py files
             └─ Delete deprecated report_generator_functional.py

Phase B ─┬─ G-24 ModDetector (independent)
         ├─ G-15 ConditionalSection (independent)
         └─ G-14 SectionComposer (depends on G-15)

Phase C ─┬─ G-25 Orchestrator consolidation (depends on Phase A0)
         └─ G-16 Executor consolidation (independent)

Phase D ─┬─ G-26 GameFilesManager Rust-only implementation (independent, no Python changes)
         └─ G-12, G-13, G-17 remain as-is (no action)
```

---

## 6. Out of Scope (Stays in Python)

Unchanged from PRD v1.0. These are inherently Python-specific:

| Module | Reason |
|--------|--------|
| `ClassicLib/Interface/` (PySide6 GUI) | Qt framework bindings |
| `ClassicLib/TUI/` (Textual TUI) | Textual framework |
| `ClassicLib/core/async_bridge.py` | Python sync/async bridging for Qt workers |
| `ClassicLib/integration/factory.py` | Python import mechanism for Rust/Python switching |
| `ClassicLib/core/logger.py` | Python logging configuration |
| `ClassicLib/messaging/` | UI-facing message routing |
| `CLASSIC_ScanLogs.py`, `CLASSIC_Interface.py` | Entry points |
| `ClassicLib/integration/types.py` | TYPE_CHECKING-only protocols |
| `ClassicLib/core/performance.py` | Python TimedBlock |
| `ClassicLib/scanning/game/game_files_manager.py` | I/O-bound; Python stays as-is (Rust equivalent created separately for cross-language use) |
| `ClassicLib/scanning/logs/scanloginfo/classic_scan_logs_info.py` | YAML data aggregator; deferred to dedicated porting session (complex 30+ attribute unification) |

---

## 7. Success Criteria

### Per-Phase Metrics

| Phase | Python LoC Removed | Rust LoC Added | Key Validation |
|-------|-------------------|---------------|----------------|
| Phase A0 | ~2,700 (→ thin wrappers) | 0 | All 7 files delegate to existing Rust; parity tests pass |
| Phase A1 | ~600 | 0 | All tests pass; no fallback code remains for Rust-mandatory components |
| Phase B | ~280 | ~500-700 | Report composition produces identical output via Rust |
| Phase C | ~700 | ~800-1,200 | Game scan orchestration calls Rust directly; executor summary matches |
| Phase D | 0 (Python stays as-is) | ~300-500 (G-26 Rust-only) | G-26: Rust `GameFilesManager` passes backup/restore/remove tests; G-12/13/17 stay in Python |

### Overall Completion Criteria

1. **Python business logic reduced to <1,500 lines** (from ~6,000+ at PRD v1.0), excluding UI/TUI/messaging/glue
2. **All scanning Python modules are thin wrappers** (<80 lines each) delegating to Rust
3. **No Python fallback code remains** for components where Rust is always available
4. **`*_fallback.py` files deleted** — Rust implementations are the sole path
5. **Parity tests pass**: Each migrated function has a test comparing Python wrapper output with direct Rust call
6. **Test coverage maintained**: Workspace aggregate stays above 75%
7. **CI green**: All existing tests pass after each phase

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Removing Python fallbacks breaks non-Rust environments | Moderate | `classic_registry` is already mandatory (no fallback); standardize all bindings as mandatory |
| Report composition parity | Low | Comprehensive snapshot/golden-file tests comparing report output |
| Orchestrator consolidation changes async behavior | Moderate | Keep sync adapters; test with both PySide6 GUI and CLI paths |
| ClassicScanLogsInfo unification is complex | Low | Keep Python YAML aggregator (Phase D: keep as-is) |
| GameFilesManager migration has low ROI | Low | Leave as-is (Phase D: keep) |

---

## 9. Files to Delete After Phase A

```
ClassicLib/scanning/game/checks/ba2_fallback.py
ClassicLib/scanning/game/checks/config_duplicate_fallback.py
ClassicLib/scanning/game/checks/ini_fallback.py
ClassicLib/scanning/game/checks/log_fallback.py
ClassicLib/scanning/game/checks/unpacked_fallback.py
ClassicLib/scanning/game/checks/xse_fallback.py
ClassicLib/scanning/logs/reporting/report_generator_functional.py
```

### Files to Simplify After Phase B

```
ClassicLib/scanning/logs/reporting/section_composer.py    → <30 lines
ClassicLib/scanning/logs/reporting/conditional_section.py → <30 lines
ClassicLib/scanning/logs/reporting/mod_detection.py       → <20 lines
```

### Files to Simplify After Phase C

```
ClassicLib/scanning/game/orchestrator.py  → <80 lines (single Rust orchestrator call)
ClassicLib/scanning/logs/executor.py      → <100 lines (thin Rust ScanExecutor wrapper)
```

### Files to Convert to Thin Wrappers After Phase A0

```
ClassicLib/support/versions/core.py            (~933 lines → <100 lines)
ClassicLib/support/versions/models.py          (~457 lines → <50 lines, re-export Rust types)
ClassicLib/support/versions/matching.py        (~297 lines → <30 lines)
ClassicLib/support/versions/crashgen_checker.py (~348 lines → <40 lines)
ClassicLib/support/integrity.py                (~230 lines → <40 lines)
ClassicLib/support/update.py                   (~549 lines → <60 lines)
ClassicLib/scanning/logs/detect_mods.py        (~287 lines → <40 lines)
```

### Files That Are Already Thin Wrappers (No Action Needed)

```
ClassicLib/scanning/game/config.py           (~187 lines, wraps RustConfigFileCache)
ClassicLib/scanning/game/scan_mod_inis.py    (~97 lines, delegates to RustModIniScanner)
ClassicLib/scanning/game/wrye_check.py       (~73 lines, delegates to WryeBashParser)
ClassicLib/scanning/game/check_crashgen.py   (~70 lines, delegates to CrashgenCheckOrchestrator)
ClassicLib/scanning/game/check_xse_plugins.py (~193 lines, delegates to XseChecker)
ClassicLib/support/papyrus.py                (~47 lines, delegates to Rust papyrus_logging)
ClassicLib/Utils/file_utils.py               (~121 lines, Rust-first + fallback)
ClassicLib/Utils/path_utils.py               (~168 lines, Rust-first + fallback)
ClassicLib/Utils/version_utils.py            (~327 lines, Rust-first + fallback)
```

---

## 10. Appendix: Gap Cross-Reference

### Original PRD v1.0 Gaps → v2.0 Status

| v1.0 Gap | Status | Notes |
|----------|--------|-------|
| G-01 | **COMPLETE** | `orchestrator.rs` in classic-scangame-core |
| G-02 | **COMPLETE** | Merged with G-01 |
| G-03 | **COMPLETE** | `config_cache.rs` in classic-scangame-core |
| G-04 | **COMPLETE** | `mod_ini.rs` in classic-scangame-core |
| G-05 | **COMPLETE** | `wrye.rs` in classic-scangame-core |
| G-06 | **COMPLETE** | `xse.rs` in classic-scangame-core (pre-existing) |
| G-07 | **COMPLETE** | `crashgen_orchestrator.rs` in classic-scangame-core |
| G-08 | **COMPLETE** | `dds.rs` + `dds_analyzer.rs` binding |
| G-09 | **COMPLETE** | `game_report.rs` (ScanReportBuilder) |
| G-10 | **COMPLETE** | `game_report.rs` (ScanValidators) |
| G-11 | **COMPLETE** | ReportFragment in classic-scanlog-core (pre-existing) |
| G-12 | **KEEP** | FragmentCollector (55 lines, thin adapter) |
| G-13 | **KEEP** | ReportComposer fragment (63 lines, thin adapter) |
| G-14 | **PHASE B** | SectionComposer (143 lines, builder pattern) |
| G-15 | **PHASE B** | ConditionalSection (109 lines, business logic) |
| G-16 | **PHASE C** | ScanLogsExecutor (449 lines, orchestration) |
| G-17 | **DEFERRED** | ClassicScanLogsInfo (345 lines, YAML aggregator) — dedicated porting session due to complexity |
| G-18 | **COMPLETE** | `setup.rs` in classic-scangame-core |
| G-19 | **COMPLETE** | Papyrus delegates to Rust |
| G-20 | **COMPLETE** | `validators.rs` in classic-settings-core |
| G-21 | **COMPLETE** | `pe_version.rs` in classic-version-core |
| G-22 | **COMPLETE** | `similarity.rs` in classic-file-io-core |
| G-23 | **COMPLETE** | `validator.rs` in classic-path-core |

### New Gaps Added in v2.0

| v2.0 Gap | Category | Notes |
|----------|----------|-------|
| G-24 | **PHASE B** | Mod detection fragment logic (70 lines, `reporting/mod_detection.py`) |
| G-25 | **PHASE C** | Game integrity orchestrator consolidation (456 lines) |
| G-26 | **PHASE D (Rust-only)** | Game files manager — Rust `GameFilesManager` for cross-language use; Python stays as-is |
| G-27 | **PHASE A1** | Version utils fallback cleanup |
| G-28 | **PHASE A1** | File utils fallback cleanup |
| G-29 | **PHASE A1** | Path utils fallback cleanup |
| G-30 | **PHASE A0** | VersionRegistry — 933 lines, Rust equivalent exists in classic-version-registry-core |
| G-31 | **PHASE A0** | Version data models — 457 lines, Rust types exist |
| G-32 | **PHASE A0** | Version matching — 297 lines, Rust VersionMatcher exists |
| G-33 | **PHASE A0** | Crashgen version checker — 348 lines, Rust functions exist |
| G-34 | **PHASE A0** | Game integrity checker — 230 lines, Rust GameIntegrityChecker exists |
| G-35 | **PHASE A0** | GitHub update checker — 549 lines, Rust GithubClient exists |
| G-36 | **PHASE A0** | Crash log mod detection — 287 lines, Rust mod_detector functions exist |
