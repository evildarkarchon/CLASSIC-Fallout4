use super::*;
use std::fs;
use tempfile::TempDir;

/// Helper: create a temp plugins directory with optional DLL files
fn setup_plugins_dir(dlls: &[&str]) -> TempDir {
    let temp = TempDir::new().unwrap();
    for dll in dlls {
        fs::write(temp.path().join(dll), b"").unwrap();
    }
    temp
}

/// Helper: create a plugins dir with a Buffout4 OG config
fn setup_with_og_config(toml_content: &str, dlls: &[&str]) -> TempDir {
    let temp = setup_plugins_dir(dlls);
    let buffout_dir = temp.path().join("Buffout4");
    fs::create_dir(&buffout_dir).unwrap();
    fs::write(buffout_dir.join("config.toml"), toml_content).unwrap();
    temp
}

/// Helper: create a plugins dir with a Buffout4 VR config
fn setup_with_vr_config(toml_content: &str, dlls: &[&str]) -> TempDir {
    let temp = setup_plugins_dir(dlls);
    fs::write(temp.path().join("Buffout4.toml"), toml_content).unwrap();
    temp
}

#[test]
fn test_check_no_config_file() {
    let temp = setup_plugins_dir(&[]);
    let report = CrashgenCheckOrchestrator::check(temp.path(), "Buffout4").unwrap();

    assert!(report.config_path.is_none());
    assert!(report.issues.is_empty());
    assert!(report.message.contains("Unable to find"));
}

#[test]
fn test_check_og_config_no_issues() {
    let temp = setup_with_og_config(
        "[Patches]\nAchievements = true\nMemoryManager = true\n",
        &[],
    );
    let report = CrashgenCheckOrchestrator::check(temp.path(), "Buffout4").unwrap();

    assert!(report.config_path.is_some());
    // No plugins installed that would trigger conditions, so no issues
    assert!(report.issues.is_empty());
}

#[test]
fn test_check_detects_achievements_conflict() {
    let temp = setup_with_og_config("[Patches]\nAchievements = true\n", &["achievements.dll"]);
    let report = CrashgenCheckOrchestrator::check(temp.path(), "Buffout4").unwrap();

    assert!(!report.issues.is_empty());
    assert!(report.issues.iter().any(|i| i.setting == "Achievements"));
    assert!(report.message.contains("Achievements"));
}

#[test]
fn test_check_detects_xcell_conflicts() {
    let temp = setup_with_og_config(
        "[Patches]\nMemoryManager = true\nHavokMemorySystem = true\n",
        &["x-cell-fo4.dll"],
    );
    let report = CrashgenCheckOrchestrator::check(temp.path(), "Buffout4").unwrap();

    assert!(!report.issues.is_empty());
    // Should detect MemoryManager and HavokMemorySystem issues
    let settings: Vec<&str> = report.issues.iter().map(|i| i.setting.as_str()).collect();
    assert!(settings.contains(&"MemoryManager"));
    assert!(settings.contains(&"HavokMemorySystem"));
}

#[test]
fn test_addictol_skips_all_checks() {
    let temp = setup_with_og_config(
        "[Patches]\nMemoryManager = true\nHavokMemorySystem = true\n",
        &["Addictol.dll"],
    );
    let report = CrashgenCheckOrchestrator::check(temp.path(), "Buffout4").unwrap();

    // Addictol only (no Buffout4 DLL) — skip silently, no incompatibility warning
    assert!(
        report.issues.is_empty(),
        "No issues when Addictol is present"
    );
    assert!(report.message.contains("Addictol detected"));
    assert!(
        !report.message.contains("incompatible"),
        "Should NOT warn about incompatibility when only Addictol is present"
    );
}

#[test]
fn test_addictol_and_buffout_shows_incompatibility_warning() {
    let temp = setup_with_og_config(
        "[Patches]\nMemoryManager = true\nHavokMemorySystem = true\n",
        &["Addictol.dll", "Buffout4.dll"],
    );
    let report = CrashgenCheckOrchestrator::check(temp.path(), "Buffout4").unwrap();

    // Both present — should warn about incompatibility
    assert!(
        report.issues.is_empty(),
        "No issues — TOML checks are skipped"
    );
    assert!(
        report.message.contains("incompatible"),
        "Should warn about incompatibility when both are present"
    );
    assert!(
        report.message.contains("remove one to avoid crashes"),
        "Should have clear removal guidance"
    );
}

#[test]
fn test_check_vr_config() {
    let temp = setup_with_vr_config("[Patches]\nAchievements = true\n", &["achievements.dll"]);
    let report = CrashgenCheckOrchestrator::check(temp.path(), "Buffout4").unwrap();

    assert!(report.config_path.is_some());
    assert!(
        report
            .config_path
            .as_ref()
            .unwrap()
            .ends_with("Buffout4.toml")
    );
}

#[test]
fn test_detect_plugins() {
    let temp = setup_plugins_dir(&["x-cell-fo4.dll", "achievements.dll", "SomeOther.dll"]);
    let plugins = CrashgenCheckOrchestrator::detect_plugins(temp.path()).unwrap();

    assert_eq!(plugins.len(), 3);
    assert!(plugins.contains(&"x-cell-fo4.dll".to_string()));
    assert!(plugins.contains(&"achievements.dll".to_string()));
    assert!(plugins.contains(&"someother.dll".to_string())); // lowercase
}

#[test]
fn test_detect_plugins_nonexistent_dir() {
    let result = CrashgenCheckOrchestrator::detect_plugins(Path::new("/nonexistent/path"));
    assert!(result.is_err());
}

#[test]
fn test_resolve_config_path_og() {
    let temp = setup_with_og_config("[Patches]\n", &[]);
    let path = CrashgenCheckOrchestrator::resolve_config_path(temp.path());

    assert!(path.is_some());
    assert!(path.unwrap().ends_with("Buffout4/config.toml"));
}

#[test]
fn test_resolve_config_path_vr() {
    let temp = setup_with_vr_config("[Patches]\n", &[]);
    let path = CrashgenCheckOrchestrator::resolve_config_path(temp.path());

    assert!(path.is_some());
    assert!(path.unwrap().ends_with("Buffout4.toml"));
}

#[test]
fn test_resolve_config_path_og_preferred_over_vr() {
    // When both exist, OG takes priority (matches Python behavior)
    let temp = TempDir::new().unwrap();
    let buffout_dir = temp.path().join("Buffout4");
    fs::create_dir(&buffout_dir).unwrap();
    fs::write(buffout_dir.join("config.toml"), "[Patches]\n").unwrap();
    fs::write(temp.path().join("Buffout4.toml"), "[Patches]\n").unwrap();

    let path = CrashgenCheckOrchestrator::resolve_config_path(temp.path());
    assert!(path.is_some());
    assert!(path.unwrap().ends_with("Buffout4/config.toml"));
}

#[test]
fn test_resolve_config_path_none() {
    let temp = TempDir::new().unwrap();
    let path = CrashgenCheckOrchestrator::resolve_config_path(temp.path());
    assert!(path.is_none());
}

#[test]
fn test_report_contains_crashgen_name() {
    let temp = setup_plugins_dir(&[]);
    let report = CrashgenCheckOrchestrator::check(temp.path(), "MyCustomCrashgen").unwrap();

    assert_eq!(report.crashgen_name, "MyCustomCrashgen");
}

#[test]
fn test_report_installed_plugins_populated() {
    let temp = setup_with_og_config("[Patches]\n", &["test.dll", "another.dll"]);
    let report = CrashgenCheckOrchestrator::check(temp.path(), "Buffout4").unwrap();

    // installed_plugins includes everything in the directory (including the Buffout4 subdir)
    assert!(!report.installed_plugins.is_empty());
}

#[test]
fn test_bakascrapheap_special_case() {
    let temp = setup_with_og_config(
        "[Patches]\nMemoryManager = true\n",
        &["x-cell-fo4.dll", "bakascrapheap.dll"],
    );
    let report = CrashgenCheckOrchestrator::check(temp.path(), "Buffout4").unwrap();

    // Should detect BakaScrapHeap conflict (error severity in the checker)
    assert!(!report.issues.is_empty());
    assert!(report.message.contains("Baka ScrapHeap"));
}
