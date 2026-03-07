# Phase 1 Engineering Handoff Map

- Generated: `2026-03-07T12:21:12.222614+00:00`
- Total gaps handed off: **103**

## Squad A (scanlog/config)

### `config`

- Total gaps: **21**
- Tier 1 gaps: **0**
- Tier 2 gaps: **21**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `ConfigError` | `-` |
| `rust_unmapped` | `tier2` | `CrashgenEntryRaw` | `-` |
| `rust_unmapped` | `tier2` | `format_registry_game_version` | `-` |
| `rust_unmapped` | `tier2` | `resolve_registry_version_info` | `-` |
| `node_unmapped` | `tier2` | `-` | `DEFAULT_CACHE_CLEANUP_INTERVAL` |
| `node_unmapped` | `tier2` | `-` | `DEFAULT_CACHE_CLEANUP_THRESHOLD` |
| `node_unmapped` | `tier2` | `-` | `DEFAULT_QUERY_CACHE_CAPACITY` |
| `node_unmapped` | `tier2` | `-` | `JsAnalysisConfig` |
| `node_unmapped` | `tier2` | `-` | `JsConfigDuplicateDetector` |
| `node_unmapped` | `tier2` | `-` | `JsConfigIssue` |
| `node_unmapped` | `tier2` | `-` | `JsEnbConfigResult` |
| `node_unmapped` | `tier2` | `-` | `JsGameScanConfig` |
| `node_unmapped` | `tier2` | `-` | `JsIntegrityConfig` |
| `node_unmapped` | `tier2` | `-` | `JsPathDetectionResult` |
| `node_unmapped` | `tier2` | `-` | `JsTomlConfigIssue` |
| `node_unmapped` | `tier2` | `-` | `JsXseConfig` |
| `node_unmapped` | `tier2` | `-` | `detectConfigDuplicates` |
| `node_unmapped` | `tier2` | `-` | `getDefaultCacheCleanupInterval` |
| `node_unmapped` | `tier2` | `-` | `getDefaultCacheCleanupThreshold` |
| `node_unmapped` | `tier2` | `-` | `getDefaultQueryCacheCapacity` |
| `node_unmapped` | `tier2` | `-` | `needsPathDetection` |

### `scanlog`

- Total gaps: **71**
- Tier 1 gaps: **0**
- Tier 2 gaps: **71**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `AnalysisResult` | `-` |
| `rust_unmapped` | `tier2` | `CheckId` | `-` |
| `rust_unmapped` | `tier2` | `ConfigIssue` | `-` |
| `rust_unmapped` | `tier2` | `CrashgenEntry` | `-` |
| `rust_unmapped` | `tier2` | `CrashgenRegistry` | `-` |
| `rust_unmapped` | `tier2` | `FcxModeHandler` | `-` |
| `rust_unmapped` | `tier2` | `FormIDAnalyzer` | `-` |
| `rust_unmapped` | `tier2` | `FormIDAnalyzerCore` | `-` |
| `rust_unmapped` | `tier2` | `GLOBAL_FCX_HANDLER` | `-` |
| `rust_unmapped` | `tier2` | `GpuDetector` | `-` |
| `rust_unmapped` | `tier2` | `GpuVendor` | `-` |
| `rust_unmapped` | `tier2` | `PapyrusAnalyzer` | `-` |
| `rust_unmapped` | `tier2` | `PapyrusError` | `-` |
| `rust_unmapped` | `tier2` | `PluginAnalyzer` | `-` |
| `rust_unmapped` | `tier2` | `RecordScanner` | `-` |
| `rust_unmapped` | `tier2` | `ReportComposer` | `-` |
| `rust_unmapped` | `tier2` | `ReportFragment` | `-` |
| `rust_unmapped` | `tier2` | `ReportGenerator` | `-` |
| `rust_unmapped` | `tier2` | `RustFormIDAnalyzer` | `-` |
| `rust_unmapped` | `tier2` | `ScanLogError` | `-` |
| `rust_unmapped` | `tier2` | `ScanProgressPhase` | `-` |
| `rust_unmapped` | `tier2` | `SettingsValidator` | `-` |
| `rust_unmapped` | `tier2` | `StreamingIteratorParser` | `-` |
| `rust_unmapped` | `tier2` | `StreamingLogParser` | `-` |
| `rust_unmapped` | `tier2` | `StringPool` | `-` |
| `rust_unmapped` | `tier2` | `SuspectScanner` | `-` |
| `rust_unmapped` | `tier2` | `contains_plugin` | `-` |
| `rust_unmapped` | `tier2` | `contains_record` | `-` |
| `rust_unmapped` | `tier2` | `crashgen_registry` | `-` |
| `rust_unmapped` | `tier2` | `crashgen_version_gen` | `-` |
| `rust_unmapped` | `tier2` | `detect_mods_batch` | `-` |
| `rust_unmapped` | `tier2` | `detect_mods_double` | `-` |
| `rust_unmapped` | `tier2` | `detect_mods_important` | `-` |
| `rust_unmapped` | `tier2` | `detect_mods_single` | `-` |
| `rust_unmapped` | `tier2` | `detect_plugins_batch` | `-` |
| `rust_unmapped` | `tier2` | `error` | `-` |
| `rust_unmapped` | `tier2` | `extract_formids_batch` | `-` |
| `rust_unmapped` | `tier2` | `fcx_handler` | `-` |
| `rust_unmapped` | `tier2` | `formid` | `-` |
| `rust_unmapped` | `tier2` | `formid_analyzer` | `-` |
| `rust_unmapped` | `tier2` | `gpu_detector` | `-` |
| `rust_unmapped` | `tier2` | `is_valid_formid` | `-` |
| `rust_unmapped` | `tier2` | `mod_detector` | `-` |
| `rust_unmapped` | `tier2` | `orchestrator` | `-` |
| `rust_unmapped` | `tier2` | `papyrus` | `-` |
| `rust_unmapped` | `tier2` | `parser` | `-` |
| `rust_unmapped` | `tier2` | `patterns` | `-` |
| `rust_unmapped` | `tier2` | `plugin_analyzer` | `-` |
| `rust_unmapped` | `tier2` | `record_scanner` | `-` |
| `rust_unmapped` | `tier2` | `report` | `-` |
| `rust_unmapped` | `tier2` | `scan_records_batch` | `-` |
| `rust_unmapped` | `tier2` | `segment_key` | `-` |
| `rust_unmapped` | `tier2` | `settings_validator` | `-` |
| `rust_unmapped` | `tier2` | `suspect_scanner` | `-` |
| `rust_unmapped` | `tier2` | `validate_formids_batch` | `-` |
| `rust_unmapped` | `tier2` | `version` | `-` |
| `node_unmapped` | `tier2` | `-` | `CRASH_LOG_PATTERN` |
| `node_unmapped` | `tier2` | `-` | `JsAnalysisBuildOptions` |
| `node_unmapped` | `tier2` | `-` | `JsAnalysisResult` |
| `node_unmapped` | `tier2` | `-` | `JsGpuInfo` |
| `node_unmapped` | `tier2` | `-` | `JsLogCollector` |
| `node_unmapped` | `tier2` | `-` | `JsLogErrorEntry` |
| `node_unmapped` | `tier2` | `-` | `JsLogProcessor` |
| `node_unmapped` | `tier2` | `-` | `JsLogSegments` |
| `node_unmapped` | `tier2` | `-` | `JsLogger` |
| `node_unmapped` | `tier2` | `-` | `JsPapyrusStats` |
| `node_unmapped` | `tier2` | `-` | `checkXsePlugins` |
| `node_unmapped` | `tier2` | `-` | `createLogger` |
| `node_unmapped` | `tier2` | `-` | `migrateVrSetting` |
| `node_unmapped` | `tier2` | `-` | `parseXseLog` |
| `node_unmapped` | `tier2` | `-` | `processGameLogs` |

## Squad B (version-registry/aux)

### `aux`

- Total gaps: **7**
- Tier 1 gaps: **0**
- Tier 2 gaps: **7**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `node_unmapped` | `tier2` | `-` | `JsCheckRule` |
| `node_unmapped` | `tier2` | `-` | `JsExpectedValue` |
| `node_unmapped` | `tier2` | `-` | `JsPreflightAction` |
| `node_unmapped` | `tier2` | `-` | `JsPreflightRule` |
| `node_unmapped` | `tier2` | `-` | `JsRuleMessages` |
| `node_unmapped` | `tier2` | `-` | `JsRuleTarget` |
| `node_unmapped` | `tier2` | `-` | `writeAutoscanReport` |

### `version_registry`

- Total gaps: **4**
- Tier 1 gaps: **0**
- Tier 2 gaps: **4**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `node_unmapped` | `tier2` | `-` | `JsCrashgenRegistryEntry` |
| `node_unmapped` | `tier2` | `-` | `JsCrashgenSettingsRules` |
| `node_unmapped` | `tier2` | `-` | `checkCrashgenConfigWithRules` |
| `node_unmapped` | `tier2` | `-` | `checkCrashgenFullWithRules` |
