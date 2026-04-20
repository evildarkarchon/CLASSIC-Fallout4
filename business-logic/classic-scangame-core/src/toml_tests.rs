use super::*;
use classic_config_core::{
    CheckRule, CrashgenSettingsRules, ExpectedValue, Predicate, RuleMessages, RuleSeverity,
    RuleTarget, TargetValueType,
};
use std::fs;
use tempfile::TempDir;

#[test]
fn test_checker_creation() {
    let temp_dir = TempDir::new().unwrap();
    let checker = CrashgenChecker::new(temp_dir.path(), "Buffout4");
    assert_eq!(checker.crashgen_name, "Buffout4");
}

#[test]
fn test_plugin_detection() {
    let temp_dir = TempDir::new().unwrap();

    // Create fake DLL files
    fs::write(temp_dir.path().join("x-cell-fo4.dll"), b"").unwrap();
    fs::write(temp_dir.path().join("achievements.dll"), b"").unwrap();

    let checker = CrashgenChecker::new(temp_dir.path(), "Buffout4");
    assert!(checker.has_plugin(&["x-cell-fo4.dll"]));
    assert!(checker.has_plugin(&["achievements.dll"]));
    assert!(!checker.has_plugin(&["nonexistent.dll"]));
}

#[test]
fn test_config_file_detection() {
    let temp_dir = TempDir::new().unwrap();
    let buffout_dir = temp_dir.path().join("Buffout4");
    fs::create_dir(&buffout_dir).unwrap();

    let config_file = buffout_dir.join("config.toml");
    fs::write(&config_file, "[Patches]\nAchievements = true\n").unwrap();

    let checker = CrashgenChecker::new(temp_dir.path(), "Buffout4");
    assert!(checker.config_file.is_some());
    assert_eq!(checker.config_file.unwrap(), config_file);
}

#[test]
fn test_toml_parsing() {
    let temp_dir = TempDir::new().unwrap();
    let buffout_dir = temp_dir.path().join("Buffout4");
    fs::create_dir(&buffout_dir).unwrap();

    let config_file = buffout_dir.join("config.toml");
    fs::write(
        &config_file,
        "[Patches]\nAchievements = true\nMemoryManager = true\n",
    )
    .unwrap();

    let mut checker = CrashgenChecker::new(temp_dir.path(), "Buffout4");
    checker.load_toml().unwrap();

    assert_eq!(
        checker.get_value("Patches", "Achievements"),
        Some(&Value::Boolean(true))
    );
    assert_eq!(
        checker.get_value("Patches", "MemoryManager"),
        Some(&Value::Boolean(true))
    );
}

#[test]
fn test_issue_detection() {
    let temp_dir = TempDir::new().unwrap();
    let buffout_dir = temp_dir.path().join("Buffout4");
    fs::create_dir(&buffout_dir).unwrap();

    // Create config with Achievements enabled
    let config_file = buffout_dir.join("config.toml");
    fs::write(&config_file, "[Patches]\nAchievements = true\n").unwrap();

    // Create achievements.dll to trigger condition
    fs::write(temp_dir.path().join("achievements.dll"), b"").unwrap();

    let mut checker = CrashgenChecker::new(temp_dir.path(), "Buffout4");
    let (_report, issues) = checker.check().unwrap();

    // Should detect Achievements issue
    assert!(!issues.is_empty());
    assert!(issues.iter().any(|i| i.setting == "Achievements"));
}

#[test]
fn test_addictol_skips_all_toml_checks() {
    let temp_dir = TempDir::new().unwrap();
    let buffout_dir = temp_dir.path().join("Buffout4");
    fs::create_dir(&buffout_dir).unwrap();

    // Create config with MemoryManager enabled (would normally be flagged)
    let config_file = buffout_dir.join("config.toml");
    fs::write(&config_file, "[Patches]\nMemoryManager = true\n").unwrap();

    // Addictol DLL only (no Buffout4 DLL) — skip silently, no incompatibility warning
    fs::write(temp_dir.path().join("Addictol.dll"), b"").unwrap();

    let mut checker = CrashgenChecker::new(temp_dir.path(), "Buffout4");
    let (report, issues) = checker.check().unwrap();

    assert!(
        issues.is_empty(),
        "No issues should be reported when Addictol is detected"
    );
    assert!(
        report.contains("Addictol detected"),
        "Report should mention Addictol"
    );
    assert!(
        !report.contains("incompatible"),
        "Should NOT warn about incompatibility when only Addictol is present"
    );
}

#[test]
fn test_addictol_and_buffout_shows_incompatibility_warning() {
    let temp_dir = TempDir::new().unwrap();
    let buffout_dir = temp_dir.path().join("Buffout4");
    fs::create_dir(&buffout_dir).unwrap();

    // Create config with MemoryManager enabled (would normally be flagged)
    let config_file = buffout_dir.join("config.toml");
    fs::write(&config_file, "[Patches]\nMemoryManager = true\n").unwrap();

    // Both Addictol AND Buffout4 DLLs present — should warn about incompatibility
    fs::write(temp_dir.path().join("Addictol.dll"), b"").unwrap();
    fs::write(temp_dir.path().join("Buffout4.dll"), b"").unwrap();

    let mut checker = CrashgenChecker::new(temp_dir.path(), "Buffout4");
    let (report, issues) = checker.check().unwrap();

    assert!(
        issues.is_empty(),
        "No issues should be reported — TOML checks are skipped"
    );
    assert!(
        report.contains("incompatible"),
        "Should warn about incompatibility when both are present"
    );
    assert!(
        report.contains("remove one to avoid crashes"),
        "Should have clear removal guidance"
    );
}

#[test]
fn test_xcell_still_triggers_memory_checks_without_addictol() {
    let temp_dir = TempDir::new().unwrap();
    let buffout_dir = temp_dir.path().join("Buffout4");
    fs::create_dir(&buffout_dir).unwrap();

    let config_file = buffout_dir.join("config.toml");
    fs::write(&config_file, "[Patches]\nMemoryManager = true\n").unwrap();

    // Only X-Cell DLL, no Addictol
    fs::write(temp_dir.path().join("x-cell-fo4.dll"), b"").unwrap();

    let mut checker = CrashgenChecker::new(temp_dir.path(), "Buffout4");
    let (_report, issues) = checker.check().unwrap();

    assert!(issues.iter().any(|i| i.setting == "MemoryManager"));
}

#[test]
fn test_yaml_rules_path_detects_issue() {
    let temp_dir = TempDir::new().unwrap();
    let buffout_dir = temp_dir.path().join("Buffout4");
    fs::create_dir(&buffout_dir).unwrap();

    let config_file = buffout_dir.join("config.toml");
    fs::write(&config_file, "[Patches]\nAchievements = true\n").unwrap();
    fs::write(temp_dir.path().join("achievements.dll"), b"").unwrap();

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
            when: Predicate::PluginAny(vec!["achievements.dll".to_string()]),
            expect: ExpectedValue::Bool(false),
            messages: RuleMessages {
                fail: "Achievements should be false".to_string(),
                fix: Some("Set Achievements to FALSE".to_string()),
                pass: None,
            },
            severity: RuleSeverity::Warning,
        }],
    };

    let mut checker = CrashgenChecker::new_with_rules(temp_dir.path(), "Buffout4", Some(rules));
    let (report, issues) = checker.check().unwrap();

    assert!(!issues.is_empty());
    assert!(report.contains("Achievements should be false"));
}
