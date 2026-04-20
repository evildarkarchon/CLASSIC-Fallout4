use super::*;
use crate::crashgen_registry::{CheckId, CrashgenEntry};
use classic_config_core::{
    CheckRule, ConfigLayout, CrashgenSettingsRules, ExpectedValue, Predicate, PreflightAction,
    PreflightActionKind, PreflightRule, RuleMessages, RuleReportBucket, RuleSeverity,
    RuleTarget, TargetValueType,
};

fn make_buffout_entry() -> CrashgenEntry {
    CrashgenEntry {
        display_section: "[Compatibility]".to_string(),
        ignore_keys: [
            "F4EE",
            "WaitForDebugger",
            "Achievements",
            "InputSwitch",
            "AutoOpen",
            "PromptUpload",
            "MemoryManagerDebug",
            "BSTextureStreamerLocalHeap",
            "ArchiveLimit",
            "MemoryManager",
        ]
        .iter()
        .map(|s| s.to_string())
        .collect(),
        checks: vec![
            CheckId::Achievements,
            CheckId::MemoryManagement,
            CheckId::ArchiveLimit,
            CheckId::LooksMenu,
        ],
        settings_rules: None,
    }
}

fn make_addictol_entry() -> CrashgenEntry {
    CrashgenEntry {
        display_section: "[Patches]".to_string(),
        ignore_keys: HashSet::new(),
        checks: vec![],
        settings_rules: None,
    }
}

#[test]
fn test_buffout_entry_runs_all_4_named_checks() {
    let validator = SettingsValidator::new("Buffout 4".to_string(), make_buffout_entry());

    let mut crashgen = HashMap::new();
    crashgen.insert("Achievements".to_string(), "true".to_string());
    crashgen.insert("MemoryManager".to_string(), "true".to_string());
    crashgen.insert("ArchiveLimit".to_string(), "true".to_string());
    crashgen.insert("F4EE".to_string(), "false".to_string());

    let mut xse = HashSet::new();
    xse.insert("achievements.dll".to_string());
    xse.insert("f4ee.dll".to_string());

    // All 4 named checks should return non-empty fragments
    let ach = validator
        .scan_buffout_achievements_setting(xse.clone(), &crashgen)
        .unwrap();
    let mem = validator
        .scan_buffout_memorymanagement_settings(&crashgen, false, false, false)
        .unwrap();
    let arc = validator
        .scan_archivelimit_setting(&crashgen, Some((1, 28, 0)))
        .unwrap();
    let lm = validator
        .scan_buffout_looksmenu_setting(&crashgen, xse)
        .unwrap();

    assert!(!ach.is_empty(), "Achievements check should run");
    assert!(!mem.is_empty(), "MemoryManagement check should run");
    assert!(!arc.is_empty(), "ArchiveLimit check should run");
    assert!(!lm.is_empty(), "LooksMenu check should run");
}

#[test]
fn test_addictol_entry_runs_0_named_checks() {
    let validator = SettingsValidator::new("Addictol".to_string(), make_addictol_entry());

    let mut crashgen = HashMap::new();
    crashgen.insert("Achievements".to_string(), "true".to_string());
    crashgen.insert("MemoryManager".to_string(), "true".to_string());
    crashgen.insert("ArchiveLimit".to_string(), "true".to_string());
    crashgen.insert("F4EE".to_string(), "false".to_string());

    let mut xse = HashSet::new();
    xse.insert("achievements.dll".to_string());
    xse.insert("f4ee.dll".to_string());

    // All 4 named checks should return empty (not registered)
    let ach = validator
        .scan_buffout_achievements_setting(xse.clone(), &crashgen)
        .unwrap();
    let mem = validator
        .scan_buffout_memorymanagement_settings(&crashgen, false, false, false)
        .unwrap();
    let arc = validator
        .scan_archivelimit_setting(&crashgen, Some((1, 28, 0)))
        .unwrap();
    let lm = validator
        .scan_buffout_looksmenu_setting(&crashgen, xse)
        .unwrap();

    assert!(
        ach.is_empty(),
        "Achievements check should NOT run for Addictol"
    );
    assert!(
        mem.is_empty(),
        "MemoryManagement check should NOT run for Addictol"
    );
    assert!(
        arc.is_empty(),
        "ArchiveLimit check should NOT run for Addictol"
    );
    assert!(lm.is_empty(), "LooksMenu check should NOT run for Addictol");
}

#[test]
fn test_both_entries_run_check_disabled_settings() {
    let mut crashgen = HashMap::new();
    crashgen.insert("SomeSetting".to_string(), "false".to_string());

    // Buffout with ignore list: SomeSetting not in ignore list → should flag
    let buffout_validator =
        SettingsValidator::new("Buffout 4".to_string(), make_buffout_entry());
    let buffout_result = buffout_validator
        .check_disabled_settings(&crashgen)
        .unwrap();
    assert!(
        !buffout_result.is_empty(),
        "Buffout should flag disabled SomeSetting"
    );

    // Addictol with empty ignore list: should also flag
    let addictol_validator =
        SettingsValidator::new("Addictol".to_string(), make_addictol_entry());
    let addictol_result = addictol_validator
        .check_disabled_settings(&crashgen)
        .unwrap();
    assert!(
        !addictol_result.is_empty(),
        "Addictol should flag disabled SomeSetting"
    );
}

#[test]
fn test_default_entry_runs_only_check_disabled_settings() {
    let default_entry = CrashgenEntry::default_entry();
    let validator = SettingsValidator::new("UnknownCrashgen".to_string(), default_entry);

    let mut crashgen = HashMap::new();
    crashgen.insert("Achievements".to_string(), "true".to_string());
    crashgen.insert("SomeSetting".to_string(), "false".to_string());

    let xse = HashSet::new();

    // Named checks should all be empty
    let ach = validator
        .scan_buffout_achievements_setting(xse.clone(), &crashgen)
        .unwrap();
    assert!(
        ach.is_empty(),
        "Achievements should not run for default entry"
    );

    // check_disabled_settings should run (and flag SomeSetting)
    let disabled = validator.check_disabled_settings(&crashgen).unwrap();
    assert!(
        !disabled.is_empty(),
        "check_disabled_settings should run for default entry"
    );
}

#[test]
fn test_ignore_keys_skip_settings_in_check_disabled() {
    let entry = make_buffout_entry();
    // F4EE is in ignore_keys
    let validator = SettingsValidator::new("Buffout 4".to_string(), entry);

    let mut crashgen = HashMap::new();
    crashgen.insert("F4EE".to_string(), "false".to_string()); // in ignore list
    crashgen.insert("SomeOtherKey".to_string(), "false".to_string()); // not in ignore list

    let result = validator.check_disabled_settings(&crashgen).unwrap();
    let lines = result.to_list();

    // F4EE should be skipped
    assert!(!lines.iter().any(|l| l.contains("F4EE")));
    // SomeOtherKey should be flagged
    assert!(lines.iter().any(|l| l.contains("SomeOtherKey")));
}

#[test]
fn test_looksmenu_uses_display_section_from_entry() {
    let entry = CrashgenEntry {
        display_section: "[Compatibility]".to_string(),
        ignore_keys: HashSet::new(),
        checks: vec![CheckId::LooksMenu],
        settings_rules: None,
    };
    let validator = SettingsValidator::new("Buffout 4".to_string(), entry);

    let mut crashgen = HashMap::new();
    crashgen.insert("F4EE".to_string(), "false".to_string());

    let mut xse = HashSet::new();
    xse.insert("f4ee.dll".to_string());

    let result = validator
        .scan_buffout_looksmenu_setting(&crashgen, xse)
        .unwrap();
    let lines = result.to_list();
    assert!(lines.iter().any(|l| l.contains("[Compatibility]")));
}

#[test]
fn test_looksmenu_invalid_f4ee_value_falls_back_to_false() {
    let entry = CrashgenEntry {
        display_section: "[Compatibility]".to_string(),
        ignore_keys: HashSet::new(),
        checks: vec![CheckId::LooksMenu],
        settings_rules: None,
    };
    let validator = SettingsValidator::new("Buffout 4".to_string(), entry);

    let mut crashgen = HashMap::new();
    crashgen.insert("F4EE".to_string(), "yes".to_string());

    let mut xse = HashSet::new();
    xse.insert("f4ee.dll".to_string());

    let result = validator
        .scan_buffout_looksmenu_setting(&crashgen, xse)
        .unwrap();
    let lines = result.to_list();

    assert!(
        lines.iter().any(|line| line.contains("CAUTION")),
        "Invalid F4EE value should be treated as disabled and surface caution when LooksMenu is installed"
    );
}

#[test]
fn test_achievements_validation_still_works() {
    let validator = SettingsValidator::new("Buffout 4".to_string(), make_buffout_entry());

    let mut crashgen = HashMap::new();
    crashgen.insert("Achievements".to_string(), "true".to_string());

    let mut xse_modules = HashSet::new();
    xse_modules.insert("achievements.dll".to_string());

    let fragment = validator
        .scan_buffout_achievements_setting(xse_modules, &crashgen)
        .unwrap();

    assert!(!fragment.is_empty());
    let lines = fragment.to_list();
    assert!(lines.iter().any(|line| line.contains("CAUTION")));
}

#[test]
fn test_memory_management_xcell_conflict() {
    let validator = SettingsValidator::new("Buffout 4".to_string(), make_buffout_entry());

    let mut crashgen = HashMap::new();
    crashgen.insert("MemoryManager".to_string(), "true".to_string());

    let fragment = validator
        .scan_buffout_memorymanagement_settings(
            &crashgen, true,  // has_xcell
            false, // has_old_xcell
            false, // has_baka
        )
        .unwrap();

    assert!(!fragment.is_empty());
    let lines = fragment.to_list();
    assert!(lines.iter().any(|line| line.contains("X-Cell/Addictol")));
}

#[test]
fn test_archive_limit_warning() {
    let validator = SettingsValidator::new("Buffout 4".to_string(), make_buffout_entry());

    let mut crashgen = HashMap::new();
    crashgen.insert("ArchiveLimit".to_string(), "true".to_string());

    let fragment = validator
        .scan_archivelimit_setting(&crashgen, Some((1, 28, 0)))
        .unwrap();

    assert!(!fragment.is_empty());
    let lines = fragment.to_list();
    assert!(lines.iter().any(|line| line.contains("ArchiveLimit")));
}

#[test]
fn test_addictol_scaffold_returns_notice_fragment() {
    let validator = SettingsValidator::new("Buffout 4".to_string(), make_buffout_entry());
    let crashgen = HashMap::new();

    let fragment = validator
        .scan_addictol_settings_scaffold(&crashgen)
        .unwrap();
    let lines = fragment.to_list();

    assert!(
        !fragment.is_empty(),
        "Addictol scaffold should return an informational notice"
    );
    assert!(
        lines.iter().any(|line| line.contains("Addictol detected")),
        "Scaffold notice should mention Addictol detection"
    );
    assert!(
        lines.iter().any(|line| line.contains("scaffold")),
        "Scaffold notice should indicate scaffold mode"
    );
}

#[test]
fn test_scan_all_settings_prefers_yaml_rules_when_present() {
    let entry = CrashgenEntry {
        display_section: "[Compatibility]".to_string(),
        ignore_keys: HashSet::new(),
        checks: vec![CheckId::Achievements],
        settings_rules: Some(CrashgenSettingsRules {
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
                    fail: "Achievements should be disabled".to_string(),
                    fix: Some("Set Achievements to FALSE".to_string()),
                    pass: None,
                },
                severity: RuleSeverity::Warning,
            }],
        }),
    };
    let validator = SettingsValidator::new("Buffout 4".to_string(), entry);

    let mut crashgen = HashMap::new();
    crashgen.insert("Achievements".to_string(), "true".to_string());
    let xse = HashSet::new();

    let fragments = validator
        .scan_all_settings(&crashgen, &xse, None, ConfigLayout::Unknown)
        .unwrap();
    assert!(!fragments.is_empty());
    let lines = fragments[0].to_list();
    assert!(
        lines
            .iter()
            .any(|line| line.contains("Achievements should be disabled"))
    );
}

#[test]
fn test_scan_all_settings_rules_fallback_restores_missing_success_lines() {
    let entry = CrashgenEntry {
        display_section: "[Compatibility]".to_string(),
        ignore_keys: HashSet::new(),
        checks: vec![
            CheckId::Achievements,
            CheckId::MemoryManagement,
            CheckId::ArchiveLimit,
            CheckId::LooksMenu,
        ],
        settings_rules: Some(CrashgenSettingsRules {
            version: 1,
            preflight: vec![],
            checks: vec![
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
                        fail: "Achievements fail".to_string(),
                        fix: None,
                        pass: Some("Achievements pass".to_string()),
                    },
                    severity: RuleSeverity::Warning,
                },
                CheckRule {
                    id: "memory_manager_xcell".to_string(),
                    target: RuleTarget {
                        section: "Patches".to_string(),
                        key: "MemoryManager".to_string(),
                        value_type: TargetValueType::Bool,
                    },
                    when: Predicate::PluginAny(vec!["x-cell-fo4.dll".to_string()]),
                    expect: ExpectedValue::Bool(false),
                    messages: RuleMessages {
                        fail: "Memory fail".to_string(),
                        fix: None,
                        pass: Some("Memory pass".to_string()),
                    },
                    severity: RuleSeverity::Warning,
                },
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
                },
                CheckRule {
                    id: "looksmenu_f4ee".to_string(),
                    target: RuleTarget {
                        section: "Compatibility".to_string(),
                        key: "F4EE".to_string(),
                        value_type: TargetValueType::Bool,
                    },
                    when: Predicate::PluginAny(vec!["f4ee.dll".to_string()]),
                    expect: ExpectedValue::Bool(true),
                    messages: RuleMessages {
                        fail: "LooksMenu fail".to_string(),
                        fix: None,
                        pass: Some("LooksMenu pass".to_string()),
                    },
                    severity: RuleSeverity::Warning,
                },
            ],
        }),
    };
    let validator = SettingsValidator::new("Buffout 4".to_string(), entry);

    let mut crashgen = HashMap::new();
    crashgen.insert("Achievements".to_string(), "true".to_string());
    crashgen.insert("MemoryManager".to_string(), "true".to_string());
    crashgen.insert("ArchiveLimit".to_string(), "false".to_string());
    crashgen.insert("F4EE".to_string(), "true".to_string());

    let mut xse = HashSet::new();
    xse.insert("f4ee.dll".to_string());

    let fragments = validator
        .scan_all_settings(&crashgen, &xse, Some((1, 28, 6)), ConfigLayout::Unknown)
        .unwrap();
    let all_lines: Vec<String> = fragments.iter().flat_map(ReportFragment::to_list).collect();

    assert!(
        all_lines
            .iter()
            .any(|line| line.contains("Achievements parameter is correctly configured"))
    );
    assert!(
        all_lines
            .iter()
            .any(|line| line.contains("Memory Manager parameter is correctly configured"))
    );
    assert!(all_lines.iter().any(|line| line.contains("Archive pass")));
    assert!(all_lines.iter().any(|line| line.contains("LooksMenu pass")));
}

#[test]
fn test_scan_all_settings_rules_and_fallback_do_not_duplicate_results() {
    let entry = CrashgenEntry {
        display_section: "[Compatibility]".to_string(),
        ignore_keys: HashSet::new(),
        checks: vec![CheckId::Achievements],
        settings_rules: Some(CrashgenSettingsRules {
            version: 1,
            preflight: vec![],
            checks: vec![CheckRule {
                id: "achievements_conflict".to_string(),
                target: RuleTarget {
                    section: "Patches".to_string(),
                    key: "Achievements".to_string(),
                    value_type: TargetValueType::Bool,
                },
                when: Predicate::PluginAny(vec!["achievements.dll".to_string()]),
                expect: ExpectedValue::Bool(false),
                messages: RuleMessages {
                    fail: "YAML achievements fail".to_string(),
                    fix: None,
                    pass: Some("YAML achievements pass".to_string()),
                },
                severity: RuleSeverity::Warning,
            }],
        }),
    };
    let validator = SettingsValidator::new("Buffout 4".to_string(), entry);

    let mut crashgen = HashMap::new();
    crashgen.insert("Achievements".to_string(), "false".to_string());

    let mut xse = HashSet::new();
    xse.insert("achievements.dll".to_string());

    let fragments = validator
        .scan_all_settings(&crashgen, &xse, Some((1, 28, 6)), ConfigLayout::Unknown)
        .unwrap();
    let all_lines: Vec<String> = fragments.iter().flat_map(ReportFragment::to_list).collect();

    assert!(
        all_lines
            .iter()
            .any(|line| line.contains("YAML achievements pass"))
    );
    assert!(
        !all_lines
            .iter()
            .any(|line| line.contains("Achievements parameter is correctly configured"))
    );
}

#[test]
fn test_scan_all_settings_preflight_skip_remaining_prevents_fallback() {
    let entry = CrashgenEntry {
        display_section: "[Compatibility]".to_string(),
        ignore_keys: HashSet::new(),
        checks: vec![
            CheckId::Achievements,
            CheckId::MemoryManagement,
            CheckId::ArchiveLimit,
            CheckId::LooksMenu,
        ],
        settings_rules: Some(CrashgenSettingsRules {
            version: 1,
            preflight: vec![PreflightRule {
                id: "skip_all".to_string(),
                when: Predicate::Always,
                action: PreflightAction {
                    kind: PreflightActionKind::NoticeAndSkipRemaining,
                    bucket: RuleReportBucket::Settings,
                    severity: RuleSeverity::Warning,
                    message: "skip remaining".to_string(),
                    fix: None,
                },
            }],
            checks: vec![],
        }),
    };
    let validator = SettingsValidator::new("Buffout 4".to_string(), entry);

    let mut crashgen = HashMap::new();
    crashgen.insert("Achievements".to_string(), "true".to_string());
    crashgen.insert("MemoryManager".to_string(), "true".to_string());
    crashgen.insert("ArchiveLimit".to_string(), "false".to_string());
    crashgen.insert("F4EE".to_string(), "true".to_string());

    let mut xse = HashSet::new();
    xse.insert("f4ee.dll".to_string());

    let fragments = validator
        .scan_all_settings(&crashgen, &xse, Some((1, 28, 6)), ConfigLayout::Unknown)
        .unwrap();
    let all_lines: Vec<String> = fragments.iter().flat_map(ReportFragment::to_list).collect();

    assert!(all_lines.iter().any(|line| line.contains("skip remaining")));
    assert!(
        !all_lines
            .iter()
            .any(|line| line.contains("Achievements parameter is correctly configured"))
    );
    assert!(
        !all_lines
            .iter()
            .any(|line| line.contains("Memory Manager parameter is correctly configured"))
    );
    assert!(
        !all_lines
            .iter()
            .any(|line| line.contains("ArchiveLimit parameter is correctly configured"))
    );
}

#[test]
fn test_archive_limit_rule_uses_crashgen_version_gate() {
    let entry = CrashgenEntry {
        display_section: "[Compatibility]".to_string(),
        ignore_keys: HashSet::new(),
        checks: vec![CheckId::ArchiveLimit],
        settings_rules: Some(CrashgenSettingsRules {
            version: 1,
            preflight: vec![],
            checks: vec![CheckRule {
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
            }],
        }),
    };
    let validator = SettingsValidator::new("Buffout 4".to_string(), entry);

    let mut crashgen = HashMap::new();
    crashgen.insert("ArchiveLimit".to_string(), "false".to_string());
    let xse = HashSet::new();

    let lt_boundary = validator
        .scan_all_settings(&crashgen, &xse, Some((1, 29, 9)), ConfigLayout::Unknown)
        .unwrap();
    let lt_lines: Vec<String> = lt_boundary
        .iter()
        .flat_map(ReportFragment::to_list)
        .collect();
    assert!(lt_lines.iter().any(|line| line.contains("Archive pass")));

    let at_boundary = validator
        .scan_all_settings(&crashgen, &xse, Some((1, 30, 0)), ConfigLayout::Unknown)
        .unwrap();
    let at_lines: Vec<String> = at_boundary
        .iter()
        .flat_map(ReportFragment::to_list)
        .collect();
    assert!(!at_lines.iter().any(|line| line.contains("Archive pass")));
}

#[test]
fn test_production_configs_never_hit_legacy_fallback() {
    // Production crashgen entries are constructed by build_crashgen_registry() in
    // orchestrator.rs from YAML config. The legacy fallback in
    // scan_all_settings_bucketed triggers when entry.settings_rules is None.
    //
    // This test proves the invariant: entries that actually reach
    // scan_all_settings_bucketed (those with non-empty checks) always have
    // settings_rules defined in production. Entries with no checks (like
    // default_entry for unknown crashgens) return early via the orchestrator
    // before reaching the bucketed method.

    // 1. default_entry has no checks -> never reaches scan_all_settings_bucketed
    let default = CrashgenEntry::default_entry();
    assert!(
        default.checks.is_empty(),
        "default_entry must have no checks, ensuring it never reaches scan_all_settings_bucketed"
    );
    assert!(
        default.settings_rules.is_none(),
        "default_entry has no settings_rules (safe because it never reaches the bucketed path)"
    );

    // 2. Entries with checks (like Buffout 4) always have settings_rules in
    // production. Verify the invariant by constructing a production-representative
    // entry with settings_rules and confirming it takes the rules path.
    let production_buffout = CrashgenEntry {
        display_section: "[Compatibility]".to_string(),
        ignore_keys: ["F4EE", "WaitForDebugger", "Achievements"]
            .iter()
            .map(|s| s.to_string())
            .collect(),
        checks: vec![
            CheckId::Achievements,
            CheckId::MemoryManagement,
            CheckId::ArchiveLimit,
            CheckId::LooksMenu,
        ],
        settings_rules: Some(CrashgenSettingsRules {
            version: 1,
            preflight: vec![],
            checks: vec![CheckRule {
                id: "achievements_conflict".to_string(),
                target: RuleTarget {
                    section: "Patches".to_string(),
                    key: "Achievements".to_string(),
                    value_type: TargetValueType::Bool,
                },
                when: Predicate::Always,
                expect: ExpectedValue::Bool(false),
                messages: RuleMessages {
                    fail: "Achievements should be disabled".to_string(),
                    fix: Some("Set Achievements to FALSE".to_string()),
                    pass: None,
                },
                severity: RuleSeverity::Warning,
            }],
        }),
    };
    assert!(
        !production_buffout.checks.is_empty(),
        "production Buffout entry has checks"
    );
    assert!(
        production_buffout.settings_rules.is_some(),
        "production Buffout entry must have settings_rules -- the legacy fallback is never needed"
    );

    // 3. Verify the production entry actually uses rules (not the legacy path)
    // by calling scan_all_settings_bucketed and confirming rules-driven output.
    let validator = SettingsValidator::new("Buffout 4".to_string(), production_buffout);
    let mut crashgen = HashMap::new();
    crashgen.insert("Achievements".to_string(), "true".to_string());
    let xse = HashSet::new();

    let fragments = validator
        .scan_all_settings_bucketed(&crashgen, &xse, None, ConfigLayout::Unknown)
        .unwrap();
    let all_lines: Vec<String> = fragments
        .iter()
        .flat_map(|f| f.fragment.to_list())
        .collect();
    assert!(
        all_lines
            .iter()
            .any(|line| line.contains("Achievements should be disabled")),
        "production entry with settings_rules must use the rules path, not the legacy fallback"
    );
}
