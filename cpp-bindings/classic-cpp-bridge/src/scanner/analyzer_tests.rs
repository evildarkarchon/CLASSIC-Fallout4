use std::sync::Arc;

use super::*;

fn rules_json() -> String {
    serde_json::json!({
        "version": 1,
        "preflight": [{
            "id": "plugin_notice",
            "when": { "plugin_any": ["Example.dll"] },
            "action": {
                "kind": "notice",
                "placement": "error_information",
                "severity": "info",
                "message": "{crashgen_name} found Example.dll",
                "fix": "Remove Example.dll"
            }
        }],
        "checks": [{
            "id": "memory_manager",
            "target": {
                "section": "Patches",
                "key": "MemoryManager",
                "type": "bool"
            },
            "expect": { "equals": true },
            "messages": {
                "fail": "Enable {setting} in {display_section}",
                "fix": "Set {setting} to true",
                "pass": "{setting} is enabled"
            },
            "severity": "warning"
        }]
    })
    .to_string()
}

fn valid_configuration() -> ffi::CrashgenSettingsAnalyzerConfigurationDto {
    ffi::CrashgenSettingsAnalyzerConfigurationDto {
        crashgen_name: "Buffout 4".to_string(),
        display_section: "[Compatibility]".to_string(),
        ignore_keys: vec!["IgnoreMe".to_string()],
        has_settings_rules: true,
        has_settings_rules_version: true,
        settings_rules_version: 1,
        settings_rules_json: rules_json(),
    }
}

fn input_with_failure() -> ffi::CrashgenSettingsAnalysisInputDto {
    ffi::CrashgenSettingsAnalysisInputDto {
        settings: vec![
            ffi::CrashgenSettingDto {
                has_section: true,
                section: "Patches".to_string(),
                key: "MemoryManager".to_string(),
                value: "false".to_string(),
            },
            ffi::CrashgenSettingDto {
                has_section: false,
                section: String::new(),
                key: "DisabledThing".to_string(),
                value: "false".to_string(),
            },
            ffi::CrashgenSettingDto {
                has_section: false,
                section: String::new(),
                key: "IgnoreMe".to_string(),
                value: "false".to_string(),
            },
        ],
        installed_plugins: vec![" EXAMPLE.DLL ".to_string()],
        has_crashgen_version: true,
        crashgen_version_major: 1,
        crashgen_version_minor: 28,
        crashgen_version_patch: 6,
        config_layout: ffi::CrashgenConfigLayout::Og,
    }
}

fn empty_input() -> ffi::CrashgenSettingsAnalysisInputDto {
    ffi::CrashgenSettingsAnalysisInputDto {
        settings: Vec::new(),
        installed_plugins: Vec::new(),
        has_crashgen_version: false,
        crashgen_version_major: 0,
        crashgen_version_minor: 0,
        crashgen_version_patch: 0,
        config_layout: ffi::CrashgenConfigLayout::Unknown,
    }
}

fn valid_crash_suspect_configuration() -> ffi::CrashSuspectAnalyzerConfigurationDto {
    ffi::CrashSuspectAnalyzerConfigurationDto {
        main_error_rules: vec![ffi::CrashSuspectMainErrorRuleDto {
            id: "main-rule".to_string(),
            name: "Main Rule".to_string(),
            severity: 5,
            main_error_contains_any: vec!["plugin.dll".to_string()],
        }],
        stack_rules: vec![ffi::CrashSuspectStackRuleDto {
            id: "stack-rule".to_string(),
            name: "Stack Rule".to_string(),
            severity: 4,
            main_error_required_any: Vec::new(),
            main_error_optional_any: Vec::new(),
            stack_contains_any: vec!["StackSignal".to_string()],
            exclude_if_stack_contains_any: Vec::new(),
            stack_contains_at_least: Vec::new(),
        }],
    }
}

fn valid_mod_guidance_configuration() -> ffi::ModGuidanceAnalyzerConfigurationDto {
    ffi::ModGuidanceAnalyzerConfigurationDto {
        conflicts: vec![
            ffi::ModGuidanceConflictConfigurationDto {
                mod_a: "AlphaPlugin".to_string(),
                mod_b: "BetaPlugin".to_string(),
                name_a: "Alpha Mod".to_string(),
                name_b: "Beta Mod".to_string(),
                description: "These mods conflict".to_string(),
                fix: "Install the compatibility patch".to_string(),
                has_link: true,
                link: "https://example.com/patch".to_string(),
            },
            ffi::ModGuidanceConflictConfigurationDto {
                mod_a: "GammaPlugin".to_string(),
                mod_b: "DeltaPlugin".to_string(),
                name_a: "Gamma Mod".to_string(),
                name_b: "Delta Mod".to_string(),
                description: "These mods also conflict".to_string(),
                fix: "Remove one mod".to_string(),
                has_link: false,
                link: "ignored".to_string(),
            },
        ],
        frequent_crashes: vec![ffi::ModGuidanceSolutionConfigurationDto {
            id: "frequent-crash".to_string(),
            criteria_kind: ffi::ModGuidanceCriteriaKind::Any,
            criteria: vec!["FreqPart".to_string()],
            exceptions: Vec::new(),
            name: "Frequent Crash Mod".to_string(),
            description: "Frequently appears in crash reports".to_string(),
        }],
        solutions: vec![ffi::ModGuidanceSolutionConfigurationDto {
            id: "solution".to_string(),
            criteria_kind: ffi::ModGuidanceCriteriaKind::All,
            criteria: vec!["SolutionA".to_string(), "SolutionB".to_string()],
            exceptions: Vec::new(),
            name: "Solution Mod".to_string(),
            description: "Use the documented solution".to_string(),
        }],
        important_mods: vec![
            ffi::ModGuidanceImportantModConfigurationDto {
                detect: "NvidiaFix".to_string(),
                name: "NVIDIA Fix".to_string(),
                description: "Fix for NVIDIA users".to_string(),
                has_gpu: true,
                gpu: "nvidia".to_string(),
                has_gpu_mismatch_warning: true,
                gpu_mismatch_warning: "This fix is not for your GPU".to_string(),
                has_exclude_when_plugin_any: false,
                exclude_when_plugin_any: Vec::new(),
            },
            ffi::ModGuidanceImportantModConfigurationDto {
                detect: "MissingCore".to_string(),
                name: "Missing Core Mod".to_string(),
                description: "Install this important mod".to_string(),
                has_gpu: false,
                gpu: "ignored".to_string(),
                has_gpu_mismatch_warning: false,
                gpu_mismatch_warning: "ignored".to_string(),
                has_exclude_when_plugin_any: false,
                exclude_when_plugin_any: Vec::new(),
            },
        ],
    }
}

fn matching_mod_guidance_input() -> ffi::ModGuidanceAnalysisInputDto {
    ffi::ModGuidanceAnalysisInputDto {
        plugins: vec![
            ("AlphaPlugin.esp", "FE:001"),
            ("BetaPlugin.esp", "FE:002"),
            ("GammaPlugin.esp", "FE:003"),
            ("DeltaPlugin.esp", "FE:004"),
            ("FreqPart.esp", "FE:005"),
            ("SolutionA.esp", "FE:006"),
            ("SolutionB.esp", "FE:007"),
        ]
        .into_iter()
        .map(|(name, id)| ffi::ModGuidancePluginDto {
            name: name.to_string(),
            id: id.to_string(),
        })
        .collect(),
        has_user_gpu: true,
        user_gpu: "amd".to_string(),
        xse_modules: vec!["NvidiaFix.dll".to_string()],
    }
}

fn empty_mod_guidance_configuration() -> ffi::ModGuidanceAnalyzerConfigurationDto {
    ffi::ModGuidanceAnalyzerConfigurationDto {
        conflicts: Vec::new(),
        frequent_crashes: Vec::new(),
        solutions: Vec::new(),
        important_mods: Vec::new(),
    }
}

#[test]
fn crash_suspect_analysis_projects_individual_semantic_findings() {
    let analyzer = crash_suspect_analyzer_new(valid_crash_suspect_configuration());

    let execution = crash_suspect_analyze(
        &analyzer,
        ffi::CrashSuspectAnalysisInputDto {
            main_error: "plugin.dll".to_string(),
            call_stack: "StackSignal".to_string(),
        },
    );

    assert!(execution.has_result, "{}", execution.error.message);
    assert!(!execution.has_error);
    assert_eq!(execution.result.findings.len(), 3);
    let main = &execution.result.findings[0];
    assert_eq!(main.kind, ffi::CrashSuspectFindingKind::MainErrorRule);
    assert!(main.has_rule_id);
    assert_eq!(main.rule_id, "main-rule");
    assert!(main.has_name);
    assert_eq!(main.name, "Main Rule");
    assert!(main.has_severity);
    assert_eq!(main.severity, 5);
    assert_eq!(
        execution.result.findings[1].kind,
        ffi::CrashSuspectFindingKind::StackRule
    );
    let dll = &execution.result.findings[2];
    assert_eq!(dll.kind, ffi::CrashSuspectFindingKind::DllInvolvement);
    assert!(!dll.has_rule_id);
    assert!(!dll.has_name);
    assert!(!dll.has_severity);
}

#[test]
fn crash_suspect_invalid_configuration_preserves_shared_error() {
    let mut configuration = valid_crash_suspect_configuration();
    configuration.main_error_rules[0].id.clear();
    let analyzer = crash_suspect_analyzer_new(configuration);

    let construction = crash_suspect_analyzer_construction_result(&analyzer);

    assert!(!construction.has_analyzer);
    assert!(construction.has_error);
    assert_eq!(
        construction.error.analyzer_kind,
        ffi::AnalyzerKind::CrashSuspect
    );
    assert_eq!(
        construction.error.code,
        ffi::AnalyzerErrorCode::InvalidConfiguration
    );
}

#[test]
fn mod_guidance_analysis_projects_all_families_and_optional_presence() {
    let analyzer = mod_guidance_analyzer_new(valid_mod_guidance_configuration());

    let execution = mod_guidance_analyze(&analyzer, matching_mod_guidance_input());

    assert!(execution.has_result, "{}", execution.error.message);
    assert!(!execution.has_error);
    assert_eq!(execution.result.conflicts.len(), 2);
    let linked_conflict = &execution.result.conflicts[0];
    assert_eq!(linked_conflict.state, ffi::ModGuidanceMatchState::Matched);
    assert_eq!(linked_conflict.name_a, "Alpha Mod");
    assert_eq!(linked_conflict.fix, "Install the compatibility patch");
    assert!(linked_conflict.has_link);
    assert_eq!(linked_conflict.link, "https://example.com/patch");
    assert!(!execution.result.conflicts[1].has_link);
    assert!(execution.result.conflicts[1].link.is_empty());

    assert_eq!(execution.result.frequent_crashes.len(), 1);
    let frequent = &execution.result.frequent_crashes[0];
    assert_eq!(frequent.id, "frequent-crash");
    assert_eq!(frequent.matched_plugin_ids, ["FE:005"]);

    assert_eq!(execution.result.solutions.len(), 1);
    assert_eq!(
        execution.result.solutions[0].matched_plugin_ids,
        ["FE:006", "FE:007"]
    );

    assert_eq!(execution.result.important_mods.len(), 2);
    let mismatch = &execution.result.important_mods[0];
    assert_eq!(mismatch.state, ffi::ModGuidanceMatchState::GpuMismatch);
    assert!(mismatch.has_gpu);
    assert_eq!(mismatch.gpu, "nvidia");
    assert!(mismatch.has_gpu_mismatch_warning);
    assert_eq!(
        mismatch.gpu_mismatch_warning,
        "This fix is not for your GPU"
    );
    let missing = &execution.result.important_mods[1];
    assert_eq!(missing.state, ffi::ModGuidanceMatchState::Missing);
    assert!(!missing.has_gpu);
    assert!(missing.gpu.is_empty());
    assert!(!missing.has_gpu_mismatch_warning);
    assert!(missing.gpu_mismatch_warning.is_empty());
}

#[test]
fn mod_guidance_projects_important_mod_plugin_exclusions() {
    let mut configuration = valid_mod_guidance_configuration();
    configuration.important_mods[0].has_exclude_when_plugin_any = true;
    configuration.important_mods[0].exclude_when_plugin_any = vec!["Suppressor.esp".to_string()];
    let analyzer = mod_guidance_analyzer_new(configuration);
    let mut input = matching_mod_guidance_input();
    input.plugins.push(ffi::ModGuidancePluginDto {
        name: "Suppressor.esp".to_string(),
        id: "FE:008".to_string(),
    });

    let execution = mod_guidance_analyze(&analyzer, input);

    assert!(execution.has_result, "{}", execution.error.message);
    assert_eq!(execution.result.important_mods.len(), 1);
    assert_eq!(execution.result.important_mods[0].name, "Missing Core Mod");
}

#[test]
fn mod_guidance_invalid_configuration_preserves_shared_typed_error() {
    let mut configuration = valid_mod_guidance_configuration();
    configuration.conflicts[0].mod_a.clear();
    let analyzer = mod_guidance_analyzer_new(configuration);

    let construction = mod_guidance_analyzer_construction_result(&analyzer);
    let execution = mod_guidance_analyze(&analyzer, matching_mod_guidance_input());

    assert!(!construction.has_analyzer);
    assert!(construction.has_error);
    assert_eq!(
        construction.error.analyzer_kind,
        ffi::AnalyzerKind::ModGuidance
    );
    assert_eq!(
        construction.error.code,
        ffi::AnalyzerErrorCode::InvalidConfiguration
    );
    assert!(construction.error.message.contains("conflict mod_a"));
    assert!(!execution.has_result);
    assert!(execution.has_error);
    assert_eq!(execution.error.message, construction.error.message);
}

#[test]
fn completed_mod_guidance_no_match_is_an_explicit_empty_result() {
    let analyzer = mod_guidance_analyzer_new(empty_mod_guidance_configuration());

    let execution = mod_guidance_analyze(
        &analyzer,
        ffi::ModGuidanceAnalysisInputDto {
            plugins: Vec::new(),
            has_user_gpu: false,
            user_gpu: "ignored".to_string(),
            xse_modules: Vec::new(),
        },
    );

    assert!(execution.has_result, "{}", execution.error.message);
    assert!(!execution.has_error);
    assert!(execution.result.conflicts.is_empty());
    assert!(execution.result.frequent_crashes.is_empty());
    assert!(execution.result.solutions.is_empty());
    assert!(execution.result.important_mods.is_empty());
}

#[test]
fn plugin_evidence_projects_owned_typed_counts_and_explicit_empty_success() {
    let analyzer = plugin_evidence_analyzer_new(ffi::PluginEvidenceAnalyzerConfigurationDto {
        ignored_plugins: vec!["Fallout4.esm".to_string()],
    });
    let construction = plugin_evidence_analyzer_construction_result(&analyzer);
    let populated = plugin_evidence_analyze(
        &analyzer,
        ffi::PluginEvidenceAnalysisInputDto {
            call_stack: vec![
                "Example.ESP and Fallout4.esm".to_string(),
                "example.esp".to_string(),
            ],
            plugins: vec![
                "Example.ESP".to_string(),
                "Fallout4.esm".to_string(),
                " ".to_string(),
            ],
        },
    );
    let empty = plugin_evidence_analyze(
        &analyzer,
        ffi::PluginEvidenceAnalysisInputDto {
            call_stack: Vec::new(),
            plugins: vec!["Example.ESP".to_string()],
        },
    );

    assert!(construction.has_analyzer);
    assert!(!construction.has_error);
    assert!(populated.has_result, "{}", populated.error.message);
    assert!(!populated.has_error);
    assert_eq!(populated.result.evidence.len(), 1);
    assert_eq!(populated.result.evidence[0].plugin, "example.esp");
    assert_eq!(populated.result.evidence[0].occurrences, 2);
    assert!(empty.has_result, "{}", empty.error.message);
    assert!(!empty.has_error);
    assert!(empty.result.evidence.is_empty());
}

#[test]
fn plugin_evidence_invalid_configuration_uses_the_shared_typed_error_envelope() {
    let analyzer = plugin_evidence_analyzer_new(ffi::PluginEvidenceAnalyzerConfigurationDto {
        ignored_plugins: vec!["   ".to_string()],
    });
    let construction = plugin_evidence_analyzer_construction_result(&analyzer);
    let execution = plugin_evidence_analyze(
        &analyzer,
        ffi::PluginEvidenceAnalysisInputDto {
            call_stack: Vec::new(),
            plugins: Vec::new(),
        },
    );

    assert!(!construction.has_analyzer);
    assert!(construction.has_error);
    assert_eq!(
        construction.error.analyzer_kind,
        ffi::AnalyzerKind::PluginEvidence
    );
    assert_eq!(
        construction.error.code,
        ffi::AnalyzerErrorCode::InvalidConfiguration
    );
    assert!(!execution.has_result);
    assert!(execution.has_error);
    assert_eq!(
        execution.error.analyzer_kind,
        ffi::AnalyzerKind::PluginEvidence
    );
    assert_eq!(
        execution.error.code,
        ffi::AnalyzerErrorCode::InvalidConfiguration
    );
    assert_eq!(execution.error.message, construction.error.message);
}

#[test]
fn plugin_evidence_handle_is_safe_for_concurrent_owned_calls() {
    let analyzer = Arc::from(plugin_evidence_analyzer_new(
        ffi::PluginEvidenceAnalyzerConfigurationDto {
            ignored_plugins: Vec::new(),
        },
    ));
    let tasks = (0..8)
        .map(|_| {
            let analyzer = Arc::clone(&analyzer);
            std::thread::spawn(move || {
                plugin_evidence_analyze(
                    &analyzer,
                    ffi::PluginEvidenceAnalysisInputDto {
                        call_stack: vec!["Example.esp".to_string()],
                        plugins: vec!["Example.esp".to_string()],
                    },
                )
            })
        })
        .collect::<Vec<_>>();

    for task in tasks {
        let execution = task.join().expect("analysis thread should not panic");
        assert!(execution.has_result, "{}", execution.error.message);
        assert!(!execution.has_error);
        assert_eq!(execution.result.evidence.len(), 1);
        assert_eq!(execution.result.evidence[0].plugin, "example.esp");
        assert_eq!(execution.result.evidence[0].occurrences, 1);
    }
}

#[test]
fn named_record_finding_projects_owned_typed_counts_and_explicit_empty_success() {
    let analyzer =
        named_record_finding_analyzer_new(ffi::NamedRecordFindingAnalyzerConfigurationDto {
            target_records: vec!["ActorBase".to_string()],
            ignored_records: vec!["System".to_string()],
        });
    let construction = named_record_finding_analyzer_construction_result(&analyzer);
    let populated = named_record_finding_analyze(
        &analyzer,
        ffi::NamedRecordFindingAnalysisInputDto {
            crash_lines: vec![
                "ActorBase_Player".to_string(),
                "ActorBase_System".to_string(),
                "ActorBase_Player".to_string(),
            ],
        },
    );
    let empty = named_record_finding_analyze(
        &analyzer,
        ffi::NamedRecordFindingAnalysisInputDto {
            crash_lines: vec!["unrelated".to_string()],
        },
    );

    assert!(construction.has_analyzer);
    assert!(!construction.has_error);
    assert!(populated.has_result);
    assert!(!populated.has_error);
    assert_eq!(populated.result.findings.len(), 1);
    assert_eq!(populated.result.findings[0].record, "ActorBase_Player");
    assert_eq!(populated.result.findings[0].occurrences, 2);
    assert!(empty.has_result);
    assert!(empty.result.findings.is_empty());
}

#[test]
fn named_record_finding_invalid_configuration_uses_shared_typed_error_envelope() {
    let analyzer =
        named_record_finding_analyzer_new(ffi::NamedRecordFindingAnalyzerConfigurationDto {
            target_records: vec![" ".to_string()],
            ignored_records: Vec::new(),
        });
    let construction = named_record_finding_analyzer_construction_result(&analyzer);
    let execution = named_record_finding_analyze(
        &analyzer,
        ffi::NamedRecordFindingAnalysisInputDto {
            crash_lines: Vec::new(),
        },
    );

    assert!(!construction.has_analyzer);
    assert!(construction.has_error);
    assert_eq!(
        construction.error.analyzer_kind,
        ffi::AnalyzerKind::NamedRecordFinding
    );
    assert_eq!(
        construction.error.code,
        ffi::AnalyzerErrorCode::InvalidConfiguration
    );
    assert!(!execution.has_result);
    assert!(execution.has_error);
    assert_eq!(
        execution.error.analyzer_kind,
        ffi::AnalyzerKind::NamedRecordFinding
    );
}

#[test]
fn construction_status_exposes_a_valid_immutable_handle() {
    let analyzer = crashgen_settings_analyzer_new(valid_configuration());

    let construction = crashgen_settings_analyzer_construction_result(&analyzer);

    assert!(construction.has_analyzer);
    assert!(!construction.has_error);
    assert!(construction.error.message.is_empty());
}

#[test]
fn analysis_projects_typed_outcomes_placement_optional_values_and_notices() {
    let analyzer = crashgen_settings_analyzer_new(valid_configuration());

    let execution = crashgen_settings_analyze(&analyzer, input_with_failure());

    assert!(execution.has_result, "{}", execution.error.message);
    assert!(!execution.has_error);
    assert_eq!(execution.result.expectation_outcomes.len(), 2);

    let notice = &execution.result.expectation_outcomes[0];
    assert_eq!(notice.rule_id, "plugin_notice");
    assert_eq!(notice.kind, ffi::CrashgenExpectationOutcomeKind::Notice);
    assert_eq!(notice.severity, ffi::CrashgenExpectationSeverity::Info);
    assert_eq!(notice.message, "Buffout 4 found Example.dll");
    assert!(notice.has_fix);
    assert_eq!(notice.fix, "Remove Example.dll");
    assert_eq!(
        notice.placement,
        ffi::AutoscanReportPlacement::ErrorInformation
    );
    assert!(!notice.has_section);
    assert!(!notice.has_setting);
    assert!(!notice.has_expected);
    assert!(!notice.has_actual);

    let issue = &execution.result.expectation_outcomes[1];
    assert_eq!(issue.rule_id, "memory_manager");
    assert_eq!(issue.kind, ffi::CrashgenExpectationOutcomeKind::Issue);
    assert_eq!(issue.severity, ffi::CrashgenExpectationSeverity::Warning);
    assert_eq!(issue.message, "Enable MemoryManager in [Compatibility]");
    assert_eq!(issue.fix, "Set MemoryManager to true");
    assert_eq!(issue.placement, ffi::AutoscanReportPlacement::Settings);
    assert!(issue.has_section);
    assert_eq!(issue.section, "Patches");
    assert!(issue.has_setting);
    assert_eq!(issue.setting, "MemoryManager");
    assert!(issue.has_expected);
    assert_eq!(issue.expected, "true");
    assert!(issue.has_actual);
    assert_eq!(issue.actual, "false");

    assert_eq!(execution.result.disabled_setting_notices.len(), 2);
    let disabled_names = execution
        .result
        .disabled_setting_notices
        .iter()
        .map(|notice| notice.setting_name.as_str())
        .collect::<Vec<_>>();
    assert!(disabled_names.contains(&"DisabledThing"));
    assert!(disabled_names.contains(&"MemoryManager"));
    assert!(!disabled_names.contains(&"IgnoreMe"));
}

#[test]
fn completed_analysis_with_no_matches_is_an_explicit_empty_result() {
    let analyzer = crashgen_settings_analyzer_new(valid_configuration());

    let execution = crashgen_settings_analyze(&analyzer, empty_input());

    assert!(execution.has_result);
    assert!(!execution.has_error);
    assert!(execution.result.expectation_outcomes.is_empty());
    assert!(execution.result.disabled_setting_notices.is_empty());
}

#[test]
fn malformed_carrier_configuration_returns_a_stable_typed_error() {
    let mut configuration = valid_configuration();
    configuration.settings_rules_json = "not json".to_string();
    let analyzer = crashgen_settings_analyzer_new(configuration);

    let construction = crashgen_settings_analyzer_construction_result(&analyzer);
    let execution = crashgen_settings_analyze(&analyzer, empty_input());

    assert!(!construction.has_analyzer);
    assert!(construction.has_error);
    assert_eq!(
        construction.error.analyzer_kind,
        ffi::AnalyzerKind::CrashgenSettings
    );
    assert_eq!(
        construction.error.code,
        ffi::AnalyzerErrorCode::InvalidConfiguration
    );
    assert!(construction.error.message.contains("not valid JSON"));
    assert!(!execution.has_result);
    assert!(execution.has_error);
    assert_eq!(execution.error.message, construction.error.message);
}

#[test]
fn parser_diagnostics_are_rejected_during_construction() {
    let mut configuration = valid_configuration();
    configuration.settings_rules_json = serde_json::json!({
        "version": 1,
        "preflight": [{ "id": "missing_action" }],
        "checks": []
    })
    .to_string();
    let analyzer = crashgen_settings_analyzer_new(configuration);

    let construction = crashgen_settings_analyzer_construction_result(&analyzer);

    assert!(!construction.has_analyzer);
    assert!(construction.has_error);
    assert_eq!(
        construction.error.code,
        ffi::AnalyzerErrorCode::InvalidConfiguration
    );
    assert!(construction.error.message.contains("$.preflight[0].action"));
}

#[test]
fn unsupported_rule_version_preserves_the_core_error_contract() {
    let mut configuration = valid_configuration();
    configuration.settings_rules_json = serde_json::json!({
        "version": 99,
        "preflight": [],
        "checks": []
    })
    .to_string();
    let analyzer = crashgen_settings_analyzer_new(configuration);

    let construction = crashgen_settings_analyzer_construction_result(&analyzer);

    assert!(!construction.has_analyzer);
    assert!(construction.has_error);
    assert_eq!(
        construction.error.analyzer_kind,
        ffi::AnalyzerKind::CrashgenSettings
    );
    assert_eq!(
        construction.error.code,
        ffi::AnalyzerErrorCode::UnsupportedConfigurationVersion
    );
    assert!(construction.error.message.contains("version 99"));
}

#[test]
fn unsupported_sibling_rule_version_is_validated_when_json_omits_version() {
    let mut configuration = valid_configuration();
    configuration.settings_rules_version = 99;
    configuration.settings_rules_json = serde_json::json!({
        "preflight": [],
        "checks": []
    })
    .to_string();
    let analyzer = crashgen_settings_analyzer_new(configuration);

    let construction = crashgen_settings_analyzer_construction_result(&analyzer);

    assert!(!construction.has_analyzer);
    assert!(construction.has_error);
    assert_eq!(
        construction.error.code,
        ffi::AnalyzerErrorCode::UnsupportedConfigurationVersion
    );
    assert!(construction.error.message.contains("version 99"));
}

#[test]
fn one_immutable_handle_is_safe_for_concurrent_owned_calls() {
    let analyzer = Arc::from(crashgen_settings_analyzer_new(valid_configuration()));
    let tasks = (0..8)
        .map(|_| {
            let analyzer = Arc::clone(&analyzer);
            std::thread::spawn(move || crashgen_settings_analyze(&analyzer, input_with_failure()))
        })
        .collect::<Vec<_>>();

    for task in tasks {
        let execution = task.join().expect("analysis thread should not panic");
        assert!(execution.has_result, "{}", execution.error.message);
        assert_eq!(execution.result.expectation_outcomes.len(), 2);
        assert_eq!(execution.result.disabled_setting_notices.len(), 2);
    }
}

#[test]
fn formid_finding_cxx_projects_owned_optional_values_and_unresolved_identifiers() {
    let analyzer = formid_finding_analyzer_in_memory_new(vec![ffi::FormIDFindingLookupEntryDto {
        formid: "123456".to_string(),
        plugin: "Found.esp".to_string(),
        reply_kind: ffi::FormIDFindingLookupReplyKind::Found,
        value: "Resolved value".to_string(),
        error_message: String::new(),
    }]);
    let construction = formid_finding_analyzer_construction_result(&analyzer);
    let execution = formid_finding_analyze(
        &analyzer,
        ffi::FormIDFindingAnalysisInputDto {
            crash_lines: vec![
                "Form ID: 0x01123456".to_string(),
                "Form ID: 0x02ABCDEF".to_string(),
            ],
            plugins: vec![ffi::FormIDPluginDto {
                name: "Found.esp".to_string(),
                prefix: "01".to_string(),
            }],
        },
    );

    assert!(construction.has_analyzer);
    assert!(execution.has_result, "{}", execution.error.message);
    assert_eq!(execution.result.findings.len(), 2);
    let found = &execution.result.findings[0];
    assert!(found.has_plugin);
    assert_eq!(found.plugin, "Found.esp");
    assert_eq!(
        found.value_lookup_status,
        ffi::FormIDValueLookupStatus::Found
    );
    assert!(found.has_value);
    assert_eq!(found.value, "Resolved value");
    let unresolved = &execution.result.findings[1];
    assert!(!unresolved.has_plugin);
    assert_eq!(
        unresolved.value_lookup_status,
        ffi::FormIDValueLookupStatus::NotApplicable
    );
    assert!(!unresolved.has_value);
}

#[test]
fn formid_finding_cxx_preserves_lookup_failure_as_shared_error() {
    let analyzer = formid_finding_analyzer_in_memory_new(vec![ffi::FormIDFindingLookupEntryDto {
        formid: "123456".to_string(),
        plugin: "Broken.esp".to_string(),
        reply_kind: ffi::FormIDFindingLookupReplyKind::OperationalFailure,
        value: String::new(),
        error_message: "fixture offline".to_string(),
    }]);
    let execution = formid_finding_analyze(
        &analyzer,
        ffi::FormIDFindingAnalysisInputDto {
            crash_lines: vec!["Form ID: 0x01123456".to_string()],
            plugins: vec![ffi::FormIDPluginDto {
                name: "Broken.esp".to_string(),
                prefix: "01".to_string(),
            }],
        },
    );

    assert!(!execution.has_result);
    assert!(execution.has_error);
    assert_eq!(
        execution.error.analyzer_kind,
        ffi::AnalyzerKind::FormIdFinding
    );
    assert_eq!(
        execution.error.code,
        ffi::AnalyzerErrorCode::OperationalFailure
    );
    assert!(execution.error.message.contains("fixture offline"));
}
