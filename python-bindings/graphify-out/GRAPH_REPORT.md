# Graph Report - D:\repos\CLASSIC-Fallout4\python-bindings  (2026-07-28)

## Corpus Check
- 152 files · ~350,415 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3560 nodes · 6680 edges · 221 communities (141 shown, 80 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 103 edges (avg confidence: 0.66)
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
- Community 134
- Community 137
- Community 138
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
- Community 157
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
- Community 170
- Community 171
- Community 172
- Community 173
- Community 174
- Community 175
- Community 176
- Community 177
- Community 178
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
- Community 203
- Community 204
- Community 205
- Community 206
- Community 207
- Community 208
- Community 209
- Community 210
- Community 211
- Community 212
- Community 213
- Community 214
- Community 215
- Community 216

## God Nodes (most connected - your core abstractions)
1. `CommandContext` - 43 edges
2. `CommandResult` - 40 edges
3. `PyVersionInfo` - 38 edges
4. `PyYamlData` - 34 edges
5. `PyUserSettingsUpdate` - 27 edges
6. `PyDatabasePool` - 25 edges
7. `failure()` - 25 edges
8. `PyScanRunResult` - 25 edges
9. `PyFileIOCore` - 23 edges
10. `PyResourceType` - 23 edges

## Surprising Connections (you probably didn't know these)
- `test_compliance_run_fails_when_scenario_expectation_missed()` --calls--> `Scenario`  [INFERRED]
  tests/test_classic_py_cli.py → classic-py-cli/src/classic_py_cli/scenarios.py
- `test_smoke_scanlog_contract_rejects_outdated_warning()` --calls--> `Scenario`  [INFERRED]
  tests/test_classic_py_cli.py → classic-py-cli/src/classic_py_cli/scenarios.py
- `crashgen_entry_from_py_strict()` --calls--> `parse_settings_rules_with_diagnostics()`  [INFERRED]
  classic-scanlog-py/src/py_adapters.rs → classic-config-py/src/crashgen_rules.rs
- `test_compliance_run_fails_when_scenario_expectation_missed()` --calls--> `main()`  [INFERRED]
  tests/test_classic_py_cli.py → classic-py-cli/src/classic_py_cli/app.py
- `test_fake_version_binding_command()` --calls--> `main()`  [INFERRED]
  tests/test_classic_py_cli.py → classic-py-cli/src/classic_py_cli/app.py

## Import Cycles
- 3-file cycle: `classic-py-cli/src/classic_py_cli/__init__.py -> classic-py-cli/src/classic_py_cli/app.py -> classic-py-cli/src/classic_py_cli/parser.py -> classic-py-cli/src/classic_py_cli/__init__.py`

## Hyperedges (group relationships)
- **Python Binding Parity Evidence Set** — python_bindings_binding_audit_criteria_thin_binding_standard, python_bindings_parity_artifacts_classic_python_cli_report_delegated_gates, python_bindings_parity_artifacts_parity_diff_report_zero_gap_baseline, python_bindings_parity_artifacts_runtime_coverage_summary_full_runtime_verification, python_bindings_parity_artifacts_tier1_gate_report_gate_pass [INFERRED 0.95]

## Communities (221 total, 80 thin omitted)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (43): CheckRule, auto_init_application_dir(), check_rule_to_pydict(), classic_config(), config_error_to_pyerr(), create_yamldata(), get_application_dir(), pathbuf_to_string() (+35 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (40): BufReader, PyFileIOCore, Bound, HashMap, Option, PathLike, Py, PyAny (+32 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (31): classic_database(), initialize_async_runtime(), Bound, PyErr, PyModule, PyResult, to_pyerr(), formid_value_lookup_error_to_pyerr() (+23 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (16): BackupManager, classic_path(), DocsPathFinder, DocumentsChecker, GamePathFinder, IniCheckResult, PathValidator, remove_readonly() (+8 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (38): PyConfigIssue, PyIniValidator, PyIssueSeverity, register_ini(), Bound, PathBuf, PyDict, PyModule (+30 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (56): CaptureFixture, main(), _normalize_global_options(), Allow documented global options before or after subcommands., Run the CLI, normalize boundary errors, and return a stable exit code., Run the CLASSIC Python binding CLI as a module., Return validation errors for missing required scenario metadata., validate_catalog() (+48 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (35): CoreModEntry, ModConflictEntry, PyImportantModGuidance, PyModConflictGuidance, PyModGuidanceAnalysisInput, PyModGuidanceAnalysisResult, PyModGuidanceAnalyzer, PyModGuidanceConflictRule (+27 more)

### Community 8 - "Community 8"
Cohesion: 0.08
Nodes (55): fixture, _configuration(), _copy_shared_scan_run_data_root(), _isolate_installed_yaml_cache(), MonkeyPatch, parametrize, Path, Public contract tests for the final Python Crash Log Scan Run adapter. (+47 more)

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (35): cache_keys(), cache_stats(), classic_settings(), clear_cache(), coerce_setting_value(), get_cached(), load_batch_async(), load_batch_sync() (+27 more)

### Community 10 - "Community 10"
Cohesion: 0.07
Nodes (40): clear_all(), extract_formids_batch(), String, Vec, validate_formids_batch(), auto_init_application_dir(), classic_scanlog(), register_scan_run_exports() (+32 more)

### Community 11 - "Community 11"
Cohesion: 0.05
Nodes (48): get_runtime_coverage_case_ids(), load_runtime_coverage_registry(), Any, Helpers for reading Python binding runtime coverage registry data., Fixtures for Python Tier-1 binding parity smoke tests., Path, Per-class smoke tests for Phase 3 Plan 06 — classic-config-py promotions.  Cov, YamlData — real-fixture deserialization using the repo PARITY_*_YAML set. (+40 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (23): CheckType, convert_integrity_error(), PyCheckType, PyGameIntegrityChecker, PyIntegrityCheckResult, PyIntegrityConfig, register(), Bound (+15 more)

### Community 13 - "Community 13"
Cohesion: 0.06
Nodes (17): PyGithubAsset, PyGithubClient, PyGithubRelease, register(), Bound, From, Option, PyAny (+9 more)

### Community 14 - "Community 14"
Cohesion: 0.09
Nodes (10): PyScanRunDiscoveryResult, PyScanRunLogFailure, PyScanRunLogResult, PyScanRunRejectedInput, PyScanRunSetupCheck, PyScanRunSetupPathUpdate, PyScanRunSetupResult, PyConfigIssue (+2 more)

### Community 15 - "Community 15"
Cohesion: 0.10
Nodes (44): BaseException, Import a required binding or raise ImportError with module context., require_binding(), bindings_list(), bindings_smoke(), config_inspect(), config_main_version(), database_info() (+36 more)

### Community 16 - "Community 16"
Cohesion: 0.09
Nodes (27): PyCrashSuspectAnalysisInput, PyCrashSuspectAnalysisResult, PyCrashSuspectAnalyzer, PyCrashSuspectFinding, PyCrashSuspectFindingKind, PyCrashSuspectMainErrorRule, PyCrashSuspectStackCountRule, PyCrashSuspectStackRule (+19 more)

### Community 17 - "Community 17"
Cohesion: 0.07
Nodes (23): Cancellation, infrastructure_error_to_py(), PyObserverAdapter, PyScanRunCancellation, PyScanRunContinuation, PyScanRunExecution, PyScanRunInfrastructureError, PyScanRunLocalIgnoreRecoveryDecision (+15 more)

### Community 18 - "Community 18"
Cohesion: 0.10
Nodes (30): check_crashgen_settings(), convert_report(), PyCrashgenCheckOrchestrator, PyCrashgenReport, register_crashgen_orchestrator(), Bound, Option, PathBuf (+22 more)

### Community 19 - "Community 19"
Cohesion: 0.09
Nodes (17): classic_resource(), count_resources_by_type(), detect_resource_type(), enumerate_resources(), parse_resource_type(), PyResourceInfo, PyResourceType, Bound (+9 more)

### Community 20 - "Community 20"
Cohesion: 0.10
Nodes (25): convert_check(), convert_path_update(), convert_result(), game_setup_needs_path_detection_py(), normalize_game_setup_version_selection_py(), PyGameSetupCheck, PyGameSetupIntake, PyGameSetupIntakeResult (+17 more)

### Community 21 - "Community 21"
Cohesion: 0.12
Nodes (33): apply_yaml_update(), build_config(), check_yaml_update(), core_file_to_py(), core_outcome_to_py(), core_status_to_py(), entries_to_core(), PyApprovedUpdate (+25 more)

### Community 22 - "Community 22"
Cohesion: 0.11
Nodes (20): convert_scan_result(), PyConfigFileCache, PyDuplicateEntry, PyModIniScanner, PyModIniScanResult, PyVsyncEntry, register_config_cache(), Bound (+12 more)

### Community 23 - "Community 23"
Cohesion: 0.05
Nodes (37): Smoke tests for independently useful scanlog utilities.  Crash Log Scan Run orch, ``to_tuple()`` returns ``(major, minor, patch)`` as a 3-tuple of ints., Two ``CrashgenVersion`` instances are equal if their major/minor/patch match., ``__hash__`` matches for two equal ``CrashgenVersion`` instances., ``CrashgenVersionStatus`` exposes four ``#[classattr]`` string constants.      V, ``parse_crashgen_version`` is a free function returning ``Optional[CrashgenVersi, Invalid version strings yield ``None`` (per -py wrapper returning ``Option``)., ``check_crashgen_version_status`` compares against a list of valid strings. (+29 more)

### Community 24 - "Community 24"
Cohesion: 0.09
Nodes (37): MonkeyPatch, Path, Runtime coverage for the typed, read-only User Settings Python adapter., Return the repository-level User Settings compatibility corpus., Expose Update Source as a canonical token with independent provenance., Expose shared preferences, GUI geometry, and namespaced TUI remembered state., Expose User Settings without retaining the flat ClassicConfig facade., Project scan choices, provenance, aliases, and safe fallbacks as typed values. (+29 more)

### Community 25 - "Community 25"
Cohesion: 0.09
Nodes (36): compliance_run(), Any, Command handlers for binding diagnostics, compliance, and product workflows., Run a compliance profile and write JSON and Markdown reports., Execute one scenario through the same handler surface used by users., Return a scenario-specific semantic failure not captured by exit status., Return compact command data worth preserving in compliance reports., Run source-level gates delegated by the python-ci profile. (+28 more)

### Community 26 - "Community 26"
Cohesion: 0.11
Nodes (26): lookup_entry_to_core(), PyFormIDFinding, PyFormIDFindingAnalysisInput, PyFormIDFindingAnalysisResult, PyFormIDFindingAnalyzer, PyFormIDFindingLookupEntry, PyFormIDFindingLookupReplyKind, PyFormIDPlugin (+18 more)

### Community 27 - "Community 27"
Cohesion: 0.08
Nodes (7): PyCompatibleRange, PyVersionInfo, Option, String, Vec, CompatibleRange, VersionInfo

### Community 28 - "Community 28"
Cohesion: 0.09
Nodes (15): classic_xse(), detect_xse_version(), get_xse_info(), is_xse_installed(), parse_xse_type(), PyXseInfo, PyXseType, Bound (+7 more)

### Community 29 - "Community 29"
Cohesion: 0.12
Nodes (36): isolate_cache(), MonkeyPatch, parametrize, Path, Focused contract tests for Installed YAML Data inspection., An incompatible canonical cache file is attributed without being modified., Unsupported games and exhausted sources remain separately catchable., A valid load exposes one stable snapshot of independently selected bytes. (+28 more)

### Community 30 - "Community 30"
Cohesion: 0.09
Nodes (30): ArgumentParser, _fallback_context_from_argv(), _json_mode_requested(), _parse_args(), _parse_error_message(), Application boundary for the CLASSIC Python binding CLI., Parse argv and normalize JSON-mode argparse failures through render_result., Return whether the caller requested JSON output from raw argv tokens. (+22 more)

### Community 31 - "Community 31"
Cohesion: 0.07
Nodes (16): PyDDSAnalyzer, register_dds_analyzer(), Bound, PyModule, PyResult, Python, Self, String (+8 more)

### Community 32 - "Community 32"
Cohesion: 0.15
Nodes (15): PyLogParser, Arc, Bound, HashMap, Option, Py, PyDict, PyResult (+7 more)

### Community 33 - "Community 33"
Cohesion: 0.11
Nodes (35): classification_token(), commit_eligibility_token(), crash_log_scan_settings_to_py(), frontend_preferences_to_py(), frontend_state_to_py(), game_setup_settings_to_py(), gui_window_geometry_to_py(), open_user_settings() (+27 more)

### Community 34 - "Community 34"
Cohesion: 0.09
Nodes (15): papyrus_logging(), PyPapyrusAnalyzer, PyPapyrusStats, register(), Bound, From, Option, PathBuf (+7 more)

### Community 35 - "Community 35"
Cohesion: 0.10
Nodes (32): discovery_to_py(), disposition_to_string(), event_to_py(), installed_yaml_data_file_to_py(), installed_yaml_data_identity_to_py(), installed_yaml_data_provenance_to_string(), installed_yaml_data_role_to_string(), installed_yaml_data_to_py() (+24 more)

### Community 36 - "Community 36"
Cohesion: 0.09
Nodes (16): check_crashgen_version_status(), parse_crashgen_version(), PyCrashgenVersion, PyCrashgenVersionStatus, register(), Bound, From, Option (+8 more)

### Community 37 - "Community 37"
Cohesion: 0.11
Nodes (29): parse_settings_rules(), parse_settings_rules_with_diagnostics(), pyany_to_document(), Bound, Option, PyAny, Value, parse_settings_rules_accepts_canonical_target_type() (+21 more)

### Community 38 - "Community 38"
Cohesion: 0.17
Nodes (30): classic_registry(), get(), get_application_dir(), get_game(), get_game_path_gui(), get_game_version_string(), get_local_dir(), get_manual_docs_gui() (+22 more)

### Community 39 - "Community 39"
Cohesion: 0.14
Nodes (21): configuration_to_core(), PyScanRunConfiguration, PyScanRunRequest, PyScanRunStandardSource, PyScanRunTargetedSource, PyScanRunUnsolvedLogs, required_path(), Bound (+13 more)

### Community 40 - "Community 40"
Cohesion: 0.13
Nodes (18): convert_file_io_error(), generate_ignore_file_async(), generate_local_yaml_async(), PyFileGenerator, PyFileGeneratorConfig, register(), Bound, FileIOError (+10 more)

### Community 41 - "Community 41"
Cohesion: 0.14
Nodes (21): import_legacy_tui_state_into_user_settings(), legacy_tui_state_import_outcome_to_py(), legacy_tui_state_import_restore_outcome_to_py(), migration_apply_outcome_to_py(), migration_receipt_to_py(), migration_restore_outcome_to_py(), PyLegacyTuiStateImportOutcome, PyLegacyTuiStateImportReceipt (+13 more)

### Community 42 - "Community 42"
Cohesion: 0.09
Nodes (13): PyMatchConfidence, PyMatchResult, register(), Bound, From, Option, PyAny, PyModule (+5 more)

### Community 43 - "Community 43"
Cohesion: 0.08
Nodes (9): PyFallout4Version, register(), Bound, PyModule, PyResult, Self, String, Vec (+1 more)

### Community 44 - "Community 44"
Cohesion: 0.10
Nodes (17): content_identity_to_py(), explicit_yaml_data_error_to_py(), explicit_yaml_data_role_name(), load_explicit_yaml_data(), PyExplicitYamlDataSnapshot, PyYamlDataContentIdentity, register(), Bound (+9 more)

### Community 45 - "Community 45"
Cohesion: 0.07
Nodes (29): Python Boundary Exemptions, Binding-Layer Business Logic Prohibition, Rust Core-Owned Batch Concurrency, classic-database-py batch_lookup Shim Removal, Python Binding Audit Criteria, classic-pybridge-py Retirement, classic-scanlog-py Binding Cleanup, Thin Rust-Backed Python Binding Standard (+21 more)

### Community 46 - "Community 46"
Cohesion: 0.13
Nodes (11): PyGpuDetector, PyGpuInfo, PyGpuVendor, Default, HashMap, Option, Self, String (+3 more)

### Community 47 - "Community 47"
Cohesion: 0.11
Nodes (22): block_on_notification_future(), check_app_notification(), classification_tag(), core_status_to_py(), PyAppNotificationDisplay, PyNotificationStatus, register(), Bound (+14 more)

### Community 48 - "Community 48"
Cohesion: 0.07
Nodes (27): Per-class smoke tests for Phase 3 Plan 07 — classic-version-registry-py promotio, GameVersion.semantic_distance — Tier-2 runtime-verified migration.      Covers, VersionInfo — fetched via registry; exercise fields and crashgen helpers., AddressLibraryConfig — fetched via VersionInfo.address_library.      Covers co, XseConfig — fetched via VersionInfo.xse.      Covers contract rows:       - v, CrashgenConfig — fetched via VersionInfo.crashgen_versions.      Covers contra, CompatibleRange — fetched via VersionInfo.compatible_range or CrashgenConfig.com, UnknownVersionHandling — fetched via registry.unknown_version_handling.      N (+19 more)

### Community 49 - "Community 49"
Cohesion: 0.09
Nodes (9): PyGameVersion, register(), Bound, From, GameVersion, PyModule, PyResult, Self (+1 more)

### Community 50 - "Community 50"
Cohesion: 0.12
Nodes (24): _ComplianceExplainArgs, _ComplianceRunArgs, _OptionalPathArg, _OptionalPathCommandArgs, _PathCommandArgs, Arguments supplied by the `compliance explain` parser., Arguments supplied by the `compliance run` parser., Arguments supplied by the `version parse` parser. (+16 more)

### Community 51 - "Community 51"
Cohesion: 0.15
Nodes (15): check_xse_plugins(), PyAddressLibInfo, PyGameVersion, PyValidationResult, PyXseChecker, register_xse(), Bound, GameVersion (+7 more)

### Community 52 - "Community 52"
Cohesion: 0.22
Nodes (8): get_version_registry(), PyVersionRegistry, HashMap, HashSet, Option, Self, String, Vec

### Community 53 - "Community 53"
Cohesion: 0.13
Nodes (15): build_url_with_query(), classic_web(), extract_domain(), get_user_agent(), get_user_agent_with_suffix(), join_url(), PyModSite, Bound (+7 more)

### Community 54 - "Community 54"
Cohesion: 0.10
Nodes (8): PyLogger, register(), Bound, PyModule, PyResult, Self, String, Logger

### Community 55 - "Community 55"
Cohesion: 0.12
Nodes (21): log_failure_stage_to_string(), log_result_to_py(), PyErr, scan_run_reset_error_to_py(), configuration_conversion_treats_blank_destination_as_absent(), discovery(), durability_unknown_maps_shared_outcome_to_typed_python_exception(), log_event() (+13 more)

### Community 56 - "Community 56"
Cohesion: 0.08
Nodes (23): Per-class smoke tests for Phase 3 Plan 03 - scanlog Wave 2 analysis.  Covers run, ``GpuInfo.to_dict()`` returns a dict representation., ``GpuVendor("AMD")`` constructs the AMD variant.      The Python wrapper is a, ``GpuVendor`` accepts case-insensitive vendor-name strings., ``ConfigIssue(...)`` exposes its getters., ``ConfigIssue`` accepts ``section=None`` for TOML-style files., ``GpuDetector()`` constructs with no arguments., ``extract_gpu_info([])`` returns an empty-state ``GpuInfo`` instance. (+15 more)

### Community 57 - "Community 57"
Cohesion: 0.13
Nodes (16): classic_perf(), clear_metrics(), get_summary(), MetricsSummary, record_timing(), reset_metrics(), Bound, From (+8 more)

### Community 58 - "Community 58"
Cohesion: 0.14
Nodes (13): check_enb(), PyEnbChecker, PyEnbConfigResult, PyEnbResult, PyEnbValidationResult, register_enb(), Bound, PathBuf (+5 more)

### Community 59 - "Community 59"
Cohesion: 0.11
Nodes (3): PyUserSettingsUpdate, Option, UserSettingsUpdate

### Community 60 - "Community 60"
Cohesion: 0.17
Nodes (14): diagnostic_kind_token(), diagnostic_to_py(), inspect_installed_yaml_data(), inspected_file_to_py(), provenance_token(), PyInspectedYamlDataFile, PyInstalledYamlDataInspection, PyInstalledYamlDataSnapshot (+6 more)

### Community 61 - "Community 61"
Cohesion: 0.17
Nodes (16): convert_severity(), parse_wrye_report(), PyWryeBashParser, PyWryeIssue, PyWryeSeverity, register_wrye(), Bound, HashMap (+8 more)

### Community 62 - "Community 62"
Cohesion: 0.14
Nodes (16): PyNamedRecordFinding, PyNamedRecordFindingAnalysisInput, PyNamedRecordFindingAnalysisResult, PyNamedRecordFindingAnalyzer, register(), Bound, CoreAnalysisInput, CoreAnalysisResult (+8 more)

### Community 63 - "Community 63"
Cohesion: 0.14
Nodes (16): PyPluginEvidence, PyPluginEvidenceAnalysisInput, PyPluginEvidenceAnalysisResult, PyPluginEvidenceAnalyzer, register(), Bound, CoreAnalysisInput, CoreAnalysisResult (+8 more)

### Community 64 - "Community 64"
Cohesion: 0.19
Nodes (12): BA2Scanner, PyBA2Issues, PyBA2Scanner, register_ba2(), Bound, PathBuf, PyModule, PyResult (+4 more)

### Community 65 - "Community 65"
Cohesion: 0.17
Nodes (15): detect_config_duplicates(), PyConfigDuplicateDetector, PyDuplicateGroup, register_config(), Bound, PathBuf, Py, PyDict (+7 more)

### Community 66 - "Community 66"
Cohesion: 0.13
Nodes (8): PyYamlFile, register(), Bound, PyModule, PyResult, Self, String, YamlFile

### Community 67 - "Community 67"
Cohesion: 0.20
Nodes (12): PyUnpackedIssues, PyUnpackedScanner, register_unpacked(), Bound, PathBuf, PyModule, PyResult, Self (+4 more)

### Community 68 - "Community 68"
Cohesion: 0.16
Nodes (11): PyRustFormIDAnalyzer, Bound, Default, Option, PyDict, PyResult, Python, Self (+3 more)

### Community 69 - "Community 69"
Cohesion: 0.19
Nodes (6): PyScanRunEvent, PyScanRunLogEvent, PyScanRunSetupContext, Option, setup_context_to_core(), CrashLogScanSetupContext

### Community 70 - "Community 70"
Cohesion: 0.17
Nodes (12): classic_user_settings(), frontend_transition_outcome_to_py(), PyUserSettingsFrontendTransitionOutcome, PyUserSettingsUpdateDiagnostic, Bound, Py, PyAny, PyModule (+4 more)

### Community 71 - "Community 71"
Cohesion: 0.13
Nodes (14): classic_version(), extract_all_versions(), extract_pe_version(), extract_version_from_filename(), extract_version_from_log(), format_version(), parse_version(), Bound (+6 more)

### Community 72 - "Community 72"
Cohesion: 0.13
Nodes (7): AddressLibraryConfig, PyAddressLibraryConfig, PyUnknownVersionHandling, From, HashMap, Self, UnknownVersionHandling

### Community 73 - "Community 73"
Cohesion: 0.14
Nodes (16): BindingDiagnostic, inspect_binding(), list_bindings(), public_exports(), Any, ModuleType, Structured import diagnostics for maintained CLASSIC Python bindings., Import status and public surface metadata for one binding module. (+8 more)

### Community 74 - "Community 74"
Cohesion: 0.16
Nodes (11): analyzer_error_parts_to_pyerr(), analyzer_error_to_pyerr(), PyAnalyzerKind, PyAutoscanReportPlacement, PyCrashgenSettingsAnalyzer, CoreAnalyzer, HashSet, PyErr (+3 more)

### Community 75 - "Community 75"
Cohesion: 0.14
Nodes (16): migration_diagnostic_to_py(), migration_endpoint_to_py(), migration_plan_to_py(), migration_planning_outcome_to_py(), PyUserSettingsMigrationDiagnostic, PyUserSettingsMigrationEndpoint, PyUserSettingsMigrationPlan, PyUserSettingsMigrationPlanningOutcome (+8 more)

### Community 76 - "Community 76"
Cohesion: 0.14
Nodes (6): PyCrashgenConfig, register(), Bound, PyModule, PyResult, CrashgenConfig

### Community 77 - "Community 77"
Cohesion: 0.20
Nodes (9): PyFileHasher, Bound, Py, PyAny, PyDict, PyResult, Python, String (+1 more)

### Community 78 - "Community 78"
Cohesion: 0.23
Nodes (8): PyLogCollector, Option, PyResult, Python, Self, String, Vec, LogCollector

### Community 79 - "Community 79"
Cohesion: 0.24
Nodes (12): process_logs(), PyLogErrorEntry, PyLogProcessor, register_logs(), Bound, PathBuf, PyModule, PyResult (+4 more)

### Community 80 - "Community 80"
Cohesion: 0.21
Nodes (6): PyConfigIssue, From, Option, Self, String, ConfigIssue

### Community 81 - "Community 81"
Cohesion: 0.23
Nodes (7): PyInstalledYamlDataDiagnostic, PyLocalIgnoreResetConflictOutcome, PyLocalIgnoreResetOutcome, Option, PathBuf, Vec, CoreYamlDataContentIdentity

### Community 82 - "Community 82"
Cohesion: 0.20
Nodes (13): crashgen_snapshot_from_py_sections(), PyCrashgenSettingsAnalysisInput, register(), Bound, CoreAnalysisInput, PyAny, PyDict, PyModule (+5 more)

### Community 83 - "Community 83"
Cohesion: 0.18
Nodes (11): PyAnalyzerSeverity, PyCrashgenExpectationOutcome, PyCrashgenSettingsAnalysisResult, PyDisabledSettingNotice, CoreAnalysisResult, From, Option, RuleSeverity (+3 more)

### Community 84 - "Community 84"
Cohesion: 0.19
Nodes (12): AcceptedUserSettingsUpdate, PyCrashLogScanSettings, PyUserSettingsUpdateField, PyUserSettingsUpdatePreview, PyUserSettingsUpdateValue, HashMap, PyRef, Vec (+4 more)

### Community 85 - "Community 85"
Cohesion: 0.32
Nodes (14): BTreeMap, BTreeSet, build_archived_report(), build_combined_scan_report(), build_unpacked_report(), dict_to_btreemap(), get_scan_issue_messages(), register_game_report() (+6 more)

### Community 86 - "Community 86"
Cohesion: 0.30
Nodes (6): PyLocalIgnoreRecoveryPlan, register(), Bound, PyModule, PyResult, CoreRecoveryPlan

### Community 87 - "Community 87"
Cohesion: 0.16
Nodes (15): _fixture_yaml_root(), _path_is_relative_to(), Path, Return whether one final per-log disposition succeeded., Return a JSON-safe summary for a failed per-log scan result., Return whether path is under root without requiring either to exist., Find a fixture-local YAML root for deterministic compliance scans., Map a User Settings game token to the shared binding's typed identity. (+7 more)

### Community 88 - "Community 88"
Cohesion: 0.19
Nodes (7): PyPatternMatcher, Option, PyResult, Self, String, Vec, PatternMatcher

### Community 89 - "Community 89"
Cohesion: 0.23
Nodes (14): Path, Runtime coverage for side-effect-free User Settings migration planning., Return the repository-level User Settings compatibility corpus., Describe both legacy-location and unversioned transitions without relocating fil, Publish an approved plan, report its verified backup, and restore it explicitly., Preserve newer documents on apply/restore conflicts and type operational failure, Expose every flat-shape transition and its exact in-memory inverse., Distinguish a current no-op from an unsupported version gap without writes. (+6 more)

### Community 90 - "Community 90"
Cohesion: 0.25
Nodes (4): Message, Option, PyRefMut, String

### Community 91 - "Community 91"
Cohesion: 0.17
Nodes (12): installed_yaml_data_error_to_py(), installed_yaml_data_load_error_to_py(), local_ignore_reset_error_to_py(), reset_publication_stage_token(), role_token(), PyErr, replacement_durability_unknown_projects_string_paths_and_receipt(), CoreInstalledYamlDataInspectionError (+4 more)

### Community 92 - "Community 92"
Cohesion: 0.26
Nodes (11): ModGuidanceAnalysisResult, ModGuidanceAnalyzer, _analyze(), _analyzer(), Runtime contract tests for semantic Mod Guidance analysis., Represent absent conflict remediation as ``None`` end to end., test_mod_guidance_analyzer_accepts_and_preserves_missing_fix(), test_mod_guidance_analyzer_error_exposes_kind_code_and_message() (+3 more)

### Community 93 - "Community 93"
Cohesion: 0.23
Nodes (3): PyExplicitYamlDataGame, GameId, Self

### Community 94 - "Community 94"
Cohesion: 0.24
Nodes (3): core::MessageTarget, MessageTarget, From

### Community 95 - "Community 95"
Cohesion: 0.24
Nodes (3): core::MessageType, MessageType, Self

### Community 96 - "Community 96"
Cohesion: 0.17
Nodes (11): compliance_explain(), compliance_list(), List compliance scenarios from the data-backed catalog., Explain one compliance scenario by stable ID., all_scenarios(), get_scenario(), Data-backed compliance scenario catalog for the Python CLI., Return the maintained scenario catalog. (+3 more)

### Community 97 - "Community 97"
Cohesion: 0.36
Nodes (11): bench_formid_extraction(), bench_log_parsing(), bench_mod_detection(), bench_plugin_matching(), bench_suspect_scanning(), generate_plugins(), generate_test_log_lines(), Criterion (+3 more)

### Community 98 - "Community 98"
Cohesion: 0.27
Nodes (11): ExplicitYamlDataPaths, Path, Focused public-contract tests for deterministic explicit YAML Data loading., A missing exact Local Ignore path stays missing after the typed read error., Write arbitrary-name fixtures and return the public typed path request., The snapshot keeps parsed data and identity tied to the original bytes., Unsupported games and malformed Local Ignore data stay distinguishable., test_explicit_loader_does_not_generate_a_missing_ignore_file() (+3 more)

### Community 99 - "Community 99"
Cohesion: 0.20
Nodes (11): FormIDPlugin, plugin(), Path, Public-seam tests for semantic FormID Finding analysis., Create one owned plugin-prefix fact., The Python result keeps all semantic states without rendered report lines., Operational lookup failure uses the common analyzer exception envelope., SQLite setup failure uses the same analyzer exception envelope as analysis. (+3 more)

### Community 100 - "Community 100"
Cohesion: 0.17
Nodes (11): Smoke tests for Phase 3 Plan 08 classic_file_io promotion (105 contract rows)., clear_cache is synchronous and returns None., Fewer than 128 bytes is not a valid DDS header., EncodingDetector() is parameterless; detect_encoding returns str., R13: cache_size() is #[staticmethod] — call via class, not instance.      Retu, cache_stats() static method returns a dict with the canonical 5 keys., test_dds_header_from_bytes_none_on_short_bytes(), test_encoding_detector_default_construction_and_detect() (+3 more)

### Community 101 - "Community 101"
Cohesion: 0.27
Nodes (6): load_installed_yaml_data(), PyInstalledYamlDataLoadOutcome, PyInstalledYamlDataLocalIgnoreRecoveryRequiredOutcome, Py, PyAny, Python

### Community 102 - "Community 102"
Cohesion: 0.20
Nodes (10): load_main_yaml_version(), main_yaml_version_error_to_py(), register(), Bound, Option, PyErr, PyModule, PyResult (+2 more)

### Community 103 - "Community 103"
Cohesion: 0.40
Nodes (10): CrashgenSettingsAnalysisResult, CrashgenSettingsAnalyzer, _analyze(), _entry(), Runtime contract tests for semantic Crashgen Settings Analysis., test_crashgen_analyzer_error_exposes_kind_code_and_message(), test_crashgen_analyzer_handle_is_reusable_across_python_threads(), test_crashgen_analyzer_rejects_tolerantly_parsed_rule_diagnostics() (+2 more)

### Community 104 - "Community 104"
Cohesion: 0.35
Nodes (10): load_module(), minimal_coverage_summary(), minimal_diff_report(), MonkeyPatch, parametrize, Path, Tests for Node/Python parity gate baseline refresh behavior., test_load_module_restores_import_state() (+2 more)

### Community 105 - "Community 105"
Cohesion: 0.18
Nodes (11): Path, hash_file returns the lowercase hex SHA256 of the file contents., hash_files_parallel returns a dict mapping paths to hashes-or-None., file_exists / get_file_size / get_file_info are synchronous helpers., PySyncLineStreamer is a real Python iterator obtained via FileIOCore.      Exe, PyLineStreamer is an async iterator — exercises __aiter__ / __anext__., test_file_hasher_hash_file_sha256_roundtrip(), test_file_hasher_hash_files_parallel_returns_dict() (+3 more)

### Community 107 - "Community 107"
Cohesion: 0.36
Nodes (9): CrashSuspectAnalysisResult, CrashSuspectAnalyzer, _analyze(), _analyzer(), Runtime contract tests for semantic Crash Suspect analysis., test_crash_suspect_analyzer_error_exposes_kind_code_and_message(), test_crash_suspect_analyzer_handle_is_reusable_across_python_threads(), test_crash_suspect_analyzer_returns_explicit_empty_result() (+1 more)

### Community 108 - "Community 108"
Cohesion: 0.20
Nodes (9): Smoke tests for the app-notification PyO3 surface.  Verifies that ``check_app_, All public names land on the `classic_update` module namespace., ClassicNotificationError subclasses ClassicUpdateError, and each     variant-sp, Unparseable ``installed_version`` must deterministically raise     :class:`Clas, Consumers that catch :class:`ClassicNotificationError` (or the     broader :cla, test_check_app_notification_rejects_unparseable_installed_version(), test_exception_hierarchy_is_exported_and_well_formed(), test_installed_version_parse_error_is_subclass_of_notification_base() (+1 more)

### Community 109 - "Community 109"
Cohesion: 0.20
Nodes (9): Per-class smoke tests for Phase 3 Plan 02 - scanlog Wave 1 (parsing primitives)., RecordScanner.clear_cache() runs without raising., PluginAnalyzer(game_ignore_plugins, ignore_list, crashgen_name) - first 3 requir, PatternMatcher.clear_cache() runs without raising., LogParser(custom_boundaries=...) with explicit boundary list., test_log_parser_construct_with_custom_boundaries(), test_pattern_matcher_clear_cache(), test_plugin_analyzer_construct() (+1 more)

### Community 110 - "Community 110"
Cohesion: 0.24
Nodes (9): CompletedProcess, parametrize, Unicode output guard coverage for PyO3 binding imports., Run Python with a legacy strict stdout encoding., Each binding module applies the shared import-time stdout/stderr guard., The binding keeps Unicode strings intact but makes legacy printing safe., _run_with_strict_cp1252_stdio(), test_binding_import_makes_legacy_stdio_safe() (+1 more)

### Community 111 - "Community 111"
Cohesion: 0.29
Nodes (8): _main_entry(), Any, Smoke tests for the yaml-update-delivery PyO3 surface.  These tests verify tha, Canonical entry for ``CLASSIC Main.yaml`` matching the client_schemas     const, test_apply_yaml_update_accepts_request_object(), test_check_yaml_update_accepts_bundled_yaml_dir_kwarg(), test_check_yaml_update_disabled_short_circuits(), test_yaml_client_schema_entry_defaults()

### Community 112 - "Community 112"
Cohesion: 0.39
Nodes (8): bench_batch_aggregation(), bench_dds_header_parsing(), bench_path_filtering(), bench_path_processing(), generate_test_paths(), Criterion, PathBuf, Vec

### Community 113 - "Community 113"
Cohesion: 0.31
Nodes (5): PyEncodingDetector, Default, Self, String, EncodingDetector

### Community 114 - "Community 114"
Cohesion: 0.39
Nodes (8): exclude_when_from_pydict(), exclude_when_to_pydict(), Bound, Option, PyDict, PyResult, Python, CoreModExclude

### Community 115 - "Community 115"
Cohesion: 0.42
Nodes (8): analyzer_entry(), python_construction_error_exposes_kind_code_and_message(), python_projection_preserves_semantics_and_explicit_empty_results(), Bound, PyDict, PyResult, Python, settings()

### Community 116 - "Community 116"
Cohesion: 0.32
Nodes (7): classic_message(), format_contract_event(), format_log_message(), Bound, HashMap, PyModule, PyResult

### Community 117 - "Community 117"
Cohesion: 0.25
Nodes (7): classic_scangame(), Bound, Display, PyErr, PyModule, PyResult, to_pyerr()

### Community 118 - "Community 118"
Cohesion: 0.25
Nodes (7): Smoke tests for the classic_shared Python module (HARM-03 / HARM-04, Phase 3 Pla, cache_stats, cache_metrics, clear_cache, cleanup_cache all callable., process_batch / process_batch_fast / intern_batch return list[str]., HARM-03 / D-10 step 3 — RuntimeStats factory returns a populated struct., test_get_runtime_stats_returns_healthy_struct(), test_path_handler_cache_helpers(), test_string_processor_batch_operations()

### Community 119 - "Community 119"
Cohesion: 0.38
Nodes (5): match_version_string(), register(), Bound, PyModule, PyResult

### Community 120 - "Community 120"
Cohesion: 0.43
Nodes (5): load_tool_module(), Tests for shared binding runtime coverage tooling., test_build_coverage_summary_classifies_runtime_and_newly_uncovered(), test_build_coverage_summary_flags_tier1_rows_without_runtime_metadata(), test_build_coverage_summary_reports_selector_snapshot_mismatch()

### Community 121 - "Community 121"
Cohesion: 0.43
Nodes (5): load_generate_baseline_module(), Tests for method-aware Python parity tooling., test_generate_diff_report_flags_missing_contract_python_export_identifier(), test_generate_diff_report_matches_python_export_paths(), test_parse_python_surface_tracks_method_export_paths()

### Community 123 - "Community 123"
Cohesion: 0.33
Nodes (4): installed_yaml_data_diagnostic_kind_to_string(), installed_yaml_data_diagnostic_to_py(), InstalledYamlDataRunDiagnostic, InstalledYamlDataRunDiagnosticKind

### Community 124 - "Community 124"
Cohesion: 0.40
Nodes (3): Self, String, TestClass

### Community 125 - "Community 125"
Cohesion: 0.33
Nodes (5): Behavioral coverage for the owned strict FormID Value Lookup facade., Owned replies cross PyO3 without callbacks or collapsed failure states., Disabled and existing-pool adapters expose positional semantic outcomes., test_disabled_and_shared_pool_adapters_remain_owned(), test_in_memory_lookup_distinguishes_hit_miss_malformed_and_failure()

### Community 126 - "Community 126"
Cohesion: 0.40
Nodes (4): classic_update(), Bound, PyModule, PyResult

### Community 127 - "Community 127"
Cohesion: 0.40
Nodes (5): migration_change_kind_token(), migration_change_to_py(), PyUserSettingsMigrationChange, MigrationChange, MigrationChangeKind

### Community 128 - "Community 128"
Cohesion: 0.40
Nodes (4): classic_version_registry(), Bound, PyModule, PyResult

### Community 129 - "Community 129"
Cohesion: 0.50
Nodes (3): _import_classic_scanlog(), Focused regression tests for Phase 2 dead code removal., test_gpu_detector_binding_is_stateless_and_repeatable()

### Community 131 - "Community 131"
Cohesion: 0.67
Nodes (3): commit_outcome_to_py(), PyUserSettingsCommitOutcome, UserSettingsCommitOutcome

### Community 134 - "Community 134"
Cohesion: 0.50
Nodes (4): Path, Prepare Game Setup from typed User Settings without rewriting the document., test_scangame_game_setup_intake_helpers_smoke(), test_scangame_game_setup_intake_opens_canonical_user_settings()

### Community 137 - "Community 137"
Cohesion: 0.67
Nodes (3): MonkeyPatch, generate_ignore_file_async and generate_local_yaml_async are callable.      Bo, test_generate_ignore_file_async_and_local_yaml_async()

### Community 138 - "Community 138"
Cohesion: 0.67
Nodes (3): Path, LogParser.parse_complete([]) returns a ScanOutput factory product., test_log_parser_parse_complete_returns_scan_output()

## Knowledge Gaps
- **16 isolated node(s):** `classic-py-cli`, `Keys`, `classic-python-bindings-tools`, `Python Binding Audit Criteria`, `Binding-Layer Business Logic Prohibition` (+11 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **80 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `clear_all()` connect `Community 10` to `Community 38`?**
  _High betweenness centrality (0.004) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `CommandContext` (e.g. with `_ComplianceExplainArgs` and `_ComplianceRunArgs`) actually correct?**
  _`CommandContext` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `CommandResult` (e.g. with `_ComplianceExplainArgs` and `_ComplianceRunArgs`) actually correct?**
  _`CommandResult` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `classic-py-cli`, `Keys`, `classic-python-bindings-tools` to the rest of the system?**
  _16 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.014084507042253521 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.05956112852664577 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.07927565392354124 - nodes in this community are weakly interconnected._