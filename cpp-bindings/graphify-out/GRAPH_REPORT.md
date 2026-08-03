# Graph Report - D:\repos\CLASSIC-Fallout4\cpp-bindings  (2026-07-28)

## Corpus Check
- 49 files · ~56,202 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1522 nodes · 3809 edges · 63 communities (60 shown, 3 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 532 edges (avg confidence: 0.8)
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
- Community 61

## God Nodes (most connected - your core abstractions)
1. `YamlData` - 47 edges
2. `yaml_ops_new()` - 25 edges
3. `AnalyzerErrorDto` - 24 edges
4. `markdown_to_html()` - 20 edges
5. `YamlOps` - 20 edges
6. `block_on_result()` - 19 edges
7. `BridgeAnalyzerError` - 19 edges
8. `yaml_ops_parse()` - 17 edges
9. `YamlDataContentIdentityDto` - 16 edges
10. `block_on()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `test_settings_validate_value_unknown_type_errors()` --calls--> `settings_validate_value()`  [INFERRED]
  classic-cpp-bridge/src/settings_tests.rs → classic-cpp-bridge/src/settings.rs
- `test_xse_get_info_nonexistent_returns_not_installed()` --calls--> `xse_get_info()`  [INFERRED]
  classic-cpp-bridge/src/xse_tests.rs → classic-cpp-bridge/src/xse.rs
- `fallout4_vr_loads_the_shared_fallout4_yaml_through_the_bridge()` --calls--> `yaml_data_load()`  [INFERRED]
  classic-cpp-bridge/src/config_tests.rs → classic-cpp-bridge/src/config.rs
- `test_yaml_data_accessors_fallback_when_game_info_is_minimal()` --calls--> `yaml_data_load()`  [INFERRED]
  classic-cpp-bridge/src/config_tests.rs → classic-cpp-bridge/src/config.rs
- `test_yaml_data_load_from_real_dirs()` --calls--> `yaml_data_load()`  [INFERRED]
  classic-cpp-bridge/src/config_tests.rs → classic-cpp-bridge/src/config.rs

## Import Cycles
- None detected.

## Communities (63 total, 3 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (72): AppNotificationDisplay, ApprovedUpdate, AsRef, approved_update_from_dto(), ApprovedUpdateDto, build_client_schema_set(), build_yaml_config(), check_app_notification() (+64 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (68): Arc, db_pool_cache_size(), db_pool_clear_cache(), db_pool_close(), db_pool_game_table(), db_pool_get_entries_batch(), db_pool_get_entries_batch_typed(), db_pool_get_entry() (+60 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (62): CacheStats, empty_installed_yaml_data_inspection_error(), empty_installed_yaml_data_load_error(), explicit_yaml_data_snapshot_game_role(), ExplicitYamlDataGameRole, installed_yaml_data_diagnostic_kind_to_ffi(), installed_yaml_data_diagnostic_to_dto(), installed_yaml_data_inspection_error_to_dto() (+54 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (57): from_bridge_yaml_file(), LegacyTuiStateImportRestoreOutcomeDto, migration_change_kind_from_token(), migration_change_kind_token(), parse_setting_type_token(), Result, String, settings_cache_keys() (+49 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (56): BackupManager, BackupType, backup_manager_create(), backup_manager_exists(), backup_manager_new(), backup_manager_remove(), backup_manager_restore(), backup_type_from_str() (+48 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (38): check_restricted_path(), validate_path(), backup_create_timestamped(), backup_list_existing(), detect_fallout4_docs_path(), detect_fallout4_game_path(), docs_checker_run_all_checks(), docs_checker_validate_ini_file() (+30 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (53): discovery_to_dto(), empty_discovery_dto(), empty_execution_result_dto(), empty_infrastructure_error_dto(), empty_inspected_yaml_data_file_dto(), empty_installed_yaml_data_dto(), empty_local_ignore_reset_run_data_dto(), empty_resume_error_dto() (+45 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (48): empty_mod_guidance_configuration(), AutoscanReportPlacement, CrashgenConfigLayout, CrashgenExpectationOutcomeDto, CrashgenExpectationOutcomeKind, CrashgenExpectationSeverity, CrashgenSettingDto, CrashgenSettingsAnalysisExecutionResultDto (+40 more)

### Community 8 - "Community 8"
Cohesion: 0.10
Nodes (39): settings_clear_cache(), settings_load_sync(), settings_reset_cache_stats(), make_settings_yaml(), test_cache_management(), test_dump_no_document_error(), test_get_setting_value_missing(), test_get_setting_value_types() (+31 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (32): CrashgenConfigDto, fallout4_version_as_str(), fallout4_version_docs_folder_name(), fallout4_version_exe_name(), fallout4_version_is_standard(), fallout4_version_is_vr(), fallout4_version_registry_id(), fallout4_version_steam_app_id() (+24 more)

### Community 10 - "Community 10"
Cohesion: 0.13
Nodes (40): installed_yaml_data_snapshot_simplify_remove_list(), ModSolutionEntry, String, Vec, SuspectErrorRuleDto, SuspectStackRuleMetadataDto, test_yaml_data_load_from_real_dirs(), yaml_data_classic_game_hints() (+32 more)

### Community 11 - "Community 11"
Cohesion: 0.10
Nodes (38): BTreeMap, commit_eligibility_token(), CrashLogScanSettingsDto, document_classification_token(), empty_migration_planning_outcome(), flatten_formid_databases(), frontend_window_geometry_dto(), FrontendStateDto (+30 more)

### Community 12 - "Community 12"
Cohesion: 0.10
Nodes (31): extract_domain_string(), from_bridge_mod_site(), from_bridge_web_game_id(), mod_site_base_url(), mod_site_game_url(), mod_site_name(), ModSite, CoreGameId (+23 more)

### Community 13 - "Community 13"
Cohesion: 0.14
Nodes (37): installed_yaml_data_load(), installed_yaml_data_load_error_to_dto(), installed_yaml_data_load_operation_from_result(), installed_yaml_data_load_status(), installed_yaml_data_load_take_recovery_plan(), installed_yaml_data_load_take_snapshot(), installed_yaml_data_snapshot_game_file(), installed_yaml_data_snapshot_local_ignore_identity() (+29 more)

### Community 14 - "Community 14"
Cohesion: 0.10
Nodes (19): Self, String, Vec, string_map_contains(), string_map_get(), string_map_is_empty(), string_map_keys(), string_map_len() (+11 more)

### Community 15 - "Community 15"
Cohesion: 0.16
Nodes (35): configuration_to_core(), map_local_ignore_recovery_decision(), optional_flagged_path(), required_path(), Box, Result, String, scan_run_continuation_resume() (+27 more)

### Community 16 - "Community 16"
Cohesion: 0.10
Nodes (33): empty_user_settings_migration_receipt_dto(), revision_from_token(), revision_token(), Option, source_location_token(), install_user_settings_fixture(), Path, PathBuf (+25 more)

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (30): markdown_to_html(), normalize_markdown(), normalize_report_content(), String, test_html_blockquote(), test_html_bold(), test_html_bullet_list(), test_html_code_block() (+22 more)

### Community 18 - "Community 18"
Cohesion: 0.16
Nodes (28): Cancellation, scan_run_cancellation_cancel(), scan_run_cancellation_is_cancelled(), scan_run_cancellation_new(), scan_run_contract_execute(), scan_run_contract_execution_take_result(), scan_run_unsolved_logs_leave_in_place(), ScanRunCancellation (+20 more)

### Community 19 - "Community 19"
Cohesion: 0.15
Nodes (30): commit_user_settings_update(), core_user_settings_update(), FormIdDatabasePathDto, invalid_gui_window_diagnostic(), empty_user_settings_update(), test_user_settings_bootstrap_preview_commits_only_through_explicit_bootstrap_seam(), test_user_settings_bootstrap_preview_is_explicit_and_does_not_write(), test_user_settings_commit_update_requires_the_accepted_base_revision() (+22 more)

### Community 20 - "Community 20"
Cohesion: 0.16
Nodes (27): build_analyzer(), crashgen_settings_analyze(), crashgen_settings_analyzer_construction_result(), crashgen_settings_analyzer_new(), CxxCrashgenSettingsAnalyzer, input_to_core(), result_to_dto(), analysis_projects_typed_outcomes_placement_optional_values_and_notices() (+19 more)

### Community 21 - "Community 21"
Cohesion: 0.12
Nodes (19): registry_clear_all(), registry_get_game(), registry_get_string(), registry_key_game(), registry_key_is_gui_mode(), registry_set_bool(), registry_set_game(), registry_set_i32() (+11 more)

### Community 22 - "Community 22"
Cohesion: 0.13
Nodes (25): BridgeAnalyzerError, build_mod_guidance_analyzer(), crash_suspect_analyzer_new(), CxxCrashSuspectAnalyzer, CxxFormIDFindingAnalyzer, CxxModGuidanceAnalyzer, formid_finding_analyzer_disabled_new(), formid_finding_analyzer_in_memory_new() (+17 more)

### Community 23 - "Community 23"
Cohesion: 0.12
Nodes (26): content_identity_to_dto(), empty_content_identity(), empty_local_ignore_reset_error(), explicit_yaml_data_snapshot_game_identity(), explicit_yaml_data_snapshot_ignore_identity(), explicit_yaml_data_snapshot_main_identity(), ExplicitYamlDataSnapshot, local_ignore_reset_conflict_expected_identity() (+18 more)

### Community 24 - "Community 24"
Cohesion: 0.12
Nodes (23): CrashgenConfigDto, detect_xse_version_string(), extract_pe_version_string(), find_game_path(), GameVersionDto, is_xse_installed_check(), MatchResultDto, CrashgenConfigDto (+15 more)

### Community 25 - "Community 25"
Cohesion: 0.18
Nodes (23): CxxPapyrusAnalyzer, papyrus_analyze_full(), papyrus_analyzer_new(), papyrus_check_updates(), papyrus_log_exists(), papyrus_reset(), papyrus_start_monitoring(), papyrus_stats_to_dto() (+15 more)

### Community 26 - "Community 26"
Cohesion: 0.14
Nodes (23): analysis_error_result(), analyzer_kind_to_dto(), bridge_error_to_dto(), crash_suspect_analyzer_construction_result(), empty_error_dto(), formid_finding_analyze(), formid_finding_analyzer_construction_result(), formid_finding_error_result() (+15 more)

### Community 27 - "Community 27"
Cohesion: 0.15
Nodes (20): save_local_yaml_paths(), SuspectStackCountRuleDto, fallout4_vr_loads_the_shared_fallout4_yaml_through_the_bridge(), make_yaml_data_with_suspect_rules(), Box, Option, test_save_local_yaml_paths_creates_file(), test_save_local_yaml_paths_preserves_empty_adapter_field() (+12 more)

### Community 28 - "Community 28"
Cohesion: 0.12
Nodes (11): enb_checker_validate(), integrity_run_all_checks(), Path, test_enb_checker_validate_empty_dir_real_variants(), test_enb_checker_validate_partial_real_variant(), test_enb_checker_validate_present_no_config(), test_enb_checker_validate_present_real_variants(), test_integrity_run_all_checks_empty_path_returns_empty() (+3 more)

### Community 29 - "Community 29"
Cohesion: 0.16
Nodes (20): inspected_yaml_data_file_to_dto(), InspectedYamlDataFileDto, installed_yaml_data_inspection_diagnostics(), installed_yaml_data_inspection_game_file(), installed_yaml_data_inspection_main(), installed_yaml_data_inspection_take(), installed_yaml_data_provenance_to_ffi(), installed_yaml_data_snapshot_main() (+12 more)

### Community 30 - "Community 30"
Cohesion: 0.17
Nodes (18): init_logging(), log_debug(), log_error(), log_info(), log_startup_acceleration_status(), log_startup_binding_contract_failed(), log_startup_binding_contract_validated(), log_trace() (+10 more)

### Community 31 - "Community 31"
Cohesion: 0.24
Nodes (19): detect_xse_version(), detect_xse_version_string(), detect_xse_version_string_impl(), from_bridge_xse_type(), game_id_from_str(), is_xse_installed(), is_xse_installed_check(), is_xse_installed_check_impl() (+11 more)

### Community 32 - "Community 32"
Cohesion: 0.15
Nodes (19): empty_explicit_yaml_data_error(), explicit_yaml_data_error_to_dto(), explicit_yaml_data_load(), explicit_yaml_data_load_status(), explicit_yaml_data_load_take_snapshot(), explicit_yaml_data_role_to_ffi(), explicit_yaml_data_snapshot_yaml_data(), ExplicitYamlDataLoad (+11 more)

### Community 34 - "Community 34"
Cohesion: 0.15
Nodes (18): flatten_optional(), important_mod_guidance_to_dto(), mod_conflict_guidance_to_dto(), mod_guidance_match_state_to_dto(), mod_guidance_result_to_dto(), mod_solution_guidance_to_dto(), outcome_to_dto(), Option (+10 more)

### Community 35 - "Community 35"
Cohesion: 0.17
Nodes (15): CxxObserverAdapter, empty_event_dto(), event_to_dto(), log_event_to_dto(), map_log_disposition(), map_phase(), event_mapping_covers_discovery_concurrency_and_every_log_variant(), ScanRunContractEventKind (+7 more)

### Community 36 - "Community 36"
Cohesion: 0.16
Nodes (16): log_result_to_dto(), map_log_failure_stage(), optional_path_to_dto(), optional_string_to_dto(), path_to_string(), Option, PathBuf, scan_run_contract_execution_has_continuation() (+8 more)

### Community 37 - "Community 37"
Cohesion: 0.20
Nodes (14): ba2_scan_archive_summary(), Ba2IssuesSummaryDto, CheckType, EnbConfigResult, EnbResult, EnbValidationResultDto, IntegrityCheckResultDto, map_check_type() (+6 more)

### Community 38 - "Community 38"
Cohesion: 0.19
Nodes (15): CxxPluginEvidenceAnalyzer, plugin_evidence_analyze(), plugin_evidence_analyzer_construction_result(), plugin_evidence_analyzer_new(), plugin_evidence_error_result(), plugin_evidence_result_to_dto(), plugin_evidence_handle_is_safe_for_concurrent_owned_calls(), plugin_evidence_invalid_configuration_uses_the_shared_typed_error_envelope() (+7 more)

### Community 40 - "Community 40"
Cohesion: 0.27
Nodes (14): explicit_game_id_to_core(), explicit_game_id_to_ffi(), explicit_yaml_data_snapshot_game(), ExplicitYamlDataGameId, installed_yaml_data_inspect(), installed_yaml_data_inspection_game(), installed_yaml_data_inspection_operation_from_result(), installed_yaml_data_snapshot_game() (+6 more)

### Community 41 - "Community 41"
Cohesion: 0.25
Nodes (11): perf_clear_metrics(), perf_get_operation_average(), perf_get_summary(), perf_record_timing(), String, Vec, test_clear_metrics(), test_missing_operation() (+3 more)

### Community 42 - "Community 42"
Cohesion: 0.20
Nodes (14): CxxNamedRecordFindingAnalyzer, named_record_finding_analyze(), named_record_finding_analyzer_construction_result(), named_record_finding_analyzer_new(), named_record_finding_error_result(), named_record_finding_result_to_dto(), named_record_finding_invalid_configuration_uses_shared_typed_error_envelope(), named_record_finding_projects_owned_typed_counts_and_explicit_empty_success() (+6 more)

### Community 43 - "Community 43"
Cohesion: 0.29
Nodes (13): BA2Issues, ba2_get_snd_frmt_for_archive(), ba2_get_tex_dims_for_archive(), ba2_get_tex_frmt_for_archive(), ba2_get_xse_files_for_archive(), crashgen_checker_get_issues(), GameSetupIntakeDto, GameSetupPathUpdateDto (+5 more)

### Community 44 - "Community 44"
Cohesion: 0.21
Nodes (13): inspected_yaml_data_file_to_dto(), installed_yaml_data_diagnostic_to_dto(), map_installed_yaml_data_diagnostic_kind(), map_installed_yaml_data_provenance(), map_installed_yaml_data_role(), ScanRunInspectedYamlDataFileDto, ScanRunInstalledYamlDataDiagnosticDto, ScanRunInstalledYamlDataDiagnosticKind (+5 more)

### Community 45 - "Community 45"
Cohesion: 0.30
Nodes (12): mod_guidance_analyze(), mod_guidance_analyzer_new(), mod_guidance_error_result(), completed_mod_guidance_no_match_is_an_explicit_empty_result(), matching_mod_guidance_input(), mod_guidance_analysis_projects_all_families_and_optional_presence(), mod_guidance_invalid_configuration_preserves_shared_typed_error(), mod_guidance_projects_important_mod_plugin_exclusions() (+4 more)

### Community 46 - "Community 46"
Cohesion: 0.22
Nodes (11): crash_suspect_analyze(), crash_suspect_error_result(), crash_suspect_finding_to_dto(), crash_suspect_result_to_dto(), CrashSuspectAnalysisExecutionResultDto, CrashSuspectAnalysisInputDto, CrashSuspectAnalysisResultDto, CrashSuspectFindingDto (+3 more)

### Community 47 - "Community 47"
Cohesion: 0.24
Nodes (5): detect_crash_pattern(), String, test_detect_crash_pattern_empty(), test_detect_crash_pattern_positive_fixture_excerpt(), test_detect_crash_pattern_repeated_calls_keep_same_positive_result()

### Community 48 - "Community 48"
Cohesion: 0.33
Nodes (6): init_runtime(), shutdown_runtime(), test_block_on_works(), test_init_runtime_idempotent(), test_runtime_is_active(), test_shutdown_is_noop()

### Community 49 - "Community 49"
Cohesion: 0.31
Nodes (9): legacy_tui_state_import_outcome_dto(), LegacyTuiStateImportHandle, LegacyTuiStateImportOutcomeDto, Box, test_legacy_tui_state_import_maps_every_non_applied_outcome(), test_legacy_tui_state_import_reports_verified_receipt_and_coded_errors(), user_settings_import_legacy_tui_state(), user_settings_legacy_tui_import_outcome() (+1 more)

### Community 50 - "Community 50"
Cohesion: 0.29
Nodes (8): convert_ini_issue(), ini_validator_detect_all_issues_for_root(), IniConfigIssueDto, IssueSeverity, map_ini_severity(), test_ini_validator_detect_all_issues_nonexistent_dir_returns_empty(), CoreIniConfigIssue, CoreIniIssueSeverity

### Community 51 - "Community 51"
Cohesion: 0.33
Nodes (7): convert_toml_issue(), crashgen_orchestrator_get_issues(), map_toml_severity(), TomlConfigIssueDto, TomlIssueSeverity, CoreTomlConfigIssue, CoreTomlIssueSeverity

### Community 52 - "Community 52"
Cohesion: 0.29
Nodes (7): crashgen_orchestrator_check_summary(), crashgen_orchestrator_get_installed_plugins(), CrashgenReportSummaryDto, run_crashgen_orchestrator(), test_crashgen_orchestrator_check_summary_empty_path_returns_empty_dto(), test_crashgen_orchestrator_check_summary_nonexistent_real_fields(), CoreCrashgenReport

### Community 53 - "Community 53"
Cohesion: 0.40
Nodes (6): map_wrye_severity(), test_wrye_parse_html_rows_one_issue_two_plugins_produces_two_rows(), wrye_parse_html_rows(), WryeIssueRowDto, WryeSeverity, CoreWryeSeverity

### Community 54 - "Community 54"
Cohesion: 0.53
Nodes (5): from_bridge_game_id(), game_id_as_str(), GameId, CoreGameId, String

### Community 55 - "Community 55"
Cohesion: 0.40
Nodes (3): ScanRunContractEvent, ScanRunObserver, on_scan_run_event

### Community 56 - "Community 56"
Cohesion: 0.50
Nodes (4): crashgen_checker_check(), CrashgenCheckResultDto, test_crashgen_checker_check_empty_path_returns_empty_dto(), test_crashgen_checker_check_nonexistent_returns_zero_issues()

### Community 57 - "Community 57"
Cohesion: 0.50
Nodes (4): game_setup_result_to_dto(), run_game_setup_intake_from_user_settings(), test_run_game_setup_intake_from_user_settings_uses_typed_paths_without_writing(), GameSetupIntakeResult

### Community 58 - "Community 58"
Cohesion: 0.67
Nodes (3): ini_validator_validate_inis(), Result, test_ini_validator_validate_inis_nonexistent_dir()

## Knowledge Gaps
- **6 isolated node(s):** `ScanRunContractEvent`, `on_scan_run_event`, `CacheStats`, `CacheStats`, `GameVersionDto` (+1 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `GameId` connect `Community 54` to `Community 31`, `Community 6`, `Community 15`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Why does `Fallout4Version` connect `Community 9` to `Community 5`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Why does `block_on()` connect `Community 1` to `Community 4`, `Community 15`, `Community 18`, `Community 22`, `Community 26`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **What connects `ScanRunContractEvent`, `on_scan_run_event`, `CacheStats` to the rest of the system?**
  _6 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.05209274314965372 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.0782608695652174 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.051715309779825906 - nodes in this community are weakly interconnected._