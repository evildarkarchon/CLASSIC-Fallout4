# Phase 1 Engineering Handoff Map

- Generated: `2026-02-25T11:51:14.966043+00:00`
- Total gaps handed off: **315**

## Squad A (scanlog/config)

### `config`

- Total gaps: **58**
- Tier 1 gaps: **0**
- Tier 2 gaps: **58**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `ConfigError` | `-` |
| `rust_unmapped` | `tier2` | `CrashgenEntryRaw` | `-` |
| `rust_unmapped` | `tier2` | `PathConfig` | `-` |
| `rust_unmapped` | `tier2` | `config` | `-` |
| `rust_unmapped` | `tier2` | `get_runtime` | `-` |
| `rust_unmapped` | `tier2` | `yamldata` | `-` |
| `node_unmapped` | `tier2` | `-` | `BATCH_CACHE_TTL` |
| `node_unmapped` | `tier2` | `-` | `DEFAULT_CACHE_TTL` |
| `node_unmapped` | `tier2` | `-` | `FileIoConfig` |
| `node_unmapped` | `tier2` | `-` | `JsAnalysisConfig` |
| `node_unmapped` | `tier2` | `-` | `JsConfigDuplicateDetector` |
| `node_unmapped` | `tier2` | `-` | `JsConfigIssue` |
| `node_unmapped` | `tier2` | `-` | `JsEnbConfigResult` |
| `node_unmapped` | `tier2` | `-` | `JsGameScanConfig` |
| `node_unmapped` | `tier2` | `-` | `JsIntegrityConfig` |
| `node_unmapped` | `tier2` | `-` | `JsPathConfig` |
| `node_unmapped` | `tier2` | `-` | `JsPathDetectionResult` |
| `node_unmapped` | `tier2` | `-` | `JsTomlConfigIssue` |
| `node_unmapped` | `tier2` | `-` | `JsXseConfig` |
| `node_unmapped` | `tier2` | `-` | `JsYamlFile` |
| `node_unmapped` | `tier2` | `-` | `MAX_CACHE_TTL` |
| `node_unmapped` | `tier2` | `-` | `SettingsCacheStats` |
| `node_unmapped` | `tier2` | `-` | `YamlDocument` |
| `node_unmapped` | `tier2` | `-` | `clearSettingsCache` |
| `node_unmapped` | `tier2` | `-` | `detectConfigDuplicates` |
| `node_unmapped` | `tier2` | `-` | `generateLocalYaml` |
| `node_unmapped` | `tier2` | `-` | `getAllYamlFiles` |
| `node_unmapped` | `tier2` | `-` | `getBatchCacheTtl` |
| `node_unmapped` | `tier2` | `-` | `getCached` |
| `node_unmapped` | `tier2` | `-` | `getDefaultCacheTtl` |
| `node_unmapped` | `tier2` | `-` | `getMaxCacheTtl` |
| `node_unmapped` | `tier2` | `-` | `getSettingsCacheStats` |
| `node_unmapped` | `tier2` | `-` | `getYamlFileDescription` |
| `node_unmapped` | `tier2` | `-` | `invalidateSettings` |
| `node_unmapped` | `tier2` | `-` | `isCached` |
| `node_unmapped` | `tier2` | `-` | `loadSettingsAsync` |
| `node_unmapped` | `tier2` | `-` | `loadSettingsSync` |
| `node_unmapped` | `tier2` | `-` | `needsPathDetection` |
| `node_unmapped` | `tier2` | `-` | `resetSettingsCacheStats` |
| `node_unmapped` | `tier2` | `-` | `settingsCacheKeys` |
| `node_unmapped` | `tier2` | `-` | `settingsCacheSize` |
| `node_unmapped` | `tier2` | `-` | `validateSettingsPath` |
| `node_unmapped` | `tier2` | `-` | `validateSettingsPaths` |
| `node_unmapped` | `tier2` | `-` | `yamlClearCache` |
| `node_unmapped` | `tier2` | `-` | `yamlGetCacheStats` |
| `node_unmapped` | `tier2` | `-` | `yamlGetHashmapValue` |
| `node_unmapped` | `tier2` | `-` | `yamlGetHashmapVecValue` |
| `node_unmapped` | `tier2` | `-` | `yamlGetIndexmapValue` |
| `node_unmapped` | `tier2` | `-` | `yamlGetSettingsBatch` |
| `node_unmapped` | `tier2` | `-` | `yamlGetStringValue` |
| `node_unmapped` | `tier2` | `-` | `yamlGetValue` |
| `node_unmapped` | `tier2` | `-` | `yamlGetVecValue` |
| `node_unmapped` | `tier2` | `-` | `yamlLoadFile` |
| `node_unmapped` | `tier2` | `-` | `yamlParse` |
| `node_unmapped` | `tier2` | `-` | `yamlSaveFile` |
| `node_unmapped` | `tier2` | `-` | `yamlSetSetting` |
| `node_unmapped` | `tier2` | `-` | `yamlSetSettingsBatch` |
| `node_unmapped` | `tier2` | `-` | `yamlStringify` |

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
| `rust_unmapped` | `tier2` | `CrashgenVersionStatus` | `-` |
| `rust_unmapped` | `tier2` | `FcxModeHandler` | `-` |
| `rust_unmapped` | `tier2` | `FormIDAnalyzer` | `-` |
| `rust_unmapped` | `tier2` | `FormIDAnalyzerCore` | `-` |
| `rust_unmapped` | `tier2` | `GLOBAL_FCX_HANDLER` | `-` |
| `rust_unmapped` | `tier2` | `GpuDetector` | `-` |
| `rust_unmapped` | `tier2` | `GpuVendor` | `-` |
| `rust_unmapped` | `tier2` | `PapyrusAnalyzer` | `-` |
| `rust_unmapped` | `tier2` | `PapyrusError` | `-` |
| `rust_unmapped` | `tier2` | `PatternMatcher` | `-` |
| `rust_unmapped` | `tier2` | `PluginAnalyzer` | `-` |
| `rust_unmapped` | `tier2` | `RecordScanner` | `-` |
| `rust_unmapped` | `tier2` | `ReportComposer` | `-` |
| `rust_unmapped` | `tier2` | `ReportFragment` | `-` |
| `rust_unmapped` | `tier2` | `ReportGenerator` | `-` |
| `rust_unmapped` | `tier2` | `RustFormIDAnalyzer` | `-` |
| `rust_unmapped` | `tier2` | `ScanLogError` | `-` |
| `rust_unmapped` | `tier2` | `SettingsValidator` | `-` |
| `rust_unmapped` | `tier2` | `StreamingIteratorParser` | `-` |
| `rust_unmapped` | `tier2` | `StreamingLogParser` | `-` |
| `rust_unmapped` | `tier2` | `StringPool` | `-` |
| `rust_unmapped` | `tier2` | `SuspectScanner` | `-` |
| `rust_unmapped` | `tier2` | `build_analysis_config_from_yaml` | `-` |
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

- Total gaps: **142**
- Tier 1 gaps: **0**
- Tier 2 gaps: **142**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `node_unmapped` | `tier2` | `-` | `BackupManager` |
| `node_unmapped` | `tier2` | `-` | `CRASH_AUTOSCAN_PATTERN` |
| `node_unmapped` | `tier2` | `-` | `DocsPathFinder` |
| `node_unmapped` | `tier2` | `-` | `DocumentsChecker` |
| `node_unmapped` | `tier2` | `-` | `GamePathFinder` |
| `node_unmapped` | `tier2` | `-` | `GithubClient` |
| `node_unmapped` | `tier2` | `-` | `JsBa2Issues` |
| `node_unmapped` | `tier2` | `-` | `JsBa2ScanResult` |
| `node_unmapped` | `tier2` | `-` | `JsBa2Scanner` |
| `node_unmapped` | `tier2` | `-` | `JsBackupInfo` |
| `node_unmapped` | `tier2` | `-` | `JsBackupManager` |
| `node_unmapped` | `tier2` | `-` | `JsBatchEntry` |
| `node_unmapped` | `tier2` | `-` | `JsCheckResult` |
| `node_unmapped` | `tier2` | `-` | `JsCheckType` |
| `node_unmapped` | `tier2` | `-` | `JsDDSAnalyzer` |
| `node_unmapped` | `tier2` | `-` | `JsDatabasePool` |
| `node_unmapped` | `tier2` | `-` | `JsDdsAnalyzer` |
| `node_unmapped` | `tier2` | `-` | `JsDdsBatchResult` |
| `node_unmapped` | `tier2` | `-` | `JsDdsIssue` |
| `node_unmapped` | `tier2` | `-` | `JsDuplicateGroup` |
| `node_unmapped` | `tier2` | `-` | `JsEnbChecker` |
| `node_unmapped` | `tier2` | `-` | `JsEnbResult` |
| `node_unmapped` | `tier2` | `-` | `JsEnbValidationResult` |
| `node_unmapped` | `tier2` | `-` | `JsFileGenerator` |
| `node_unmapped` | `tier2` | `-` | `JsFileIO` |
| `node_unmapped` | `tier2` | `-` | `JsFileOperationResult` |
| `node_unmapped` | `tier2` | `-` | `JsGameFilesManager` |
| `node_unmapped` | `tier2` | `-` | `JsGameId` |
| `node_unmapped` | `tier2` | `-` | `JsGameIntegrityChecker` |
| `node_unmapped` | `tier2` | `-` | `JsGameScanResult` |
| `node_unmapped` | `tier2` | `-` | `JsGithubAsset` |
| `node_unmapped` | `tier2` | `-` | `JsGithubRelease` |
| `node_unmapped` | `tier2` | `-` | `JsIniCheckResult` |
| `node_unmapped` | `tier2` | `-` | `JsIniValidator` |
| `node_unmapped` | `tier2` | `-` | `JsIntegrityCheckResult` |
| `node_unmapped` | `tier2` | `-` | `JsIssueSeverity` |
| `node_unmapped` | `tier2` | `-` | `JsMatchResult` |
| `node_unmapped` | `tier2` | `-` | `JsMessage` |
| `node_unmapped` | `tier2` | `-` | `JsMessageTarget` |
| `node_unmapped` | `tier2` | `-` | `JsMessageType` |
| `node_unmapped` | `tier2` | `-` | `JsModDuplicateEntry` |
| `node_unmapped` | `tier2` | `-` | `JsModIniScanResult` |
| `node_unmapped` | `tier2` | `-` | `JsModScanResult` |
| `node_unmapped` | `tier2` | `-` | `JsModSite` |
| `node_unmapped` | `tier2` | `-` | `JsPoolStatistics` |
| `node_unmapped` | `tier2` | `-` | `JsTomlIssueSeverity` |
| `node_unmapped` | `tier2` | `-` | `JsUnpackedIssues` |
| `node_unmapped` | `tier2` | `-` | `JsUnpackedScanner` |
| `node_unmapped` | `tier2` | `-` | `JsUpdateCheckResult` |
| `node_unmapped` | `tier2` | `-` | `JsValidationResult` |
| `node_unmapped` | `tier2` | `-` | `JsVsyncEntry` |
| `node_unmapped` | `tier2` | `-` | `JsWryeBashParser` |
| `node_unmapped` | `tier2` | `-` | `JsWryeIssue` |
| `node_unmapped` | `tier2` | `-` | `JsXseChecker` |
| `node_unmapped` | `tier2` | `-` | `JsXseInfo` |
| `node_unmapped` | `tier2` | `-` | `JsXseType` |
| `node_unmapped` | `tier2` | `-` | `MetricsSummaryResult` |
| `node_unmapped` | `tier2` | `-` | `QueryParam` |
| `node_unmapped` | `tier2` | `-` | `ResourceCount` |
| `node_unmapped` | `tier2` | `-` | `ResourceInfo` |
| `node_unmapped` | `tier2` | `-` | `RuntimeInfo` |
| `node_unmapped` | `tier2` | `-` | `TimingStats` |
| `node_unmapped` | `tier2` | `-` | `buildUrlWithQuery` |
| `node_unmapped` | `tier2` | `-` | `calculateFileSimilarity` |
| `node_unmapped` | `tier2` | `-` | `calculateTextSimilarity` |
| `node_unmapped` | `tier2` | `-` | `checkDriveExists` |
| `node_unmapped` | `tier2` | `-` | `checkEnb` |
| `node_unmapped` | `tier2` | `-` | `checkForUpdates` |
| `node_unmapped` | `tier2` | `-` | `checkReadPermissions` |
| `node_unmapped` | `tier2` | `-` | `checkWritePermissions` |
| `node_unmapped` | `tier2` | `-` | `clearAllMetrics` |
| `node_unmapped` | `tier2` | `-` | `countResourcesByType` |
| `node_unmapped` | `tier2` | `-` | `createMessage` |
| `node_unmapped` | `tier2` | `-` | `createResourceInfo` |
| `node_unmapped` | `tier2` | `-` | `createResourceInfoWithSize` |
| `node_unmapped` | `tier2` | `-` | `detectCrashPattern` |
| `node_unmapped` | `tier2` | `-` | `detectEncoding` |
| `node_unmapped` | `tier2` | `-` | `detectResourceType` |
| `node_unmapped` | `tier2` | `-` | `enumerateResources` |
| `node_unmapped` | `tier2` | `-` | `extractDomain` |
| `node_unmapped` | `tier2` | `-` | `formatMessage` |
| `node_unmapped` | `tier2` | `-` | `generateIgnoreFile` |
| `node_unmapped` | `tier2` | `-` | `getAllGameIds` |
| `node_unmapped` | `tier2` | `-` | `getGameName` |
| `node_unmapped` | `tier2` | `-` | `getLatestRelease` |
| `node_unmapped` | `tier2` | `-` | `getMetricsSummary` |
| `node_unmapped` | `tier2` | `-` | `getModSiteGameUrl` |
| `node_unmapped` | `tier2` | `-` | `getModSiteName` |
| `node_unmapped` | `tier2` | `-` | `getModSiteUrl` |
| `node_unmapped` | `tier2` | `-` | `getResourceExtensions` |
| `node_unmapped` | `tier2` | `-` | `getRuntimeInfo` |
| `node_unmapped` | `tier2` | `-` | `getSystemDocumentsPath` |
| `node_unmapped` | `tier2` | `-` | `getUserAgent` |
| `node_unmapped` | `tier2` | `-` | `getUserAgentPrefix` |
| `node_unmapped` | `tier2` | `-` | `getUserAgentWithSuffix` |
| `node_unmapped` | `tier2` | `-` | `getXseInfo` |
| `node_unmapped` | `tier2` | `-` | `hasUpdate` |
| `node_unmapped` | `tier2` | `-` | `hashFile` |
| `node_unmapped` | `tier2` | `-` | `hashFilesParallel` |
| `node_unmapped` | `tier2` | `-` | `internString` |
| `node_unmapped` | `tier2` | `-` | `isRestrictedPath` |
| `node_unmapped` | `tier2` | `-` | `isRuntimeAvailable` |
| `node_unmapped` | `tier2` | `-` | `isSupportedResource` |
| `node_unmapped` | `tier2` | `-` | `isValidExecutablePath` |
| `node_unmapped` | `tier2` | `-` | `isValidPath` |
| `node_unmapped` | `tier2` | `-` | `isValidUrl` |
| `node_unmapped` | `tier2` | `-` | `isXseInstalled` |
| `node_unmapped` | `tier2` | `-` | `joinPaths` |
| `node_unmapped` | `tier2` | `-` | `joinUrl` |
| `node_unmapped` | `tier2` | `-` | `loadBatchAsync` |
| `node_unmapped` | `tier2` | `-` | `loadBatchSync` |
| `node_unmapped` | `tier2` | `-` | `normalizePath` |
| `node_unmapped` | `tier2` | `-` | `normalizeString` |
| `node_unmapped` | `tier2` | `-` | `parseResourceType` |
| `node_unmapped` | `tier2` | `-` | `parseSteamLibrary` |
| `node_unmapped` | `tier2` | `-` | `parseXseType` |
| `node_unmapped` | `tier2` | `-` | `processStringBatch` |
| `node_unmapped` | `tier2` | `-` | `queryGameRegistry` |
| `node_unmapped` | `tier2` | `-` | `recordTimingMetric` |
| `node_unmapped` | `tier2` | `-` | `registryClear` |
| `node_unmapped` | `tier2` | `-` | `registryGet` |
| `node_unmapped` | `tier2` | `-` | `registryGetGame` |
| `node_unmapped` | `tier2` | `-` | `registryRemove` |
| `node_unmapped` | `tier2` | `-` | `registrySet` |
| `node_unmapped` | `tier2` | `-` | `registrySetGame` |
| `node_unmapped` | `tier2` | `-` | `removeReadonly` |
| `node_unmapped` | `tier2` | `-` | `runGameChecks` |
| `node_unmapped` | `tier2` | `-` | `runModScans` |
| `node_unmapped` | `tier2` | `-` | `scanAllBa2Archives` |
| `node_unmapped` | `tier2` | `-` | `scanModInis` |
| `node_unmapped` | `tier2` | `-` | `scanUnpackedFiles` |
| `node_unmapped` | `tier2` | `-` | `stripEmojiText` |
| `node_unmapped` | `tier2` | `-` | `validateCustomScanPath` |
| `node_unmapped` | `tier2` | `-` | `validatePathWithPermissions` |
| `node_unmapped` | `tier2` | `-` | `validatePathsBatch` |
| `node_unmapped` | `tier2` | `-` | `validateRequiredFiles` |
| `node_unmapped` | `tier2` | `-` | `validateResource` |
| `node_unmapped` | `tier2` | `-` | `validateUrl` |
| `node_unmapped` | `tier2` | `-` | `xseDllPrefix` |
| `node_unmapped` | `tier2` | `-` | `xseLoaderName` |
| `node_unmapped` | `tier2` | `-` | `xseTypeForGame` |
| `node_unmapped` | `tier2` | `-` | `xseTypeName` |

### `version_registry`

- Total gaps: **43**
- Tier 1 gaps: **0**
- Tier 2 gaps: **43**

| Gap Type | Tier | Rust Symbol | Node Export |
|---|---|---|---|
| `rust_unmapped` | `tier2` | `AddressLibFormat` | `-` |
| `rust_unmapped` | `tier2` | `AddressLibraryConfig` | `-` |
| `rust_unmapped` | `tier2` | `CompatibleRange` | `-` |
| `rust_unmapped` | `tier2` | `LogLevel` | `-` |
| `rust_unmapped` | `tier2` | `MatchConfidence` | `-` |
| `rust_unmapped` | `tier2` | `Result` | `-` |
| `rust_unmapped` | `tier2` | `UnknownVersionHandling` | `-` |
| `rust_unmapped` | `tier2` | `UnknownVersionStrategy` | `-` |
| `rust_unmapped` | `tier2` | `VersionMatcher` | `-` |
| `rust_unmapped` | `tier2` | `VersionRegistryError` | `-` |
| `rust_unmapped` | `tier2` | `XseConfig` | `-` |
| `rust_unmapped` | `tier2` | `get_version_registry` | `-` |
| `node_unmapped` | `tier2` | `-` | `Fallout4VersionInfo` |
| `node_unmapped` | `tier2` | `-` | `JsAddressLibInfo` |
| `node_unmapped` | `tier2` | `-` | `JsAddressLibraryConfig` |
| `node_unmapped` | `tier2` | `-` | `JsCrashgenCheckResult` |
| `node_unmapped` | `tier2` | `-` | `JsCrashgenChecker` |
| `node_unmapped` | `tier2` | `-` | `JsCrashgenConfig` |
| `node_unmapped` | `tier2` | `-` | `JsCrashgenReport` |
| `node_unmapped` | `tier2` | `-` | `JsCrashgenVersionInfo` |
| `node_unmapped` | `tier2` | `-` | `JsFallout4Version` |
| `node_unmapped` | `tier2` | `-` | `JsGameVersion` |
| `node_unmapped` | `tier2` | `-` | `JsVersionInfo` |
| `node_unmapped` | `tier2` | `-` | `XseVersion` |
| `node_unmapped` | `tier2` | `-` | `checkCrashgenConfig` |
| `node_unmapped` | `tier2` | `-` | `checkCrashgenFull` |
| `node_unmapped` | `tier2` | `-` | `compareVersions` |
| `node_unmapped` | `tier2` | `-` | `detectXseVersion` |
| `node_unmapped` | `tier2` | `-` | `extractAllVersions` |
| `node_unmapped` | `tier2` | `-` | `extractVersionFromFilename` |
| `node_unmapped` | `tier2` | `-` | `extractVersionFromLog` |
| `node_unmapped` | `tier2` | `-` | `formatVersion` |
| `node_unmapped` | `tier2` | `-` | `getAddressLibInfo` |
| `node_unmapped` | `tier2` | `-` | `getAllFallout4Versions` |
| `node_unmapped` | `tier2` | `-` | `getClassicVersion` |
| `node_unmapped` | `tier2` | `-` | `getFallout4VersionInfo` |
| `node_unmapped` | `tier2` | `-` | `getVersion` |
| `node_unmapped` | `tier2` | `-` | `isKnownFallout4Version` |
| `node_unmapped` | `tier2` | `-` | `parseVersion` |
| `node_unmapped` | `tier2` | `-` | `registryGetGameVersion` |
| `node_unmapped` | `tier2` | `-` | `registryIsVrVersion` |
| `node_unmapped` | `tier2` | `-` | `resolveEffectiveGameVersion` |
| `node_unmapped` | `tier2` | `-` | `tryParseVersion` |
