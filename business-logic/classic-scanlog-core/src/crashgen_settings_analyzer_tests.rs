use std::collections::{HashSet, hash_map::RandomState};
use std::sync::Arc;

use classic_config_core::{
    AutoscanReportPlacement, CheckRule, ConfigLayout, CrashgenExpectationParseDiagnostic,
    CrashgenSettingsRules, CrashgenSettingsSnapshot, ExpectedValue, OutcomeKind, Predicate,
    PreflightAction, PreflightActionKind, PreflightRule, RuleMessages, RuleSeverity, RuleTarget,
    TargetValueType,
};

use super::*;
use crate::{AnalyzerErrorCode, AnalyzerKind, CrashgenEntry};

fn entry_with_rules(rules: CrashgenSettingsRules) -> CrashgenEntry {
    CrashgenEntry {
        display_section: "[Compatibility]".to_string(),
        ignore_keys: HashSet::from(["IgnoredSetting".to_string()]),
        settings_rules: Some(rules),
    }
}

fn rules() -> CrashgenSettingsRules {
    CrashgenSettingsRules {
        version: 1,
        preflight: vec![PreflightRule {
            id: "compatibility_notice".to_string(),
            when: Predicate::PluginAny(vec!["MixedCase.DLL".to_string()]),
            action: PreflightAction {
                kind: PreflightActionKind::Notice,
                bucket: AutoscanReportPlacement::ErrorInformation,
                severity: RuleSeverity::Warning,
                message: "Authored compatibility message for {crashgen_name}".to_string(),
                fix: Some("Authored compatibility fix".to_string()),
            },
        }],
        checks: vec![CheckRule {
            id: "setting_check".to_string(),
            target: RuleTarget {
                section: "Patches".to_string(),
                key: "Achievements".to_string(),
                value_type: TargetValueType::Bool,
            },
            when: Predicate::Always,
            expect: ExpectedValue::Bool(false),
            messages: RuleMessages {
                fail: "Authored expectation message".to_string(),
                fix: Some("Authored expectation fix".to_string()),
                pass: None,
            },
            severity: RuleSeverity::Error,
        }],
    }
}

fn input() -> CrashgenSettingsAnalysisInput {
    let mut settings = CrashgenSettingsSnapshot::new();
    settings.insert("Patches", "Achievements", "true");
    settings.insert("Compatibility", "DisabledSetting", "false");
    settings.insert("Compatibility", "IgnoredSetting", "false");

    CrashgenSettingsAnalysisInput {
        settings,
        installed_plugins: HashSet::<String, RandomState>::from(["MIXEDCASE.DLL".to_string()]),
        crashgen_version: Some((1, 30, 0)),
        config_layout: ConfigLayout::Og,
    }
}

#[test]
fn analyze_returns_typed_outcomes_and_separate_disabled_notices() {
    let analyzer =
        CrashgenSettingsAnalyzer::new("Buffout 4".to_string(), entry_with_rules(rules())).unwrap();

    let result = analyzer.analyze(input()).unwrap();

    assert_eq!(result.expectation_outcomes.len(), 2);
    assert_eq!(
        result.expectation_outcomes[0].rule_id,
        "compatibility_notice"
    );
    assert_eq!(result.expectation_outcomes[0].kind, OutcomeKind::Notice);
    assert_eq!(
        result.expectation_outcomes[0].severity,
        RuleSeverity::Warning
    );
    assert_eq!(
        result.expectation_outcomes[0].message,
        "Authored compatibility message for Buffout 4"
    );
    assert_eq!(
        result.expectation_outcomes[0].fix.as_deref(),
        Some("Authored compatibility fix")
    );
    assert_eq!(
        result.expectation_outcomes[0].placement,
        AutoscanReportPlacement::ErrorInformation
    );

    assert_eq!(result.expectation_outcomes[1].rule_id, "setting_check");
    assert_eq!(result.expectation_outcomes[1].kind, OutcomeKind::Issue);
    assert_eq!(result.expectation_outcomes[1].severity, RuleSeverity::Error);
    assert_eq!(
        result.expectation_outcomes[1].message,
        "Authored expectation message"
    );
    assert_eq!(
        result.expectation_outcomes[1].fix.as_deref(),
        Some("Authored expectation fix")
    );
    assert_eq!(
        result.expectation_outcomes[1].placement,
        AutoscanReportPlacement::Settings
    );
    assert_eq!(
        result.disabled_setting_notices,
        vec![DisabledSettingNotice {
            setting_name: "DisabledSetting".to_string(),
        }]
    );
}

#[test]
fn completed_analysis_without_matches_is_an_explicit_empty_result() {
    let analyzer =
        CrashgenSettingsAnalyzer::new("Buffout 4".to_string(), CrashgenEntry::default_entry())
            .unwrap();

    let result = analyzer
        .analyze(CrashgenSettingsAnalysisInput::default())
        .unwrap();

    assert_eq!(result, CrashgenSettingsAnalysisResult::default());
}

#[test]
fn construction_rejects_unsupported_rule_versions_with_a_stable_error() {
    let mut unsupported = rules();
    unsupported.version = 2;

    let error =
        CrashgenSettingsAnalyzer::new("Buffout 4".to_string(), entry_with_rules(unsupported))
            .unwrap_err();

    assert_eq!(error.analyzer(), AnalyzerKind::CrashgenSettings);
    assert_eq!(
        error.code(),
        AnalyzerErrorCode::UnsupportedConfigurationVersion
    );
    assert_eq!(
        error.message(),
        "unsupported Crashgen Expectations version 2"
    );
}

#[test]
fn parsed_configuration_diagnostics_fail_construction_in_core() {
    let error = CrashgenSettingsAnalyzer::from_parsed_configuration(
        "Buffout 4".to_string(),
        CrashgenEntry::default_entry(),
        vec![CrashgenExpectationParseDiagnostic {
            path: "$.preflight[0].action.kind".to_string(),
            message: "unknown action kind".to_string(),
        }],
    )
    .unwrap_err();

    assert_eq!(error.analyzer(), AnalyzerKind::CrashgenSettings);
    assert_eq!(error.code(), AnalyzerErrorCode::InvalidConfiguration);
    assert_eq!(
        error.message(),
        "Crashgen Expectations configuration is invalid: $.preflight[0].action.kind: unknown action kind"
    );
}

#[test]
fn one_immutable_handle_is_safe_for_concurrent_analysis() {
    let analyzer = Arc::new(
        CrashgenSettingsAnalyzer::new("Buffout 4".to_string(), entry_with_rules(rules())).unwrap(),
    );
    let threads = (0..8)
        .map(|_| {
            let analyzer = Arc::clone(&analyzer);
            std::thread::spawn(move || analyzer.analyze(input()).unwrap())
        })
        .collect::<Vec<_>>();

    for thread in threads {
        let result = thread.join().unwrap();
        assert_eq!(result.expectation_outcomes.len(), 2);
        assert_eq!(result.disabled_setting_notices.len(), 1);
    }
}

#[test]
fn immutable_analyzer_handle_is_send_and_sync() {
    fn assert_send_sync<T: Send + Sync>() {}

    assert_send_sync::<CrashgenSettingsAnalyzer>();
}
