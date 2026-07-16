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
