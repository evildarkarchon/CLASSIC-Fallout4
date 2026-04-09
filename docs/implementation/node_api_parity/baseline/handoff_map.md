# Phase 1 Engineering Handoff Map

- Generated: `2026-04-09T23:04:18.237319+00:00`
- Total gaps handed off: **473**

## Squad A (scanlog/config)

### `config`

- Total gaps: **35**
- Tier 1 gaps: **0**
- Tier 2 gaps: **35**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `ConfigError` | `-` |
| `rust_unmapped` | `tier2` | `CoreModEntry` | `-` |
| `rust_unmapped` | `tier2` | `CoreModExclude` | `-` |
| `rust_unmapped` | `tier2` | `CrashgenEntryRaw` | `-` |
| `rust_unmapped` | `tier2` | `ModConflictEntry` | `-` |
| `rust_unmapped` | `tier2` | `ModSolutionCriteria` | `-` |
| `rust_unmapped` | `tier2` | `ModSolutionEntry` | `-` |
| `rust_unmapped` | `tier2` | `SuspectErrorRule` | `-` |
| `rust_unmapped` | `tier2` | `SuspectStackCountRule` | `-` |
| `rust_unmapped` | `tier2` | `SuspectStackRule` | `-` |
| `rust_unmapped` | `tier2` | `format_registry_game_version` | `-` |
| `rust_unmapped` | `tier2` | `resolve_registry_version_info` | `-` |
| `node_unmapped` | `tier2` | `-` | `DEFAULT_CACHE_CLEANUP_INTERVAL` |
| `node_unmapped` | `tier2` | `-` | `DEFAULT_CACHE_CLEANUP_THRESHOLD` |
| `node_unmapped` | `tier2` | `-` | `DEFAULT_QUERY_CACHE_CAPACITY` |
| `node_unmapped` | `tier2` | `-` | `HashCacheStats` |
| `node_unmapped` | `tier2` | `-` | `JsAnalysisConfig` |
| `node_unmapped` | `tier2` | `-` | `JsConfigDuplicateDetector` |
| `node_unmapped` | `tier2` | `-` | `JsConfigIssue` |
| `node_unmapped` | `tier2` | `-` | `JsEnbConfigResult` |
| `node_unmapped` | `tier2` | `-` | `JsFcxConfigIssue` |
| `node_unmapped` | `tier2` | `-` | `JsGameScanConfig` |
| `node_unmapped` | `tier2` | `-` | `JsIntegrityConfig` |
| `node_unmapped` | `tier2` | `-` | `JsPathDetectionResult` |
| `node_unmapped` | `tier2` | `-` | `JsTomlConfigIssue` |
| `node_unmapped` | `tier2` | `-` | `JsXseConfig` |
| `node_unmapped` | `tier2` | `-` | `clearHashCache` |
| `node_unmapped` | `tier2` | `-` | `detectConfigDuplicates` |
| `node_unmapped` | `tier2` | `-` | `getDefaultCacheCleanupInterval` |
| `node_unmapped` | `tier2` | `-` | `getDefaultCacheCleanupThreshold` |
| `node_unmapped` | `tier2` | `-` | `getDefaultQueryCacheCapacity` |
| `node_unmapped` | `tier2` | `-` | `getFcxConfigIssues` |
| `node_unmapped` | `tier2` | `-` | `getHashCacheStats` |
| `node_unmapped` | `tier2` | `-` | `needsPathDetection` |
| `node_unmapped` | `tier2` | `-` | `resetHashCacheStats` |

### `scanlog`

- Total gaps: **72**
- Tier 1 gaps: **0**
- Tier 2 gaps: **72**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `AnalysisResult` | `-` |
| `rust_unmapped` | `tier2` | `CheckId` | `-` |
| `rust_unmapped` | `tier2` | `ConfigIssue` | `-` |
| `rust_unmapped` | `tier2` | `CrashgenEntry` | `-` |
| `rust_unmapped` | `tier2` | `CrashgenRegistry` | `-` |
| `rust_unmapped` | `tier2` | `FcxModeHandler` | `-` |
| `rust_unmapped` | `tier2` | `FcxResetError` | `-` |
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
| `rust_unmapped` | `tier2` | `resolve_batch_concurrency` | `-` |
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
| `node_unmapped` | `tier2` | `-` | `parseXseLog` |
| `node_unmapped` | `tier2` | `-` | `processGameLogs` |

## Squad B (version-registry/aux)

### `aux`

- Total gaps: **16**
- Tier 1 gaps: **0**
- Tier 2 gaps: **16**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `node_unmapped` | `tier2` | `-` | `JsCheckRule` |
| `node_unmapped` | `tier2` | `-` | `JsExpectedValue` |
| `node_unmapped` | `tier2` | `-` | `JsModConflictEntry` |
| `node_unmapped` | `tier2` | `-` | `JsModSolutionCriteria` |
| `node_unmapped` | `tier2` | `-` | `JsModSolutionEntry` |
| `node_unmapped` | `tier2` | `-` | `JsPreflightAction` |
| `node_unmapped` | `tier2` | `-` | `JsPreflightRule` |
| `node_unmapped` | `tier2` | `-` | `JsRuleMessages` |
| `node_unmapped` | `tier2` | `-` | `JsRuleTarget` |
| `node_unmapped` | `tier2` | `-` | `JsSuspectErrorRule` |
| `node_unmapped` | `tier2` | `-` | `JsSuspectStackCountRule` |
| `node_unmapped` | `tier2` | `-` | `JsSuspectStackRule` |
| `node_unmapped` | `tier2` | `-` | `getApplicationDir` |
| `node_unmapped` | `tier2` | `-` | `resetFcxGlobalState` |
| `node_unmapped` | `tier2` | `-` | `setApplicationDir` |
| `node_unmapped` | `tier2` | `-` | `writeAutoscanReport` |

### `constants`

- Total gaps: **30**
- Tier 1 gaps: **0**
- Tier 2 gaps: **30**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `Fallout4Version` | `-` |
| `rust_unmapped` | `tier2` | `GameId` | `-` |
| `rust_unmapped` | `tier2` | `NULL_VERSION` | `-` |
| `rust_unmapped` | `tier2` | `SETTINGS_IGNORE_NONE` | `-` |
| `rust_unmapped` | `tier2` | `YamlFile` | `-` |
| `rust_unmapped` | `tier2` | `display_name` | `-` |
| `rust_unmapped` | `tier2` | `display_name_string` | `-` |
| `rust_unmapped` | `tier2` | `fn` | `-` |
| `rust_unmapped` | `tier2` | `fn` | `-` |
| `rust_unmapped` | `tier2` | `fn` | `-` |
| `rust_unmapped` | `tier2` | `fn` | `-` |
| `rust_unmapped` | `tier2` | `fn` | `-` |
| `rust_unmapped` | `tier2` | `fn` | `-` |
| `rust_unmapped` | `tier2` | `fn` | `-` |
| `rust_unmapped` | `tier2` | `fn` | `-` |
| `rust_unmapped` | `tier2` | `fn` | `-` |
| `rust_unmapped` | `tier2` | `fn` | `-` |
| `rust_unmapped` | `tier2` | `fn` | `-` |
| `rust_unmapped` | `tier2` | `fn` | `-` |
| `rust_unmapped` | `tier2` | `fn` | `-` |
| `rust_unmapped` | `tier2` | `fn` | `-` |
| `rust_unmapped` | `tier2` | `fn` | `-` |
| `rust_unmapped` | `tier2` | `game_version` | `-` |
| `rust_unmapped` | `tier2` | `get_version_info` | `-` |
| `rust_unmapped` | `tier2` | `must_not_be_none` | `-` |
| `rust_unmapped` | `tier2` | `short_name` | `-` |
| `rust_unmapped` | `tier2` | `version_semver` | `-` |
| `rust_unmapped` | `tier2` | `xse_acronym` | `-` |
| `rust_unmapped` | `tier2` | `xse_acronym_string` | `-` |
| `rust_unmapped` | `tier2` | `xse_config` | `-` |

### `crashgen_settings`

- Total gaps: **22**
- Tier 1 gaps: **0**
- Tier 2 gaps: **22**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `CheckRule` | `-` |
| `rust_unmapped` | `tier2` | `ConfigLayout` | `-` |
| `rust_unmapped` | `tier2` | `CrashgenSettingsRules` | `-` |
| `rust_unmapped` | `tier2` | `EvaluationContext` | `-` |
| `rust_unmapped` | `tier2` | `EvaluationOutcome` | `-` |
| `rust_unmapped` | `tier2` | `EvaluationResult` | `-` |
| `rust_unmapped` | `tier2` | `ExpectedValue` | `-` |
| `rust_unmapped` | `tier2` | `OutcomeKind` | `-` |
| `rust_unmapped` | `tier2` | `Predicate` | `-` |
| `rust_unmapped` | `tier2` | `PreflightAction` | `-` |
| `rust_unmapped` | `tier2` | `PreflightActionKind` | `-` |
| `rust_unmapped` | `tier2` | `PreflightRule` | `-` |
| `rust_unmapped` | `tier2` | `RuleMessages` | `-` |
| `rust_unmapped` | `tier2` | `RuleReportBucket` | `-` |
| `rust_unmapped` | `tier2` | `RuleSeverity` | `-` |
| `rust_unmapped` | `tier2` | `RuleTarget` | `-` |
| `rust_unmapped` | `tier2` | `TargetValueType` | `-` |
| `rust_unmapped` | `tier2` | `parse` | `-` |
| `rust_unmapped` | `tier2` | `parse` | `-` |
| `rust_unmapped` | `tier2` | `parse` | `-` |
| `rust_unmapped` | `tier2` | `parse` | `-` |
| `rust_unmapped` | `tier2` | `parse` | `-` |

### `database`

- Total gaps: **17**
- Tier 1 gaps: **0**
- Tier 2 gaps: **17**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `BATCH_CACHE_TTL_SECS` | `-` |
| `rust_unmapped` | `tier2` | `CacheEntry` | `-` |
| `rust_unmapped` | `tier2` | `CacheKey` | `-` |
| `rust_unmapped` | `tier2` | `DEFAULT_CACHE_CLEANUP_INTERVAL_SECS` | `-` |
| `rust_unmapped` | `tier2` | `DEFAULT_CACHE_CLEANUP_OP_THRESHOLD` | `-` |
| `rust_unmapped` | `tier2` | `DEFAULT_CACHE_TTL_SECS` | `-` |
| `rust_unmapped` | `tier2` | `DEFAULT_QUERY_CACHE_CAPACITY` | `-` |
| `rust_unmapped` | `tier2` | `DatabaseError` | `-` |
| `rust_unmapped` | `tier2` | `DatabasePool` | `-` |
| `rust_unmapped` | `tier2` | `MAX_CACHE_CLEANUP_INTERVAL_SECS` | `-` |
| `rust_unmapped` | `tier2` | `MAX_CACHE_CLEANUP_OP_THRESHOLD` | `-` |
| `rust_unmapped` | `tier2` | `MAX_CACHE_TTL_SECS` | `-` |
| `rust_unmapped` | `tier2` | `MAX_QUERY_CACHE_CAPACITY` | `-` |
| `rust_unmapped` | `tier2` | `MIN_CACHE_CLEANUP_INTERVAL_SECS` | `-` |
| `rust_unmapped` | `tier2` | `MIN_CACHE_CLEANUP_OP_THRESHOLD` | `-` |
| `rust_unmapped` | `tier2` | `MIN_QUERY_CACHE_CAPACITY` | `-` |
| `rust_unmapped` | `tier2` | `PoolStatistics` | `-` |

### `file_io`

- Total gaps: **26**
- Tier 1 gaps: **0**
- Tier 2 gaps: **26**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `BackupType` | `-` |
| `rust_unmapped` | `tier2` | `CRASH_AUTOSCAN_PATTERN` | `-` |
| `rust_unmapped` | `tier2` | `CRASH_LOG_PATTERN` | `-` |
| `rust_unmapped` | `tier2` | `DDSAnalyzer` | `-` |
| `rust_unmapped` | `tier2` | `DDSHeader` | `-` |
| `rust_unmapped` | `tier2` | `DDSIssue` | `-` |
| `rust_unmapped` | `tier2` | `FileGeneratorConfig` | `-` |
| `rust_unmapped` | `tier2` | `FileIOError` | `-` |
| `rust_unmapped` | `tier2` | `FileOperation` | `-` |
| `rust_unmapped` | `tier2` | `GameTarget` | `-` |
| `rust_unmapped` | `tier2` | `LogCollector` | `-` |
| `rust_unmapped` | `tier2` | `RejectedInput` | `-` |
| `rust_unmapped` | `tier2` | `TargetedResolution` | `-` |
| `rust_unmapped` | `tier2` | `backup` | `-` |
| `rust_unmapped` | `tier2` | `core` | `-` |
| `rust_unmapped` | `tier2` | `dds` | `-` |
| `rust_unmapped` | `tier2` | `encoding` | `-` |
| `rust_unmapped` | `tier2` | `error` | `-` |
| `rust_unmapped` | `tier2` | `game_files` | `-` |
| `rust_unmapped` | `tier2` | `generate_local_yaml` | `-` |
| `rust_unmapped` | `tier2` | `generation` | `-` |
| `rust_unmapped` | `tier2` | `hash` | `-` |
| `rust_unmapped` | `tier2` | `log_collection` | `-` |
| `rust_unmapped` | `tier2` | `resolve_targeted_inputs` | `-` |
| `rust_unmapped` | `tier2` | `similarity` | `-` |
| `rust_unmapped` | `tier2` | `similarity_ratio` | `-` |

### `message`

- Total gaps: **9**
- Tier 1 gaps: **0**
- Tier 2 gaps: **9**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `ContractEvent` | `-` |
| `rust_unmapped` | `tier2` | `EVENT_STARTUP_ACCELERATION_STATUS` | `-` |
| `rust_unmapped` | `tier2` | `EVENT_STARTUP_BINDING_CONTRACT_FAILED` | `-` |
| `rust_unmapped` | `tier2` | `EVENT_STARTUP_BINDING_CONTRACT_VALIDATED` | `-` |
| `rust_unmapped` | `tier2` | `Logger` | `-` |
| `rust_unmapped` | `tier2` | `format_contract_event` | `-` |
| `rust_unmapped` | `tier2` | `logging` | `-` |
| `rust_unmapped` | `tier2` | `redact_contract_fields` | `-` |
| `rust_unmapped` | `tier2` | `redact_field_value` | `-` |

### `path`

- Total gaps: **26**
- Tier 1 gaps: **0**
- Tier 2 gaps: **26**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `// Boolean convenience wrappers drive_exists` | `-` |
| `rust_unmapped` | `tier2` | `// Permission and accessibility checks is_valid_executable_path` | `-` |
| `rust_unmapped` | `tier2` | `BackupError` | `-` |
| `rust_unmapped` | `tier2` | `BackupResult` | `-` |
| `rust_unmapped` | `tier2` | `DocsPathError` | `-` |
| `rust_unmapped` | `tier2` | `DocsPathResult` | `-` |
| `rust_unmapped` | `tier2` | `DocumentsPathManager` | `-` |
| `rust_unmapped` | `tier2` | `GamePathError` | `-` |
| `rust_unmapped` | `tier2` | `GamePathResult` | `-` |
| `rust_unmapped` | `tier2` | `IniCheckResult` | `-` |
| `rust_unmapped` | `tier2` | `IniFile` | `-` |
| `rust_unmapped` | `tier2` | `PathError` | `-` |
| `rust_unmapped` | `tier2` | `PathResult` | `-` |
| `rust_unmapped` | `tier2` | `ValidationError` | `-` |
| `rust_unmapped` | `tier2` | `ValidationResult` | `-` |
| `rust_unmapped` | `tier2` | `XseVersion` | `-` |
| `rust_unmapped` | `tier2` | `check_drive_exists` | `-` |
| `rust_unmapped` | `tier2` | `has_read_permission` | `-` |
| `rust_unmapped` | `tier2` | `has_write_permission` | `-` |
| `rust_unmapped` | `tier2` | `parse_xse_log` | `-` |
| `rust_unmapped` | `tier2` | `remove_readonly_attribute` | `-` |
| `rust_unmapped` | `tier2` | `validate_is_directory` | `-` |
| `rust_unmapped` | `tier2` | `validate_is_file` | `-` |
| `rust_unmapped` | `tier2` | `validate_path_exists` | `-` |
| `rust_unmapped` | `tier2` | `validate_settings_path` | `-` |
| `rust_unmapped` | `tier2` | `validate_settings_paths` | `-` |

### `perf`

- Total gaps: **2**
- Tier 1 gaps: **0**
- Tier 2 gaps: **2**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `Timer` | `-` |
| `rust_unmapped` | `tier2` | `start_timer` | `-` |

### `registry`

- Total gaps: **14**
- Tier 1 gaps: **0**
- Tier 2 gaps: **14**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `Keys` | `-` |
| `rust_unmapped` | `tier2` | `get_application_dir` | `-` |
| `rust_unmapped` | `tier2` | `get_game_path_gui` | `-` |
| `rust_unmapped` | `tier2` | `get_game_version` | `-` |
| `rust_unmapped` | `tier2` | `get_game_version_string` | `-` |
| `rust_unmapped` | `tier2` | `get_local_dir` | `-` |
| `rust_unmapped` | `tier2` | `get_manual_docs_gui` | `-` |
| `rust_unmapped` | `tier2` | `get_yaml_cache` | `-` |
| `rust_unmapped` | `tier2` | `is_enb_present` | `-` |
| `rust_unmapped` | `tier2` | `is_gui_mode` | `-` |
| `rust_unmapped` | `tier2` | `is_registered` | `-` |
| `rust_unmapped` | `tier2` | `is_version_auto_detected` | `-` |
| `rust_unmapped` | `tier2` | `is_xse_valid` | `-` |
| `rust_unmapped` | `tier2` | `set_application_dir` | `-` |

### `scangame`

- Total gaps: **83**
- Tier 1 gaps: **0**
- Tier 2 gaps: **83**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `AddressLibInfo` | `-` |
| `rust_unmapped` | `tier2` | `BA2Error` | `-` |
| `rust_unmapped` | `tier2` | `BA2Issues` | `-` |
| `rust_unmapped` | `tier2` | `BA2Scanner` | `-` |
| `rust_unmapped` | `tier2` | `CachedConfigFile` | `-` |
| `rust_unmapped` | `tier2` | `CheckResult` | `-` |
| `rust_unmapped` | `tier2` | `CheckType` | `-` |
| `rust_unmapped` | `tier2` | `ConfigCacheError` | `-` |
| `rust_unmapped` | `tier2` | `ConfigDuplicateDetector` | `-` |
| `rust_unmapped` | `tier2` | `ConfigError` | `-` |
| `rust_unmapped` | `tier2` | `ConfigFileCache` | `-` |
| `rust_unmapped` | `tier2` | `ConfigIssue` | `-` |
| `rust_unmapped` | `tier2` | `CrashgenCheckOrchestrator` | `-` |
| `rust_unmapped` | `tier2` | `CrashgenChecker` | `-` |
| `rust_unmapped` | `tier2` | `CrashgenOrchestratorError` | `-` |
| `rust_unmapped` | `tier2` | `CrashgenReport` | `-` |
| `rust_unmapped` | `tier2` | `DuplicateEntry` | `-` |
| `rust_unmapped` | `tier2` | `DuplicateGroup` | `-` |
| `rust_unmapped` | `tier2` | `EnbChecker` | `-` |
| `rust_unmapped` | `tier2` | `EnbConfigResult` | `-` |
| `rust_unmapped` | `tier2` | `EnbError` | `-` |
| `rust_unmapped` | `tier2` | `EnbResult` | `-` |
| `rust_unmapped` | `tier2` | `EnbValidationResult` | `-` |
| `rust_unmapped` | `tier2` | `GameIntegrityChecker` | `-` |
| `rust_unmapped` | `tier2` | `GameScanConfig` | `-` |
| `rust_unmapped` | `tier2` | `GameScanOrchestrator` | `-` |
| `rust_unmapped` | `tier2` | `GameScanResult` | `-` |
| `rust_unmapped` | `tier2` | `IniError` | `-` |
| `rust_unmapped` | `tier2` | `IniValidator` | `-` |
| `rust_unmapped` | `tier2` | `IntegrityCheckResult` | `-` |
| `rust_unmapped` | `tier2` | `IntegrityConfig` | `-` |
| `rust_unmapped` | `tier2` | `IntegrityError` | `-` |
| `rust_unmapped` | `tier2` | `IssueSeverity` | `-` |
| `rust_unmapped` | `tier2` | `LogError` | `-` |
| `rust_unmapped` | `tier2` | `LogErrorEntry` | `-` |
| `rust_unmapped` | `tier2` | `LogProcessor` | `-` |
| `rust_unmapped` | `tier2` | `ModIniScanResult` | `-` |
| `rust_unmapped` | `tier2` | `ModIniScanner` | `-` |
| `rust_unmapped` | `tier2` | `ModScanResult` | `-` |
| `rust_unmapped` | `tier2` | `OrchestratorError` | `-` |
| `rust_unmapped` | `tier2` | `ScanGameError` | `-` |
| `rust_unmapped` | `tier2` | `ScanReportBuilder` | `-` |
| `rust_unmapped` | `tier2` | `ScanValidators` | `-` |
| `rust_unmapped` | `tier2` | `SetupCheckConfig` | `-` |
| `rust_unmapped` | `tier2` | `SetupCheckResults` | `-` |
| `rust_unmapped` | `tier2` | `SetupError` | `-` |
| `rust_unmapped` | `tier2` | `SetupResult` | `-` |
| `rust_unmapped` | `tier2` | `TomlConfigIssue` | `-` |
| `rust_unmapped` | `tier2` | `TomlError` | `-` |
| `rust_unmapped` | `tier2` | `TomlIssueSeverity` | `-` |
| `rust_unmapped` | `tier2` | `UnpackedError` | `-` |
| `rust_unmapped` | `tier2` | `UnpackedIssues` | `-` |
| `rust_unmapped` | `tier2` | `UnpackedScanner` | `-` |
| `rust_unmapped` | `tier2` | `VERSION` | `-` |
| `rust_unmapped` | `tier2` | `ValidationResult` | `-` |
| `rust_unmapped` | `tier2` | `VsyncEntry` | `-` |
| `rust_unmapped` | `tier2` | `WryeBashParser` | `-` |
| `rust_unmapped` | `tier2` | `WryeError` | `-` |
| `rust_unmapped` | `tier2` | `WryeIssue` | `-` |
| `rust_unmapped` | `tier2` | `WryeSeverity` | `-` |
| `rust_unmapped` | `tier2` | `XseChecker` | `-` |
| `rust_unmapped` | `tier2` | `XseError` | `-` |
| `rust_unmapped` | `tier2` | `ba2` | `-` |
| `rust_unmapped` | `tier2` | `config_cache` | `-` |
| `rust_unmapped` | `tier2` | `crashgen_orchestrator` | `-` |
| `rust_unmapped` | `tier2` | `detect_config_issues` | `-` |
| `rust_unmapped` | `tier2` | `enb` | `-` |
| `rust_unmapped` | `tier2` | `error` | `-` |
| `rust_unmapped` | `tier2` | `game_report` | `-` |
| `rust_unmapped` | `tier2` | `ini` | `-` |
| `rust_unmapped` | `tier2` | `integrity` | `-` |
| `rust_unmapped` | `tier2` | `logs` | `-` |
| `rust_unmapped` | `tier2` | `migrate_game_version_setting` | `-` |
| `rust_unmapped` | `tier2` | `mod_ini` | `-` |
| `rust_unmapped` | `tier2` | `needs_path_detection` | `-` |
| `rust_unmapped` | `tier2` | `orchestrator` | `-` |
| `rust_unmapped` | `tier2` | `resolve_effective_game_version` | `-` |
| `rust_unmapped` | `tier2` | `run_combined_checks` | `-` |
| `rust_unmapped` | `tier2` | `setup` | `-` |
| `rust_unmapped` | `tier2` | `toml` | `-` |
| `rust_unmapped` | `tier2` | `unpacked` | `-` |
| `rust_unmapped` | `tier2` | `wrye` | `-` |
| `rust_unmapped` | `tier2` | `xse` | `-` |

### `settings`

- Total gaps: **23**
- Tier 1 gaps: **0**
- Tier 2 gaps: **23**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `CacheStats` | `-` |
| `rust_unmapped` | `tier2` | `SettingsError` | `-` |
| `rust_unmapped` | `tier2` | `SettingsSource` | `-` |
| `rust_unmapped` | `tier2` | `Yaml` | `-` |
| `rust_unmapped` | `tier2` | `cache_keys` | `-` |
| `rust_unmapped` | `tier2` | `cache_size` | `-` |
| `rust_unmapped` | `tier2` | `cache_stats` | `-` |
| `rust_unmapped` | `tier2` | `clear_cache` | `-` |
| `rust_unmapped` | `tier2` | `get_cached` | `-` |
| `rust_unmapped` | `tier2` | `invalidate` | `-` |
| `rust_unmapped` | `tier2` | `is_cached` | `-` |
| `rust_unmapped` | `tier2` | `load_settings_async` | `-` |
| `rust_unmapped` | `tier2` | `load_settings_sync` | `-` |
| `rust_unmapped` | `tier2` | `load_yaml_async` | `-` |
| `rust_unmapped` | `tier2` | `load_yaml_batch_async` | `-` |
| `rust_unmapped` | `tier2` | `load_yaml_batch_sync` | `-` |
| `rust_unmapped` | `tier2` | `load_yaml_merged_async` | `-` |
| `rust_unmapped` | `tier2` | `load_yaml_merged_sync` | `-` |
| `rust_unmapped` | `tier2` | `load_yaml_sync` | `-` |
| `rust_unmapped` | `tier2` | `merge_yaml_documents` | `-` |
| `rust_unmapped` | `tier2` | `parse_yaml_content` | `-` |
| `rust_unmapped` | `tier2` | `reset_cache_stats` | `-` |
| `rust_unmapped` | `tier2` | `validators` | `-` |

### `shared`

- Total gaps: **15**
- Tier 1 gaps: **0**
- Tier 2 gaps: **15**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `AsyncBridge` | `-` |
| `rust_unmapped` | `tier2` | `BridgeError` | `-` |
| `rust_unmapped` | `tier2` | `ClassicError` | `-` |
| `rust_unmapped` | `tier2` | `ClassicResult` | `-` |
| `rust_unmapped` | `tier2` | `EventLoopDispatcher` | `-` |
| `rust_unmapped` | `tier2` | `IntoClassicError` | `-` |
| `rust_unmapped` | `tier2` | `RuntimeConfig` | `-` |
| `rust_unmapped` | `tier2` | `SlintDispatcher` | `-` |
| `rust_unmapped` | `tier2` | `async_bridge` | `-` |
| `rust_unmapped` | `tier2` | `cpu_optimized` | `-` |
| `rust_unmapped` | `tier2` | `errors` | `-` |
| `rust_unmapped` | `tier2` | `io_optimized` | `-` |
| `rust_unmapped` | `tier2` | `minimal` | `-` |
| `rust_unmapped` | `tier2` | `performance_core` | `-` |
| `rust_unmapped` | `tier2` | `set_dispatcher` | `-` |

### `update`

- Total gaps: **7**
- Tier 1 gaps: **0**
- Tier 2 gaps: **7**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `GithubAsset` | `-` |
| `rust_unmapped` | `tier2` | `GithubClient` | `-` |
| `rust_unmapped` | `tier2` | `GithubRelease` | `-` |
| `rust_unmapped` | `tier2` | `UpdateError` | `-` |
| `rust_unmapped` | `tier2` | `VERSION` | `-` |
| `rust_unmapped` | `tier2` | `error` | `-` |
| `rust_unmapped` | `tier2` | `github` | `-` |

### `version`

- Total gaps: **16**
- Tier 1 gaps: **0**
- Tier 2 gaps: **16**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `NULL_VERSION` | `-` |
| `rust_unmapped` | `tier2` | `PeVersionError` | `-` |
| `rust_unmapped` | `tier2` | `PeVersionResult` | `-` |
| `rust_unmapped` | `tier2` | `VersionError` | `-` |
| `rust_unmapped` | `tier2` | `VersionResult` | `-` |
| `rust_unmapped` | `tier2` | `compare_versions` | `-` |
| `rust_unmapped` | `tier2` | `extract_all_versions` | `-` |
| `rust_unmapped` | `tier2` | `extract_pe_version` | `-` |
| `rust_unmapped` | `tier2` | `extract_version_from_filename` | `-` |
| `rust_unmapped` | `tier2` | `extract_version_from_log` | `-` |
| `rust_unmapped` | `tier2` | `format_version` | `-` |
| `rust_unmapped` | `tier2` | `is_known_f4se_version` | `-` |
| `rust_unmapped` | `tier2` | `is_known_fallout4_version` | `-` |
| `rust_unmapped` | `tier2` | `parse_version` | `-` |
| `rust_unmapped` | `tier2` | `pe_version` | `-` |
| `rust_unmapped` | `tier2` | `try_parse_version` | `-` |

### `version_registry`

- Total gaps: **5**
- Tier 1 gaps: **0**
- Tier 2 gaps: **5**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `node_unmapped` | `tier2` | `-` | `JsCrashgenRegistryEntry` |
| `node_unmapped` | `tier2` | `-` | `JsCrashgenSettingsRules` |
| `node_unmapped` | `tier2` | `-` | `checkCrashgenConfigWithRules` |
| `node_unmapped` | `tier2` | `-` | `checkCrashgenFullWithRules` |
| `node_unmapped` | `tier2` | `-` | `migrateGameVersionSetting` |

### `web`

- Total gaps: **15**
- Tier 1 gaps: **0**
- Tier 2 gaps: **15**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `CLASSIC_VERSION` | `-` |
| `rust_unmapped` | `tier2` | `ModSite` | `-` |
| `rust_unmapped` | `tier2` | `USER_AGENT_PREFIX` | `-` |
| `rust_unmapped` | `tier2` | `WebError` | `-` |
| `rust_unmapped` | `tier2` | `WebResult` | `-` |
| `rust_unmapped` | `tier2` | `base_url` | `-` |
| `rust_unmapped` | `tier2` | `build_url_with_query` | `-` |
| `rust_unmapped` | `tier2` | `extract_domain` | `-` |
| `rust_unmapped` | `tier2` | `game_url` | `-` |
| `rust_unmapped` | `tier2` | `get_user_agent` | `-` |
| `rust_unmapped` | `tier2` | `get_user_agent_with_suffix` | `-` |
| `rust_unmapped` | `tier2` | `is_valid_url` | `-` |
| `rust_unmapped` | `tier2` | `join_url` | `-` |
| `rust_unmapped` | `tier2` | `name` | `-` |
| `rust_unmapped` | `tier2` | `validate_url` | `-` |

### `xse`

- Total gaps: **17**
- Tier 1 gaps: **0**
- Tier 2 gaps: **17**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `XseError` | `-` |
| `rust_unmapped` | `tier2` | `XseInfo` | `-` |
| `rust_unmapped` | `tier2` | `XseResult` | `-` |
| `rust_unmapped` | `tier2` | `XseType` | `-` |
| `rust_unmapped` | `tier2` | `as_str` | `-` |
| `rust_unmapped` | `tier2` | `check_installed` | `-` |
| `rust_unmapped` | `tier2` | `compare_versions` | `-` |
| `rust_unmapped` | `tier2` | `detect_xse_version` | `-` |
| `rust_unmapped` | `tier2` | `dll_prefix` | `-` |
| `rust_unmapped` | `tier2` | `from_game_id` | `-` |
| `rust_unmapped` | `tier2` | `get_xse_info` | `-` |
| `rust_unmapped` | `tier2` | `is_xse_installed` | `-` |
| `rust_unmapped` | `tier2` | `loader_name` | `-` |
| `rust_unmapped` | `tier2` | `loader_path` | `-` |
| `rust_unmapped` | `tier2` | `new` | `-` |
| `rust_unmapped` | `tier2` | `parse_version` | `-` |
| `rust_unmapped` | `tier2` | `try_parse_version` | `-` |

### `yaml`

- Total gaps: **23**
- Tier 1 gaps: **0**
- Tier 2 gaps: **23**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `CacheStats` | `-` |
| `rust_unmapped` | `tier2` | `YamlError` | `-` |
| `rust_unmapped` | `tier2` | `YamlOperations` | `-` |
| `rust_unmapped` | `tier2` | `cache_stats` | `-` |
| `rust_unmapped` | `tier2` | `clear_cache` | `-` |
| `rust_unmapped` | `tier2` | `dump_yaml` | `-` |
| `rust_unmapped` | `tier2` | `get_cache_stats` | `-` |
| `rust_unmapped` | `tier2` | `get_hashmap_value` | `-` |
| `rust_unmapped` | `tier2` | `get_indexmap_value` | `-` |
| `rust_unmapped` | `tier2` | `get_setting` | `-` |
| `rust_unmapped` | `tier2` | `get_settings_batch` | `-` |
| `rust_unmapped` | `tier2` | `get_string_value` | `-` |
| `rust_unmapped` | `tier2` | `get_vec_value` | `-` |
| `rust_unmapped` | `tier2` | `is_cache_enabled` | `-` |
| `rust_unmapped` | `tier2` | `load_yaml_file` | `-` |
| `rust_unmapped` | `tier2` | `load_yaml_files_batch` | `-` |
| `rust_unmapped` | `tier2` | `merge_keys` | `-` |
| `rust_unmapped` | `tier2` | `new` | `-` |
| `rust_unmapped` | `tier2` | `parse_yaml` | `-` |
| `rust_unmapped` | `tier2` | `reset_cache_stats` | `-` |
| `rust_unmapped` | `tier2` | `save_yaml_file` | `-` |
| `rust_unmapped` | `tier2` | `set_cache_enabled` | `-` |
| `rust_unmapped` | `tier2` | `set_setting` | `-` |
