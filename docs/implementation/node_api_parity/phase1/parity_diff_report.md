# Rust↔Node Parity Diff Baseline (Phase 1)

- Generated: `2026-02-25T11:51:14.966043+00:00`
- Tier-1 contract rows: **35**
- Tier-1 matched: **35**
- Tier-1 missing Rust: **0**
- Tier-1 missing Node: **0**
- Tier-1 signature mismatch: **0**
- Total gaps (Tier-1 + Tier-2): **315**

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
| `config-yamldata-class` | `config` | `YamlDataCore` | `YamlData` | `matched` |
| `config-create-yamldata-content` | `config` | `YamlDataCore` | `createYamlDataFromContent` | `matched` |
| `config-classic-config-class` | `config` | `ClassicConfig` | `ClassicConfigJs` | `matched` |
| `config-create-default-config` | `config` | `ClassicConfig` | `createDefaultConfig` | `matched` |
| `config-clear-yaml-cache` | `config` | `clear_global_yaml_cache` | `clearYamlCache` | `matched` |
| `config-yaml-source-enum` | `config` | `YamlSource` | `JsYamlSource` | `matched` |
| `config-yaml-source-path` | `config` | `YamlSource` | `getYamlSourcePath` | `matched` |
| `config-yaml-source-display-name` | `config` | `YamlSource` | `getYamlSourceDisplayName` | `matched` |
| `config-yaml-source-display-name-with-game` | `config` | `YamlSource` | `getYamlSourceDisplayNameWithGame` | `matched` |
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

## Gap Counts By Owner/Tier

| Owner Module | Tier 1 Gaps | Tier 2 Gaps |
|---|---:|---:|
| `scanlog` | 0 | 72 |
| `config` | 0 | 58 |
| `version_registry` | 0 | 43 |
| `aux` | 0 | 142 |

Detailed, per-gap annotations (including `tier`, `owner_module`, and `squad`) are in `parity_diff_report.json`.
