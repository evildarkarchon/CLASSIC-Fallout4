use super::*;
use crate::crashgen_registry::CrashgenEntry;
use classic_config_core::{
    AutoscanReportPlacement, CheckRule, ConfigLayout, CrashgenSettingsRules,
    CrashgenSettingsSnapshot, ExpectedValue, Predicate, PreflightAction, PreflightActionKind,
    PreflightRule, RuleMessages, RuleSeverity, RuleTarget, TargetValueType,
};

fn make_entry(
    ignore_keys: impl IntoIterator<Item = &'static str>,
    settings_rules: Option<CrashgenSettingsRules>,
) -> CrashgenEntry {
    CrashgenEntry {
        display_section: "[Compatibility]".to_string(),
        ignore_keys: ignore_keys.into_iter().map(str::to_string).collect(),
        settings_rules,
    }
}

fn achievements_rule() -> CheckRule {
    CheckRule {
        id: "achievements_conflict".to_string(),
        target: RuleTarget {
            section: "Patches".to_string(),
            key: "Achievements".to_string(),
            value_type: TargetValueType::Bool,
        },
        when: Predicate::PluginAny(vec!["achievements.dll".to_string()]),
        expect: ExpectedValue::Bool(false),
        messages: RuleMessages {
            fail: "Achievements should be disabled".to_string(),
            fix: Some("Set Achievements to FALSE".to_string()),
            pass: Some("Achievements pass".to_string()),
        },
        severity: RuleSeverity::Warning,
    }
}

fn archive_limit_rule() -> CheckRule {
    CheckRule {
        id: "archive_limit".to_string(),
        target: RuleTarget {
            section: "Patches".to_string(),
            key: "ArchiveLimit".to_string(),
            value_type: TargetValueType::Bool,
        },
        when: Predicate::CrashgenVersionLt((1, 30, 0)),
        expect: ExpectedValue::Bool(false),
        messages: RuleMessages {
            fail: "Archive fail".to_string(),
            fix: None,
            pass: Some("Archive pass".to_string()),
        },
        severity: RuleSeverity::Warning,
    }
}

fn rules(checks: Vec<CheckRule>) -> CrashgenSettingsRules {
    CrashgenSettingsRules {
        version: 1,
        preflight: vec![],
        checks,
    }
}

fn collect_lines(fragments: Vec<ReportFragment>) -> Vec<String> {
    fragments.iter().flat_map(ReportFragment::to_list).collect()
}

fn snapshot(
    settings: impl IntoIterator<Item = (&'static str, &'static str, &'static str)>,
) -> CrashgenSettingsSnapshot {
    let mut snapshot = CrashgenSettingsSnapshot::new();
    for (section, key, value) in settings {
        snapshot.insert(section, key, value.to_string());
    }
    snapshot
}

#[test]
fn scan_all_settings_uses_yaml_rules() {
    let validator = SettingsValidator::new(
        "Buffout 4".to_string(),
        make_entry([], Some(rules(vec![achievements_rule()]))),
    );

    let crashgen = snapshot([("Patches", "Achievements", "true")]);
    let mut xse = HashSet::new();
    xse.insert("achievements.dll".to_string());

    let fragments = validator
        .scan_all_settings(&crashgen, &xse, None, ConfigLayout::Unknown)
        .unwrap();
    let lines = collect_lines(fragments);

    assert!(
        lines
            .iter()
            .any(|line| line.contains("Achievements should be disabled"))
    );
}

#[test]
fn scan_all_settings_does_not_run_legacy_fallback_when_rules_do_not_cover_setting() {
    let validator =
        SettingsValidator::new("Buffout 4".to_string(), make_entry([], Some(rules(vec![]))));

    let crashgen = snapshot([("Patches", "Achievements", "true")]);
    let mut xse = HashSet::new();
    xse.insert("achievements.dll".to_string());

    let fragments = validator
        .scan_all_settings(&crashgen, &xse, None, ConfigLayout::Unknown)
        .unwrap();
    let lines = collect_lines(fragments);

    assert!(lines.is_empty());
}

#[test]
fn scan_all_settings_appends_disabled_setting_notices() {
    let validator = SettingsValidator::new(
        "Buffout 4".to_string(),
        make_entry([], Some(rules(vec![achievements_rule()]))),
    );

    let crashgen = snapshot([
        ("Patches", "Achievements", "true"),
        ("Compatibility", "SomeSetting", "false"),
    ]);
    let mut xse = HashSet::new();
    xse.insert("achievements.dll".to_string());

    let fragments = validator
        .scan_all_settings(&crashgen, &xse, None, ConfigLayout::Unknown)
        .unwrap();
    let lines = collect_lines(fragments);

    assert!(
        lines
            .iter()
            .any(|line| line.contains("Achievements should be disabled"))
    );
    assert!(
        lines
            .iter()
            .any(|line| line.contains("SomeSetting is disabled"))
    );
}

#[test]
fn disabled_setting_notices_respect_ignore_keys() {
    let validator = SettingsValidator::new(
        "Buffout 4".to_string(),
        make_entry(["F4EE"], Some(rules(vec![]))),
    );

    let crashgen = snapshot([
        ("Compatibility", "F4EE", "false"),
        ("Patches", "SomeOtherKey", "false"),
    ]);

    let result = validator.check_disabled_settings(&crashgen).unwrap();
    let lines = result.to_list();

    assert!(!lines.iter().any(|line| line.contains("F4EE")));
    assert!(lines.iter().any(|line| line.contains("SomeOtherKey")));
}

#[test]
fn scan_all_settings_without_rules_returns_disabled_notices_only() {
    let validator = SettingsValidator::new("Buffout 4".to_string(), make_entry([], None));

    let crashgen = snapshot([
        ("Patches", "Achievements", "true"),
        ("Compatibility", "SomeSetting", "false"),
    ]);
    let mut xse = HashSet::new();
    xse.insert("achievements.dll".to_string());

    let fragments = validator
        .scan_all_settings(&crashgen, &xse, None, ConfigLayout::Unknown)
        .unwrap();
    let lines = collect_lines(fragments);

    assert!(
        lines
            .iter()
            .any(|line| line.contains("SomeSetting is disabled"))
    );
    assert!(
        !lines
            .iter()
            .any(|line| line.contains("Achievements Mod and/or Unlimited Survival Mode"))
    );
}

#[test]
fn preflight_skip_remaining_still_allows_disabled_setting_notices() {
    let entry = make_entry(
        [],
        Some(CrashgenSettingsRules {
            version: 1,
            preflight: vec![PreflightRule {
                id: "skip_all".to_string(),
                when: Predicate::Always,
                action: PreflightAction {
                    kind: PreflightActionKind::NoticeAndSkipRemaining,
                    bucket: AutoscanReportPlacement::Settings,
                    severity: RuleSeverity::Warning,
                    message: "skip remaining".to_string(),
                    fix: None,
                },
            }],
            checks: vec![achievements_rule()],
        }),
    );
    let validator = SettingsValidator::new("Buffout 4".to_string(), entry);

    let crashgen = snapshot([
        ("Patches", "Achievements", "true"),
        ("Compatibility", "SomeSetting", "false"),
    ]);
    let mut xse = HashSet::new();
    xse.insert("achievements.dll".to_string());

    let fragments = validator
        .scan_all_settings(&crashgen, &xse, None, ConfigLayout::Unknown)
        .unwrap();
    let lines = collect_lines(fragments);

    assert!(lines.iter().any(|line| line.contains("skip remaining")));
    assert!(
        lines
            .iter()
            .any(|line| line.contains("SomeSetting is disabled"))
    );
    assert!(
        !lines
            .iter()
            .any(|line| line.contains("Achievements should be disabled"))
    );
}

#[test]
fn archive_limit_rule_uses_crashgen_version_gate() {
    let validator = SettingsValidator::new(
        "Buffout 4".to_string(),
        make_entry([], Some(rules(vec![archive_limit_rule()]))),
    );

    let crashgen = snapshot([("Patches", "ArchiveLimit", "false")]);
    let xse = HashSet::new();

    let lt_boundary = validator
        .scan_all_settings(&crashgen, &xse, Some((1, 29, 9)), ConfigLayout::Unknown)
        .unwrap();
    let lt_lines = collect_lines(lt_boundary);
    assert!(lt_lines.iter().any(|line| line.contains("Archive pass")));

    let at_boundary = validator
        .scan_all_settings(&crashgen, &xse, Some((1, 30, 0)), ConfigLayout::Unknown)
        .unwrap();
    let at_lines = collect_lines(at_boundary);
    assert!(!at_lines.iter().any(|line| line.contains("Archive pass")));
}
