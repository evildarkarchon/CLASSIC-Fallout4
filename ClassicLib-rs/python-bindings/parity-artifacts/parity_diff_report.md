# Rust<->Python Parity Diff Baseline

- Generated: `2026-03-27T06:53:01.797446+00:00`
- Tier-1 contract rows: **59**
- Tier-1 matched: **59**
- Tier-1 missing Rust: **0**
- Tier-1 missing Python: **0**
- Tier-1 signature mismatch: **0**
- Total gaps (Tier-1 + Tier-2): **290**

## Tier-1 Contract Evaluation

| ID | Owner Module | Rust Symbol | Python Export | Status |
|---|---|---|---|---|
| `config-yamldata-class` | `config` | `YamlDataCore` | `classic_config.YamlData` | `matched` |
| `config-yamldata-from-content` | `config` | `YamlDataCore` | `classic_config.YamlData.from_yaml_content` | `matched` |
| `config-clear-yaml-cache` | `config` | `clear_global_yaml_cache` | `classic_config.clear_yaml_cache` | `matched` |
| `config-classic-config-class` | `config` | `ClassicConfig` | `classic_config.ClassicConfig` | `matched` |
| `config-classic-config-load-from-yaml` | `config` | `ClassicConfig` | `classic_config.ClassicConfig.load_from_yaml` | `matched` |
| `config-classic-config-load-or-default` | `config` | `ClassicConfig` | `classic_config.ClassicConfig.load_or_default` | `matched` |
| `config-classic-config-save-to-yaml` | `config` | `ClassicConfig` | `classic_config.ClassicConfig.save_to_yaml` | `matched` |
| `config-classic-config-get-config-path` | `config` | `ClassicConfig` | `classic_config.ClassicConfig.get_config_path` | `matched` |
| `config-classic-config-validate-paths` | `config` | `ClassicConfig` | `classic_config.ClassicConfig.validate_paths` | `matched` |
| `config-classic-config-load-local-yaml-paths` | `config` | `ClassicConfig` | `classic_config.ClassicConfig.load_local_yaml_paths` | `matched` |
| `config-path-config-class` | `config` | `PathConfig` | `classic_config.PathConfig` | `matched` |
| `config-yaml-source-class` | `config` | `YamlSource` | `classic_config.YamlSource` | `matched` |
| `config-yaml-source-path` | `config` | `YamlSource` | `classic_config.YamlSource.path` | `matched` |
| `config-yaml-source-display-name` | `config` | `YamlSource` | `classic_config.YamlSource.display_name` | `matched` |
| `config-yaml-source-display-name-with-game` | `config` | `YamlSource` | `classic_config.YamlSource.display_name_with_game` | `matched` |
| `scanlog-logparser-class` | `scanlog` | `LogParser` | `classic_scanlog.LogParser` | `matched` |
| `scanlog-logparser-extract-formids` | `scanlog` | `LogParser` | `classic_scanlog.LogParser.extract_formids` | `matched` |
| `scanlog-logparser-extract-plugins` | `scanlog` | `LogParser` | `classic_scanlog.LogParser.extract_plugins` | `matched` |
| `scanlog-logparser-detect-vr` | `scanlog` | `detect_vr_log` | `classic_scanlog.LogParser.detect_vr_log` | `matched` |
| `scanlog-analysis-config-class` | `scanlog` | `AnalysisConfig` | `classic_scanlog.AnalysisConfig` | `matched` |
| `scanlog-analysis-config-from-yamldata` | `scanlog` | `build_analysis_config_from_yaml` | `classic_scanlog.AnalysisConfig.from_yamldata` | `matched` |
| `scanlog-orchestrator-class` | `scanlog` | `OrchestratorCore` | `classic_scanlog.Orchestrator` | `matched` |
| `scanlog-orchestrator-process-log` | `scanlog` | `OrchestratorCore` | `classic_scanlog.Orchestrator.process_log` | `matched` |
| `scanlog-orchestrator-process-batch` | `scanlog` | `OrchestratorCore` | `classic_scanlog.Orchestrator.process_logs_batch` | `matched` |
| `scanlog-pattern-matcher-class` | `scanlog` | `PatternMatcher` | `classic_scanlog.PatternMatcher` | `matched` |
| `scanlog-pattern-matcher-find-first` | `scanlog` | `PatternMatcher` | `classic_scanlog.PatternMatcher.find_first` | `matched` |
| `scanlog-gpu-detector-class` | `scanlog` | `GpuDetector` | `classic_scanlog.GpuDetector` | `matched` |
| `scanlog-gpu-detector-extract-info` | `scanlog` | `GpuDetector` | `classic_scanlog.GpuDetector.extract_gpu_info` | `matched` |
| `scanlog-papyrus-analyzer-class` | `scanlog` | `PapyrusAnalyzer` | `classic_scanlog.PapyrusAnalyzer` | `matched` |
| `scanlog-papyrus-analyze-full` | `scanlog` | `PapyrusAnalyzer` | `classic_scanlog.PapyrusAnalyzer.analyze_full` | `matched` |
| `scanlog-crashgen-version-class` | `scanlog` | `CrashgenVersion` | `classic_scanlog.CrashgenVersion` | `matched` |
| `scanlog-parse-crashgen-version` | `scanlog` | `CrashgenVersion` | `classic_scanlog.parse_crashgen_version` | `matched` |
| `scanlog-crashgen-version-status` | `scanlog` | `check_crashgen_version_status` | `classic_scanlog.check_crashgen_version_status` | `matched` |
| `scanlog-crashgen-version-status-class` | `scanlog` | `CrashgenVersionStatus` | `classic_scanlog.CrashgenVersionStatus` | `matched` |
| `scanlog-extract-formids-batch` | `scanlog` | `extract_formids_batch` | `classic_scanlog.extract_formids_batch` | `matched` |
| `version-registry-game-version-class` | `version_registry` | `GameVersion` | `classic_version_registry.GameVersion` | `matched` |
| `version-registry-match-confidence-class` | `version_registry` | `MatchConfidence` | `classic_version_registry.MatchConfidence` | `matched` |
| `version-registry-match-result-class` | `version_registry` | `MatchResult` | `classic_version_registry.MatchResult` | `matched` |
| `version-registry-version-info-class` | `version_registry` | `VersionInfo` | `classic_version_registry.VersionInfo` | `matched` |
| `version-registry-unknown-version-handling-class` | `version_registry` | `UnknownVersionHandling` | `classic_version_registry.UnknownVersionHandling` | `matched` |
| `version-registry-unknown-version-get-default` | `version_registry` | `UnknownVersionHandling` | `classic_version_registry.UnknownVersionHandling.get_default` | `matched` |
| `version-registry-class` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry` | `matched` |
| `version-registry-get-singleton` | `version_registry` | `get_version_registry` | `classic_version_registry.get_version_registry` | `matched` |
| `version-registry-match-version-string` | `version_registry` | `VersionRegistry` | `classic_version_registry.match_version_string` | `matched` |
| `version-registry-get-by-id` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_by_id` | `matched` |
| `version-registry-get-by-version` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_by_version` | `matched` |
| `version-registry-get-by-short-name` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_by_short_name` | `matched` |
| `version-registry-get-all` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_all` | `matched` |
| `version-registry-get-all-for-game` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_all_for_game` | `matched` |
| `version-registry-get-correct-versions` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_correct_versions` | `matched` |
| `version-registry-get-wrong-versions` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_wrong_versions` | `matched` |
| `version-registry-match-version` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.match_version` | `matched` |
| `version-registry-get-address-library-filename` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_address_library_filename` | `matched` |
| `version-registry-get-crashgen-configs` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_crashgen_configs` | `matched` |
| `version-registry-get-crashgen-versions` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_crashgen_versions` | `matched` |
| `version-registry-get-crashgen-for-version` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_crashgen_for_version` | `matched` |
| `version-registry-get-all-exe-hashes` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_all_exe_hashes` | `matched` |
| `version-registry-get-all-script-hashes` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_all_script_hashes` | `matched` |
| `version-registry-get-script-hashes-for-version` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_script_hashes_for_version` | `matched` |

## Gap Counts By Owner/Tier

| Owner Module | Tier 1 Gaps | Tier 2 Gaps |
|---|---:|---:|
| `scanlog` | 0 | 231 |
| `config` | 0 | 24 |
| `version_registry` | 0 | 35 |
| `aux` | 0 | 0 |

Detailed per-gap diagnostics are in `parity_diff_report.json`.
