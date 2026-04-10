# Phase 3 Plan 01 -- Pitfall 4 Audit Report

Generated: 2026-04-08 03:57:26

## Audit Methodology

For each `classic-*-py` crate plus `classic-shared-py` the audit:

1. Walks the `pub mod` / `mod` declaration graph starting at `src/lib.rs` to determine which source files are REACHABLE (i.e., compiled into the crate).
2. Enumerates every `#[pyclass]` declaration across every `.rs` file under `src/`.
3. Enumerates every `m.add_class::<...>()` call in REACHABLE files, handling both bare names (`m.add_class::<FooStruct>()`) and path-qualified names (`m.add_class::<parser::FooStruct>()` -- last `::` segment is the class name).
4. Classifies each `#[pyclass]` as:
   - **REGISTERED** -- the class name appears in at least one reachable `m.add_class::<>()` call.
   - **MISSING** -- the class is in a reachable file but has no corresponding `m.add_class::<>()` call -- Phase 3 promotion would produce `AttributeError` at runtime.
   - **ORPHAN** -- the source file declaring the class is NOT reachable from `lib.rs` via the `pub mod` chain -- the class does not compile into the crate at all, so no registration is required or possible. This is equivalent to dead code.

## STATUS: PASS

All reachable `#[pyclass]` declarations across 17 `-py` crates have matching `m.add_class::<>()` registrations in their `#[pymodule]` function.

The 1 `#[pyclass]` declaration(s) classified as ORPHAN are in source files that are not compiled into any crate (see `## Known Exclusions` below for rationale).

## Known Exclusions

The following `#[pyclass]` declarations live in source files that are NOT reachable from the crate's `lib.rs` via the `pub mod` chain. They do not compile into the crate binary and therefore cannot -- and should not -- be registered via `m.add_class::<>()`. They are dead code and are excluded from Phase 3 promotion concerns.

| Crate | File | Line | `#[pyclass]` | Reason |
|-------|------|------|---------------|--------|
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/test_class.rs | 5 | TestClass | source file not reachable from lib.rs |

## Summary

- Total `#[pyclass]` declarations discovered: **126**
- Total `-py` crates audited: **17**
- REGISTERED (reachable and wired into `#[pymodule]`): **125**
- MISSING (reachable but not registered -- BLOCKING): **0**
- ORPHAN (dead source files, excluded): **1**

## Full Audit Table

| Crate | File | Line | `#[pyclass]` | Status |
|-------|------|------|---------------|:------:|
| classic-config-py | ClassicLib-rs/python-bindings/classic-config-py/src/lib.rs | 277 | PyPathConfig | REGISTERED |
| classic-config-py | ClassicLib-rs/python-bindings/classic-config-py/src/lib.rs | 370 | PyYamlSource | REGISTERED |
| classic-config-py | ClassicLib-rs/python-bindings/classic-config-py/src/lib.rs | 480 | PyClassicConfig | REGISTERED |
| classic-config-py | ClassicLib-rs/python-bindings/classic-config-py/src/lib.rs | 688 | PyYamlData | REGISTERED |
| classic-constants-py | ClassicLib-rs/python-bindings/classic-constants-py/src/lib.rs | 50 | PyYamlFile | REGISTERED |
| classic-constants-py | ClassicLib-rs/python-bindings/classic-constants-py/src/lib.rs | 196 | PyGameId | REGISTERED |
| classic-constants-py | ClassicLib-rs/python-bindings/classic-constants-py/src/lib.rs | 354 | PyFallout4Version | REGISTERED |
| classic-database-py | ClassicLib-rs/python-bindings/classic-database-py/src/pool.rs | 73 | PyDatabasePool | REGISTERED |
| classic-file-io-py | ClassicLib-rs/python-bindings/classic-file-io-py/src/core.rs | 20 | PyFileIOCore | REGISTERED |
| classic-file-io-py | ClassicLib-rs/python-bindings/classic-file-io-py/src/dds_analyzer.rs | 24 | PyDDSAnalyzer | REGISTERED |
| classic-file-io-py | ClassicLib-rs/python-bindings/classic-file-io-py/src/dds.rs | 36 | PyDDSHeader | REGISTERED |
| classic-file-io-py | ClassicLib-rs/python-bindings/classic-file-io-py/src/encoding.rs | 7 | PyEncodingDetector | REGISTERED |
| classic-file-io-py | ClassicLib-rs/python-bindings/classic-file-io-py/src/generation.rs | 10 | PyFileGeneratorConfig | REGISTERED |
| classic-file-io-py | ClassicLib-rs/python-bindings/classic-file-io-py/src/generation.rs | 59 | PyFileGenerator | REGISTERED |
| classic-file-io-py | ClassicLib-rs/python-bindings/classic-file-io-py/src/hash.rs | 30 | PyFileHasher | REGISTERED |
| classic-file-io-py | ClassicLib-rs/python-bindings/classic-file-io-py/src/log_collector.rs | 44 | PyLogCollector | REGISTERED |
| classic-file-io-py | ClassicLib-rs/python-bindings/classic-file-io-py/src/stream.rs | 11 | PyLineStreamer | REGISTERED |
| classic-file-io-py | ClassicLib-rs/python-bindings/classic-file-io-py/src/stream.rs | 50 | PySyncLineStreamer | REGISTERED |
| classic-message-py | ClassicLib-rs/python-bindings/classic-message-py/src/lib.rs | 31 | MessageType | REGISTERED |
| classic-message-py | ClassicLib-rs/python-bindings/classic-message-py/src/lib.rs | 128 | MessageTarget | REGISTERED |
| classic-message-py | ClassicLib-rs/python-bindings/classic-message-py/src/lib.rs | 242 | Message | REGISTERED |
| classic-message-py | ClassicLib-rs/python-bindings/classic-message-py/src/logging.rs | 22 | PyLogger | REGISTERED |
| classic-path-py | ClassicLib-rs/python-bindings/classic-path-py/src/lib.rs | 48 | GamePathFinder | REGISTERED |
| classic-path-py | ClassicLib-rs/python-bindings/classic-path-py/src/lib.rs | 260 | PathValidator | REGISTERED |
| classic-path-py | ClassicLib-rs/python-bindings/classic-path-py/src/lib.rs | 778 | DocsPathFinder | REGISTERED |
| classic-path-py | ClassicLib-rs/python-bindings/classic-path-py/src/lib.rs | 982 | BackupManager | REGISTERED |
| classic-path-py | ClassicLib-rs/python-bindings/classic-path-py/src/lib.rs | 1153 | XseVersion | REGISTERED |
| classic-path-py | ClassicLib-rs/python-bindings/classic-path-py/src/lib.rs | 1227 | IniCheckResult | REGISTERED |
| classic-path-py | ClassicLib-rs/python-bindings/classic-path-py/src/lib.rs | 1340 | DocumentsChecker | REGISTERED |
| classic-perf-py | ClassicLib-rs/python-bindings/classic-perf-py/src/lib.rs | 24 | MetricsSummary | REGISTERED |
| classic-perf-py | ClassicLib-rs/python-bindings/classic-perf-py/src/lib.rs | 151 | Timer | REGISTERED |
| classic-registry-py | ClassicLib-rs/python-bindings/classic-registry-py/src/lib.rs | 28 | Keys | REGISTERED |
| classic-resource-py | ClassicLib-rs/python-bindings/classic-resource-py/src/lib.rs | 11 | PyResourceType | REGISTERED |
| classic-resource-py | ClassicLib-rs/python-bindings/classic-resource-py/src/lib.rs | 164 | PyResourceInfo | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/ba2.rs | 8 | PyBA2Issues | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/ba2.rs | 62 | PyBA2Scanner | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/config_cache.rs | 10 | PyVsyncEntry | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/config_cache.rs | 34 | PyDuplicateEntry | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/config_cache.rs | 58 | PyModIniScanResult | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/config_cache.rs | 148 | PyConfigFileCache | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/config_cache.rs | 234 | PyModIniScanner | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/config.rs | 9 | PyDuplicateGroup | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/config.rs | 42 | PyConfigDuplicateDetector | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/crashgen_orchestrator.rs | 14 | PyCrashgenReport | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/crashgen_orchestrator.rs | 89 | PyCrashgenCheckOrchestrator | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/enb.rs | 11 | PyEnbResult | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/enb.rs | 23 | PyEnbConfigResult | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/enb.rs | 35 | PyEnbValidationResult | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/enb.rs | 74 | PyEnbChecker | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/ini.rs | 10 | PyIssueSeverity | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/ini.rs | 22 | PyConfigIssue | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/ini.rs | 74 | PyIniValidator | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/integrity.rs | 12 | PyCheckType | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/integrity.rs | 62 | PyIntegrityCheckResult | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/integrity.rs | 109 | PyIntegrityConfig | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/integrity.rs | 193 | PyGameIntegrityChecker | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/logs.rs | 8 | PyLogErrorEntry | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/logs.rs | 46 | PyLogProcessor | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/orchestrator.rs | 23 | PyCheckResult | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/orchestrator.rs | 46 | PyGameScanResult | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/orchestrator.rs | 81 | PyModScanResult | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/orchestrator.rs | 124 | PyGameScanConfig | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/orchestrator.rs | 263 | PyGameScanOrchestrator | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/setup.rs | 28 | PySetupCheckConfig | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/setup.rs | 83 | PySetupCheckResults | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/toml_check.rs | 11 | PyTomlIssueSeverity | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/toml_check.rs | 23 | PyTomlConfigIssue | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/toml_check.rs | 71 | PyCrashgenChecker | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/unpacked.rs | 8 | PyUnpackedIssues | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/unpacked.rs | 75 | PyUnpackedScanner | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/wrye.rs | 8 | PyWryeSeverity | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/wrye.rs | 20 | PyWryeIssue | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/wrye.rs | 65 | PyWryeBashParser | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/xse.rs | 8 | PyGameVersion | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/xse.rs | 24 | PyValidationResult | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/xse.rs | 40 | PyAddressLibInfo | REGISTERED |
| classic-scangame-py | ClassicLib-rs/python-bindings/classic-scangame-py/src/xse.rs | 127 | PyXseChecker | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/fcx_handler.rs | 83 | PyConfigIssue | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/fcx_handler.rs | 183 | PyFcxModeHandler | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/formid_analyzer.rs | 39 | PyFormIDAnalyzerCore | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/formid.rs | 10 | PyRustFormIDAnalyzer | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/gpu_detector.rs | 10 | PyGpuVendor | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/gpu_detector.rs | 49 | PyGpuInfo | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/gpu_detector.rs | 115 | PyGpuDetector | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/orchestrator.rs | 443 | PyCancellationToken | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/orchestrator.rs | 494 | PyAnalysisConfig | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/orchestrator.rs | 1081 | PyAnalysisResult | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/orchestrator.rs | 1177 | PyRustOrchestrator | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/papyrus.rs | 9 | PyPapyrusStats | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/papyrus.rs | 81 | PyPapyrusAnalyzer | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/parser.rs | 17 | ScanOutput | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/parser.rs | 37 | PyLogParser | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/patterns.rs | 7 | PyPatternMatcher | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/plugin_analyzer.rs | 21 | PyPluginAnalyzer | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/record_scanner.rs | 7 | PyRecordScanner | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/report.rs | 9 | PyStringPool | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/report.rs | 55 | PyReportFragment | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/report.rs | 122 | PyReportComposer | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/report.rs | 181 | PyReportGenerator | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/report.rs | 333 | PyParallelReportProcessor | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/settings_validator.rs | 13 | PySettingsValidator | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/suspect_scanner.rs | 23 | PySuspectScanner | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/test_class.rs | 5 | TestClass | ORPHAN |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/version.rs | 7 | PyCrashgenVersion | REGISTERED |
| classic-scanlog-py | ClassicLib-rs/python-bindings/classic-scanlog-py/src/version.rs | 76 | PyCrashgenVersionStatus | REGISTERED |
| classic-shared-py | ClassicLib-rs/foundation/classic-shared-py/src/lib.rs | 252 | RuntimeStats | REGISTERED |
| classic-shared-py | ClassicLib-rs/foundation/classic-shared-py/src/path_py.rs | 11 | PyPathHandler | REGISTERED |
| classic-shared-py | ClassicLib-rs/foundation/classic-shared-py/src/performance_py.rs | 11 | PyRustPerformanceMonitor | REGISTERED |
| classic-shared-py | ClassicLib-rs/foundation/classic-shared-py/src/strings_py.rs | 11 | PyStringProcessor | REGISTERED |
| classic-update-py | ClassicLib-rs/python-bindings/classic-update-py/src/github.rs | 27 | PyGithubRelease | REGISTERED |
| classic-update-py | ClassicLib-rs/python-bindings/classic-update-py/src/github.rs | 128 | PyGithubAsset | REGISTERED |
| classic-update-py | ClassicLib-rs/python-bindings/classic-update-py/src/github.rs | 207 | PyGithubClient | REGISTERED |
| classic-version-registry-py | ClassicLib-rs/python-bindings/classic-version-registry-py/src/matching.rs | 25 | PyMatchConfidence | REGISTERED |
| classic-version-registry-py | ClassicLib-rs/python-bindings/classic-version-registry-py/src/matching.rs | 129 | PyMatchResult | REGISTERED |
| classic-version-registry-py | ClassicLib-rs/python-bindings/classic-version-registry-py/src/models.rs | 17 | PyAddressLibraryConfig | REGISTERED |
| classic-version-registry-py | ClassicLib-rs/python-bindings/classic-version-registry-py/src/models.rs | 73 | PyXseConfig | REGISTERED |
| classic-version-registry-py | ClassicLib-rs/python-bindings/classic-version-registry-py/src/models.rs | 142 | PyCompatibleRange | REGISTERED |
| classic-version-registry-py | ClassicLib-rs/python-bindings/classic-version-registry-py/src/models.rs | 207 | PyCrashgenConfig | REGISTERED |
| classic-version-registry-py | ClassicLib-rs/python-bindings/classic-version-registry-py/src/models.rs | 302 | PyUnknownVersionHandling | REGISTERED |
| classic-version-registry-py | ClassicLib-rs/python-bindings/classic-version-registry-py/src/models.rs | 387 | PyVersionInfo | REGISTERED |
| classic-version-registry-py | ClassicLib-rs/python-bindings/classic-version-registry-py/src/registry.rs | 27 | PyVersionRegistry | REGISTERED |
| classic-version-registry-py | ClassicLib-rs/python-bindings/classic-version-registry-py/src/version.rs | 23 | PyGameVersion | REGISTERED |
| classic-web-py | ClassicLib-rs/python-bindings/classic-web-py/src/lib.rs | 10 | PyModSite | REGISTERED |
| classic-xse-py | ClassicLib-rs/python-bindings/classic-xse-py/src/lib.rs | 11 | PyXseType | REGISTERED |
| classic-xse-py | ClassicLib-rs/python-bindings/classic-xse-py/src/lib.rs | 126 | PyXseInfo | REGISTERED |
| classic-yaml-py | ClassicLib-rs/python-bindings/classic-yaml-py/src/lib.rs | 135 | PyYamlOperations | REGISTERED |
