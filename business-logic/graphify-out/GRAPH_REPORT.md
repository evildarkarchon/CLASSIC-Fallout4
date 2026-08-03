# Graph Report - D:\repos\CLASSIC-Fallout4\business-logic  (2026-07-28)

## Corpus Check
- 304 files · ~322,098 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 6176 nodes · 15223 edges · 243 communities (237 shown, 6 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 843 edges (avg confidence: 0.8)
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
- Community 78
- Community 79
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
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 139
- Community 140
- Community 141
- Community 142
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148
- Community 149
- Community 150
- Community 151
- Community 152
- Community 153
- Community 154
- Community 155
- Community 156
- Community 158
- Community 159
- Community 160
- Community 161
- Community 162
- Community 163
- Community 164
- Community 165
- Community 166
- Community 167
- Community 168
- Community 169
- Community 171
- Community 172
- Community 173
- Community 174
- Community 175
- Community 177
- Community 179
- Community 180
- Community 181
- Community 182
- Community 183
- Community 184
- Community 185
- Community 186
- Community 187
- Community 188
- Community 189
- Community 190
- Community 191
- Community 192
- Community 193
- Community 194
- Community 195
- Community 196
- Community 197
- Community 198
- Community 199
- Community 200
- Community 201
- Community 202
- Community 205
- Community 207
- Community 220
- Community 223
- Community 224
- Community 226
- Community 228
- Community 229
- Community 230
- Community 233
- Community 235

## God Nodes (most connected - your core abstractions)
1. `DatabasePool` - 70 edges
2. `OrchestratorCore` - 61 edges
3. `clear_global_yaml_cache()` - 59 edges
4. `FileIOError` - 57 edges
5. `VersionInfo` - 57 edges
6. `PreferenceOrigin` - 47 edges
7. `GithubClient` - 46 edges
8. `FileIOCore` - 43 edges
9. `LogParser` - 41 edges
10. `VersionRegistry` - 41 edges

## Surprising Connections (you probably didn't know these)
- `parse_yaml_document()` --calls--> `parse_yaml_content()`  [INFERRED]
  classic-config-core/src/crashgen_registry_yaml_tests.rs → classic-settings-core/src/loader.rs
- `parse_yaml_document()` --calls--> `merge_yaml_documents()`  [INFERRED]
  classic-config-core/src/crashgen_registry_yaml_tests.rs → classic-settings-core/src/merge/documents.rs
- `validate_shippable_role()` --calls--> `schema_compat_check()`  [INFERRED]
  classic-config-core/src/explicit_yaml_data.rs → classic-settings-core/src/schema_version/compat.rs
- `validate_shippable_role()` --calls--> `extract_schema_version()`  [INFERRED]
  classic-config-core/src/explicit_yaml_data.rs → classic-settings-core/src/schema_version/extract.rs
- `persist_game_local_paths()` --calls--> `load_yaml_merged_async()`  [INFERRED]
  classic-config-core/src/game_local.rs → classic-settings-core/src/loader.rs

## Import Cycles
- 2-file cycle: `classic-version-registry-core/src/matching.rs -> classic-version-registry-core/src/registry.rs -> classic-version-registry-core/src/matching.rs`
- 2-file cycle: `classic-user-settings-core/src/document.rs -> classic-user-settings-core/src/scan_settings.rs -> classic-user-settings-core/src/document.rs`
- 3-file cycle: `classic-user-settings-core/src/document.rs -> classic-user-settings-core/src/scan_settings.rs -> classic-user-settings-core/src/preference.rs -> classic-user-settings-core/src/document.rs`

## Communities (243 total, 6 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (91): canonical_game_data_name(), ConfigError, CoreModEntry, CoreModExclude, CrashgenEntryRaw, format_registry_game_version(), get_crashgen_registry_entry(), main_root_matches_registry_info() (+83 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (56): Cancellation, CrashLogScanRunContinuation, emit(), Event, execute(), execute_inner(), execute_with_test_hooks(), InfrastructureError (+48 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (71): ExplicitYamlDataLoadError, ExplicitYamlDataRequest, ExplicitYamlDataRole, ExplicitYamlDataSnapshot, game_data_key(), game_data_role(), game_validation_error(), GameDataRole (+63 more)

### Community 3 - "Community 3"
Cohesion: 0.09
Nodes (63): ScanProgressPhase, cancellation_requested(), cancelled_log_outcome(), claim_available_destination(), cleanup_incomplete_destination(), configuration_issue_scan_root(), F, CrashLogScanDiscoveryResult (+55 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (54): CrashLogScanFacts, CrashLogScanIntake, CrashLogScanIntake<'a>, CrashLogScanIntakePaths, CrashLogScanOptions, FormIdReadiness, load_simplify_remove_list(), resolve_formid_database_paths() (+46 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (68): Vec, shippable_schema_entries(), ShippableSchemaEntry, CandidateRejection, load_shippable_with_cache_path(), load_shippable_yaml(), load_shippable_yaml_with_env(), LoadedShippable (+60 more)

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (63): adaptive_low_volume_run_selects_and_retains_one_worker(), admitted_analysis_failure_does_not_abort_other_admitted_log(), admitted_standard_log_finishes_report_failure_and_movement_after_cancellation(), assert_isolated_fcx_run(), cancellation_before_recovery_resume_returns_normal_cancelled_after_discovery_result(), cancellation_before_reset_to_default_performs_no_durable_or_analysis_work(), cancellation_control_is_opaque_cloneable_and_separate_from_the_request(), cancellation_racing_after_reset_begins_returns_cancelled_after_durable_reset() (+55 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (66): BackupError, DocsPathError, GamePathError, PathError, Error, PathBuf, String, ValidationError (+58 more)

### Community 8 - "Community 8"
Cohesion: 0.06
Nodes (45): check_drive_exists(), check_read_permissions(), check_write_permissions(), drive_exists(), has_read_permission(), has_write_permission(), is_restricted_path(), is_valid_executable_path() (+37 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (71): apply_yaml_update_with_decision(), classify_manifest(), fetch_yaml_manifest(), classify_detects_same_schema_content_churn_as_update_available(), classify_treats_matching_sha_as_up_to_date_even_when_schema_bumped(), local_ignore_remains_unclassifiable_even_when_a_generic_caller_registers_it(), validate_manifest_rejects_case_only_duplicate_file_names(), validate_manifest() (+63 more)

### Community 10 - "Community 10"
Cohesion: 0.12
Nodes (21): append_mod_found_entry(), AutoscanReportAssembler, AutoscanReportFacts, crash_suspect_kind_rank(), crash_suspect_rule_order(), disabled_setting_notice_lines(), ModGuidanceGroup, parse_plugin_id_for_sort() (+13 more)

### Community 11 - "Community 11"
Cohesion: 0.07
Nodes (37): merge_keys(), merge_keys_recursive(), Result, Yaml, test_merge_keys_in_array(), test_merge_keys_invalid_value(), test_merge_keys_multiple_mappings(), test_merge_keys_nested() (+29 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (30): YamlDataContentIdentity, build_installed_yaml_data_snapshot(), CandidateAttempt, explicit_validation_reason(), inspect_installed_yaml_data(), InspectedYamlDataFile, InstalledYamlDataInspection, InstalledYamlDataInspectionRequest (+22 more)

### Community 13 - "Community 13"
Cohesion: 0.09
Nodes (21): AcceptedUserSettingsUpdate, GuiWindow, PendingTuiRememberedState, PendingWindowGeometry, BTreeMap, GameId, Into, Option (+13 more)

### Community 14 - "Community 14"
Cohesion: 0.10
Nodes (20): compile_static_regex(), LogParser, Arc, DashMap, HashMap, I, Item, Iterator (+12 more)

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (46): configured_game_exe_for_root(), detect_registry_info_from_exe(), docs_relative_path(), documents_game_name(), game_id_for_selected_version(), game_id_for_version_info(), game_setup_needs_path_detection(), GameSetupCheck (+38 more)

### Community 16 - "Community 16"
Cohesion: 0.10
Nodes (34): canonical_flat_value(), canonicalize_key_alias(), canonicalize_scalar_alias(), get_path(), merge_unrecognized_root(), migrate_flat_document(), migrate_nested_document(), MigrationChange (+26 more)

### Community 17 - "Community 17"
Cohesion: 0.08
Nodes (46): main(), Keys, test_convenience_functions(), test_get_nonexistent(), test_is_registered(), test_register_and_get(), test_thread_safety(), clear_all() (+38 more)

### Community 18 - "Community 18"
Cohesion: 0.11
Nodes (53): cache_keys(), cache_stats(), CacheStats, clear_cache(), get_cached(), invalidate(), is_cached(), load_batch_async() (+45 more)

### Community 19 - "Community 19"
Cohesion: 0.05
Nodes (26): create_test_database(), NamedTempFile, PathBuf, Result, test_batch_formid_query(), test_batch_query_adaptive_sizing(), test_batch_query_case_insensitive_plugin(), test_batch_query_mixed_hit_miss_preserves_output_keys() (+18 more)

### Community 21 - "Community 21"
Cohesion: 0.06
Nodes (28): build_url_with_query(), extract_domain(), get_user_agent(), get_user_agent_with_suffix(), is_valid_url(), join_url(), ModSite, GameId (+20 more)

### Community 22 - "Community 22"
Cohesion: 0.08
Nodes (32): clean_path_value(), detect_xse_version(), discover_xse_folder(), docs_relative_path(), get_xse_info(), is_xse_installed(), non_empty_path(), resolve_version_info() (+24 more)

### Community 23 - "Community 23"
Cohesion: 0.12
Nodes (42): fallout4_vr_loads_the_shared_fallout4_file_and_keyed_data(), minimal_game_yaml(), minimal_game_yaml_main_root_only(), minimal_game_yaml_main_root_only_compact(), minimal_ignore_yaml(), minimal_main_yaml(), test_accessor_methods(), test_from_yaml_content_auto_game_version_uses_game_info_values() (+34 more)

### Community 24 - "Community 24"
Cohesion: 0.14
Nodes (47): inspect_installed_yaml_data_with_env(), load_installed_yaml_data_with_env(), authoritative_reread_failure_returns_error_after_complete_publication(), bundled_dir(), cache_dir(), concurrent_generation_preserves_one_winner_and_every_loader_rereads_it(), deleting_local_ignore_regenerates_it_from_the_new_selected_snapshot(), fallout4_vr_maps_to_fallout4_and_unsupported_games_fail_before_file_io() (+39 more)

### Community 25 - "Community 25"
Cohesion: 0.10
Nodes (25): LogCollector, matches_crash_log_pattern(), RejectedInput, resolve_targeted_inputs(), resolve_targeted_inputs_until_cancelled(), AsRef, Option, Path (+17 more)

### Community 26 - "Community 26"
Cohesion: 0.10
Nodes (21): DocumentsChecker, DocumentsCheckResult, DocumentsCheckState, IniCheckResult, DocsPathResult, From, Into, Option (+13 more)

### Community 27 - "Community 27"
Cohesion: 0.11
Nodes (34): apply_template(), AutoscanReportPlacement, CheckRule, ConfigLayout, CrashgenSettingRef, CrashgenSettingsSnapshot, evaluate_predicate(), EvaluationContext (+26 more)

### Community 28 - "Community 28"
Cohesion: 0.10
Nodes (20): CommitEligibility, DocumentClassification, invalid_nested_group(), is_legacy_flat_document(), is_recognized_nested_document(), AsRef, Error, Into (+12 more)

### Community 29 - "Community 29"
Cohesion: 0.11
Nodes (23): get_default_unknown_handling(), get_default_versions(), HashMap, String, AddressLibFormat, AddressLibraryConfig, CompatibleRange, CrashgenConfig (+15 more)

### Community 30 - "Community 30"
Cohesion: 0.13
Nodes (19): BufReader, FileIOCore, FileMetadata, Arc, AsRef, DashMap, Default, File (+11 more)

### Community 31 - "Community 31"
Cohesion: 0.11
Nodes (26): CrashgenCheckOrchestrator, CrashgenOrchestratorError, CrashgenReport, Error, Option, Path, PathBuf, Result (+18 more)

### Community 33 - "Community 33"
Cohesion: 0.11
Nodes (29): Revision, backup_path(), content_revision(), hex_digest(), import_with_publisher(), legacy_source_conflict(), LegacyTuiState, LegacyTuiStateImportError (+21 more)

### Community 34 - "Community 34"
Cohesion: 0.09
Nodes (24): BuildError, Error, String, ScanLogError, load_installed_yaml_data_for_run(), InfrastructureFault, InjectedInfrastructureFailure, InjectedMovementFailure (+16 more)

### Community 35 - "Community 35"
Cohesion: 0.09
Nodes (31): build_analysis_config_from_yaml(), build_crashgen_registry(), addictol_version_newer_than_ae_registry_floor(), build_analysis_config_does_not_double_prefix_classic_version(), build_analysis_config_resolves_identical_metadata_for_spaced_and_compact_names(), build_analysis_config_resolves_registry_metadata_for_spaced_game_and_root_name(), build_analysis_config_uses_registry_metadata_when_yaml_game_info_is_missing(), build_orchestrator_with_structured_mods_solu() (+23 more)

### Community 36 - "Community 36"
Cohesion: 0.12
Nodes (23): FormIdValueLookup, FormIdValueLookupAdapter, FormIdValueLookupEntry, FormIdValueLookupError, FormIdValueLookupErrorKind, FormIdValueLookupInMemoryReply, FormIdValueLookupOutcome, lookup_database() (+15 more)

### Community 37 - "Community 37"
Cohesion: 0.11
Nodes (30): main(), test_clear_metrics(), test_multiple_timings(), test_summary_statistics(), test_thread_safety(), test_timer_basic(), test_timer_drop_records(), clear_metrics() (+22 more)

### Community 38 - "Community 38"
Cohesion: 0.10
Nodes (34): CachedYaml, clear_global_yaml_cache(), reset_yaml_cache_stats(), Arc, Option, String, SystemTime, Yaml (+26 more)

### Community 39 - "Community 39"
Cohesion: 0.06
Nodes (19): approved_file_sha_map(), check_client_schema_bounds(), HashMap, approved_file_sha_map_accepts_uppercase_hex(), approved_file_sha_map_accepts_valid(), approved_file_sha_map_rejects_duplicate_names(), approved_file_sha_map_rejects_invalid_digest(), approved_file_sha_map_rejects_mismatched_lengths() (+11 more)

### Community 40 - "Community 40"
Cohesion: 0.12
Nodes (29): AcceptedUserSettingsUpdate, acquire_commit_lock(), cleanup_failed_publication(), commit_frontend_transition_attempt(), field_yaml_value(), latest_document(), patch_accepted_fields(), PublicationStage (+21 more)

### Community 41 - "Community 41"
Cohesion: 0.16
Nodes (29): acquire_local_ignore_reset_lock(), create_local_ignore_backup_directory(), load_installed_yaml_data_with_env_and_io(), LocalIgnoreResetDurabilityReceipt, LocalIgnoreResetError, LocalIgnoreResetOutcome, LocalIgnoreResetPublicationKind, LocalIgnoreResetPublicationStage (+21 more)

### Community 42 - "Community 42"
Cohesion: 0.17
Nodes (40): env_map(), main_yaml_version_accepts_single_digit_zero_components(), main_yaml_version_cache_empty_version_falls_back_to_bundled(), main_yaml_version_cache_incompatible_bundled_wins(), main_yaml_version_cache_invalid_shape_falls_back_to_bundled(), main_yaml_version_cache_missing_section_falls_back_to_bundled(), main_yaml_version_cache_nonstring_version_falls_back_to_bundled(), main_yaml_version_cache_structural_with_bundled_missing_surfaces_error() (+32 more)

### Community 43 - "Community 43"
Cohesion: 0.15
Nodes (39): acquire_install_lock(), fsync_directory(), install_atomic(), InstallOutcome, paths_refer_to_same_directory(), prev_path_for(), rollback(), RollbackOutcome (+31 more)

### Community 44 - "Community 44"
Cohesion: 0.11
Nodes (24): CachedConfigFile, compute_file_hash(), ConfigCacheError, ConfigFileCache, decode_with_detection(), read_toml_value(), ConfigIssue, Error (+16 more)

### Community 45 - "Community 45"
Cohesion: 0.08
Nodes (6): PreferenceOrigin, FrontendPreferences, FrontendState, Self, TuiRememberedState, CrashLogScanSettings

### Community 46 - "Community 46"
Cohesion: 0.14
Nodes (26): Publisher, backup_path(), concat_code(), content_revision(), hex_digest(), map_lock_error(), map_publication_error(), path_for_location() (+18 more)

### Community 47 - "Community 47"
Cohesion: 0.12
Nodes (14): String, VersionRegistryError, VersionMatcher, GameVersion, HashMap, Option, Path, Result (+6 more)

### Community 48 - "Community 48"
Cohesion: 0.11
Nodes (12): AnalysisConfig, OrchestratorCore, parse_crashgen_settings_snapshot(), resolve_batch_concurrency(), Arc, IndexMap, Option, Path (+4 more)

### Community 49 - "Community 49"
Cohesion: 0.09
Nodes (24): Compatibility, Self, schema_compat_check(), SchemaCompat, Display, Err, Formatter, FromStr (+16 more)

### Community 50 - "Community 50"
Cohesion: 0.10
Nodes (25): classic_main_yaml_path(), crashgen_signature(), create_test_registry(), find_crashgen(), floor_crashgen_versions(), Fn, PathBuf, Vec (+17 more)

### Community 51 - "Community 51"
Cohesion: 0.14
Nodes (13): ConnectionAllocationPlan, ConnectionAllocator, DatabaseError, PoolRegistry, PoolStatistics, DashMap, Error, Hash (+5 more)

### Community 52 - "Community 52"
Cohesion: 0.12
Nodes (30): dds_parsing_benchmarks(), decode_mmap_bytes(), encoding_detection_benchmarks(), file_io_core_benchmarks(), generate_path_list(), generate_utf8_bom_content(), generate_utf8_content(), generate_windows_1252_content() (+22 more)

### Community 53 - "Community 53"
Cohesion: 0.08
Nodes (29): is_https_cta_url(), is_release_tag(), is_rfc3339(), map_ensure_cache_result(), PathBuf, clear_fallback_cache_is_noop_when_cache_dir_is_none(), clear_fallback_marker_is_noop_when_marker_absent(), future_pathcore_variant_stays_typed_as_cache_io() (+21 more)

### Community 54 - "Community 54"
Cohesion: 0.16
Nodes (35): apply_yaml_update(), check_yaml_update(), check_yaml_update_with_cache_dir(), download_release_asset(), ensure_path_in_cache(), fetch_from_releases_api(), FileInstallOutcome, install_one() (+27 more)

### Community 55 - "Community 55"
Cohesion: 0.13
Nodes (17): calculate_sha256_file(), CheckType, GameIntegrityChecker, IntegrityCheckResult, IntegrityConfig, IntegrityError, Default, Error (+9 more)

### Community 56 - "Community 56"
Cohesion: 0.12
Nodes (20): check_crashgen_version_status(), check_crashgen_version_status_with_exceptions(), compile_static_regex(), crashgen_version_gen(), CrashgenVersion, CrashgenVersionStatus, is_fake_bot_compatible_buffout_version(), Display (+12 more)

### Community 57 - "Community 57"
Cohesion: 0.14
Nodes (34): AppNotificationDisplay, AppNotificationManifest, build_app_notification_pages_url(), build_pages_url(), check_app_notification(), Classification, clear_fallback_cache(), clear_fallback_marker() (+26 more)

### Community 58 - "Community 58"
Cohesion: 0.13
Nodes (11): GameSetupSettings, managed_game_preference(), parse_managed_game(), published_managed_game(), published_optional_string(), GameId, Option, Self (+3 more)

### Community 59 - "Community 59"
Cohesion: 0.13
Nodes (18): GithubAsset, GithubClient, GithubRelease, Into, Option, Result, Self, String (+10 more)

### Community 60 - "Community 60"
Cohesion: 0.11
Nodes (11): Fallout4Version, Display, Err, Formatter, FromStr, GameVersion, Option, Result (+3 more)

### Community 61 - "Community 61"
Cohesion: 0.10
Nodes (4): AtomicU64, PoolStats, test_database_pool_clone_arc_count(), test_drop_warning_condition_logic()

### Community 62 - "Community 62"
Cohesion: 0.11
Nodes (7): CacheEntry, CacheKey, QueryCache, AtomicUsize, Duration, H, Instant

### Community 63 - "Community 63"
Cohesion: 0.14
Nodes (15): DDSAnalyzer, DDSHeader, DDSIssue, GameTarget, is_power_of_2(), Default, Display, Formatter (+7 more)

### Community 64 - "Community 64"
Cohesion: 0.08
Nodes (9): detect_plugins_batch(), Vec, test_detect_plugins_batch_empty(), test_detect_plugins_batch_light_plugins(), test_detect_plugins_batch_multiple_logs(), test_detect_plugins_batch_no_plugins(), test_detect_plugins_batch_preserves_order(), test_detect_plugins_batch_single_log() (+1 more)

### Community 65 - "Community 65"
Cohesion: 0.18
Nodes (28): parse_crashgen_registry(), parse_settings_rules(), parse_string_list_field(), parse_version_field(), HashMap, Option, Result, String (+20 more)

### Community 66 - "Community 66"
Cohesion: 0.14
Nodes (18): candidate_diagnostic(), game_file_name(), inspect_candidate(), InstalledYamlDataDiagnostic, InstalledYamlDataDiagnosticKind, InstalledYamlDataInspectionError, InstalledYamlDataLoadError, InstalledYamlDataProvenance (+10 more)

### Community 67 - "Community 67"
Cohesion: 0.14
Nodes (29): load_yaml_sync(), create_test_yaml(), NamedTempFile, test_await_batch_result_reports_join_error_with_path(), test_load_yaml_async_complex_structures(), test_load_yaml_async_empty_file(), test_load_yaml_async_file_not_found(), test_load_yaml_async_multi_document() (+21 more)

### Community 68 - "Community 68"
Cohesion: 0.20
Nodes (16): Preference, bool_preference(), concurrency_preference(), custom_scan_input_preference(), formid_databases_preference(), game_version_preference(), GameVersionSelection, published_formid_databases() (+8 more)

### Community 69 - "Community 69"
Cohesion: 0.17
Nodes (15): ConditionalReplacement, LocalIgnoreFileSystem, BarrierLocalIgnoreFileSystem, BlockingReplacementPublisher, CorruptingBackupPublisher, MainReplacingLocalIgnoreFileSystem, PublicationFailureLocalIgnoreFileSystem, RacingReplacementPublisher (+7 more)

### Community 70 - "Community 70"
Cohesion: 0.20
Nodes (23): compile_main_error_rule(), compile_matcher(), compile_stack_rule(), CompiledConfiguration, CompiledMainErrorRule, CompiledStackRule, CrashSuspectAnalysisInput, CrashSuspectAnalysisResult (+15 more)

### Community 71 - "Community 71"
Cohesion: 0.12
Nodes (19): create_sample_log(), create_sample_log_patches_only(), make_log_no_header(), make_log_with_known_header(), make_log_with_unknown_header(), Arc, Vec, test_addictol_patches_header_in_settings_segment() (+11 more)

### Community 72 - "Community 72"
Cohesion: 0.09
Nodes (11): coerce_setting_value(), parse_bool(), Option, Result, String, test_coerce_float(), validate_setting_value(), CoercedValue (+3 more)

### Community 73 - "Community 73"
Cohesion: 0.25
Nodes (17): Diagnostic, aliased_bool_preference(), bool_preference(), bounded_u8_preference(), child(), dotted_prefix(), group(), KnownGroup (+9 more)

### Community 74 - "Community 74"
Cohesion: 0.15
Nodes (7): MessageTarget, MessageType, Message, Into, Option, Self, String

### Community 75 - "Community 75"
Cohesion: 0.19
Nodes (20): CheckResult, detect_config_issues(), FullScanPart, GameScanConfig, GameScanOrchestrator, GameScanResult, ModScanResult, OrchestratorError (+12 more)

### Community 78 - "Community 78"
Cohesion: 0.16
Nodes (24): LocalIgnoreRunState, assert_installed_yaml_data(), assert_result(), configuration(), copy_logs(), copy_yaml_tree(), diagnostic_kind_token(), event_kind() (+16 more)

### Community 79 - "Community 79"
Cohesion: 0.07
Nodes (4): test_check_crashgen_version_status_convenience(), test_check_crashgen_version_status_with_crashgen_prefix(), test_check_crashgen_version_status_with_exceptions_convenience(), test_crashgen_version_gen()

### Community 81 - "Community 81"
Cohesion: 0.12
Nodes (16): GameVersion, Default, Display, Eq, Err, Formatter, FromStr, H (+8 more)

### Community 82 - "Community 82"
Cohesion: 0.19
Nodes (17): calculate_file_hash(), calculate_text_similarity(), compare_ini_files(), ConfigDuplicateDetector, ConfigError, DuplicateGroup, Default, Error (+9 more)

### Community 83 - "Community 83"
Cohesion: 0.16
Nodes (10): AnalysisResult, CrashgenScanContext, extract_module_names(), HashMap, HashSet, I, String, Vec (+2 more)

### Community 84 - "Community 84"
Cohesion: 0.13
Nodes (11): Configuration, Options, GameId, SetupMode, StandardRequest, TargetedRequest, CrashLogScanSetupContext, StandardCrashLogScanRunIntent (+3 more)

### Community 85 - "Community 85"
Cohesion: 0.24
Nodes (24): both_incompatible_returns_no_compatible_source(), cache_compatible_wins_over_bundled(), cache_incompatible_bundled_compatible_falls_back(), env_map(), load_with_env(), malformed_schema_version_in_cache_is_rejected_not_deleted(), neither_exists_returns_no_compatible_source(), resolve_cache_dir() (+16 more)

### Community 86 - "Community 86"
Cohesion: 0.14
Nodes (15): FileIOError, Error, JoinError, PathBuf, String, FileGenerator, FileGeneratorConfig, generate_ignore_file() (+7 more)

### Community 87 - "Community 87"
Cohesion: 0.19
Nodes (17): copy_dir_recursive(), copy_entry(), FileOperation, FileOperationResult, GameFilesManager, matches_any_pattern(), process_entries_chunked(), remove_entry() (+9 more)

### Community 88 - "Community 88"
Cohesion: 0.22
Nodes (16): ConfigIssue, IniError, IniValidator, IssueSeverity, Error, HashMap, Ini, Into (+8 more)

### Community 89 - "Community 89"
Cohesion: 0.16
Nodes (11): compile_static_regex(), FormIDAnalyzer, DashMap, Default, HashMap, Option, Regex, Self (+3 more)

### Community 90 - "Community 90"
Cohesion: 0.14
Nodes (20): T, V, parse_test(), Result, String, TestManifest, tokenless_client(), try_pages_304_with_corrupt_cached_body_returns_invalid_error() (+12 more)

### Community 91 - "Community 91"
Cohesion: 0.18
Nodes (4): QueryFailurePolicy, HashSet, Option, String

### Community 92 - "Community 92"
Cohesion: 0.15
Nodes (22): create_test_database(), NamedTempFile, PathBuf, Result, test_batch_lookup_workflow(), test_cache_clear_workflow(), test_cache_hit_miss_workflow(), test_cache_ttl_workflow() (+14 more)

### Community 93 - "Community 93"
Cohesion: 0.19
Nodes (11): BackupInfo, BackupManager, BackupType, Option, Path, PathBuf, Result, Self (+3 more)

### Community 94 - "Community 94"
Cohesion: 0.19
Nodes (19): count_resources_by_type(), detect_resource_type(), enumerate_resources(), is_supported_resource(), ResourceError, ResourceInfo, ResourceType, Err (+11 more)

### Community 95 - "Community 95"
Cohesion: 0.17
Nodes (12): BA2Error, BA2Issues, BA2Scanner, Default, Error, Path, PathBuf, Result (+4 more)

### Community 96 - "Community 96"
Cohesion: 0.20
Nodes (24): bridge_style_detect_crash_pattern_uncached(), bridge_style_detect_crash_pattern_with_parser(), create_error_patterns(), create_phase5_important_entries(), create_phase5_important_xse_modules(), create_record_types(), extract_callstack_lines(), extract_fixture_plugins() (+16 more)

### Community 97 - "Community 97"
Cohesion: 0.16
Nodes (17): CrashgenEntry, CrashgenRegistry, Default, HashMap, HashSet, Option, Self, String (+9 more)

### Community 98 - "Community 98"
Cohesion: 0.16
Nodes (12): PapyrusAnalyzer, PapyrusError, PapyrusStats, Error, Option, Path, PathBuf, Result (+4 more)

### Community 99 - "Community 99"
Cohesion: 0.34
Nodes (9): Parser, Fn, Option, Self, String, T, Value, Vec (+1 more)

### Community 100 - "Community 100"
Cohesion: 0.18
Nodes (13): Default, Error, HashSet, Option, Path, PathBuf, Result, Self (+5 more)

### Community 101 - "Community 101"
Cohesion: 0.21
Nodes (19): compile_predicate(), CompiledConfiguration, CrashgenExpectationOutcome, CrashgenSettingsAnalysisInput, CrashgenSettingsAnalysisResult, CrashgenSettingsAnalyzer, DisabledSettingNotice, expected_value_matches_type() (+11 more)

### Community 102 - "Community 102"
Cohesion: 0.19
Nodes (21): aggregate_identifiers(), FormIDFinding, FormIDFindingAnalysisInput, FormIDFindingAnalysisResult, FormIDFindingAnalyzer, FormIDPlugin, FormIDValueLookupStatus, invalid_configuration() (+13 more)

### Community 103 - "Community 103"
Cohesion: 0.17
Nodes (12): GpuDetector, GpuInfo, GpuVendor, Default, Display, Formatter, HashMap, Option (+4 more)

### Community 104 - "Community 104"
Cohesion: 0.24
Nodes (13): contains_record(), RecordScanner, AhoCorasick, HashSet, Option, Self, String, Vec (+5 more)

### Community 105 - "Community 105"
Cohesion: 0.11
Nodes (20): Duration, Error, Option, ParseError, PathBuf, String, UpdateError, PagesError (+12 more)

### Community 106 - "Community 106"
Cohesion: 0.13
Nodes (15): canonical_source_wins_even_when_a_valid_legacy_document_exists(), canonical_update_source_is_exposed_as_a_typed_preference(), fixture_path(), install_fixture(), open_current_document_exposes_typed_preferences_without_writing(), open_flat_legacy_document_projects_update_preferences_without_rewriting(), open_future_major_document_blocks_commits_and_update_checks(), open_invalid_known_values_fall_back_safely_without_blocking_later_updates() (+7 more)

### Community 107 - "Community 107"
Cohesion: 0.23
Nodes (17): minimal_game_yaml(), minimal_ignore_yaml(), minimal_main_yaml(), test_complete_config_load_workflow(), test_concurrent_config_loading(), test_config_clone(), test_config_debug_format(), test_empty_document_error() (+9 more)

### Community 109 - "Community 109"
Cohesion: 0.15
Nodes (17): calculate_similarity(), longest_common_subsequence_length(), longest_common_subsequence_length_inner(), read_file_lossy(), Error, Path, Result, String (+9 more)

### Community 110 - "Community 110"
Cohesion: 0.09
Nodes (7): test_load_save_roundtrip(), test_load_yaml_file_success(), test_load_yaml_files_batch(), test_load_yaml_files_batch_larger_batch(), test_load_yaml_files_batch_with_missing(), test_save_yaml_file_atomic_write(), test_save_yaml_file_success()

### Community 111 - "Community 111"
Cohesion: 0.19
Nodes (20): arguments(), main(), Path, PathBuf, Result, String, run(), check_compatibility_mirror() (+12 more)

### Community 112 - "Community 112"
Cohesion: 0.17
Nodes (14): create_broken_sqlite_fixture(), create_skyrim_sqlite_fixture(), create_sqlite_fixture(), create_sqlite_fixture_from_statements(), owned_sqlite_adapter_errors_when_the_active_game_table_is_absent(), owned_sqlite_adapter_returns_hits_without_a_private_runtime(), owned_sqlite_batch_preserves_hit_and_miss_positions(), NamedTempFile (+6 more)

### Community 113 - "Community 113"
Cohesion: 0.13
Nodes (12): auto_without_registry_match_requests_version_choice(), complete_xse_checks_use_registry_expectations(), configured_game_exe_path_allows_non_default_executable_under_root(), configured_game_exe_path_outside_resolved_root_falls_back_to_root_executable(), executable_hash_matching_uses_registry_candidates(), intake_returns_ready_diagnostics_for_explicit_paths(), Path, PathBuf (+4 more)

### Community 114 - "Community 114"
Cohesion: 0.24
Nodes (13): LogError, LogErrorEntry, LogProcessor, AhoCorasick, Error, HashSet, Option, Path (+5 more)

### Community 115 - "Community 115"
Cohesion: 0.20
Nodes (15): create_test_dir(), create_test_file(), make_manager(), Path, PathBuf, test_backup_directories(), test_backup_files(), test_backup_no_matches() (+7 more)

### Community 116 - "Community 116"
Cohesion: 0.21
Nodes (10): CacheStats, encode_hex(), FileHasher, HashMap, Option, Path, PathBuf, Result (+2 more)

### Community 117 - "Community 117"
Cohesion: 0.18
Nodes (17): TempDir, setup_plugins_dir(), setup_with_og_config(), setup_with_vr_config(), test_addictol_and_buffout_shows_incompatibility_warning(), test_addictol_skips_all_checks(), test_bakascrapheap_special_case(), test_check_detects_achievements_conflict() (+9 more)

### Community 118 - "Community 118"
Cohesion: 0.13
Nodes (14): merge_ba2_issues(), BTreeMap, BTreeSet, default_config(), PathBuf, test_config_clone(), test_merge_ba2_issues_empty(), test_merge_ba2_issues_populated() (+6 more)

### Community 119 - "Community 119"
Cohesion: 0.27
Nodes (21): check_yaml_data_update_with_env(), check_first_party_main_fixture(), check_yaml_data_update_with_uses_first_party_schema_entries(), first_party_bundled_dir(), first_party_cache_dir(), first_party_cache_env(), first_party_check_detects_same_schema_content_churn(), first_party_check_ignores_previous_when_present_canonical_is_invalid() (+13 more)

### Community 120 - "Community 120"
Cohesion: 0.20
Nodes (19): accepted_bootstrap(), accepted_update(), bootstrap_commit_applies_requested_fields_but_loses_to_a_concurrent_creator(), commit_patches_only_the_requested_node_in_a_document_with_unrelated_external_content(), commit_preserves_untouched_invalid_values_and_legacy_aliases_semantically(), concurrent_commits_allow_one_publication_and_report_one_revision_conflict(), fixture_path(), frontend_geometry_transition_replays_once_without_losing_a_newer_setting() (+11 more)

### Community 121 - "Community 121"
Cohesion: 0.20
Nodes (20): collect_semantic_differences(), corpus_dir(), load_expectations(), load_yaml_fixture(), read_fixture_bytes(), BTreeSet, Option, PathBuf (+12 more)

### Community 122 - "Community 122"
Cohesion: 0.25
Nodes (17): analysis_failure(), compile_matcher(), CompiledConfiguration, invalid_configuration(), NamedRecordFinding, NamedRecordFindingAnalysisInput, NamedRecordFindingAnalysisResult, NamedRecordFindingAnalyzer (+9 more)

### Community 123 - "Community 123"
Cohesion: 0.17
Nodes (13): Display, Error, Formatter, From, JoinError, Option, Path, PathBuf (+5 more)

### Community 124 - "Community 124"
Cohesion: 0.28
Nodes (19): await_batch_result(), load_yaml_async(), load_yaml_batch_async(), load_yaml_batch_sync(), load_yaml_merged_async(), load_yaml_merged_sync(), parse_yaml_content(), parse_yaml_content_with_source() (+11 more)

### Community 125 - "Community 125"
Cohesion: 0.14
Nodes (9): published_default_yaml(), published_defaults_document(), PublishedDefault, Option, Result, String, Yaml, SettingMetadata (+1 more)

### Community 126 - "Community 126"
Cohesion: 0.24
Nodes (8): MatchConfidence, MatchResult, GameVersion, Into, Option, Self, String, VersionMatcher<'a>

### Community 127 - "Community 127"
Cohesion: 0.15
Nodes (10): create_test_version_info_with_crashgens(), test_version_info_get_compatible_crashgens_empty(), test_version_info_get_compatible_crashgens_with_future_version(), test_version_info_get_compatible_crashgens_with_ng_version(), test_version_info_get_compatible_crashgens_with_og_version(), test_version_info_get_compatible_crashgens_with_own_version(), test_version_info_get_crashgen_for_version_found(), test_version_info_get_crashgen_for_version_not_found() (+2 more)

### Community 128 - "Community 128"
Cohesion: 0.22
Nodes (9): BackupResult, BackupManager, Into, Path, PathBuf, Self, String, Vec (+1 more)

### Community 130 - "Community 130"
Cohesion: 0.17
Nodes (11): EnbChecker, EnbConfigResult, EnbError, EnbResult, EnbValidationResult, AsRef, Error, Path (+3 more)

### Community 131 - "Community 131"
Cohesion: 0.19
Nodes (15): TempDir, setup_test_plugins_dir(), test_correct_version_non_vr_ae(), test_correct_version_non_vr_ng(), test_correct_version_non_vr_og(), test_correct_version_vr_mode(), test_message_formatting_correct(), test_message_formatting_not_found() (+7 more)

### Community 132 - "Community 132"
Cohesion: 0.27
Nodes (13): classify_plugin_status(), compile_static_regex(), contains_plugin(), insert_plugin_if_new(), normalize_plugin_name(), PluginAnalyzer, HashSet, IndexMap (+5 more)

### Community 133 - "Community 133"
Cohesion: 0.21
Nodes (14): backup_publication_errors_retain_the_failed_durability_stage(), CorruptBackup, corrupted_backup_fails_verification_before_settings_publication(), EditAfterBackup, install_sources(), legacy_edit_during_backup_returns_a_source_conflict_and_leaves_it_dormant(), Cell, Into (+6 more)

### Community 134 - "Community 134"
Cohesion: 0.27
Nodes (15): aliased_optional_absolute_path_preference(), AliasedOptionalPathPreference, classify_optional_absolute_path(), is_absolute_user_path(), optional_absolute_path_preference(), OptionalPathField, OptionalPathNode, Preference<T> (+7 more)

### Community 135 - "Community 135"
Cohesion: 0.20
Nodes (17): bootstrap_preview_only_accepts_a_missing_trusted_snapshot(), fixture_path(), install_fixture(), preview_accepts_a_multi_field_update_without_changing_unknown_entries_or_snapshot_values(), preview_accepts_a_typed_update_source_without_persisting_it(), preview_accepts_one_typed_gui_window_geometry_transition_without_persisting_it(), preview_accepts_the_frontend_auto_switch_preference_without_persisting_it(), preview_carries_every_requested_game_setup_field_as_canonical_paths() (+9 more)

### Community 136 - "Community 136"
Cohesion: 0.15
Nodes (12): extract_pe_version(), is_valid_executable_path(), PeVersionError, Error, Path, PathBuf, String, test_extract_pe_version_invalid_path() (+4 more)

### Community 137 - "Community 137"
Cohesion: 0.16
Nodes (10): create_test_dds(), Vec, test_analyzer_large_fallout4_texture(), test_analyzer_large_skyrim_texture(), test_analyzer_valid_texture_no_issues(), test_bc_dimension_validation(), test_dds_header_parsing(), test_power_of_2_dimensions() (+2 more)

### Community 138 - "Community 138"
Cohesion: 0.24
Nodes (8): DocsPathFinder, DocsPathResult, Into, Option, Path, PathBuf, Self, String

### Community 139 - "Community 139"
Cohesion: 0.24
Nodes (10): BTreeMap, BTreeSet, Default, Self, String, ScanReportBuilder, ScanReportBuilder<'a>, ScanValidators (+2 more)

### Community 140 - "Community 140"
Cohesion: 0.14
Nodes (9): make_issues(), BTreeMap, BTreeSet, String, test_build_archived_report_with_issues(), test_build_combined_report(), test_build_unpacked_report_with_issues(), test_report_items_sorted() (+1 more)

### Community 141 - "Community 141"
Cohesion: 0.26
Nodes (11): DuplicateEntry, ModIniScanner, ModIniScanResult, ConfigIssue, Path, PathBuf, Result, String (+3 more)

### Community 142 - "Community 142"
Cohesion: 0.23
Nodes (17): autoscan_report_assembler_applies_canonical_order_to_typed_contributions(), autoscan_report_assembler_distinguishes_absent_from_completed_empty_plugin_evidence(), autoscan_report_assembler_omits_absent_mod_conflict_fix_line(), autoscan_report_assembler_omits_formid_section_for_unresolved_only_findings(), autoscan_report_assembler_owns_crash_suspect_presentation(), autoscan_report_assembler_owns_named_record_sorting_counts_and_legacy_prose(), autoscan_report_assembler_owns_plugin_evidence_sorting_and_legacy_prose(), autoscan_report_assembler_preserves_legacy_output_for_completed_empty_formid_analysis() (+9 more)

### Community 143 - "Community 143"
Cohesion: 0.22
Nodes (17): compare_versions(), extract_all_versions(), extract_version_from_filename(), extract_version_from_log(), format_version(), is_known_f4se_version(), is_known_fallout4_version(), parse_version() (+9 more)

### Community 144 - "Community 144"
Cohesion: 0.13
Nodes (7): init_with_filter(), CountingLogger, test_init_is_opt_in_idempotent_and_does_not_replace_existing_logger(), test_logger_methods_compile(), Log, Metadata, Record

### Community 145 - "Community 145"
Cohesion: 0.20
Nodes (12): analyzer_failure(), AutoscanReportCollectionInput, AutoscanReportContributionCollector, AutoscanReportContributionCollector<'a>, AutoscanReportContributions, detected_gpu(), HashSet, IndexMap (+4 more)

### Community 146 - "Community 146"
Cohesion: 0.18
Nodes (9): PatternMatcher, AhoCorasick, Arc, DashMap, Option, Result, Self, String (+1 more)

### Community 147 - "Community 147"
Cohesion: 0.26
Nodes (15): assert_golden_case(), assert_report_bytes(), complete_scan_runs_persist_byte_exact_autoscan_report_goldens_with_isolated_cache(), copy_directory(), create_formid_database(), expected_report_bytes(), ExpectedOutcome, fcx_fixture_paths() (+7 more)

### Community 148 - "Community 148"
Cohesion: 0.21
Nodes (16): check_app_notification_with(), Self, fallback_leg_decode_failure_surfaces_decode_error(), fallback_leg_manifest_invalid_surfaces_schema_error(), fallback_leg_unsupported_version_surfaces_structural_error(), pages_404_and_empty_releases_returns_not_published(), pages_404_with_fresh_fallback_cache_still_checks_releases_absence(), pages_404_with_matching_release_missing_manifest_asset_returns_fetch_failed() (+8 more)

### Community 149 - "Community 149"
Cohesion: 0.19
Nodes (9): CorruptFirstCanonicalPublication, CorruptFirstPublication, failed_backup_reread_verification_never_publishes_the_migration(), failed_post_publication_verification_rolls_back_the_last_accepted_document(), failed_restore_reopen_verification_rolls_back_the_migrated_document(), Cell, Path, Result (+1 more)

### Community 150 - "Community 150"
Cohesion: 0.24
Nodes (11): create_test_docs(), create_test_ini(), Path, PathBuf, test_run_all_checks(), test_run_all_checks_with_issues(), test_validate_custom_ini_has_archive(), test_validate_custom_ini_missing_archive() (+3 more)

### Community 151 - "Community 151"
Cohesion: 0.22
Nodes (13): construct_proton_docs_path(), extract_vdf_value(), get_home_directory(), parse_steam_library_vdf(), parse_vdf_content(), DocsPathResult, Option, Path (+5 more)

### Community 152 - "Community 152"
Cohesion: 0.23
Nodes (13): TempDir, setup_game_root(), test_cache_creation_and_contains(), test_detect_issue_not_triggered(), test_detect_issue_triggered(), test_get_bool(), test_get_float(), test_get_int() (+5 more)

### Community 153 - "Community 153"
Cohesion: 0.23
Nodes (13): TempDir, setup_game_root(), test_console_command_detection(), test_epo_particle_issue(), test_epo_particle_ok(), test_espexplorer_hotkey_issue(), test_f4ee_issues(), test_f4ee_no_issues_when_unlocked() (+5 more)

### Community 154 - "Community 154"
Cohesion: 0.28
Nodes (10): HashMap, Option, Self, String, Vec, WryeBashParser, WryeError, WryeIssue (+2 more)

### Community 155 - "Community 155"
Cohesion: 0.19
Nodes (6): AnalyzerError, AnalyzerErrorCode, AnalyzerKind, Into, Self, String

### Community 156 - "Community 156"
Cohesion: 0.22
Nodes (13): alias_only_current_document_has_an_optional_reviewable_plan(), alias_plan_promotes_the_typed_fallback_when_the_canonical_value_is_invalid(), current_and_same_major_newer_documents_need_no_migration_or_downgrade(), explicit_alias_plan_is_optional_and_removes_aliases_without_touching_disk(), fixture_path(), flat_classic_config_plans_the_golden_canonical_document_and_reverses_in_memory(), install_fixture(), missing_and_untrusted_documents_do_not_produce_migration_plans() (+5 more)

### Community 158 - "Community 158"
Cohesion: 0.20
Nodes (9): contract_severity_name(), ContractEvent, escape_contract_value(), format_contract_event(), init(), BTreeMap, String, test_format_contract_event_redacts_sensitive_fields() (+1 more)

### Community 159 - "Community 159"
Cohesion: 0.18
Nodes (3): Logger, Default, Level

### Community 160 - "Community 160"
Cohesion: 0.16
Nodes (5): parse_xse_log(), test_parse_xse_log_missing_line(), test_parse_xse_log_not_found(), test_parse_xse_log_success(), test_parse_xse_log_with_quotes()

### Community 161 - "Community 161"
Cohesion: 0.23
Nodes (13): create_test_ini(), Path, PathBuf, test_get_bool(), test_get_int(), test_get_value(), test_has_key(), test_has_section() (+5 more)

### Community 162 - "Community 162"
Cohesion: 0.48
Nodes (6): GameSetupIntake, GameSetupPathUpdate, non_empty_pathbuf(), Into, PathBuf, Self

### Community 163 - "Community 163"
Cohesion: 0.17
Nodes (5): sample_html(), test_parse_extracts_plugins(), test_parse_extracts_sections(), test_parse_skips_active_plugins(), test_parse_with_warnings()

### Community 164 - "Community 164"
Cohesion: 0.29
Nodes (12): CompiledConfiguration, invalid_configuration(), PluginEvidence, PluginEvidenceAnalysisInput, PluginEvidenceAnalysisResult, PluginEvidenceAnalyzer, AnalyzerResult, Arc (+4 more)

### Community 165 - "Community 165"
Cohesion: 0.26
Nodes (13): merge_yaml_documents(), merge_yaml_documents_with_source(), merge_yaml_values(), Into, Result, SettingsSource, String, Yaml (+5 more)

### Community 166 - "Community 166"
Cohesion: 0.31
Nodes (13): decode_like_read_file_mmap(), generate_utf8_content(), map_copy(), map_copy_read_only(), map_shared(), File, Mmap, MmapMut (+5 more)

### Community 167 - "Community 167"
Cohesion: 0.18
Nodes (8): format_log_message(), Option, String, test_format_log_message_appends_details_verbatim(), test_format_log_message_no_details_returns_content_only(), test_format_log_message_preserves_emoji_in_content(), test_format_log_message_preserves_symbols_and_whitespace(), test_integration_message_with_formatting()

### Community 168 - "Community 168"
Cohesion: 0.23
Nodes (12): get_documents_path(), query_game_registry(), query_registry_path(), remove_readonly(), DocsPathResult, GamePathResult, Path, PathBuf (+4 more)

### Community 169 - "Community 169"
Cohesion: 0.15
Nodes (6): registry_auto_candidates_keep_fallout4_non_vr(), registry_auto_candidates_prefer_fallout4vr_registry_identity(), test_extract_version_from_log(), test_is_known_f4se_version(), test_is_known_fallout4_version(), get_version_registry()

### Community 171 - "Community 171"
Cohesion: 0.25
Nodes (10): installation_root_from_layout_hint(), resolve_bundled_yaml_dir(), resolve_installation_root(), resolve_native_installation_root(), Option, PathBuf, Self, first_party_installation_root_supports_native_parent_and_install_layouts() (+2 more)

### Community 172 - "Community 172"
Cohesion: 0.25
Nodes (13): corrupted_backup_blocks_restore_without_changing_the_migrated_document(), explicit_alias_migration_publishes_only_the_approved_canonicalization_plan(), explicit_flat_migration_retains_verified_backup_and_reports_reopened_publication(), explicit_restore_republishes_verified_backup_byte_for_byte_and_retains_it(), fixture_path(), install_fixture(), legacy_location_restore_reactivates_the_verified_legacy_source(), parse_one() (+5 more)

### Community 173 - "Community 173"
Cohesion: 0.17
Nodes (6): Cache, Display, Formatter, Result, Self, YamlFile

### Community 174 - "Community 174"
Cohesion: 0.42
Nodes (11): Box, Error, Result, test_hash_cache_bounded_eviction(), test_hash_cache_stats_reset_preserves_cache_entries(), test_hash_clear_cache_empties_entries_without_resetting_stats(), test_hash_file_basic(), test_hash_file_caching() (+3 more)

### Community 175 - "Community 175"
Cohesion: 0.23
Nodes (7): contains_token(), normalized(), redact_contract_fields(), redact_field_value(), BTreeMap, String, test_redact_contract_fields_map()

### Community 177 - "Community 177"
Cohesion: 0.33
Nodes (6): GamePathFinder, GamePathResult, Option, Path, PathBuf, String

### Community 180 - "Community 180"
Cohesion: 0.26
Nodes (8): CrashgenExpectationParseDiagnostic, CrashgenExpectationParseResult, parse_crashgen_expectations(), accepts_compatibility_aliases_with_canonical_precedence(), parses_canonical_crashgen_expectation_document(), preserves_tolerant_defaults_and_reports_diagnostics(), rejects_non_mapping_root_with_diagnostic(), uses_yaml_sibling_version_when_document_version_is_missing()

### Community 181 - "Community 181"
Cohesion: 0.18
Nodes (3): current_dir_lock(), main_load_routes_through_shippable_loader(), Mutex

### Community 182 - "Community 182"
Cohesion: 0.27
Nodes (8): create_test_docs_structure(), create_test_ini(), Path, PathBuf, test_find_docs_path_with_valid_cache(), test_validate_docs_path_success(), test_validate_ini_files_missing(), test_validate_ini_files_success()

### Community 183 - "Community 183"
Cohesion: 0.20
Nodes (5): analyze_maps_an_absent_active_game_table_to_operational_failure(), plugin(), NamedTempFile, PathBuf, wrong_game_sqlite_fixture()

### Community 184 - "Community 184"
Cohesion: 0.29
Nodes (12): persist_fallback_manifest_body(), body_write_failure_clears_existing_marker_to_prevent_stale_reuse(), body_write_failure_with_no_prior_marker_stays_marker_free(), clear_fallback_cache_removes_marker_body_and_etag(), clear_fallback_marker_removes_existing_marker(), minimal_manifest_bytes(), persist_ignores_occupied_legacy_fixed_tmp_path(), persist_is_noop_when_cache_dir_is_none() (+4 more)

### Community 185 - "Community 185"
Cohesion: 0.27
Nodes (11): import_legacy_tui_state(), AsRef, absent_legacy_source_is_a_noop_outcome(), explicit_import_bootstraps_missing_settings_from_published_defaults(), explicit_import_updates_current_settings_and_retains_an_exact_content_addressed_backup(), invalid_legacy_json_and_values_fail_before_backup_or_settings_changes(), migration_required_and_untrusted_settings_bases_are_distinct_noop_outcomes(), parsed_document() (+3 more)

### Community 186 - "Community 186"
Cohesion: 0.29
Nodes (9): fixture_path(), install_fixture(), missing_and_untrusted_documents_use_distinct_scan_defaults_and_safety_fallbacks(), open_alias_only_document_projects_custom_scan_input_without_rewriting_the_alias(), open_conflicting_alias_document_prefers_the_valid_canonical_label_with_a_diagnostic(), open_current_document_projects_complete_crash_log_scan_settings_without_writing(), open_invalid_known_values_uses_field_safe_fallbacks_and_preserves_original_nodes(), Path (+1 more)

### Community 187 - "Community 187"
Cohesion: 0.35
Nodes (7): CrashgenSettingsRules, analyze_returns_typed_outcomes_and_separate_disabled_notices(), construction_rejects_unsupported_rule_versions_with_a_stable_error(), entry_with_rules(), input(), one_immutable_handle_is_safe_for_concurrent_analysis(), rules()

### Community 188 - "Community 188"
Cohesion: 0.38
Nodes (8): evaluate_rules(), base_context(), evaluate_check_does_not_match_unscoped_settings(), evaluate_check_fail_and_pass(), evaluate_check_normalizes_section_names(), evaluate_check_uses_target_section_for_lookup(), evaluate_preflight_skip_remaining(), version_predicate_does_not_match_when_crashgen_version_is_unknown()

### Community 190 - "Community 190"
Cohesion: 0.36
Nodes (3): Into, Option, Self

### Community 191 - "Community 191"
Cohesion: 0.47
Nodes (10): create_directory(), invalid_proton_docs_path_falls_back_to_local_share(), legacy_local_share_regression_still_works_without_proton(), local_share(), proton_docs_path_wins_over_valid_local_share(), proton_docs_root(), proton_path_ignored_when_steam_app_id_unset(), Path (+2 more)

### Community 192 - "Community 192"
Cohesion: 0.35
Nodes (10): create_test_game_dir(), TempDir, test_enb_not_installed(), test_enb_partial(), test_enb_partial_is_present(), test_enb_present(), test_enb_present_no_config(), test_format_message_not_installed() (+2 more)

### Community 193 - "Community 193"
Cohesion: 0.44
Nodes (10): generate_multi_document_yaml(), generate_nested_yaml(), generate_yaml_content(), Criterion, String, yaml_modification_benchmarks(), yaml_operations_benchmarks(), yaml_parsing_benchmarks() (+2 more)

### Community 194 - "Community 194"
Cohesion: 0.29
Nodes (11): classify(), classify_deprecated_when_below_min_supported(), classify_deprecated_wins_over_up_to_date(), classify_installed_ahead_of_latest_is_up_to_date(), classify_strips_leading_v_and_big_v(), classify_unknown_when_installed_version_unparseable(), classify_unknown_when_manifest_latest_unparseable(), classify_up_to_date_when_installed_equals_latest() (+3 more)

### Community 195 - "Community 195"
Cohesion: 0.33
Nodes (10): assert_default(), checked_in_mirror_is_fresh_and_covers_every_canonical_known_setting(), ExpectedDefault, generation_is_idempotent_and_check_rejects_default_drift(), generation_preserves_crlf_and_every_byte_outside_the_mirror(), node_at(), Path, Yaml (+2 more)

### Community 196 - "Community 196"
Cohesion: 0.44
Nodes (9): batch_lookup_benchmarks(), init_pool(), multi_db_budget_benchmarks(), multi_db_fallback_benchmarks(), repeated_bucket_reuse_benchmarks(), Criterion, PathBuf, Vec (+1 more)

### Community 197 - "Community 197"
Cohesion: 0.44
Nodes (7): AnalyzerFixture, applicable_analyses_retain_present_empty_results(), collection_distinguishes_not_performed_from_always_performed_empty_analysis(), formid_malformed_lookup_result_preserves_findings_without_value_enrichment(), formid_operational_failure_preserves_findings_without_value_enrichment(), immutable_collector_reuse_is_deterministic_sequentially_and_concurrently(), Self

### Community 198 - "Community 198"
Cohesion: 0.27
Nodes (6): extract_formids_batch(), is_valid_formid(), String, Vec, batch_extraction_preserves_segments_and_filters_ff_prefixes(), validate_formids_batch()

### Community 199 - "Community 199"
Cohesion: 0.31
Nodes (9): check_app_notification_with_env(), cache_dir_creation_failure_surfaces_as_notification_cache_io(), invalid_installed_version_surfaces_before_cache_dir_creation_failure(), invalid_path_degrades_to_no_cache_and_orchestrator_continues(), Fn, Option, PathBuf, String (+1 more)

### Community 200 - "Community 200"
Cohesion: 0.29
Nodes (6): canonical_frontend_state_is_typed_and_read_only(), fixture_path(), frontend_preference_compatibility_sources_have_stable_precedence(), invalid_frontend_values_report_diagnostics_without_rewriting(), missing_and_untrusted_documents_expose_distinct_frontend_origins(), PathBuf

### Community 201 - "Community 201"
Cohesion: 0.24
Nodes (3): canonical_mods_and_custom_paths_win_conflicts_without_rewriting_aliases(), fixture_path(), PathBuf

### Community 202 - "Community 202"
Cohesion: 0.31
Nodes (7): persist_game_local_paths(), Option, Path, Result, persist_game_local_paths_creates_missing_file_with_both_paths(), persist_game_local_paths_updates_supplied_path_and_preserves_other_documents(), persist_game_local_paths_with_no_updates_does_not_create_file()

### Community 207 - "Community 207"
Cohesion: 0.39
Nodes (7): create_test_registry(), test_exact_match(), test_exact_match_ng(), test_exact_match_vr(), test_nearest_match(), test_nearest_match_prefers_higher_priority(), test_vr_mode_filtering()

### Community 220 - "Community 220"
Cohesion: 0.47
Nodes (4): ConfigIssue, Option, Self, String

### Community 223 - "Community 223"
Cohesion: 0.40
Nodes (4): Self, S1, S2, S3

### Community 224 - "Community 224"
Cohesion: 0.80
Nodes (4): get_system_documents_path(), parse_steam_library(), DocsPathResult, PathBuf

### Community 226 - "Community 226"
Cohesion: 0.60
Nodes (5): autoscan_report_path(), Path, PathBuf, Result, write_autoscan_report()

### Community 228 - "Community 228"
Cohesion: 0.50
Nodes (4): accepted_update(), every_injected_publication_failure_preserves_a_parseable_original_and_cleans_temp_files(), AcceptedUserSettingsUpdate, Path

### Community 229 - "Community 229"
Cohesion: 0.50
Nodes (3): ActiveGameTable, Arc, RwLock

### Community 230 - "Community 230"
Cohesion: 0.67
Nodes (3): Error, String, ScanGameError

## Knowledge Gaps
- **3 isolated node(s):** `Keys`, `VsyncSetting`, `Preference<T>`
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `OrchestratorCore` connect `Community 48` to `Community 0`, `Community 129`, `Community 3`, `Community 132`, `Community 101`, `Community 102`, `Community 70`, `Community 164`, `Community 35`, `Community 14`, `Community 83`, `Community 56`, `Community 122`, `Community 30`?**
  _High betweenness centrality (0.133) - this node is a cross-community bridge._
- **Why does `F` connect `Community 3` to `Community 1`, `Community 66`, `Community 5`, `Community 7`, `Community 199`, `Community 41`, `Community 42`, `Community 44`, `Community 83`, `Community 119`, `Community 85`, `Community 87`, `Community 24`?**
  _High betweenness centrality (0.117) - this node is a cross-community bridge._
- **Why does `DatabasePool` connect `Community 129` to `Community 196`, `Community 229`, `Community 36`, `Community 4`, `Community 48`, `Community 51`, `Community 189`, `Community 91`, `Community 61`, `Community 62`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Are the 58 inferred relationships involving `clear_global_yaml_cache()` (e.g. with `both_incompatible_returns_no_compatible_source()` and `cache_compatible_wins_over_bundled()`) actually correct?**
  _`clear_global_yaml_cache()` has 58 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Keys`, `VsyncSetting`, `Preference<T>` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06044226044226044 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.05982905982905983 - nodes in this community are weakly interconnected._