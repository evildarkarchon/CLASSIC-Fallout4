# Rust<->Python Parity Diff Baseline

- Generated: `2026-04-08T23:02:16.784250+00:00`
- Tier-1 contract rows: **240**
- Tier-1 matched: **240**
- Tier-1 missing Rust: **0**
- Tier-1 missing Python: **0**
- Tier-1 signature mismatch: **0**
- Total gaps (Tier-1 + Tier-2): **1026**

## Tier-1 Contract Evaluation

| ID | Owner Module | Rust Symbol | Python Export | Status |
|---|---|---|---|---|
| `config-classic-config-class` | `config` | `ClassicConfig` | `classic_config.ClassicConfig` | `matched` |
| `config-classic-config-get-config-path` | `config` | `ClassicConfig` | `classic_config.ClassicConfig.get_config_path` | `matched` |
| `config-classic-config-load-from-yaml` | `config` | `ClassicConfig` | `classic_config.ClassicConfig.load_from_yaml` | `matched` |
| `config-classic-config-load-local-yaml-paths` | `config` | `ClassicConfig` | `classic_config.ClassicConfig.load_local_yaml_paths` | `matched` |
| `config-classic-config-load-or-default` | `config` | `ClassicConfig` | `classic_config.ClassicConfig.load_or_default` | `matched` |
| `config-classic-config-save-to-yaml` | `config` | `ClassicConfig` | `classic_config.ClassicConfig.save_to_yaml` | `matched` |
| `config-classic-config-validate-paths` | `config` | `ClassicConfig` | `classic_config.ClassicConfig.validate_paths` | `matched` |
| `config-clear-yaml-cache` | `config` | `clear_global_yaml_cache` | `classic_config.clear_yaml_cache` | `matched` |
| `config-path-config-class` | `config` | `PathConfig` | `classic_config.PathConfig` | `matched` |
| `config-yaml-source-class` | `config` | `YamlSource` | `classic_config.YamlSource` | `matched` |
| `config-yaml-source-display-name` | `config` | `YamlSource` | `classic_config.YamlSource.display_name` | `matched` |
| `config-yaml-source-display-name-with-game` | `config` | `YamlSource` | `classic_config.YamlSource.display_name_with_game` | `matched` |
| `config-yaml-source-path` | `config` | `YamlSource` | `classic_config.YamlSource.path` | `matched` |
| `config-yamldata-class` | `config` | `YamlDataCore` | `classic_config.YamlData` | `matched` |
| `config-yamldata-from-content` | `config` | `YamlDataCore` | `classic_config.YamlData.from_yaml_content` | `matched` |
| `scanlog-analysis-config-class` | `scanlog` | `AnalysisConfig` | `classic_scanlog.AnalysisConfig` | `matched` |
| `scanlog-analysis-config-from-yamldata` | `scanlog` | `build_analysis_config_from_yaml` | `classic_scanlog.AnalysisConfig.from_yamldata` | `matched` |
| `scanlog-crashgen-version-class` | `scanlog` | `CrashgenVersion` | `classic_scanlog.CrashgenVersion` | `matched` |
| `scanlog-crashgen-version-status` | `scanlog` | `check_crashgen_version_status` | `classic_scanlog.check_crashgen_version_status` | `matched` |
| `scanlog-crashgen-version-status-class` | `scanlog` | `CrashgenVersionStatus` | `classic_scanlog.CrashgenVersionStatus` | `matched` |
| `scanlog-extract-formids-batch` | `scanlog` | `extract_formids_batch` | `classic_scanlog.extract_formids_batch` | `matched` |
| `scanlog-gpu-detector-class` | `scanlog` | `GpuDetector` | `classic_scanlog.GpuDetector` | `matched` |
| `scanlog-gpu-detector-extract-info` | `scanlog` | `GpuDetector` | `classic_scanlog.GpuDetector.extract_gpu_info` | `matched` |
| `scanlog-logparser-class` | `scanlog` | `LogParser` | `classic_scanlog.LogParser` | `matched` |
| `scanlog-logparser-detect-vr` | `scanlog` | `detect_vr_log` | `classic_scanlog.LogParser.detect_vr_log` | `matched` |
| `scanlog-logparser-extract-formids` | `scanlog` | `LogParser` | `classic_scanlog.LogParser.extract_formids` | `matched` |
| `scanlog-logparser-extract-plugins` | `scanlog` | `LogParser` | `classic_scanlog.LogParser.extract_plugins` | `matched` |
| `scanlog-orchestrator-class` | `scanlog` | `OrchestratorCore` | `classic_scanlog.Orchestrator` | `matched` |
| `scanlog-orchestrator-process-batch` | `scanlog` | `OrchestratorCore` | `classic_scanlog.Orchestrator.process_logs_batch` | `matched` |
| `scanlog-orchestrator-process-log` | `scanlog` | `OrchestratorCore` | `classic_scanlog.Orchestrator.process_log` | `matched` |
| `scanlog-papyrus-analyze-full` | `scanlog` | `PapyrusAnalyzer` | `classic_scanlog.PapyrusAnalyzer.analyze_full` | `matched` |
| `scanlog-papyrus-analyzer-class` | `scanlog` | `PapyrusAnalyzer` | `classic_scanlog.PapyrusAnalyzer` | `matched` |
| `scanlog-parse-crashgen-version` | `scanlog` | `CrashgenVersion` | `classic_scanlog.parse_crashgen_version` | `matched` |
| `scanlog-pattern-matcher-class` | `scanlog` | `PatternMatcher` | `classic_scanlog.PatternMatcher` | `matched` |
| `scanlog-pattern-matcher-find-first` | `scanlog` | `PatternMatcher` | `classic_scanlog.PatternMatcher.find_first` | `matched` |
| `scanlog.crashgen_registry.CheckId@rust` | `scanlog` | `CheckId` | `classic_scanlog.CrashgenVersion` | `matched` |
| `scanlog.crashgen_registry.CrashgenEntry@rust` | `scanlog` | `CrashgenEntry` | `classic_scanlog.CrashgenVersion` | `matched` |
| `scanlog.crashgen_registry.CrashgenRegistry@rust` | `scanlog` | `CrashgenRegistry` | `classic_scanlog.CrashgenVersion` | `matched` |
| `scanlog.crashgen_registry.crashgen_registry@rust` | `scanlog` | `crashgen_registry` | `classic_scanlog.CrashgenVersion` | `matched` |
| `scanlog.error.ScanLogError@rust` | `scanlog` | `ScanLogError` | `classic_scanlog.CrashgenVersion` | `matched` |
| `scanlog.error.error@rust` | `scanlog` | `error` | `classic_scanlog.CrashgenVersion` | `matched` |
| `scanlog.fcx_handler.ConfigIssue` | `scanlog` | `ConfigIssue` | `classic_scanlog.ConfigIssue` | `matched` |
| `scanlog.fcx_handler.ConfigIssue.__init__` | `scanlog` | `ConfigIssue` | `classic_scanlog.ConfigIssue.__init__` | `matched` |
| `scanlog.fcx_handler.ConfigIssue.format_report` | `scanlog` | `ConfigIssue` | `classic_scanlog.ConfigIssue.format_report` | `matched` |
| `scanlog.fcx_handler.ConfigIssue@rust` | `scanlog` | `ConfigIssue` | `classic_scanlog.ConfigIssue` | `matched` |
| `scanlog.fcx_handler.FcxModeHandler` | `scanlog` | `FcxModeHandler` | `classic_scanlog.FcxModeHandler` | `matched` |
| `scanlog.fcx_handler.FcxModeHandler.__init__` | `scanlog` | `FcxModeHandler` | `classic_scanlog.FcxModeHandler.__init__` | `matched` |
| `scanlog.fcx_handler.FcxModeHandler.add_issue` | `scanlog` | `FcxModeHandler` | `classic_scanlog.FcxModeHandler.add_issue` | `matched` |
| `scanlog.fcx_handler.FcxModeHandler.check_fcx_mode` | `scanlog` | `FcxModeHandler` | `classic_scanlog.FcxModeHandler.check_fcx_mode` | `matched` |
| `scanlog.fcx_handler.FcxModeHandler.get_detected_issues` | `scanlog` | `FcxModeHandler` | `classic_scanlog.FcxModeHandler.get_detected_issues` | `matched` |
| `scanlog.fcx_handler.FcxModeHandler.get_fcx_messages` | `scanlog` | `FcxModeHandler` | `classic_scanlog.FcxModeHandler.get_fcx_messages` | `matched` |
| `scanlog.fcx_handler.FcxModeHandler.get_fcx_status_message` | `scanlog` | `FcxModeHandler` | `classic_scanlog.FcxModeHandler.get_fcx_status_message` | `matched` |
| `scanlog.fcx_handler.FcxModeHandler.has_results` | `scanlog` | `FcxModeHandler` | `classic_scanlog.FcxModeHandler.has_results` | `matched` |
| `scanlog.fcx_handler.FcxModeHandler.reset` | `scanlog` | `FcxModeHandler` | `classic_scanlog.FcxModeHandler.reset` | `matched` |
| `scanlog.fcx_handler.FcxModeHandler.reset_fcx_checks` | `scanlog` | `FcxModeHandler` | `classic_scanlog.FcxModeHandler.reset_fcx_checks` | `matched` |
| `scanlog.fcx_handler.FcxModeHandler.set_detected_issues` | `scanlog` | `FcxModeHandler` | `classic_scanlog.FcxModeHandler.set_detected_issues` | `matched` |
| `scanlog.fcx_handler.FcxModeHandler.set_game_files_result` | `scanlog` | `FcxModeHandler` | `classic_scanlog.FcxModeHandler.set_game_files_result` | `matched` |
| `scanlog.fcx_handler.FcxModeHandler.set_main_files_result` | `scanlog` | `FcxModeHandler` | `classic_scanlog.FcxModeHandler.set_main_files_result` | `matched` |
| `scanlog.fcx_handler.FcxModeHandler@rust` | `scanlog` | `FcxModeHandler` | `classic_scanlog.FcxModeHandler` | `matched` |
| `scanlog.fcx_handler.FcxResetError@rust` | `scanlog` | `FcxResetError` | `classic_scanlog.FcxResetError` | `matched` |
| `scanlog.fcx_handler.fcx_handler@rust` | `scanlog` | `fcx_handler` | `classic_scanlog.FcxModeHandler` | `matched` |
| `scanlog.formid.RustFormIDAnalyzer@rust` | `scanlog` | `RustFormIDAnalyzer` | `classic_scanlog.FormIDAnalyzer` | `matched` |
| `scanlog.formid.formid@rust` | `scanlog` | `formid` | `classic_scanlog.FormIDAnalyzer` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzer` | `scanlog` | `RustFormIDAnalyzer` | `classic_scanlog.FormIDAnalyzer` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzer.__init__` | `scanlog` | `RustFormIDAnalyzer` | `classic_scanlog.FormIDAnalyzer.__init__` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzer.analyze_batch` | `scanlog` | `RustFormIDAnalyzer` | `classic_scanlog.FormIDAnalyzer.analyze_batch` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzer.cache_stats` | `scanlog` | `RustFormIDAnalyzer` | `classic_scanlog.FormIDAnalyzer.cache_stats` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzer.clear_cache` | `scanlog` | `RustFormIDAnalyzer` | `classic_scanlog.FormIDAnalyzer.clear_cache` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzer.extract_formids` | `scanlog` | `RustFormIDAnalyzer` | `classic_scanlog.FormIDAnalyzer.extract_formids` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzer.parse_formid` | `scanlog` | `RustFormIDAnalyzer` | `classic_scanlog.FormIDAnalyzer.parse_formid` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzer@rust` | `scanlog` | `FormIDAnalyzer` | `classic_scanlog.FormIDAnalyzer` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzerCore` | `scanlog` | `FormIDAnalyzerCore` | `classic_scanlog.FormIDAnalyzerCore` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzerCore.__init__` | `scanlog` | `FormIDAnalyzerCore` | `classic_scanlog.FormIDAnalyzerCore.__init__` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzerCore.cache_plugins` | `scanlog` | `FormIDAnalyzerCore` | `classic_scanlog.FormIDAnalyzerCore.cache_plugins` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzerCore.extract_formids` | `scanlog` | `FormIDAnalyzerCore` | `classic_scanlog.FormIDAnalyzerCore.extract_formids` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzerCore.extract_formids_nocopy` | `scanlog` | `FormIDAnalyzerCore` | `classic_scanlog.FormIDAnalyzerCore.extract_formids_nocopy` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzerCore.extract_plugin_index` | `scanlog` | `FormIDAnalyzerCore` | `classic_scanlog.FormIDAnalyzerCore.extract_plugin_index` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzerCore.formid_match` | `scanlog` | `FormIDAnalyzerCore` | `classic_scanlog.FormIDAnalyzerCore.formid_match` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzerCore.is_valid_formid` | `scanlog` | `FormIDAnalyzerCore` | `classic_scanlog.FormIDAnalyzerCore.is_valid_formid` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzerCore.parse_formid` | `scanlog` | `FormIDAnalyzerCore` | `classic_scanlog.FormIDAnalyzerCore.parse_formid` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzerCore.process_formids_cached` | `scanlog` | `FormIDAnalyzerCore` | `classic_scanlog.FormIDAnalyzerCore.process_formids_cached` | `matched` |
| `scanlog.formid_analyzer.FormIDAnalyzerCore@rust` | `scanlog` | `FormIDAnalyzerCore` | `classic_scanlog.FormIDAnalyzerCore` | `matched` |
| `scanlog.formid_analyzer.formid_analyzer@rust` | `scanlog` | `formid_analyzer` | `classic_scanlog.FormIDAnalyzerCore` | `matched` |
| `scanlog.formid_analyzer.is_valid_formid` | `scanlog` | `is_valid_formid` | `classic_scanlog.is_valid_formid` | `matched` |
| `scanlog.formid_analyzer.is_valid_formid@rust` | `scanlog` | `is_valid_formid` | `classic_scanlog.is_valid_formid` | `matched` |
| `scanlog.formid_analyzer.validate_formids_batch` | `scanlog` | `validate_formids_batch` | `classic_scanlog.validate_formids_batch` | `matched` |
| `scanlog.formid_analyzer.validate_formids_batch@rust` | `scanlog` | `validate_formids_batch` | `classic_scanlog.validate_formids_batch` | `matched` |
| `scanlog.gpu_detector.GpuDetector.__init__` | `scanlog` | `GpuDetector` | `classic_scanlog.GpuDetector.__init__` | `matched` |
| `scanlog.gpu_detector.GpuDetector.extract_gpu_info_batch` | `scanlog` | `GpuDetector` | `classic_scanlog.GpuDetector.extract_gpu_info_batch` | `matched` |
| `scanlog.gpu_detector.GpuInfo` | `scanlog` | `GpuInfo` | `classic_scanlog.GpuInfo` | `matched` |
| `scanlog.gpu_detector.GpuInfo.__init__` | `scanlog` | `GpuInfo` | `classic_scanlog.GpuInfo.__init__` | `matched` |
| `scanlog.gpu_detector.GpuInfo.to_dict` | `scanlog` | `GpuInfo` | `classic_scanlog.GpuInfo.to_dict` | `matched` |
| `scanlog.gpu_detector.GpuInfo@rust` | `scanlog` | `GpuInfo` | `classic_scanlog.GpuInfo` | `matched` |
| `scanlog.gpu_detector.GpuVendor` | `scanlog` | `GpuVendor` | `classic_scanlog.GpuVendor` | `matched` |
| `scanlog.gpu_detector.GpuVendor.__init__` | `scanlog` | `GpuVendor` | `classic_scanlog.GpuVendor.__init__` | `matched` |
| `scanlog.gpu_detector.GpuVendor@rust` | `scanlog` | `GpuVendor` | `classic_scanlog.GpuVendor` | `matched` |
| `scanlog.gpu_detector.gpu_detector@rust` | `scanlog` | `gpu_detector` | `classic_scanlog.GpuDetector` | `matched` |
| `scanlog.mod_detector.detect_mods_batch` | `scanlog` | `detect_mods_batch` | `classic_scanlog.detect_mods_batch` | `matched` |
| `scanlog.mod_detector.detect_mods_batch@rust` | `scanlog` | `detect_mods_batch` | `classic_scanlog.detect_mods_batch` | `matched` |
| `scanlog.mod_detector.detect_mods_double` | `scanlog` | `detect_mods_double` | `classic_scanlog.detect_mods_double` | `matched` |
| `scanlog.mod_detector.detect_mods_double@rust` | `scanlog` | `detect_mods_double` | `classic_scanlog.detect_mods_double` | `matched` |
| `scanlog.mod_detector.detect_mods_important` | `scanlog` | `detect_mods_important` | `classic_scanlog.detect_mods_important` | `matched` |
| `scanlog.mod_detector.detect_mods_important@rust` | `scanlog` | `detect_mods_important` | `classic_scanlog.detect_mods_important` | `matched` |
| `scanlog.mod_detector.detect_mods_single` | `scanlog` | `detect_mods_single` | `classic_scanlog.detect_mods_single` | `matched` |
| `scanlog.mod_detector.detect_mods_single@rust` | `scanlog` | `detect_mods_single` | `classic_scanlog.detect_mods_single` | `matched` |
| `scanlog.mod_detector.mod_detector@rust` | `scanlog` | `mod_detector` | `classic_scanlog.detect_mods_single` | `matched` |
| `scanlog.orchestrator.AnalysisConfig.__init__` | `scanlog` | `AnalysisConfig` | `classic_scanlog.AnalysisConfig.__init__` | `matched` |
| `scanlog.orchestrator.AnalysisResult` | `scanlog` | `AnalysisResult` | `classic_scanlog.AnalysisResult` | `matched` |
| `scanlog.orchestrator.AnalysisResult.__init__` | `scanlog` | `AnalysisResult` | `classic_scanlog.AnalysisResult.__init__` | `matched` |
| `scanlog.orchestrator.AnalysisResult.get_report_text` | `scanlog` | `AnalysisResult` | `classic_scanlog.AnalysisResult.get_report_text` | `matched` |
| `scanlog.orchestrator.AnalysisResult.to_dict` | `scanlog` | `AnalysisResult` | `classic_scanlog.AnalysisResult.to_dict` | `matched` |
| `scanlog.orchestrator.AnalysisResult@rust` | `scanlog` | `AnalysisResult` | `classic_scanlog.AnalysisResult` | `matched` |
| `scanlog.orchestrator.CancellationToken` | `scanlog` | `OrchestratorCore` | `classic_scanlog.CancellationToken` | `matched` |
| `scanlog.orchestrator.CancellationToken.__init__` | `scanlog` | `OrchestratorCore` | `classic_scanlog.CancellationToken.__init__` | `matched` |
| `scanlog.orchestrator.CancellationToken.cancel` | `scanlog` | `OrchestratorCore` | `classic_scanlog.CancellationToken.cancel` | `matched` |
| `scanlog.orchestrator.CancellationToken.is_cancelled` | `scanlog` | `OrchestratorCore` | `classic_scanlog.CancellationToken.is_cancelled` | `matched` |
| `scanlog.orchestrator.CancellationToken.reset` | `scanlog` | `OrchestratorCore` | `classic_scanlog.CancellationToken.reset` | `matched` |
| `scanlog.orchestrator.Orchestrator.__init__` | `scanlog` | `OrchestratorCore` | `classic_scanlog.Orchestrator.__init__` | `matched` |
| `scanlog.orchestrator.Orchestrator.attach_database` | `scanlog` | `OrchestratorCore` | `classic_scanlog.Orchestrator.attach_database` | `matched` |
| `scanlog.orchestrator.Orchestrator.check_loadorder_exists` | `scanlog` | `OrchestratorCore` | `classic_scanlog.Orchestrator.check_loadorder_exists` | `matched` |
| `scanlog.orchestrator.Orchestrator.has_database_pool` | `scanlog` | `OrchestratorCore` | `classic_scanlog.Orchestrator.has_database_pool` | `matched` |
| `scanlog.orchestrator.Orchestrator.is_feature_complete` | `scanlog` | `OrchestratorCore` | `classic_scanlog.Orchestrator.is_feature_complete` | `matched` |
| `scanlog.orchestrator.Orchestrator.is_initialized` | `scanlog` | `OrchestratorCore` | `classic_scanlog.Orchestrator.is_initialized` | `matched` |
| `scanlog.orchestrator.Orchestrator.load_loadorder` | `scanlog` | `OrchestratorCore` | `classic_scanlog.Orchestrator.load_loadorder` | `matched` |
| `scanlog.orchestrator.Orchestrator.process_logs_parallel` | `scanlog` | `OrchestratorCore` | `classic_scanlog.Orchestrator.process_logs_parallel` | `matched` |
| `scanlog.orchestrator.Orchestrator.write_reports_batch` | `scanlog` | `OrchestratorCore` | `classic_scanlog.Orchestrator.write_reports_batch` | `matched` |
| `scanlog.orchestrator.ScanProgressPhase@rust` | `scanlog` | `ScanProgressPhase` | `classic_scanlog.AnalysisResult` | `matched` |
| `scanlog.orchestrator.orchestrator@rust` | `scanlog` | `orchestrator` | `classic_scanlog.Orchestrator` | `matched` |
| `scanlog.orchestrator.resolve_batch_concurrency@rust` | `scanlog` | `resolve_batch_concurrency` | `classic_scanlog.Orchestrator` | `matched` |
| `scanlog.papyrus.PapyrusAnalyzer.__init__` | `scanlog` | `PapyrusAnalyzer` | `classic_scanlog.PapyrusAnalyzer.__init__` | `matched` |
| `scanlog.papyrus.PapyrusAnalyzer.analyze_to_string` | `scanlog` | `PapyrusAnalyzer` | `classic_scanlog.PapyrusAnalyzer.analyze_to_string` | `matched` |
| `scanlog.papyrus.PapyrusAnalyzer.check_for_updates` | `scanlog` | `PapyrusAnalyzer` | `classic_scanlog.PapyrusAnalyzer.check_for_updates` | `matched` |
| `scanlog.papyrus.PapyrusAnalyzer.log_exists` | `scanlog` | `PapyrusAnalyzer` | `classic_scanlog.PapyrusAnalyzer.log_exists` | `matched` |
| `scanlog.papyrus.PapyrusAnalyzer.log_path` | `scanlog` | `PapyrusAnalyzer` | `classic_scanlog.PapyrusAnalyzer.log_path` | `matched` |
| `scanlog.papyrus.PapyrusAnalyzer.reset` | `scanlog` | `PapyrusAnalyzer` | `classic_scanlog.PapyrusAnalyzer.reset` | `matched` |
| `scanlog.papyrus.PapyrusAnalyzer.start_monitoring` | `scanlog` | `PapyrusAnalyzer` | `classic_scanlog.PapyrusAnalyzer.start_monitoring` | `matched` |
| `scanlog.papyrus.PapyrusAnalyzer.stats` | `scanlog` | `PapyrusAnalyzer` | `classic_scanlog.PapyrusAnalyzer.stats` | `matched` |
| `scanlog.papyrus.PapyrusError@rust` | `scanlog` | `PapyrusError` | `classic_scanlog.PapyrusError` | `matched` |
| `scanlog.papyrus.PapyrusStats` | `scanlog` | `PapyrusStats` | `classic_scanlog.PapyrusStats` | `matched` |
| `scanlog.papyrus.PapyrusStats.__init__` | `scanlog` | `PapyrusStats` | `classic_scanlog.PapyrusStats.__init__` | `matched` |
| `scanlog.papyrus.PapyrusStats.dumps_to_stacks_ratio` | `scanlog` | `PapyrusStats` | `classic_scanlog.PapyrusStats.dumps_to_stacks_ratio` | `matched` |
| `scanlog.papyrus.PapyrusStats@rust` | `scanlog` | `PapyrusStats` | `classic_scanlog.PapyrusStats` | `matched` |
| `scanlog.papyrus.papyrus@rust` | `scanlog` | `papyrus` | `classic_scanlog.PapyrusAnalyzer` | `matched` |
| `scanlog.papyrus.papyrus_logging` | `scanlog` | `PapyrusAnalyzer` | `classic_scanlog.papyrus_logging` | `matched` |
| `scanlog.parser.LogParser.__init__` | `scanlog` | `LogParser` | `classic_scanlog.LogParser.__init__` | `matched` |
| `scanlog.parser.LogParser.add_pattern` | `scanlog` | `LogParser` | `classic_scanlog.LogParser.add_pattern` | `matched` |
| `scanlog.parser.LogParser.benchmark` | `scanlog` | `LogParser` | `classic_scanlog.LogParser.benchmark` | `matched` |
| `scanlog.parser.LogParser.clear_caches` | `scanlog` | `LogParser` | `classic_scanlog.LogParser.clear_caches` | `matched` |
| `scanlog.parser.LogParser.extract_addresses` | `scanlog` | `LogParser` | `classic_scanlog.LogParser.extract_addresses` | `matched` |
| `scanlog.parser.LogParser.extract_section` | `scanlog` | `LogParser` | `classic_scanlog.LogParser.extract_section` | `matched` |
| `scanlog.parser.LogParser.extract_sections_batch` | `scanlog` | `LogParser` | `classic_scanlog.LogParser.extract_sections_batch` | `matched` |
| `scanlog.parser.LogParser.find_patterns` | `scanlog` | `LogParser` | `classic_scanlog.LogParser.find_patterns` | `matched` |
| `scanlog.parser.LogParser.find_patterns_chunked` | `scanlog` | `LogParser` | `classic_scanlog.LogParser.find_patterns_chunked` | `matched` |
| `scanlog.parser.LogParser.get_section` | `scanlog` | `LogParser` | `classic_scanlog.LogParser.get_section` | `matched` |
| `scanlog.parser.LogParser.get_segment_sizes` | `scanlog` | `LogParser` | `classic_scanlog.LogParser.get_segment_sizes` | `matched` |
| `scanlog.parser.LogParser.get_stats` | `scanlog` | `LogParser` | `classic_scanlog.LogParser.get_stats` | `matched` |
| `scanlog.parser.LogParser.parse_all_sections` | `scanlog` | `LogParser` | `classic_scanlog.LogParser.parse_all_sections` | `matched` |
| `scanlog.parser.LogParser.parse_complete` | `scanlog` | `LogParser` | `classic_scanlog.LogParser.parse_complete` | `matched` |
| `scanlog.parser.LogParser.parse_crash_header` | `scanlog` | `LogParser` | `classic_scanlog.LogParser.parse_crash_header` | `matched` |
| `scanlog.parser.LogParser.parse_segments_parallel` | `scanlog` | `LogParser` | `classic_scanlog.LogParser.parse_segments_parallel` | `matched` |
| `scanlog.parser.ScanOutput` | `scanlog` | `LogParser` | `classic_scanlog.ScanOutput` | `matched` |
| `scanlog.parser.StreamingIteratorParser@rust` | `scanlog` | `StreamingIteratorParser` | `classic_scanlog.LogParser` | `matched` |
| `scanlog.parser.StreamingLogParser@rust` | `scanlog` | `StreamingLogParser` | `classic_scanlog.LogParser` | `matched` |
| `scanlog.parser.parser@rust` | `scanlog` | `parser` | `classic_scanlog.LogParser` | `matched` |
| `scanlog.patterns.PatternMatcher.__init__` | `scanlog` | `PatternMatcher` | `classic_scanlog.PatternMatcher.__init__` | `matched` |
| `scanlog.patterns.PatternMatcher.clear_cache` | `scanlog` | `PatternMatcher` | `classic_scanlog.PatternMatcher.clear_cache` | `matched` |
| `scanlog.patterns.PatternMatcher.get_stats` | `scanlog` | `PatternMatcher` | `classic_scanlog.PatternMatcher.get_stats` | `matched` |
| `scanlog.patterns.PatternMatcher.replace_all` | `scanlog` | `PatternMatcher` | `classic_scanlog.PatternMatcher.replace_all` | `matched` |
| `scanlog.patterns.patterns@rust` | `scanlog` | `patterns` | `classic_scanlog.PatternMatcher` | `matched` |
| `scanlog.plugin_analyzer.PluginAnalyzer` | `scanlog` | `PluginAnalyzer` | `classic_scanlog.PluginAnalyzer` | `matched` |
| `scanlog.plugin_analyzer.PluginAnalyzer.__init__` | `scanlog` | `PluginAnalyzer` | `classic_scanlog.PluginAnalyzer.__init__` | `matched` |
| `scanlog.plugin_analyzer.PluginAnalyzer.check_plugin_limit` | `scanlog` | `PluginAnalyzer` | `classic_scanlog.PluginAnalyzer.check_plugin_limit` | `matched` |
| `scanlog.plugin_analyzer.PluginAnalyzer.filter_ignored_plugins` | `scanlog` | `PluginAnalyzer` | `classic_scanlog.PluginAnalyzer.filter_ignored_plugins` | `matched` |
| `scanlog.plugin_analyzer.PluginAnalyzer.loadorder_scan_log` | `scanlog` | `PluginAnalyzer` | `classic_scanlog.PluginAnalyzer.loadorder_scan_log` | `matched` |
| `scanlog.plugin_analyzer.PluginAnalyzer.plugin_match` | `scanlog` | `PluginAnalyzer` | `classic_scanlog.PluginAnalyzer.plugin_match` | `matched` |
| `scanlog.plugin_analyzer.PluginAnalyzer@rust` | `scanlog` | `PluginAnalyzer` | `classic_scanlog.PluginAnalyzer` | `matched` |
| `scanlog.plugin_analyzer.contains_plugin` | `scanlog` | `contains_plugin` | `classic_scanlog.contains_plugin` | `matched` |
| `scanlog.plugin_analyzer.contains_plugin@rust` | `scanlog` | `contains_plugin` | `classic_scanlog.contains_plugin` | `matched` |
| `scanlog.plugin_analyzer.detect_plugins_batch` | `scanlog` | `detect_plugins_batch` | `classic_scanlog.detect_plugins_batch` | `matched` |
| `scanlog.plugin_analyzer.detect_plugins_batch@rust` | `scanlog` | `detect_plugins_batch` | `classic_scanlog.detect_plugins_batch` | `matched` |
| `scanlog.plugin_analyzer.plugin_analyzer@rust` | `scanlog` | `plugin_analyzer` | `classic_scanlog.PluginAnalyzer` | `matched` |
| `scanlog.record_scanner.RecordScanner` | `scanlog` | `RecordScanner` | `classic_scanlog.RecordScanner` | `matched` |
| `scanlog.record_scanner.RecordScanner.__init__` | `scanlog` | `RecordScanner` | `classic_scanlog.RecordScanner.__init__` | `matched` |
| `scanlog.record_scanner.RecordScanner.clear_cache` | `scanlog` | `RecordScanner` | `classic_scanlog.RecordScanner.clear_cache` | `matched` |
| `scanlog.record_scanner.RecordScanner.extract_records` | `scanlog` | `RecordScanner` | `classic_scanlog.RecordScanner.extract_records` | `matched` |
| `scanlog.record_scanner.RecordScanner.scan_named_records` | `scanlog` | `RecordScanner` | `classic_scanlog.RecordScanner.scan_named_records` | `matched` |
| `scanlog.record_scanner.RecordScanner@rust` | `scanlog` | `RecordScanner` | `classic_scanlog.RecordScanner` | `matched` |
| `scanlog.record_scanner.contains_record` | `scanlog` | `contains_record` | `classic_scanlog.contains_record` | `matched` |
| `scanlog.record_scanner.contains_record@rust` | `scanlog` | `contains_record` | `classic_scanlog.contains_record` | `matched` |
| `scanlog.record_scanner.record_scanner@rust` | `scanlog` | `record_scanner` | `classic_scanlog.RecordScanner` | `matched` |
| `scanlog.record_scanner.scan_records_batch` | `scanlog` | `scan_records_batch` | `classic_scanlog.scan_records_batch` | `matched` |
| `scanlog.record_scanner.scan_records_batch@rust` | `scanlog` | `scan_records_batch` | `classic_scanlog.scan_records_batch` | `matched` |
| `scanlog.segment_key.segment_key@rust` | `scanlog` | `segment_key` | `classic_scanlog.CrashgenVersion` | `matched` |
| `scanlog.settings_validator.SettingsValidator` | `scanlog` | `SettingsValidator` | `classic_scanlog.SettingsValidator` | `matched` |
| `scanlog.settings_validator.SettingsValidator.__init__` | `scanlog` | `SettingsValidator` | `classic_scanlog.SettingsValidator.__init__` | `matched` |
| `scanlog.settings_validator.SettingsValidator.check_disabled_settings` | `scanlog` | `SettingsValidator` | `classic_scanlog.SettingsValidator.check_disabled_settings` | `matched` |
| `scanlog.settings_validator.SettingsValidator.scan_all_settings` | `scanlog` | `SettingsValidator` | `classic_scanlog.SettingsValidator.scan_all_settings` | `matched` |
| `scanlog.settings_validator.SettingsValidator.scan_archivelimit_setting` | `scanlog` | `SettingsValidator` | `classic_scanlog.SettingsValidator.scan_archivelimit_setting` | `matched` |
| `scanlog.settings_validator.SettingsValidator.scan_buffout_achievements_setting` | `scanlog` | `SettingsValidator` | `classic_scanlog.SettingsValidator.scan_buffout_achievements_setting` | `matched` |
| `scanlog.settings_validator.SettingsValidator.scan_buffout_looksmenu_setting` | `scanlog` | `SettingsValidator` | `classic_scanlog.SettingsValidator.scan_buffout_looksmenu_setting` | `matched` |
| `scanlog.settings_validator.SettingsValidator.scan_buffout_memorymanagement_settings` | `scanlog` | `SettingsValidator` | `classic_scanlog.SettingsValidator.scan_buffout_memorymanagement_settings` | `matched` |
| `scanlog.settings_validator.SettingsValidator@rust` | `scanlog` | `SettingsValidator` | `classic_scanlog.SettingsValidator` | `matched` |
| `scanlog.settings_validator.settings_validator@rust` | `scanlog` | `settings_validator` | `classic_scanlog.SettingsValidator` | `matched` |
| `scanlog.suspect_scanner.SuspectScanner` | `scanlog` | `SuspectScanner` | `classic_scanlog.SuspectScanner` | `matched` |
| `scanlog.suspect_scanner.SuspectScanner.__init__` | `scanlog` | `SuspectScanner` | `classic_scanlog.SuspectScanner.__init__` | `matched` |
| `scanlog.suspect_scanner.SuspectScanner.check_dll_crash` | `scanlog` | `SuspectScanner` | `classic_scanlog.SuspectScanner.check_dll_crash` | `matched` |
| `scanlog.suspect_scanner.SuspectScanner.scan_suspects_batch` | `scanlog` | `SuspectScanner` | `classic_scanlog.SuspectScanner.scan_suspects_batch` | `matched` |
| `scanlog.suspect_scanner.SuspectScanner.suspect_scan_mainerror` | `scanlog` | `SuspectScanner` | `classic_scanlog.SuspectScanner.suspect_scan_mainerror` | `matched` |
| `scanlog.suspect_scanner.SuspectScanner.suspect_scan_stack` | `scanlog` | `SuspectScanner` | `classic_scanlog.SuspectScanner.suspect_scan_stack` | `matched` |
| `scanlog.suspect_scanner.SuspectScanner@rust` | `scanlog` | `SuspectScanner` | `classic_scanlog.SuspectScanner` | `matched` |
| `scanlog.suspect_scanner.suspect_scanner@rust` | `scanlog` | `suspect_scanner` | `classic_scanlog.SuspectScanner` | `matched` |
| `scanlog.version.CrashgenVersion.__eq__` | `scanlog` | `CrashgenVersion` | `classic_scanlog.CrashgenVersion.__eq__` | `matched` |
| `scanlog.version.CrashgenVersion.__hash__` | `scanlog` | `CrashgenVersion` | `classic_scanlog.CrashgenVersion.__hash__` | `matched` |
| `scanlog.version.CrashgenVersion.__init__` | `scanlog` | `CrashgenVersion` | `classic_scanlog.CrashgenVersion.__init__` | `matched` |
| `scanlog.version.crashgen_version_gen@rust` | `scanlog` | `crashgen_version_gen` | `classic_scanlog.parse_crashgen_version` | `matched` |
| `scanlog.version.version@rust` | `scanlog` | `version` | `classic_scanlog.CrashgenVersion` | `matched` |
| `version-registry-class` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry` | `matched` |
| `version-registry-game-version-class` | `version_registry` | `GameVersion` | `classic_version_registry.GameVersion` | `matched` |
| `version-registry-get-address-library-filename` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_address_library_filename` | `matched` |
| `version-registry-get-all` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_all` | `matched` |
| `version-registry-get-all-exe-hashes` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_all_exe_hashes` | `matched` |
| `version-registry-get-all-for-game` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_all_for_game` | `matched` |
| `version-registry-get-all-script-hashes` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_all_script_hashes` | `matched` |
| `version-registry-get-by-id` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_by_id` | `matched` |
| `version-registry-get-by-short-name` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_by_short_name` | `matched` |
| `version-registry-get-by-version` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_by_version` | `matched` |
| `version-registry-get-correct-versions` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_correct_versions` | `matched` |
| `version-registry-get-crashgen-configs` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_crashgen_configs` | `matched` |
| `version-registry-get-crashgen-for-version` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_crashgen_for_version` | `matched` |
| `version-registry-get-crashgen-versions` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_crashgen_versions` | `matched` |
| `version-registry-get-script-hashes-for-version` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_script_hashes_for_version` | `matched` |
| `version-registry-get-singleton` | `version_registry` | `get_version_registry` | `classic_version_registry.get_version_registry` | `matched` |
| `version-registry-get-wrong-versions` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.get_wrong_versions` | `matched` |
| `version-registry-match-confidence-class` | `version_registry` | `MatchConfidence` | `classic_version_registry.MatchConfidence` | `matched` |
| `version-registry-match-result-class` | `version_registry` | `MatchResult` | `classic_version_registry.MatchResult` | `matched` |
| `version-registry-match-version` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry.match_version` | `matched` |
| `version-registry-match-version-string` | `version_registry` | `VersionRegistry` | `classic_version_registry.match_version_string` | `matched` |
| `version-registry-unknown-version-get-default` | `version_registry` | `UnknownVersionHandling` | `classic_version_registry.UnknownVersionHandling.get_default` | `matched` |
| `version-registry-unknown-version-handling-class` | `version_registry` | `UnknownVersionHandling` | `classic_version_registry.UnknownVersionHandling` | `matched` |
| `version-registry-version-info-class` | `version_registry` | `VersionInfo` | `classic_version_registry.VersionInfo` | `matched` |

## Gap Counts By Owner/Tier

| Owner Module | Tier 1 Gaps | Tier 2 Gaps |
|---|---:|---:|
| `scanlog` | 0 | 51 |
| `config` | 0 | 28 |
| `version_registry` | 0 | 35 |
| `yaml` | 0 | 37 |
| `database` | 0 | 46 |
| `file_io` | 0 | 105 |
| `scangame` | 0 | 215 |
| `registry` | 0 | 39 |
| `perf` | 0 | 16 |
| `settings` | 0 | 39 |
| `message` | 0 | 53 |
| `path` | 0 | 85 |
| `constants` | 0 | 59 |
| `version` | 0 | 28 |
| `resource` | 0 | 40 |
| `xse` | 0 | 40 |
| `web` | 0 | 29 |
| `update` | 0 | 15 |
| `shared` | 0 | 66 |
| `aux` | 0 | 0 |

Detailed per-gap diagnostics are in `parity_diff_report.json`.
