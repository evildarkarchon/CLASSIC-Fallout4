# Rust<->Node Parity Diff Baseline (Phase 1)

- Generated: `2026-04-09T23:44:58.171684+00:00`
- Tier-1 contract rows: **327**
- Tier-1 matched: **327**
- Tier-1 missing Rust: **0**
- Tier-1 missing Node: **0**
- Tier-1 signature mismatch: **0**
- Total gaps (Tier-1 + Tier-2): **398**

## Tier-1 Contract Evaluation

| ID | Owner Module | Rust Symbol | Node Export | Status |
|---|---|---|---|---|
| `scanlog-analysis-config` | `scanlog` | `AnalysisConfig` | `createAnalysisConfig` | `matched` |
| `scanlog-process-log` | `scanlog` | `OrchestratorCore` | `processLog` | `matched` |
| `scanlog-process-batch` | `scanlog` | `OrchestratorCore` | `processLogsBatch` | `matched` |
| `scanlog-parse-segments` | `scanlog` | `LogParser` | `parseLogSegments` | `matched` |
| `scanlog-extract-formids` | `scanlog` | `LogParser` | `extractFormIds` | `matched` |
| `scanlog-extract-plugins` | `scanlog` | `LogParser` | `extractPluginList` | `matched` |
| `scanlog-detect-vr` | `scanlog` | `detect_vr_log` | `detectVrLog` | `matched` |
| `scanlog-detect-gpu` | `scanlog` | `GpuInfo` | `detectGpuInfo` | `matched` |
| `scanlog-parse-crashgen-version` | `scanlog` | `CrashgenVersion` | `parseCrashgenVersion` | `matched` |
| `scanlog-crashgen-version-status` | `scanlog` | `check_crashgen_version_status` | `checkCrashgenVersionStatus` | `matched` |
| `scanlog-papyrus-analysis` | `scanlog` | `PapyrusStats` | `analyzePapyrusLog` | `matched` |
| `scanlog-analysis-config-from-yaml-content` | `scanlog` | `build_analysis_config_from_yaml` | `createAnalysisConfigFromYamlContent` | `matched` |
| `scanlog-process-log-with-yaml-content` | `scanlog` | `OrchestratorCore` | `processLogWithYamlContent` | `matched` |
| `scanlog-process-batch-with-yaml-content` | `scanlog` | `OrchestratorCore` | `processLogsBatchWithYamlContent` | `matched` |
| `scanlog-detect-crash-pattern` | `scanlog` | `PatternMatcher` | `detectCrashPattern` | `matched` |
| `scanlog-crashgen-version-status-enum` | `scanlog` | `CrashgenVersionStatus` | `JsCrashgenVersionStatus` | `matched` |
| `config-yamldata-class` | `config` | `YamlDataCore` | `YamlData` | `matched` |
| `config-create-yamldata-content` | `config` | `YamlDataCore` | `createYamlDataFromContent` | `matched` |
| `config-classic-config-class` | `config` | `ClassicConfig` | `ClassicConfigJs` | `matched` |
| `config-create-default-config` | `config` | `ClassicConfig` | `createDefaultConfig` | `matched` |
| `config-clear-yaml-cache` | `config` | `clear_global_yaml_cache` | `clearYamlCache` | `matched` |
| `config-yaml-source-enum` | `config` | `YamlSource` | `JsYamlSource` | `matched` |
| `config-yaml-source-path` | `config` | `YamlSource` | `getYamlSourcePath` | `matched` |
| `config-yaml-source-display-name` | `config` | `YamlSource` | `getYamlSourceDisplayName` | `matched` |
| `config-yaml-source-display-name-with-game` | `config` | `YamlSource` | `getYamlSourceDisplayNameWithGame` | `matched` |
| `config-fileio-config-interface` | `config` | `config` | `FileIoConfig` | `matched` |
| `config-path-config-interface` | `config` | `PathConfig` | `JsPathConfig` | `matched` |
| `config-yaml-file-enum` | `config` | `YamlSource` | `JsYamlFile` | `matched` |
| `config-get-all-yaml-files` | `config` | `YamlSource` | `getAllYamlFiles` | `matched` |
| `config-get-yaml-file-description` | `config` | `YamlSource` | `getYamlFileDescription` | `matched` |
| `config-default-cache-ttl-const` | `config` | `config` | `DEFAULT_CACHE_TTL` | `matched` |
| `config-batch-cache-ttl-const` | `config` | `config` | `BATCH_CACHE_TTL` | `matched` |
| `config-max-cache-ttl-const` | `config` | `config` | `MAX_CACHE_TTL` | `matched` |
| `config-get-default-cache-ttl` | `config` | `config` | `getDefaultCacheTtl` | `matched` |
| `config-get-batch-cache-ttl` | `config` | `config` | `getBatchCacheTtl` | `matched` |
| `config-get-max-cache-ttl` | `config` | `config` | `getMaxCacheTtl` | `matched` |
| `config-generate-local-yaml` | `config` | `config` | `generateLocalYaml` | `matched` |
| `config-settings-cache-stats-interface` | `config` | `config` | `SettingsCacheStats` | `matched` |
| `config-load-settings-sync` | `config` | `config` | `loadSettingsSync` | `matched` |
| `config-load-settings-async` | `config` | `config` | `loadSettingsAsync` | `matched` |
| `config-get-cached` | `config` | `config` | `getCached` | `matched` |
| `config-is-cached` | `config` | `config` | `isCached` | `matched` |
| `config-invalidate-settings` | `config` | `config` | `invalidateSettings` | `matched` |
| `config-clear-settings-cache` | `config` | `config` | `clearSettingsCache` | `matched` |
| `config-settings-cache-size` | `config` | `config` | `settingsCacheSize` | `matched` |
| `config-settings-cache-keys` | `config` | `config` | `settingsCacheKeys` | `matched` |
| `config-get-settings-cache-stats` | `config` | `config` | `getSettingsCacheStats` | `matched` |
| `config-reset-settings-cache-stats` | `config` | `config` | `resetSettingsCacheStats` | `matched` |
| `config-validate-settings-path` | `config` | `PathConfig` | `validateSettingsPath` | `matched` |
| `config-validate-settings-paths` | `config` | `PathConfig` | `validateSettingsPaths` | `matched` |
| `config-yaml-document-class` | `config` | `yamldata` | `YamlDocument` | `matched` |
| `config-yaml-parse` | `config` | `yamldata` | `yamlParse` | `matched` |
| `config-yaml-stringify` | `config` | `yamldata` | `yamlStringify` | `matched` |
| `config-yaml-load-file` | `config` | `yamldata` | `yamlLoadFile` | `matched` |
| `config-yaml-get-value` | `config` | `yamldata` | `yamlGetValue` | `matched` |
| `config-yaml-get-string-value` | `config` | `yamldata` | `yamlGetStringValue` | `matched` |
| `config-yaml-get-vec-value` | `config` | `yamldata` | `yamlGetVecValue` | `matched` |
| `config-yaml-get-hashmap-value` | `config` | `yamldata` | `yamlGetHashmapValue` | `matched` |
| `config-yaml-save-file` | `config` | `yamldata` | `yamlSaveFile` | `matched` |
| `config-yaml-set-setting` | `config` | `yamldata` | `yamlSetSetting` | `matched` |
| `config-yaml-get-settings-batch` | `config` | `yamldata` | `yamlGetSettingsBatch` | `matched` |
| `config-yaml-set-settings-batch` | `config` | `yamldata` | `yamlSetSettingsBatch` | `matched` |
| `config-yaml-get-indexmap-value` | `config` | `yamldata` | `yamlGetIndexmapValue` | `matched` |
| `config-yaml-get-hashmap-vec-value` | `config` | `yamldata` | `yamlGetHashmapVecValue` | `matched` |
| `config-yaml-clear-cache` | `config` | `clear_global_yaml_cache` | `yamlClearCache` | `matched` |
| `config-yaml-get-cache-stats` | `config` | `clear_global_yaml_cache` | `yamlGetCacheStats` | `matched` |
| `version-registry-get-by-id` | `version_registry` | `VersionInfo` | `getVersionById` | `matched` |
| `version-registry-get-by-version` | `version_registry` | `VersionInfo` | `getVersionByVersionString` | `matched` |
| `version-registry-get-by-short-name` | `version_registry` | `VersionInfo` | `getVersionByShortName` | `matched` |
| `version-registry-get-all` | `version_registry` | `VersionRegistry` | `getAllVersions` | `matched` |
| `version-registry-get-all-for-game` | `version_registry` | `VersionRegistry` | `getAllVersionsForGame` | `matched` |
| `version-registry-get-correct-versions` | `version_registry` | `VersionRegistry` | `getCorrectVersions` | `matched` |
| `version-registry-get-wrong-versions` | `version_registry` | `VersionRegistry` | `getWrongVersions` | `matched` |
| `version-registry-match-version` | `version_registry` | `MatchResult` | `matchVersion` | `matched` |
| `version-registry-address-lib-filename` | `version_registry` | `VersionRegistry` | `getAddressLibraryFilename` | `matched` |
| `version-registry-crashgen-versions` | `version_registry` | `CrashgenConfig` | `getCrashgenVersions` | `matched` |
| `version-registry-crashgen-version-strings` | `version_registry` | `CrashgenConfig` | `getCrashgenVersionStrings` | `matched` |
| `version-registry-crashgen-for-version` | `version_registry` | `CrashgenConfig` | `getCrashgenForVersion` | `matched` |
| `version-registry-is-compatible` | `version_registry` | `GameVersion` | `isVersionCompatible` | `matched` |
| `version-registry-parse-version` | `version_registry` | `GameVersion` | `parseGameVersion` | `matched` |
| `version-registry-version-distance` | `version_registry` | `GameVersion` | `gameVersionDistance` | `matched` |
| `version-registry-promote-fallout4-version-info` | `version_registry` | `VersionInfo` | `Fallout4VersionInfo` | `matched` |
| `version-registry-promote-js-address-lib-info` | `version_registry` | `AddressLibFormat` | `JsAddressLibInfo` | `matched` |
| `version-registry-promote-js-address-library-config` | `version_registry` | `AddressLibraryConfig` | `JsAddressLibraryConfig` | `matched` |
| `version-registry-promote-js-crashgen-check-result` | `version_registry` | `MatchResult` | `JsCrashgenCheckResult` | `matched` |
| `version-registry-promote-js-crashgen-checker` | `version_registry` | `VersionMatcher` | `JsCrashgenChecker` | `matched` |
| `version-registry-promote-js-crashgen-config` | `version_registry` | `CrashgenConfig` | `JsCrashgenConfig` | `matched` |
| `version-registry-promote-js-crashgen-report` | `version_registry` | `Result` | `JsCrashgenReport` | `matched` |
| `version-registry-promote-js-crashgen-version-info` | `version_registry` | `CrashgenConfig` | `JsCrashgenVersionInfo` | `matched` |
| `version-registry-promote-js-fallout4-version` | `version_registry` | `GameVersion` | `JsFallout4Version` | `matched` |
| `version-registry-promote-js-game-version` | `version_registry` | `GameVersion` | `JsGameVersion` | `matched` |
| `version-registry-promote-js-unknown-version-handling` | `version_registry` | `UnknownVersionHandling` | `JsUnknownVersionHandling` | `matched` |
| `version-registry-promote-js-version-info` | `version_registry` | `XseConfig` | `JsVersionInfo` | `matched` |
| `version-registry-promote-js-version-registry-snapshot` | `version_registry` | `VersionMatcher` | `JsVersionRegistrySnapshot` | `matched` |
| `version-registry-promote-xse-version` | `version_registry` | `XseConfig` | `XseVersion` | `matched` |
| `version-registry-promote-check-crashgen-config` | `version_registry` | `Result` | `checkCrashgenConfig` | `matched` |
| `version-registry-promote-check-crashgen-full` | `version_registry` | `Result` | `checkCrashgenFull` | `matched` |
| `version-registry-promote-compare-versions` | `version_registry` | `GameVersion` | `compareVersions` | `matched` |
| `version-registry-promote-detect-xse-version` | `version_registry` | `XseConfig` | `detectXseVersion` | `matched` |
| `version-registry-promote-extract-all-versions` | `version_registry` | `GameVersion` | `extractAllVersions` | `matched` |
| `version-registry-promote-extract-version-from-filename` | `version_registry` | `GameVersion` | `extractVersionFromFilename` | `matched` |
| `version-registry-promote-extract-version-from-log` | `version_registry` | `GameVersion` | `extractVersionFromLog` | `matched` |
| `version-registry-promote-format-version` | `version_registry` | `GameVersion` | `formatVersion` | `matched` |
| `version-registry-promote-get-address-lib-info` | `version_registry` | `CompatibleRange` | `getAddressLibInfo` | `matched` |
| `version-registry-promote-get-all-fallout4-versions` | `version_registry` | `VersionRegistry` | `getAllFallout4Versions` | `matched` |
| `version-registry-promote-get-classic-version` | `version_registry` | `VersionRegistry` | `getClassicVersion` | `matched` |
| `version-registry-promote-get-fallout4-version-info` | `version_registry` | `VersionInfo` | `getFallout4VersionInfo` | `matched` |
| `version-registry-promote-get-script-hashes-for-version` | `version_registry` | `XseConfig` | `getScriptHashesForVersion` | `matched` |
| `version-registry-promote-get-unknown-version-default` | `version_registry` | `UnknownVersionStrategy` | `getUnknownVersionDefault` | `matched` |
| `version-registry-promote-get-unknown-version-handling` | `version_registry` | `LogLevel` | `getUnknownVersionHandling` | `matched` |
| `version-registry-promote-get-version` | `version_registry` | `VersionRegistry` | `getVersion` | `matched` |
| `version-registry-promote-get-version-registry` | `version_registry` | `get_version_registry` | `getVersionRegistry` | `matched` |
| `version-registry-promote-is-known-fallout4-version` | `version_registry` | `GameVersion` | `isKnownFallout4Version` | `matched` |
| `version-registry-promote-parse-version` | `version_registry` | `VersionRegistryError` | `parseVersion` | `matched` |
| `version-registry-promote-registry-get-game-version` | `version_registry` | `VersionRegistry` | `registryGetGameVersion` | `matched` |
| `version-registry-promote-resolve-effective-game-version` | `version_registry` | `MatchConfidence` | `resolveEffectiveGameVersion` | `matched` |
| `version-registry-promote-try-parse-version` | `version_registry` | `GameVersion` | `tryParseVersion` | `matched` |
| `aux-phase4a-backup-manager` | `aux` | `BackupManager` | `BackupManager` | `matched` |
| `aux-phase4a-docs-path-finder` | `aux` | `DocsPathFinder` | `DocsPathFinder` | `matched` |
| `aux-phase4a-documents-checker` | `aux` | `DocumentsChecker` | `DocumentsChecker` | `matched` |
| `aux-phase4a-game-path-finder` | `aux` | `GamePathFinder` | `GamePathFinder` | `matched` |
| `aux-phase4a-js-backup-info` | `aux` | `BackupInfo` | `JsBackupInfo` | `matched` |
| `aux-phase4a-js-backup-manager` | `aux` | `BackupManager` | `JsBackupManager` | `matched` |
| `aux-phase4a-js-file-generator` | `aux` | `FileGenerator` | `JsFileGenerator` | `matched` |
| `aux-phase4a-js-file-i-o` | `aux` | `FileIOCore` | `JsFileIO` | `matched` |
| `aux-phase4a-js-file-operation-result` | `aux` | `FileOperationResult` | `JsFileOperationResult` | `matched` |
| `aux-phase4a-js-game-files-manager` | `aux` | `GameFilesManager` | `JsGameFilesManager` | `matched` |
| `aux-phase4a-js-message` | `aux` | `Message` | `JsMessage` | `matched` |
| `aux-phase4a-js-message-target` | `aux` | `MessageTarget` | `JsMessageTarget` | `matched` |
| `aux-phase4a-js-message-type` | `aux` | `MessageType` | `JsMessageType` | `matched` |
| `aux-phase4a-metrics-summary-result` | `aux` | `MetricsSummary` | `MetricsSummaryResult` | `matched` |
| `aux-phase4a-runtime-info` | `aux` | `get_runtime` | `RuntimeInfo` | `matched` |
| `aux-phase4a-timing-stats` | `aux` | `MetricsSummary` | `TimingStats` | `matched` |
| `aux-phase4a-calculate-file-similarity` | `aux` | `calculate_similarity` | `calculateFileSimilarity` | `matched` |
| `aux-phase4a-check-read-permissions` | `aux` | `check_read_permissions` | `checkReadPermissions` | `matched` |
| `aux-phase4a-check-write-permissions` | `aux` | `check_write_permissions` | `checkWritePermissions` | `matched` |
| `aux-phase4a-clear-all-metrics` | `aux` | `clear_metrics` | `clearAllMetrics` | `matched` |
| `aux-phase4a-create-message` | `aux` | `Message` | `createMessage` | `matched` |
| `aux-phase4a-detect-encoding` | `aux` | `EncodingDetector` | `detectEncoding` | `matched` |
| `aux-phase4a-format-message` | `aux` | `format_log_message` | `formatMessage` | `matched` |
| `aux-phase4a-generate-ignore-file` | `aux` | `generate_ignore_file` | `generateIgnoreFile` | `matched` |
| `aux-phase4a-get-metrics-summary` | `aux` | `get_summary` | `getMetricsSummary` | `matched` |
| `aux-phase4a-get-runtime-info` | `aux` | `get_runtime` | `getRuntimeInfo` | `matched` |
| `aux-phase4a-get-system-documents-path` | `aux` | `get_system_documents_path` | `getSystemDocumentsPath` | `matched` |
| `aux-phase4a-hash-file` | `aux` | `FileHasher` | `hashFile` | `matched` |
| `aux-phase4a-hash-files-parallel` | `aux` | `FileHasher` | `hashFilesParallel` | `matched` |
| `aux-phase4a-intern-string` | `aux` | `strings_core` | `internString` | `matched` |
| `aux-phase4a-is-restricted-path` | `aux` | `is_restricted_path` | `isRestrictedPath` | `matched` |
| `aux-phase4a-is-runtime-available` | `aux` | `get_runtime` | `isRuntimeAvailable` | `matched` |
| `aux-phase4a-is-valid-executable-path` | `aux` | `is_valid_path` | `isValidExecutablePath` | `matched` |
| `aux-phase4a-is-valid-path` | `aux` | `is_valid_path` | `isValidPath` | `matched` |
| `aux-phase4a-join-paths` | `aux` | `path_core` | `joinPaths` | `matched` |
| `aux-phase4a-load-batch-async` | `aux` | `load_batch_async` | `loadBatchAsync` | `matched` |
| `aux-phase4a-load-batch-sync` | `aux` | `load_batch_sync` | `loadBatchSync` | `matched` |
| `aux-phase4a-normalize-path` | `aux` | `path_core` | `normalizePath` | `matched` |
| `aux-phase4a-normalize-string` | `aux` | `strings_core` | `normalizeString` | `matched` |
| `aux-phase4a-parse-steam-library` | `aux` | `parse_steam_library` | `parseSteamLibrary` | `matched` |
| `aux-phase4a-process-string-batch` | `aux` | `strings_core` | `processStringBatch` | `matched` |
| `aux-phase4a-query-game-registry` | `aux` | `query_game_registry` | `queryGameRegistry` | `matched` |
| `aux-phase4a-record-timing-metric` | `aux` | `record_timing` | `recordTimingMetric` | `matched` |
| `aux-phase4a-registry-clear` | `aux` | `clear_all` | `registryClear` | `matched` |
| `aux-phase4a-registry-get` | `aux` | `get` | `registryGet` | `matched` |
| `aux-phase4a-registry-get-game` | `aux` | `get_game` | `registryGetGame` | `matched` |
| `aux-phase4a-registry-remove` | `aux` | `unregister` | `registryRemove` | `matched` |
| `aux-phase4a-registry-set` | `aux` | `register` | `registrySet` | `matched` |
| `aux-phase4a-registry-set-game` | `aux` | `set_game` | `registrySetGame` | `matched` |
| `aux-phase4a-remove-readonly` | `aux` | `remove_readonly` | `removeReadonly` | `matched` |
| `aux-phase4a-strip-emoji-text` | `aux` | `strip_emoji` | `stripEmojiText` | `matched` |
| `aux-phase4a-validate-custom-scan-path` | `aux` | `validate_custom_scan_path` | `validateCustomScanPath` | `matched` |
| `aux-phase4a-validate-path-with-permissions` | `aux` | `validate_path_with_permissions` | `validatePathWithPermissions` | `matched` |
| `aux-phase4a-validate-paths-batch` | `aux` | `path_core` | `validatePathsBatch` | `matched` |
| `aux-phase4a-validate-required-files` | `aux` | `validate_required_files` | `validateRequiredFiles` | `matched` |
| `aux-phase4b-github-client` | `aux` | `path_core` | `GithubClient` | `matched` |
| `aux-phase4b-js-ba2-issues` | `aux` | `path_core` | `JsBa2Issues` | `matched` |
| `aux-phase4b-js-ba2-scan-result` | `aux` | `path_core` | `JsBa2ScanResult` | `matched` |
| `aux-phase4b-js-ba2-scanner` | `aux` | `path_core` | `JsBa2Scanner` | `matched` |
| `aux-phase4b-js-batch-entry` | `aux` | `path_core` | `JsBatchEntry` | `matched` |
| `aux-phase4b-js-check-result` | `aux` | `path_core` | `JsCheckResult` | `matched` |
| `aux-phase4b-js-check-type` | `aux` | `path_core` | `JsCheckType` | `matched` |
| `aux-phase4b-js-database-pool` | `aux` | `path_core` | `JsDatabasePool` | `matched` |
| `aux-phase4b-js-duplicate-group` | `aux` | `path_core` | `JsDuplicateGroup` | `matched` |
| `aux-phase4b-js-enb-checker` | `aux` | `path_core` | `JsEnbChecker` | `matched` |
| `aux-phase4b-js-enb-result` | `aux` | `path_core` | `JsEnbResult` | `matched` |
| `aux-phase4b-js-enb-validation-result` | `aux` | `path_core` | `JsEnbValidationResult` | `matched` |
| `aux-phase4b-js-game-integrity-checker` | `aux` | `path_core` | `JsGameIntegrityChecker` | `matched` |
| `aux-phase4b-js-game-scan-result` | `aux` | `path_core` | `JsGameScanResult` | `matched` |
| `aux-phase4b-js-github-asset` | `aux` | `path_core` | `JsGithubAsset` | `matched` |
| `aux-phase4b-js-github-release` | `aux` | `path_core` | `JsGithubRelease` | `matched` |
| `aux-phase4b-js-ini-validator` | `aux` | `path_core` | `JsIniValidator` | `matched` |
| `aux-phase4b-js-integrity-check-result` | `aux` | `path_core` | `JsIntegrityCheckResult` | `matched` |
| `aux-phase4b-js-issue-severity` | `aux` | `path_core` | `JsIssueSeverity` | `matched` |
| `aux-phase4b-js-mod-duplicate-entry` | `aux` | `path_core` | `JsModDuplicateEntry` | `matched` |
| `aux-phase4b-js-mod-ini-scan-result` | `aux` | `path_core` | `JsModIniScanResult` | `matched` |
| `aux-phase4b-js-mod-scan-result` | `aux` | `path_core` | `JsModScanResult` | `matched` |
| `aux-phase4b-js-mod-site` | `aux` | `path_core` | `JsModSite` | `matched` |
| `aux-phase4b-js-pool-statistics` | `aux` | `path_core` | `JsPoolStatistics` | `matched` |
| `aux-phase4b-js-toml-issue-severity` | `aux` | `path_core` | `JsTomlIssueSeverity` | `matched` |
| `aux-phase4b-js-unpacked-issues` | `aux` | `path_core` | `JsUnpackedIssues` | `matched` |
| `aux-phase4b-js-unpacked-scanner` | `aux` | `path_core` | `JsUnpackedScanner` | `matched` |
| `aux-phase4b-js-update-check-result` | `aux` | `path_core` | `JsUpdateCheckResult` | `matched` |
| `aux-phase4b-js-validation-result` | `aux` | `path_core` | `JsValidationResult` | `matched` |
| `aux-phase4b-js-vsync-entry` | `aux` | `path_core` | `JsVsyncEntry` | `matched` |
| `aux-phase4b-js-wrye-bash-parser` | `aux` | `path_core` | `JsWryeBashParser` | `matched` |
| `aux-phase4b-js-wrye-issue` | `aux` | `path_core` | `JsWryeIssue` | `matched` |
| `aux-phase4b-js-xse-checker` | `aux` | `path_core` | `JsXseChecker` | `matched` |
| `aux-phase4b-js-xse-info` | `aux` | `path_core` | `JsXseInfo` | `matched` |
| `aux-phase4b-js-xse-type` | `aux` | `path_core` | `JsXseType` | `matched` |
| `aux-phase4b-query-param` | `aux` | `path_core` | `QueryParam` | `matched` |
| `aux-phase4b-resource-count` | `aux` | `path_core` | `ResourceCount` | `matched` |
| `aux-phase4b-resource-info` | `aux` | `path_core` | `ResourceInfo` | `matched` |
| `aux-phase4b-build-url-with-query` | `aux` | `path_core` | `buildUrlWithQuery` | `matched` |
| `aux-phase4b-check-enb` | `aux` | `path_core` | `checkEnb` | `matched` |
| `aux-phase4b-check-for-updates` | `aux` | `path_core` | `checkForUpdates` | `matched` |
| `aux-phase4b-count-resources-by-type` | `aux` | `path_core` | `countResourcesByType` | `matched` |
| `aux-phase4b-create-resource-info` | `aux` | `path_core` | `createResourceInfo` | `matched` |
| `aux-phase4b-create-resource-info-with-size` | `aux` | `path_core` | `createResourceInfoWithSize` | `matched` |
| `aux-phase4b-detect-resource-type` | `aux` | `path_core` | `detectResourceType` | `matched` |
| `aux-phase4b-enumerate-resources` | `aux` | `path_core` | `enumerateResources` | `matched` |
| `aux-phase4b-extract-domain` | `aux` | `path_core` | `extractDomain` | `matched` |
| `aux-phase4b-get-latest-release` | `aux` | `path_core` | `getLatestRelease` | `matched` |
| `aux-phase4b-get-mod-site-game-url` | `aux` | `path_core` | `getModSiteGameUrl` | `matched` |
| `aux-phase4b-get-mod-site-name` | `aux` | `path_core` | `getModSiteName` | `matched` |
| `aux-phase4b-get-mod-site-url` | `aux` | `path_core` | `getModSiteUrl` | `matched` |
| `aux-phase4b-get-resource-extensions` | `aux` | `path_core` | `getResourceExtensions` | `matched` |
| `aux-phase4b-get-user-agent` | `aux` | `path_core` | `getUserAgent` | `matched` |
| `aux-phase4b-get-user-agent-prefix` | `aux` | `path_core` | `getUserAgentPrefix` | `matched` |
| `aux-phase4b-get-user-agent-with-suffix` | `aux` | `path_core` | `getUserAgentWithSuffix` | `matched` |
| `aux-phase4b-get-xse-info` | `aux` | `path_core` | `getXseInfo` | `matched` |
| `aux-phase4b-has-update` | `aux` | `path_core` | `hasUpdate` | `matched` |
| `aux-phase4b-is-supported-resource` | `aux` | `path_core` | `isSupportedResource` | `matched` |
| `aux-phase4b-is-valid-url` | `aux` | `path_core` | `isValidUrl` | `matched` |
| `aux-phase4b-is-xse-installed` | `aux` | `path_core` | `isXseInstalled` | `matched` |
| `aux-phase4b-join-url` | `aux` | `path_core` | `joinUrl` | `matched` |
| `aux-phase4b-parse-resource-type` | `aux` | `path_core` | `parseResourceType` | `matched` |
| `aux-phase4b-parse-xse-type` | `aux` | `path_core` | `parseXseType` | `matched` |
| `aux-phase4b-run-game-checks` | `aux` | `path_core` | `runGameChecks` | `matched` |
| `aux-phase4b-run-mod-scans` | `aux` | `path_core` | `runModScans` | `matched` |
| `aux-phase4b-scan-all-ba2-archives` | `aux` | `path_core` | `scanAllBa2Archives` | `matched` |
| `aux-phase4b-scan-mod-inis` | `aux` | `path_core` | `scanModInis` | `matched` |
| `aux-phase4b-scan-unpacked-files` | `aux` | `path_core` | `scanUnpackedFiles` | `matched` |
| `aux-phase4b-validate-resource` | `aux` | `path_core` | `validateResource` | `matched` |
| `aux-phase4b-validate-url` | `aux` | `path_core` | `validateUrl` | `matched` |
| `aux-phase4b-xse-dll-prefix` | `aux` | `path_core` | `xseDllPrefix` | `matched` |
| `aux-phase4b-xse-loader-name` | `aux` | `path_core` | `xseLoaderName` | `matched` |
| `aux-phase4b-xse-type-for-game` | `aux` | `path_core` | `xseTypeForGame` | `matched` |
| `aux-phase4b-xse-type-name` | `aux` | `path_core` | `xseTypeName` | `matched` |
| `aux-phase4c-crash-autoscan-pattern` | `aux` | `FileIOCore` | `CRASH_AUTOSCAN_PATTERN` | `matched` |
| `version-registry-phase4c-js-compatible-range` | `version_registry` | `CompatibleRange` | `JsCompatibleRange` | `matched` |
| `aux-phase4c-js-dds-analyzer-alias` | `aux` | `FileIOCore` | `JsDDSAnalyzer` | `matched` |
| `aux-phase4c-js-dds-analyzer-class` | `aux` | `FileIOCore` | `JsDdsAnalyzer` | `matched` |
| `aux-phase4c-js-dds-batch-result` | `aux` | `FileIOCore` | `JsDdsBatchResult` | `matched` |
| `aux-phase4c-js-dds-issue` | `aux` | `FileIOCore` | `JsDdsIssue` | `matched` |
| `aux-phase4c-js-game-id` | `aux` | `path_core` | `JsGameId` | `matched` |
| `aux-phase4c-js-ini-check-result` | `aux` | `path_core` | `JsIniCheckResult` | `matched` |
| `version-registry-phase4c-js-match-result` | `version_registry` | `MatchResult` | `JsMatchResult` | `matched` |
| `aux-phase4c-calculate-text-similarity` | `aux` | `calculate_similarity` | `calculateTextSimilarity` | `matched` |
| `aux-phase4c-check-drive-exists` | `aux` | `path_core` | `checkDriveExists` | `matched` |
| `version-registry-phase4c-get-all-exe-hashes` | `version_registry` | `get_version_registry` | `getAllExeHashes` | `matched` |
| `aux-phase4c-get-all-game-ids` | `aux` | `path_core` | `getAllGameIds` | `matched` |
| `version-registry-phase4c-get-all-script-hashes` | `version_registry` | `get_version_registry` | `getAllScriptHashes` | `matched` |
| `aux-phase4c-get-game-name` | `aux` | `path_core` | `getGameName` | `matched` |
| `scanlog.orchestrator.AnalysisResult@rust` | `scanlog` | `AnalysisResult@rust` | `None` | `matched` |
| `scanlog.settings_validator.CheckId@rust` | `scanlog` | `CheckId@rust` | `None` | `matched` |
| `scanlog.settings_validator.ConfigIssue@rust` | `scanlog` | `ConfigIssue@rust` | `None` | `matched` |
| `scanlog.crashgen_registry.CrashgenEntry@rust` | `scanlog` | `CrashgenEntry@rust` | `None` | `matched` |
| `scanlog.crashgen_registry.CrashgenRegistry@rust` | `scanlog` | `CrashgenRegistry@rust` | `None` | `matched` |
| `scanlog.fcx_handler.FcxModeHandler@rust` | `scanlog` | `FcxModeHandler@rust` | `None` | `matched` |
| `scanlog.fcx_handler.FcxResetError@rust` | `scanlog` | `FcxResetError@rust` | `None` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzer@rust` | `scanlog` | `FormIDAnalyzer@rust` | `None` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzerCore@rust` | `scanlog` | `FormIDAnalyzerCore@rust` | `None` | `matched` |
| `scanlog.gpu_detector.GpuDetector@rust` | `scanlog` | `GpuDetector@rust` | `None` | `matched` |
| `scanlog.gpu_detector.GpuVendor@rust` | `scanlog` | `GpuVendor@rust` | `None` | `matched` |
| `scanlog.papyrus.PapyrusAnalyzer@rust` | `scanlog` | `PapyrusAnalyzer@rust` | `None` | `matched` |
| `scanlog.papyrus.PapyrusError@rust` | `scanlog` | `PapyrusError@rust` | `None` | `matched` |
| `scanlog.plugin_analyzer.PluginAnalyzer@rust` | `scanlog` | `PluginAnalyzer@rust` | `None` | `matched` |
| `scanlog.record_scanner.RecordScanner@rust` | `scanlog` | `RecordScanner@rust` | `None` | `matched` |
| `scanlog.report.ReportComposer@rust` | `scanlog` | `ReportComposer@rust` | `None` | `matched` |
| `scanlog.report.ReportFragment@rust` | `scanlog` | `ReportFragment@rust` | `None` | `matched` |
| `scanlog.report.ReportGenerator@rust` | `scanlog` | `ReportGenerator@rust` | `None` | `matched` |
| `scanlog.formid_analyzer.RustFormIDAnalyzer@rust` | `scanlog` | `RustFormIDAnalyzer@rust` | `None` | `matched` |
| `scanlog.error.ScanLogError@rust` | `scanlog` | `ScanLogError@rust` | `None` | `matched` |
| `scanlog.orchestrator.ScanProgressPhase@rust` | `scanlog` | `ScanProgressPhase@rust` | `None` | `matched` |
| `scanlog.settings_validator.SettingsValidator@rust` | `scanlog` | `SettingsValidator@rust` | `None` | `matched` |
| `scanlog.parser.StreamingIteratorParser@rust` | `scanlog` | `StreamingIteratorParser@rust` | `None` | `matched` |
| `scanlog.parser.StreamingLogParser@rust` | `scanlog` | `StreamingLogParser@rust` | `None` | `matched` |
| `scanlog.parser.StringPool@rust` | `scanlog` | `StringPool@rust` | `None` | `matched` |
| `scanlog.suspect_scanner.SuspectScanner@rust` | `scanlog` | `SuspectScanner@rust` | `None` | `matched` |
| `scanlog.plugin_analyzer.contains_plugin@rust` | `scanlog` | `contains_plugin@rust` | `None` | `matched` |
| `scanlog.record_scanner.contains_record@rust` | `scanlog` | `contains_record@rust` | `None` | `matched` |
| `scanlog.crashgen_registry.crashgen_registry@rust` | `scanlog` | `crashgen_registry@rust` | `None` | `matched` |
| `scanlog.version.crashgen_version_gen@rust` | `scanlog` | `crashgen_version_gen@rust` | `None` | `matched` |
| `scanlog.mod_detector.detect_mods_batch@rust` | `scanlog` | `detect_mods_batch@rust` | `None` | `matched` |
| `scanlog.mod_detector.detect_mods_double@rust` | `scanlog` | `detect_mods_double@rust` | `None` | `matched` |
| `scanlog.mod_detector.detect_mods_important@rust` | `scanlog` | `detect_mods_important@rust` | `None` | `matched` |
| `scanlog.mod_detector.detect_mods_single@rust` | `scanlog` | `detect_mods_single@rust` | `None` | `matched` |
| `scanlog.plugin_analyzer.detect_plugins_batch@rust` | `scanlog` | `detect_plugins_batch@rust` | `None` | `matched` |
| `scanlog.error.error@rust` | `scanlog` | `error@rust` | `None` | `matched` |
| `scanlog.formid.extract_formids_batch@rust` | `scanlog` | `extract_formids_batch@rust` | `None` | `matched` |
| `scanlog.fcx_handler.fcx_handler@rust` | `scanlog` | `fcx_handler@rust` | `None` | `matched` |
| `scanlog.formid.formid@rust` | `scanlog` | `formid@rust` | `None` | `matched` |
| `scanlog.formid_analyzer.formid_analyzer@rust` | `scanlog` | `formid_analyzer@rust` | `None` | `matched` |
| `scanlog.gpu_detector.gpu_detector@rust` | `scanlog` | `gpu_detector@rust` | `None` | `matched` |
| `scanlog.formid.is_valid_formid@rust` | `scanlog` | `is_valid_formid@rust` | `None` | `matched` |
| `scanlog.mod_detector.mod_detector@rust` | `scanlog` | `mod_detector@rust` | `None` | `matched` |
| `scanlog.orchestrator.orchestrator@rust` | `scanlog` | `orchestrator@rust` | `None` | `matched` |
| `scanlog.papyrus.papyrus@rust` | `scanlog` | `papyrus@rust` | `None` | `matched` |
| `scanlog.parser.parser@rust` | `scanlog` | `parser@rust` | `None` | `matched` |
| `scanlog.patterns.patterns@rust` | `scanlog` | `patterns@rust` | `None` | `matched` |
| `scanlog.plugin_analyzer.plugin_analyzer@rust` | `scanlog` | `plugin_analyzer@rust` | `None` | `matched` |
| `scanlog.record_scanner.record_scanner@rust` | `scanlog` | `record_scanner@rust` | `None` | `matched` |
| `scanlog.report.report@rust` | `scanlog` | `report@rust` | `None` | `matched` |
| `scanlog.orchestrator.resolve_batch_concurrency@rust` | `scanlog` | `resolve_batch_concurrency@rust` | `None` | `matched` |
| `scanlog.record_scanner.scan_records_batch@rust` | `scanlog` | `scan_records_batch@rust` | `None` | `matched` |
| `scanlog.segment_key.segment_key@rust` | `scanlog` | `segment_key@rust` | `None` | `matched` |
| `scanlog.settings_validator.settings_validator@rust` | `scanlog` | `settings_validator@rust` | `None` | `matched` |
| `scanlog.suspect_scanner.suspect_scanner@rust` | `scanlog` | `suspect_scanner@rust` | `None` | `matched` |
| `scanlog.formid_analyzer.validate_formids_batch@rust` | `scanlog` | `validate_formids_batch@rust` | `None` | `matched` |
| `scanlog.version.version@rust` | `scanlog` | `version@rust` | `None` | `matched` |
| `scanlog.patterns.CRASH_LOG_PATTERN` | `scanlog` | `CRASH_LOG_PATTERN` | `CRASH_LOG_PATTERN` | `matched` |
| `scanlog.orchestrator.JsAnalysisBuildOptions` | `scanlog` | `build_analysis_config_from_yaml` | `JsAnalysisBuildOptions` | `matched` |
| `scanlog.orchestrator.JsAnalysisResult` | `scanlog` | `AnalysisResult` | `JsAnalysisResult` | `matched` |
| `scanlog.gpu_detector.JsGpuInfo` | `scanlog` | `GpuInfo` | `JsGpuInfo` | `matched` |
| `scanlog.parser.JsLogErrorEntry` | `scanlog` | `LogErrorEntry` | `JsLogErrorEntry` | `matched` |
| `scanlog.parser.JsLogSegments` | `scanlog` | `LogParser` | `JsLogSegments` | `matched` |
| `scanlog.papyrus.JsPapyrusStats` | `scanlog` | `PapyrusStats` | `JsPapyrusStats` | `matched` |
| `scanlog.settings_validator.checkXsePlugins` | `scanlog` | `XseChecker` | `checkXsePlugins` | `matched` |
| `scanlog.parser.parseXseLog` | `scanlog` | `parse_xse_log` | `parseXseLog` | `matched` |

## Gap Counts By Owner/Tier

| Owner Module | Tier 1 Gaps | Tier 2 Gaps |
|---|---:|---:|
| `aux` | 0 | 16 |
| `config` | 0 | 35 |
| `constants` | 0 | 30 |
| `crashgen_settings` | 0 | 22 |
| `database` | 0 | 17 |
| `file_io` | 0 | 24 |
| `message` | 0 | 9 |
| `path` | 0 | 25 |
| `perf` | 0 | 2 |
| `registry` | 0 | 14 |
| `scangame` | 0 | 78 |
| `scanlog` | 0 | 6 |
| `settings` | 0 | 23 |
| `shared` | 0 | 15 |
| `update` | 0 | 6 |
| `version` | 0 | 16 |
| `version_registry` | 0 | 5 |
| `web` | 0 | 15 |
| `xse` | 0 | 17 |
| `yaml` | 0 | 23 |

Detailed, per-gap annotations (including `tier`, `owner_module`, and `squad`) are in `parity_diff_report.json`.
