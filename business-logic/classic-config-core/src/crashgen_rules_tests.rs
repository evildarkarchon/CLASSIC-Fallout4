use super::*;

#[test]
fn autoscan_report_placement_parses_known_values_and_defaults_to_settings() {
    assert_eq!(
        AutoscanReportPlacement::parse("settings"),
        Some(AutoscanReportPlacement::Settings)
    );
    assert_eq!(
        AutoscanReportPlacement::parse("error_information"),
        Some(AutoscanReportPlacement::ErrorInformation)
    );
    assert_eq!(AutoscanReportPlacement::parse("unknown"), None);
    assert_eq!(
        AutoscanReportPlacement::default(),
        AutoscanReportPlacement::Settings
    );
    assert_eq!(
        AutoscanReportPlacement::ErrorInformation.as_str(),
        "error_information"
    );
}

fn base_context() -> EvaluationContext {
    EvaluationContext {
        crashgen_name: "Buffout 4".to_string(),
        display_section: "[Compatibility]".to_string(),
        installed_plugins: HashSet::new(),
        settings: CrashgenSettingsSnapshot::new(),
        config_layout: ConfigLayout::Unknown,
        crashgen_version: None,
    }
}

#[test]
fn evaluate_preflight_skip_remaining() {
    let rules = CrashgenSettingsRules {
        version: 1,
        preflight: vec![PreflightRule {
            id: "addictol_skip".to_string(),
            when: Predicate::PluginAny(vec!["addictol.dll".to_string()]),
            action: PreflightAction {
                kind: PreflightActionKind::NoticeAndSkipRemaining,
                bucket: AutoscanReportPlacement::ErrorInformation,
                severity: RuleSeverity::Info,
                message: "Addictol detected - skipping {crashgen_name} checks".to_string(),
                fix: None,
            },
        }],
        checks: vec![CheckRule {
            id: "achievements".to_string(),
            target: RuleTarget {
                section: "Patches".to_string(),
                key: "Achievements".to_string(),
                value_type: TargetValueType::Bool,
            },
            when: Predicate::Always,
            expect: ExpectedValue::Bool(false),
            messages: RuleMessages {
                fail: "fail".to_string(),
                fix: None,
                pass: Some("pass".to_string()),
            },
            severity: RuleSeverity::Warning,
        }],
    };

    let mut context = base_context();
    context.installed_plugins.insert("addictol.dll".to_string());
    context
        .settings
        .insert("Patches", "Achievements", "true".to_string());

    let result = evaluate_rules(&rules, &context);
    assert!(result.skip_remaining);
    assert_eq!(result.outcomes.len(), 1);
    assert_eq!(result.outcomes[0].kind, OutcomeKind::Notice);
    assert_eq!(
        result.outcomes[0].bucket,
        AutoscanReportPlacement::ErrorInformation
    );
}

#[test]
fn evaluate_check_fail_and_pass() {
    let rules = CrashgenSettingsRules {
        version: 1,
        preflight: vec![],
        checks: vec![CheckRule {
            id: "f4ee".to_string(),
            target: RuleTarget {
                section: "Compatibility".to_string(),
                key: "F4EE".to_string(),
                value_type: TargetValueType::Bool,
            },
            when: Predicate::PluginAny(vec!["f4ee.dll".to_string()]),
            expect: ExpectedValue::Bool(true),
            messages: RuleMessages {
                fail: "{setting} is disabled".to_string(),
                fix: Some("enable it".to_string()),
                pass: Some("{setting} is enabled".to_string()),
            },
            severity: RuleSeverity::Warning,
        }],
    };

    let mut fail_context = base_context();
    fail_context
        .installed_plugins
        .insert("f4ee.dll".to_string());
    fail_context
        .settings
        .insert("Compatibility", "F4EE", "false".to_string());
    let fail_result = evaluate_rules(&rules, &fail_context);
    assert_eq!(fail_result.outcomes.len(), 1);
    assert_eq!(fail_result.outcomes[0].kind, OutcomeKind::Issue);
    assert_eq!(
        fail_result.outcomes[0].bucket,
        AutoscanReportPlacement::Settings
    );

    let mut pass_context = base_context();
    pass_context
        .installed_plugins
        .insert("f4ee.dll".to_string());
    pass_context
        .settings
        .insert("Compatibility", "F4EE", "true".to_string());
    let pass_result = evaluate_rules(&rules, &pass_context);
    assert_eq!(pass_result.outcomes.len(), 1);
    assert_eq!(pass_result.outcomes[0].kind, OutcomeKind::Success);
    assert_eq!(
        pass_result.outcomes[0].bucket,
        AutoscanReportPlacement::Settings
    );
}

#[test]
fn evaluate_check_uses_target_section_for_lookup() {
    let rules = CrashgenSettingsRules {
        version: 1,
        preflight: vec![],
        checks: vec![CheckRule {
            id: "achievements".to_string(),
            target: RuleTarget {
                section: "Patches".to_string(),
                key: "Achievements".to_string(),
                value_type: TargetValueType::Bool,
            },
            when: Predicate::Always,
            expect: ExpectedValue::Bool(false),
            messages: RuleMessages {
                fail: "fail".to_string(),
                fix: None,
                pass: Some("pass".to_string()),
            },
            severity: RuleSeverity::Warning,
        }],
    };

    let mut context = base_context();
    context
        .settings
        .insert("Compatibility", "Achievements", "true".to_string());
    context
        .settings
        .insert("[Patches]", "Achievements", "false".to_string());

    let result = evaluate_rules(&rules, &context);

    assert_eq!(result.outcomes.len(), 1);
    assert_eq!(result.outcomes[0].kind, OutcomeKind::Success);
    assert_eq!(result.outcomes[0].actual, Some("false".to_string()));
}

#[test]
fn evaluate_check_normalizes_section_names() {
    let rules = CrashgenSettingsRules {
        version: 1,
        preflight: vec![],
        checks: vec![CheckRule {
            id: "f4ee".to_string(),
            target: RuleTarget {
                section: "[Compatibility]".to_string(),
                key: "F4EE".to_string(),
                value_type: TargetValueType::Bool,
            },
            when: Predicate::Always,
            expect: ExpectedValue::Bool(true),
            messages: RuleMessages {
                fail: "fail".to_string(),
                fix: None,
                pass: Some("pass".to_string()),
            },
            severity: RuleSeverity::Warning,
        }],
    };

    let mut context = base_context();
    context
        .settings
        .insert("compatibility", "F4EE", "true".to_string());

    let result = evaluate_rules(&rules, &context);

    assert_eq!(result.outcomes.len(), 1);
    assert_eq!(result.outcomes[0].kind, OutcomeKind::Success);
}

#[test]
fn evaluate_check_does_not_match_unscoped_settings() {
    let rules = CrashgenSettingsRules {
        version: 1,
        preflight: vec![],
        checks: vec![CheckRule {
            id: "f4ee".to_string(),
            target: RuleTarget {
                section: "Compatibility".to_string(),
                key: "F4EE".to_string(),
                value_type: TargetValueType::Bool,
            },
            when: Predicate::Always,
            expect: ExpectedValue::Bool(true),
            messages: RuleMessages {
                fail: "fail".to_string(),
                fix: None,
                pass: Some("pass".to_string()),
            },
            severity: RuleSeverity::Warning,
        }],
    };

    let mut context = base_context();
    context.settings.insert_unscoped("F4EE", "true".to_string());

    let result = evaluate_rules(&rules, &context);

    assert!(result.outcomes.is_empty());
}

#[test]
fn snapshot_uses_last_value_for_duplicate_key_in_section() {
    let mut snapshot = CrashgenSettingsSnapshot::new();

    snapshot.insert("Patches", "Achievements", "true".to_string());
    snapshot.insert("[Patches]", "Achievements", "false".to_string());

    assert_eq!(snapshot.value_for("patches", "Achievements"), Some("false"));
}
