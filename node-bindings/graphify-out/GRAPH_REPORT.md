# Graph Report - D:\repos\CLASSIC-Fallout4\node-bindings  (2026-07-28)

## Corpus Check
- 82 files · ~127,243 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2262 nodes · 4568 edges · 134 communities (84 shown, 50 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 74 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 117
- Community 118
- Community 119
- Community 121
- Community 122
- Community 123
- Community 124

## God Nodes (most connected - your core abstractions)
1. `YamlData` - 37 edges
2. `YamlData` - 34 edges
3. `spawn_result()` - 32 edges
4. `JsDatabasePool` - 27 edges
5. `JsDatabasePool` - 25 edges
6. `scripts` - 19 edges
7. `revision_token()` - 18 edges
8. `JsFileIO` - 17 edges
9. `JsFileIO` - 16 edges
10. `analyzer_error_to_napi()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `js_rules_to_core_uses_shared_crashgen_expectation_parser()` --calls--> `js_rules_to_core()`  [INFERRED]
  classic-node/src/crashgen_rules_tests.rs → classic-node/src/crashgen_rules.rs
- `check_crashgen_full_with_rules()` --calls--> `js_rules_to_core()`  [INFERRED]
  classic-node/src/scangame.rs → classic-node/src/crashgen_rules.rs
- `js_scan_config_to_core()` --calls--> `js_rules_to_core()`  [INFERRED]
  classic-node/src/scangame.rs → classic-node/src/crashgen_rules.rs
- `build_analyzer()` --calls--> `parse_js_rules_to_core()`  [INFERRED]
  classic-node/src/crashgen_settings_analyzer.rs → classic-node/src/crashgen_rules.rs
- `run_formid_lookup_future()` --calls--> `spawn_result()`  [INFERRED]
  classic-node/src/database.rs → classic-node/src/runtime.rs

## Import Cycles
- None detected.

## Communities (134 total, 50 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (222): Fallout4VersionInfo, FileIoConfig, HashCacheStats, JsAddressLibInfo, JsAddressLibraryConfig, JsAnalyzerKind, JsApprovedUpdate, JsAutoscanReportPlacement (+214 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (45): BackupType, C, calculate_file_similarity(), calculate_text_similarity(), clear_hash_cache(), detect_encoding(), FileIOConfig, generate_ignore_file() (+37 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (41): config_error_status(), config_error_to_napi_err(), CoreYamlSource, create_yaml_data_from_content(), ensure_app_dir_initialized(), get_application_dir(), get_yaml_source_display_name(), get_yaml_source_display_name_with_game() (+33 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (67): analyzer_error_to_napi(), base_napi_error(), build_analyzer(), config_layout_to_core(), CrashgenSettingsAnalyzer, input_to_core(), JsAnalyzerKind, JsAutoscanReportPlacement (+59 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (40): base_formid_lookup_error(), formid_lookup_entry_to_core(), formid_lookup_error_fields_to_napi(), formid_lookup_error_to_napi(), formid_lookup_outcome_to_js(), formid_lookup_task_failure_to_napi(), FormIdValueLookupBatchTask, FormIdValueLookupTask (+32 more)

### Community 5 - "Community 5"
Cohesion: 0.08
Nodes (55): apply_yaml_update(), build_yaml_update_config(), check_app_notification(), check_for_updates(), check_yaml_update(), classification_tag(), core_asset_to_js(), core_file_to_js() (+47 more)

### Community 6 - "Community 6"
Cohesion: 0.09
Nodes (33): BackupManager, check_drive_exists(), check_read_permissions(), check_write_permissions(), DocsPathFinder, DocumentsChecker, GamePathFinder, get_system_documents_path() (+25 more)

### Community 7 - "Community 7"
Cohesion: 0.10
Nodes (49): core_to_js_yaml_file(), docs_to_json(), get_all_yaml_files(), get_cached(), get_settings_cache_stats(), get_yaml_file_description(), invalidate_settings(), is_cached() (+41 more)

### Community 8 - "Community 8"
Cohesion: 0.10
Nodes (54): confidence_to_string(), core_crashgen_to_js(), core_to_js_fo4_version(), core_version_info_to_js(), Fallout4VersionInfo, game_version_distance(), get_address_library_filename(), get_all_exe_hashes() (+46 more)

### Community 9 - "Community 9"
Cohesion: 0.04
Nodes (44): bun-types, bin, classic-node, description, devDependencies, bun-types, @napi-rs/cli, @types/node (+36 more)

### Community 10 - "Community 10"
Cohesion: 0.10
Nodes (38): build_analyzer(), conflict_result_to_js(), conflict_to_core(), important_mod_result_to_js(), important_mod_to_core(), JsImportantModGuidance, JsImportantModRule, JsModConflictGuidance (+30 more)

### Community 11 - "Community 11"
Cohesion: 0.11
Nodes (31): isSupportedGame(), main(), parseArgs(), parseInteger(), printHelp(), requireValue(), calculateScanSpeed(), ClassicNodeModule (+23 more)

### Community 12 - "Community 12"
Cohesion: 0.11
Nodes (35): core_rules_to_js(), js_check_rule_to_document(), js_preflight_rule_to_document(), js_rules_to_core(), js_rules_to_document(), JsCheckRule, JsCrashgenRegistryEntry, JsCrashgenSettingsRules (+27 more)

### Community 13 - "Community 13"
Cohesion: 0.10
Nodes (27): base_explicit_yaml_data_error(), content_identity_to_js(), explicit_yaml_data_error_to_napi(), explicit_yaml_data_role_name(), ExplicitYamlDataLoadTask, ExplicitYamlDataSnapshot, ExplicitYamlDataTaskOutput, JsExplicitYamlDataGameRole (+19 more)

### Community 14 - "Community 14"
Cohesion: 0.10
Nodes (30): build_analyzer(), FormIdFindingAnalysisTask, FormIdFindingAnalysisTaskOutput, FormIdFindingAnalyzer, input_to_core(), JsFormIdFinding, JsFormIdFindingAnalysisInput, JsFormIdFindingAnalysisResult (+22 more)

### Community 15 - "Community 15"
Cohesion: 0.10
Nodes (32): get_all_game_ids(), get_game_name(), get_metrics_summary(), get_runtime_info(), intern_string(), join_paths(), js_to_core_game_id(), JsGameId (+24 more)

### Community 17 - "Community 17"
Cohesion: 0.13
Nodes (22): emit_node_runtime_startup_diagnostics(), resolve_correlation_id(), Option, String, core_to_js(), create_logger(), create_message(), format_message() (+14 more)

### Community 18 - "Community 18"
Cohesion: 0.15
Nodes (31): discovery_to_js(), JsScanRunDiscoveryResult, JsScanRunFailure, JsScanRunInfrastructureError, JsScanRunLocalIgnoreResetRunData, JsScanRunLogFailure, JsScanRunLogResult, JsScanRunRejectedInput (+23 more)

### Community 19 - "Community 19"
Cohesion: 0.10
Nodes (31): build_game_setup_intake(), config_issue_to_js(), game_setup_check_to_js(), game_setup_needs_path_detection(), game_setup_path_update_to_js(), game_setup_result_to_js(), get_address_lib_info(), JsAddressLibInfo (+23 more)

### Community 20 - "Community 20"
Cohesion: 0.12
Nodes (25): Arc, Cancellation, JsObserverAdapter, JsScanRunEvent, JsScanRunLocalIgnoreRecoveryDecision, local_ignore_recovery_decision_to_core(), AsyncTask, Option (+17 more)

### Community 21 - "Community 21"
Cohesion: 0.16
Nodes (22): build_analyzer(), CrashSuspectAnalyzer, JsCrashSuspectAnalysisInput, JsCrashSuspectAnalysisResult, JsCrashSuspectFinding, JsCrashSuspectFindingKind, JsCrashSuspectMainErrorRule, JsCrashSuspectStackCountRule (+14 more)

### Community 22 - "Community 22"
Cohesion: 0.15
Nodes (26): analyze_papyrus_log(), check_crashgen_version_status(), detect_crash_pattern(), detect_gpu_info(), detect_vr_log(), extract_form_ids(), extract_plugin_list(), is_settings_header_marker() (+18 more)

### Community 23 - "Community 23"
Cohesion: 0.17
Nodes (20): configuration_to_core(), JsScanRunConfiguration, JsScanRunSetupContext, JsScanRunStandardSource, JsScanRunTargetedSource, required_path(), JsGameId, Result (+12 more)

### Community 24 - "Community 24"
Cohesion: 0.16
Nodes (25): build_url_with_query(), extract_domain(), get_classic_version(), get_mod_site_game_url(), get_mod_site_name(), get_mod_site_url(), get_user_agent(), get_user_agent_prefix() (+17 more)

### Community 26 - "Community 26"
Cohesion: 0.19
Nodes (23): count_resources_by_type(), create_resource_info(), create_resource_info_with_size(), detect_resource_type(), enumerate_resources(), get_resource_extensions(), is_supported_resource(), parse_resource_type() (+15 more)

### Community 27 - "Community 27"
Cohesion: 0.13
Nodes (13): BA2Scanner, JsBa2Scanner, JsIniValidator, JsLogProcessor, JsUnpackedScanner, process_game_logs(), HashMap, Self (+5 more)

### Community 28 - "Community 28"
Cohesion: 0.20
Nodes (23): core_to_js_xse_type(), detect_xse_version(), get_xse_info(), is_xse_installed(), js_game_id_to_core(), js_to_core_xse_type(), JsXseInfo, JsXseType (+15 more)

### Community 29 - "Community 29"
Cohesion: 0.17
Nodes (22): classification_token(), commit_eligibility_token(), crash_log_scan_settings_to_js(), frontend_state_to_js(), game_setup_settings_to_js(), JsFrontendPreferences, JsFrontendState, JsGuiWindowGeometry (+14 more)

### Community 30 - "Community 30"
Cohesion: 0.15
Nodes (8): JsLegacyTuiStateImportReceipt, JsUserSettingsMigrationReceipt, legacy_tui_state_import_outcome_to_js(), revision_token(), JsLegacyTuiStateImportRestoreOutcome, LegacyTuiStateImportOutcome, LegacyTuiStateImportReceipt, UserSettingsMigrationReceipt

### Community 31 - "Community 31"
Cohesion: 0.18
Nodes (21): diagnostic_kind_to_js(), diagnostic_to_js(), InstalledYamlDataDurabilityReceipt, InstalledYamlDataErrorMetadata, JsInstalledYamlDataDiagnostic, JsInstalledYamlDataDiagnosticKind, JsInstalledYamlDataLoadOutcome, JsInstalledYamlDataLoadStatus (+13 more)

### Community 32 - "Community 32"
Cohesion: 0.16
Nodes (14): check_enb(), JsBa2Issues, JsBa2ScanResult, JsCheckResult, JsConfigIssue, JsEnbChecker, JsEnbValidationResult, JsGameScanResult (+6 more)

### Community 33 - "Community 33"
Cohesion: 0.19
Nodes (21): Buffer, apply_user_settings_migration(), import_legacy_tui_state_into_user_settings(), JsCrashLogScanSettings, JsGameSetupSettings, JsLegacyTuiStateImportOutcome, JsLegacyTuiStateImportRestoreOutcome, JsUpdatePreferences (+13 more)

### Community 34 - "Community 34"
Cohesion: 0.15
Nodes (18): infrastructure_error_to_js(), log_result_to_js(), project_scan_run_resume_error(), durability_unknown_projects_shared_node_recovery_receipt(), event_mapping_covers_every_variant_and_phase(), infrastructure_mapping_covers_every_stage_with_and_without_paths(), log_event(), replacement_failure_projects_shared_node_rejection_metadata() (+10 more)

### Community 35 - "Community 35"
Cohesion: 0.22
Nodes (18): compare_versions(), extract_all_versions(), extract_pe_version(), extract_version_from_filename(), extract_version_from_log(), format_version(), is_known_fallout4_version(), is_valid_pe_path() (+10 more)

### Community 36 - "Community 36"
Cohesion: 0.13
Nodes (13): EXPLICIT_MAIN_YAML, YAML_CACHE_ENV_NAMES, getRuntimeCoverageEntries(), getTier1OwnerModules(), registry, RuntimeCoverageEntry, RuntimeCoverageRegistry, configSourceCases (+5 more)

### Community 37 - "Community 37"
Cohesion: 0.15
Nodes (14): analyzer(), conflict(), important_mods(), invalid_configuration_retains_shared_mod_guidance_error(), optional_conflict_fix_projects_as_absent(), owned_projection_preserves_all_authored_fields_and_match_states(), populated_input(), Vec (+6 more)

### Community 38 - "Community 38"
Cohesion: 0.13
Nodes (17): installed_yaml_data_run_diagnostic_kind_to_js(), installed_yaml_data_run_diagnostic_to_js(), installed_yaml_data_run_to_js(), JsInstalledYamlDataRunData, JsScanRunInstalledYamlDataDiagnostic, JsScanRunInstalledYamlDataDiagnosticKind, JsScanRunLocalIgnoreState, local_ignore_run_state_to_js() (+9 more)

### Community 39 - "Community 39"
Cohesion: 0.20
Nodes (17): commit_frontend_geometry_transition(), commit_user_settings(), commit_user_settings_bootstrap(), commit_user_settings_update(), JsGuiWindow, JsGuiWindowGeometryUpdate, JsTuiRememberedStateUpdate, JsUserSettingsCommitResult (+9 more)

### Community 40 - "Community 40"
Cohesion: 0.12
Nodes (16): compilerOptions, esModuleInterop, forceConsistentCasingInFileNames, module, moduleResolution, noEmitOnError, outDir, resolveJsonModule (+8 more)

### Community 42 - "Community 42"
Cohesion: 0.15
Nodes (11): InstalledYamlDataSnapshot, JsLocalIgnoreResetResult, JsLocalIgnoreYamlDataState, local_ignore_state_to_js(), JsYamlDataContentIdentity, Vec, YamlData, CoreInstalledYamlDataSnapshot (+3 more)

### Community 43 - "Community 43"
Cohesion: 0.13
Nodes (8): CRASHGEN_VERSION_STATUS, MISSING_LOG_PATH, ScanRunExecution, ScanRunFailure, ScanRunSuccess, SHARED_SCAN_RUN_FIXTURE_ROOT, SHARED_SCAN_RUN_MANIFEST, SHARED_VALID_CRASH_LOG

### Community 44 - "Community 44"
Cohesion: 0.23
Nodes (10): inspected_file_to_js(), JsInspectedYamlDataFile, JsInstalledYamlDataProvenance, JsInstalledYamlDataRole, provenance_to_js(), role_name(), role_to_js(), CoreInspectedYamlDataFile (+2 more)

### Community 45 - "Community 45"
Cohesion: 0.33
Nodes (6): local_ignore_reset_result_to_js(), LocalIgnoreRecoveryPlan, LocalIgnoreResetTask, Result, CoreLocalIgnoreRecoveryPlan, CoreLocalIgnoreResetResult

### Community 46 - "Community 46"
Cohesion: 0.24
Nodes (11): check_crashgen_config(), check_crashgen_config_with_rules(), check_crashgen_full(), check_crashgen_full_with_rules(), JsCrashgenChecker, JsCrashgenCheckResult, JsCrashgenReport, JsTomlConfigIssue (+3 more)

### Community 47 - "Community 47"
Cohesion: 0.36
Nodes (9): base_inspection_error(), inspection_error_to_napi(), installed_yaml_data_error(), load_error_to_napi(), local_ignore_reset_error_to_napi(), Env, Error, JsValue (+1 more)

### Community 48 - "Community 48"
Cohesion: 0.18
Nodes (11): inspect_installed_yaml_data(), InstalledYamlDataInspectionTask, InstalledYamlDataLoadTask, JsInstalledYamlDataInspectionRequest, JsInstalledYamlDataLoadRequest, load_installed_yaml_data(), AsyncTask, String (+3 more)

### Community 49 - "Community 49"
Cohesion: 0.28
Nodes (8): detect_config_duplicates(), JsConfigDuplicateDetector, JsDuplicateGroup, JsLogErrorEntry, JsUnpackedIssues, Vec, scan_unpacked_files(), ConfigDuplicateDetector

### Community 50 - "Community 50"
Cohesion: 0.19
Nodes (13): geometry_dimension_to_core(), JsUserSettingsUpdateDiagnostic, JsUserSettingsUpdatePreview, preview_user_settings_bootstrap(), preview_user_settings_update(), scan_concurrency_to_core(), tui_integer_to_core(), user_settings_update_diagnostic_to_js() (+5 more)

### Community 51 - "Community 51"
Cohesion: 0.27
Nodes (11): JsUserSettingsMigrationEndpoint, JsUserSettingsMigrationPlan, migration_endpoint_to_js(), reverse_user_settings_migration_plan(), source_location_from_token(), source_location_token(), user_settings_migration_plan_from_js(), user_settings_migration_plan_to_js() (+3 more)

### Community 53 - "Community 53"
Cohesion: 0.29
Nodes (7): Env, Error, JsValue, Output, run_result_to_js(), scan_run_resume_error_to_napi(), RunResult

### Community 54 - "Community 54"
Cohesion: 0.20
Nodes (7): CliResult, DIST_CLI_PATH, PACKAGE_ROOT, replaceDocsPlaceholder(), replaceEvery(), tempDirs, writeWorkspaceDataRoot()

### Community 55 - "Community 55"
Cohesion: 0.22
Nodes (10): analyze_owned(), plugin(), preserves_shared_lookup_failure_error(), projects_resolved_unresolved_found_and_missing_findings(), AnalyzerError, Result, FormIdFindingAnalyzer, JsFormIdFindingAnalysisInput (+2 more)

### Community 56 - "Community 56"
Cohesion: 0.35
Nodes (7): game_role_to_js(), inspection_to_js(), JsInstalledYamlDataGameRole, JsInstalledYamlDataInspection, JsGameId, core_to_js_game_id(), GameDataRole

### Community 57 - "Community 57"
Cohesion: 0.22
Nodes (6): convert_integrity_result(), JsGameIntegrityChecker, JsIntegrityCheckResult, JsIntegrityConfig, CoreIntegrityCheckResult, GameIntegrityChecker

### Community 58 - "Community 58"
Cohesion: 0.24
Nodes (11): js_scan_config_to_core(), JsGameScanConfig, JsModScanResult, parse_game_target_for_scan(), Display, Error, GameTarget, run_game_checks() (+3 more)

### Community 61 - "Community 61"
Cohesion: 0.20
Nodes (10): InstalledYamlDataInspectionTaskOutput, InstalledYamlDataLoadTaskOutput, LocalIgnoreResetTaskOutput, Box, CoreInstalledYamlDataInspection, CoreInstalledYamlDataInspectionError, CoreInstalledYamlDataLoadError, CoreInstalledYamlDataLoadOutcome (+2 more)

### Community 62 - "Community 62"
Cohesion: 0.22
Nodes (10): JsUserSettingsMigrationChange, migration_change_kind_from_token(), migration_change_kind_token(), migration_change_to_js(), Error, user_settings_commit_error(), user_settings_migration_error(), Into (+2 more)

### Community 63 - "Community 63"
Cohesion: 0.20
Nodes (9): compilerOptions, noEmit, types, extends, include, bun-types, node, ../tsconfig.json (+1 more)

### Community 64 - "Community 64"
Cohesion: 0.20
Nodes (9): compilerOptions, noEmit, types, extends, include, bun-types, node, ../tsconfig.json (+1 more)

### Community 66 - "Community 66"
Cohesion: 0.28
Nodes (8): event_to_js(), JsScanRunLogEvent, log_event_to_js(), phase_to_string(), LogEvent, usize_to_u32(), Event, ScanProgressPhase

### Community 69 - "Community 69"
Cohesion: 0.32
Nodes (6): js_wrye_issue_to_core(), JsWryeBashParser, JsWryeIssue, wrye_issue_to_js(), WryeBashParser, WryeIssue

### Community 70 - "Community 70"
Cohesion: 0.25
Nodes (8): JsUserSettingsUpdateField, nullable_string_to_option(), HashMap, user_settings_update_field_to_js(), Either, Either5, Null, UserSettingsUpdateField

### Community 71 - "Community 71"
Cohesion: 0.46
Nodes (6): confidenceValues, crashgenStatusCases, dtsSignatureFragments, unknownVersionLogLevels, unknownVersionStrategies, yamlDisplayNameCases

### Community 77 - "Community 77"
Cohesion: 0.33
Nodes (6): activeTier1Owners, classic, createCliWorkspace(), replaceDocsPlaceholder(), require, runtimeCoverageRegistry

### Community 78 - "Community 78"
Cohesion: 0.29
Nodes (6): configuration, Execution, movement, setupContext, standardSource, targetedSource

### Community 82 - "Community 82"
Cohesion: 0.33
Nodes (5): conflicts, frequentCrashes, importantMods, populatedInput, solutions

### Community 92 - "Community 92"
Cohesion: 0.50
Nodes (3): analyzer(), owned_projection_returns_individual_semantic_findings(), CrashSuspectAnalyzer

### Community 93 - "Community 93"
Cohesion: 0.50
Nodes (4): check_xse_plugins(), JsXseChecker, parse_game_version(), GameVersion

### Community 107 - "Community 107"
Cohesion: 0.50
Nodes (3): mainErrorRules, populatedInput, stackRules

### Community 109 - "Community 109"
Cohesion: 0.50
Nodes (3): EMPTY_GAME_DIR, MOCK_GAME_DIR, TEST_DIR

## Knowledge Gaps
- **339 isolated node(s):** `PACKAGE_ROOT`, `DIST_CLI_PATH`, `tempDirs`, `CliResult`, `EXPLICIT_MAIN_YAML` (+334 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **50 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `spawn_result()` connect `Community 1` to `Community 4`, `Community 5`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Why does `game_setup_settings_to_js()` connect `Community 29` to `Community 56`, `Community 33`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Why does `core_to_js_game_id()` connect `Community 56` to `Community 29`, `Community 13`, `Community 15`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **What connects `PACKAGE_ROOT`, `DIST_CLI_PATH`, `tempDirs` to the rest of the system?**
  _339 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.008968609865470852 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.0707618187292984 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.059921710328214396 - nodes in this community are weakly interconnected._