use super::*;

#[test]
fn rule_report_bucket_parses_known_values_and_defaults_to_settings() {
    assert_eq!(
        RuleReportBucket::parse("settings"),
        Some(RuleReportBucket::Settings)
    );
    assert_eq!(
        RuleReportBucket::parse("error_information"),
        Some(RuleReportBucket::ErrorInformation)
    );
    assert_eq!(RuleReportBucket::parse("unknown"), None);
    assert_eq!(RuleReportBucket::default(), RuleReportBucket::Settings);
}

fn base_context() -> EvaluationContext {
    EvaluationContext {
        crashgen_name: "Buffout 4".to_string(),
        display_section: "[Compatibility]".to_string(),
        installed_plugins: HashSet::new(),
        settings: HashMap::new(),
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
                bucket: RuleReportBucket::ErrorInformation,
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
        .insert("Achievements".to_string(), "true".to_string());

    let result = evaluate_rules(&rules, &context);
    assert!(result.skip_remaining);
    assert_eq!(result.outcomes.len(), 1);
    assert_eq!(result.outcomes[0].kind, OutcomeKind::Notice);
    assert_eq!(
        result.outcomes[0].bucket,
        RuleReportBucket::ErrorInformation
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
        .insert("F4EE".to_string(), "false".to_string());
    let fail_result = evaluate_rules(&rules, &fail_context);
    assert_eq!(fail_result.outcomes.len(), 1);
    assert_eq!(fail_result.outcomes[0].kind, OutcomeKind::Issue);
    assert_eq!(fail_result.outcomes[0].bucket, RuleReportBucket::Settings);

    let mut pass_context = base_context();
    pass_context
        .installed_plugins
        .insert("f4ee.dll".to_string());
    pass_context
        .settings
        .insert("F4EE".to_string(), "true".to_string());
    let pass_result = evaluate_rules(&rules, &pass_context);
    assert_eq!(pass_result.outcomes.len(), 1);
    assert_eq!(pass_result.outcomes[0].kind, OutcomeKind::Success);
    assert_eq!(pass_result.outcomes[0].bucket, RuleReportBucket::Settings);
}
