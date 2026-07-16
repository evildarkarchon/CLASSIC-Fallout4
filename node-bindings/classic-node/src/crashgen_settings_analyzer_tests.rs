use serde_json::json;

use super::*;
use crate::crashgen_rules::{
    JsCheckRule, JsCrashgenSettingsRules, JsExpectedValue, JsPreflightAction, JsPreflightRule,
    JsRuleMessages, JsRuleTarget,
};

fn registry_entry(version: u32) -> JsCrashgenRegistryEntry {
    JsCrashgenRegistryEntry {
        display_section: "[Compatibility]".to_string(),
        ignore_keys: vec!["IgnoredSetting".to_string()],
        checks: Vec::new(),
        settings_rules_version: Some(version),
        settings_rules: Some(JsCrashgenSettingsRules {
            version,
            preflight: vec![JsPreflightRule {
                id: "compatibility_notice".to_string(),
                when: json!({"plugin_any": ["MixedCase.DLL"]}),
                action: JsPreflightAction {
                    kind: "notice".to_string(),
                    placement: Some("error_information".to_string()),
                    bucket: None,
                    severity: "warning".to_string(),
                    message: "Compatibility guidance for {crashgen_name}".to_string(),
                    fix: Some("Compatibility fix".to_string()),
                },
            }],
            checks: vec![JsCheckRule {
                id: "setting_check".to_string(),
                target: JsRuleTarget {
                    section: "Patches".to_string(),
                    key: "Achievements".to_string(),
                    value_type: "bool".to_string(),
                },
                when: json!({}),
                expect: JsExpectedValue {
                    equals: json!(false),
                },
                messages: JsRuleMessages {
                    fail: "Expectation failed".to_string(),
                    fix: Some("Expectation fix".to_string()),
                    pass: None,
                },
                severity: "error".to_string(),
            }],
        }),
    }
}

fn populated_input() -> JsCrashgenSettingsAnalysisInput {
    JsCrashgenSettingsAnalysisInput {
        settings: vec![
            JsCrashgenSetting {
                section: Some("Patches".to_string()),
                key: "Achievements".to_string(),
                value: "true".to_string(),
            },
            JsCrashgenSetting {
                section: Some("Compatibility".to_string()),
                key: "DisabledSetting".to_string(),
                value: "false".to_string(),
            },
            JsCrashgenSetting {
                section: Some("Compatibility".to_string()),
                key: "IgnoredSetting".to_string(),
                value: "false".to_string(),
            },
        ],
        installed_plugins: vec!["MIXEDCASE.DLL".to_string()],
        crashgen_version: Some(JsCrashgenVersion {
            major: 1,
            minor: 30,
            patch: 0,
        }),
        config_layout: JsCrashgenConfigLayout::Og,
    }
}

#[test]
fn populated_analysis_projects_exact_semantic_fields_and_separate_notices() {
    let analyzer = build_analyzer("Buffout 4".to_string(), registry_entry(1)).unwrap();

    let result = analyzer.analyze_owned(populated_input()).unwrap();

    assert_eq!(result.expectation_outcomes.len(), 2);
    let compatibility = &result.expectation_outcomes[0];
    assert_eq!(compatibility.rule_id, "compatibility_notice");
    assert_eq!(compatibility.kind, JsCrashgenExpectationOutcomeKind::Notice);
    assert_eq!(
        compatibility.severity,
        JsCrashgenExpectationSeverity::Warning
    );
    assert_eq!(
        compatibility.message,
        "Compatibility guidance for Buffout 4"
    );
    assert_eq!(compatibility.fix.as_deref(), Some("Compatibility fix"));
    assert_eq!(
        compatibility.placement,
        JsAutoscanReportPlacement::ErrorInformation
    );
    assert_eq!(compatibility.section, None);
    assert_eq!(compatibility.setting, None);
    assert_eq!(compatibility.expected, None);
    assert_eq!(compatibility.actual, None);

    let setting = &result.expectation_outcomes[1];
    assert_eq!(setting.rule_id, "setting_check");
    assert_eq!(setting.kind, JsCrashgenExpectationOutcomeKind::Issue);
    assert_eq!(setting.severity, JsCrashgenExpectationSeverity::Error);
    assert_eq!(setting.message, "Expectation failed");
    assert_eq!(setting.fix.as_deref(), Some("Expectation fix"));
    assert_eq!(setting.placement, JsAutoscanReportPlacement::Settings);
    assert_eq!(setting.section.as_deref(), Some("Patches"));
    assert_eq!(setting.setting.as_deref(), Some("Achievements"));
    assert_eq!(setting.expected.as_deref(), Some("false"));
    assert_eq!(setting.actual.as_deref(), Some("true"));

    assert_eq!(result.disabled_setting_notices.len(), 1);
    assert_eq!(
        result.disabled_setting_notices[0].setting_name,
        "DisabledSetting"
    );
}

#[test]
fn completed_analysis_without_matches_returns_explicit_empty_arrays() {
    let analyzer = build_analyzer(
        "Buffout 4".to_string(),
        JsCrashgenRegistryEntry {
            display_section: String::new(),
            ignore_keys: Vec::new(),
            checks: Vec::new(),
            settings_rules_version: None,
            settings_rules: None,
        },
    )
    .unwrap();

    let result = analyzer
        .analyze_owned(JsCrashgenSettingsAnalysisInput {
            settings: Vec::new(),
            installed_plugins: Vec::new(),
            crashgen_version: None,
            config_layout: JsCrashgenConfigLayout::Unknown,
        })
        .unwrap();

    assert!(result.expectation_outcomes.is_empty());
    assert!(result.disabled_setting_notices.is_empty());
}

#[test]
fn construction_preserves_the_core_stable_error_code_and_human_message() {
    let error = build_analyzer("Buffout 4".to_string(), registry_entry(2))
        .expect_err("unsupported configuration must be rejected");

    assert_eq!(error.code().as_str(), "unsupported_configuration_version");
    assert_eq!(
        error.message(),
        "unsupported Crashgen Expectations version 2"
    );
}

#[test]
fn construction_rejects_malformed_rule_tokens_through_shared_core_validation() {
    let mut entry = registry_entry(1);
    entry.settings_rules.as_mut().unwrap().checks[0].severity = "loud".to_string();

    let error = build_analyzer("Buffout 4".to_string(), entry)
        .expect_err("malformed configuration must be rejected");

    assert_eq!(error.code().as_str(), "invalid_configuration");
    assert_eq!(
        error.message(),
        "Crashgen Expectations configuration is invalid: $.checks[0].severity: invalid severity; defaulting to warning"
    );
}

#[test]
fn one_immutable_handle_can_be_reused_without_state_leaking_between_calls() {
    let analyzer = build_analyzer("Buffout 4".to_string(), registry_entry(1)).unwrap();

    let populated = analyzer.analyze_owned(populated_input()).unwrap();
    let empty = analyzer
        .analyze_owned(JsCrashgenSettingsAnalysisInput {
            settings: Vec::new(),
            installed_plugins: Vec::new(),
            crashgen_version: None,
            config_layout: JsCrashgenConfigLayout::Unknown,
        })
        .unwrap();
    let populated_again = analyzer.analyze_owned(populated_input()).unwrap();

    assert_eq!(populated.expectation_outcomes.len(), 2);
    assert!(empty.expectation_outcomes.is_empty());
    assert!(empty.disabled_setting_notices.is_empty());
    assert_eq!(populated_again.expectation_outcomes.len(), 2);
    assert_eq!(analyzer.kind(), JsAnalyzerKind::CrashgenSettings);
}
