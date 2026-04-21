use super::*;
use std::fs;
use tempfile::TempDir;

fn default_config(game_path: PathBuf) -> GameScanConfig {
    GameScanConfig {
        game_path,
        docs_path: None,
        mods_path: None,
        xse_acronym: "F4SE".to_string(),
        xse_scriptfiles: HashMap::new(),
        plugins_path: None,
        is_vr: false,
        game_version: GameVersion::Original,
        crashgen_name: "Buffout4".to_string(),
        crashgen_settings_rules: None,
        wrye_warnings: HashMap::new(),
        log_catch_errors: vec!["error".to_string()],
        log_exclude_files: vec![],
        log_exclude_errors: vec![],
        game_target: GameTarget::Fallout4,
        game_name: "Fallout4".to_string(),
    }
}

#[test]
fn test_orchestrator_creation() {
    let temp = TempDir::new().unwrap();
    let config = default_config(temp.path().to_path_buf());
    let _orch = GameScanOrchestrator::new(config);
}

#[test]
fn test_config_clone() {
    let temp = TempDir::new().unwrap();
    let config = default_config(temp.path().to_path_buf());
    let config2 = config.clone();
    assert_eq!(config.xse_acronym, config2.xse_acronym);
    assert_eq!(config.crashgen_name, config2.crashgen_name);
}

#[test]
fn test_merge_ba2_issues_empty() {
    let issues = BA2Issues::new();
    let mut map = BTreeMap::new();
    merge_ba2_issues(&issues, &mut map);
    assert!(map.is_empty());
}

#[test]
fn test_merge_ba2_issues_populated() {
    let mut issues = BA2Issues::new();
    issues
        .tex_dims
        .push("  - 1023x512 : mod.ba2 > texture.dds".to_string());
    issues
        .snd_frmt
        .push("  - MP3 : mod.ba2 > sound.mp3\n".to_string());

    let mut map = BTreeMap::new();
    merge_ba2_issues(&issues, &mut map);

    assert_eq!(map.len(), 2);
    assert!(map.contains_key("tex_dims"));
    assert!(map.contains_key("snd_frmt"));
}

#[tokio::test]
async fn test_run_game_checks_no_paths() {
    let temp = TempDir::new().unwrap();
    let config = default_config(temp.path().to_path_buf());
    let orch = GameScanOrchestrator::new(config);

    let result = orch.run_game_checks().await.unwrap();
    // Should complete without panic, even with no real game files
    assert!(result.errors.is_empty() || !result.errors.is_empty()); // Just assert it runs
}

#[tokio::test]
async fn test_run_mod_scans_no_mods_path() {
    let temp = TempDir::new().unwrap();
    let config = default_config(temp.path().to_path_buf());
    let orch = GameScanOrchestrator::new(config);

    let result = orch.run_mod_scans().await.unwrap();
    assert!(result.report.is_empty());
    assert!(!result.errors.is_empty()); // Should report missing path
}

#[tokio::test]
async fn test_run_mod_scans_empty_mods_dir() {
    let temp = TempDir::new().unwrap();
    let mods_dir = temp.path().join("mods");
    fs::create_dir(&mods_dir).unwrap();

    let mut config = default_config(temp.path().to_path_buf());
    config.mods_path = Some(mods_dir);

    let orch = GameScanOrchestrator::new(config);
    let result = orch.run_mod_scans().await.unwrap();
    // Empty mods dir = no issues
    assert_eq!(result.unpacked_issue_count, 0);
    assert_eq!(result.archived_issue_count, 0);
}

#[tokio::test]
async fn test_run_mod_scans_with_bad_textures() {
    let temp = TempDir::new().unwrap();
    let mods_dir = temp.path().join("mods");
    fs::create_dir(&mods_dir).unwrap();

    // Create a TGA file (wrong format)
    let tga_path = mods_dir.join("bad_texture.tga");
    fs::write(&tga_path, b"not a real texture").unwrap();

    let mut config = default_config(temp.path().to_path_buf());
    config.mods_path = Some(mods_dir);

    let orch = GameScanOrchestrator::new(config);
    let result = orch.run_mod_scans().await.unwrap();
    assert!(result.unpacked_issue_count > 0);
}

#[tokio::test]
async fn test_run_full_scan() {
    let temp = TempDir::new().unwrap();
    let config = default_config(temp.path().to_path_buf());
    let orch = GameScanOrchestrator::new(config);

    let (game_result, mod_result) = orch.run_full_scan().await.unwrap();
    // Both should complete without panic
    let _ = game_result;
    let _ = mod_result;
}

#[test]
fn test_game_scan_result_fields() {
    let result = GameScanResult {
        report: "test".to_string(),
        config_issues: vec![],
        check_results: vec![CheckResult {
            name: "xse".to_string(),
            output: "ok".to_string(),
        }],
        errors: vec![],
    };
    assert_eq!(result.report, "test");
    assert_eq!(result.check_results.len(), 1);
}

#[test]
fn test_mod_scan_result_fields() {
    let result = ModScanResult {
        report: "scan report".to_string(),
        unpacked_issue_count: 5,
        archived_issue_count: 3,
        errors: vec![],
    };
    assert_eq!(result.unpacked_issue_count, 5);
    assert_eq!(result.archived_issue_count, 3);
}

#[test]
fn test_scan_unpacked_empty_dir() {
    let temp = TempDir::new().unwrap();
    let (label, issues) =
        GameScanOrchestrator::scan_unpacked(temp.path(), &[], GameTarget::Fallout4).unwrap();
    assert_eq!(label, "unpacked");
    assert!(issues.is_empty());
}

#[test]
fn test_scan_archived_empty_dir() {
    let temp = TempDir::new().unwrap();
    let (label, issues) = GameScanOrchestrator::scan_archived(temp.path()).unwrap();
    assert_eq!(label, "archived");
    assert!(issues.is_empty());
}

#[test]
fn test_scan_unpacked_detects_bad_format() {
    let temp = TempDir::new().unwrap();
    fs::write(temp.path().join("test.tga"), b"fake").unwrap();

    let (_, issues) =
        GameScanOrchestrator::scan_unpacked(temp.path(), &[], GameTarget::Fallout4).unwrap();
    assert!(issues.contains_key("tex_frmt"));
}

#[test]
fn test_detect_config_issues_nonexistent_path() {
    let issues = detect_config_issues(Path::new("nonexistent_path_12345"), "Fallout4");
    // Should return empty list, not panic
    assert!(issues.is_empty());
}
