use super::*;
use std::fs;
use std::path::Path;
use tempfile::TempDir;

// ── Game Setup Intake tests ───────────────────────────────────────────────

fn write_valid_fallout4_docs_inis(docs_root: &Path) {
    fs::write(docs_root.join("Fallout4.ini"), "[General]\n").expect("main ini");
    fs::write(docs_root.join("Fallout4Custom.ini"), "[Archive]\n").expect("custom ini");
    fs::write(docs_root.join("Fallout4Prefs.ini"), "[General]\n").expect("prefs ini");
}

#[test]
fn test_run_game_setup_intake_from_user_settings_uses_typed_paths_without_writing() {
    let root = TempDir::new().expect("temp dir");
    let game_root = root.path().join("Fallout4");
    let docs_root = root.path().join("Docs");
    let mods_root = root.path().join("Mods");
    let custom_scan_root = root.path().join("Crash Logs");
    fs::create_dir_all(&game_root).expect("game root");
    fs::create_dir_all(&docs_root).expect("docs root");
    fs::create_dir_all(&mods_root).expect("mods root");
    fs::create_dir_all(&custom_scan_root).expect("custom scan root");
    write_valid_fallout4_docs_inis(&docs_root);
    let configured_exe = game_root.join("Fallout4Custom.exe");
    fs::write(&configured_exe, b"not a real pe").expect("configured exe");
    let papyrus_log = docs_root.join("Logs/Script/Papyrus.0.log");
    fs::create_dir_all(papyrus_log.parent().expect("Papyrus parent")).expect("Papyrus parent");
    fs::write(&papyrus_log, b"Papyrus log").expect("Papyrus log");
    let settings = format!(
        concat!(
            "schema_version: \"1.0\"\n",
            "CLASSIC_Settings:\n",
            "  Managed Game: Fallout4\n",
            "  Game Version: auto\n",
            "  Game Folder Path: '{}'\n",
            "  Game EXE Path: '{}'\n",
            "  Documents Folder Path: '{}'\n",
            "  MODS Folder Path: '{}'\n",
            "  SCAN Custom Path: '{}'\n",
            "  Papyrus Log Path: '{}'\n",
        ),
        game_root.display(),
        configured_exe.display(),
        docs_root.display(),
        mods_root.display(),
        custom_scan_root.display(),
        papyrus_log.display(),
    );
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    fs::write(&settings_path, &settings).expect("User Settings fixture");

    let result = run_game_setup_intake_from_user_settings(&root.path().display().to_string(), "");

    assert_ne!(result.status, "fatal_error");
    assert_eq!(
        result.game_root,
        game_root.to_string_lossy(),
        "typed game root should reach intake"
    );
    assert_eq!(
        result.docs_root,
        docs_root.to_string_lossy(),
        "typed documents root should reach intake"
    );
    assert_eq!(
        result.game_executable,
        configured_exe.to_string_lossy(),
        "typed executable should reach intake"
    );
    assert_eq!(
        fs::read(&settings_path).expect("re-read User Settings"),
        settings.as_bytes(),
        "root-based typed intake must remain read-only"
    );
}

// ── BA2 sub-domain tests ──────────────────────────────────────────────────

#[test]
fn test_ba2_scan_archive_summary_nonexistent_returns_no_issues() {
    let r = ba2_scan_archive_summary("nonexistent.ba2");
    assert!(!r.has_issues);
    assert_eq!(r.total, 0);
    assert_eq!(r.tex_dim_count, 0);
    assert_eq!(r.tex_fmt_count, 0);
    assert_eq!(r.snd_fmt_count, 0);
    assert_eq!(r.xse_file_count, 0);
}

#[test]
fn test_ba2_get_categories_empty_for_nonexistent() {
    assert!(ba2_get_tex_dims_for_archive("nonexistent.ba2").is_empty());
    assert!(ba2_get_tex_frmt_for_archive("nonexistent.ba2").is_empty());
    assert!(ba2_get_snd_frmt_for_archive("nonexistent.ba2").is_empty());
    assert!(ba2_get_xse_files_for_archive("nonexistent.ba2").is_empty());
}

// ── INI sub-domain tests ──────────────────────────────────────────────────

#[test]
fn test_ini_validator_validate_inis_empty_root_errors() {
    assert!(ini_validator_validate_inis("Fallout4", "").is_err());
}

#[test]
fn test_ini_validator_detect_all_issues_empty_root_returns_empty() {
    assert!(ini_validator_detect_all_issues_for_root("Fallout4", "").is_empty());
}

#[test]
fn test_ini_validator_validate_inis_nonexistent_dir() {
    // Real IniValidator::scan_config_files on a missing dir returns Err or empty map;
    // either way the bridge must not panic.
    let result = ini_validator_validate_inis("Fallout4", "nonexistent\\dir");
    // Accept Ok (empty report) or Err (scan failure) — both are valid
    match result {
        Ok(report) => {
            // report may be empty or contain file-not-found notices
            let _ = report;
        }
        Err(msg) => {
            assert!(!msg.is_empty());
        }
    }
}

#[test]
fn test_ini_validator_detect_all_issues_nonexistent_dir_returns_empty() {
    // scan_config_files returns Err on missing dir → bridge returns empty Vec
    let issues = ini_validator_detect_all_issues_for_root("Fallout4", "nonexistent\\dir");
    assert!(issues.is_empty());
}

// ── ENB sub-domain tests (REAL variant names — Codex HIGH correction) ────

#[test]
fn test_enb_checker_validate_empty_dir_real_variants() {
    // Empty temp dir — no ENB files at all
    let temp_dir = TempDir::new().unwrap();
    let r = enb_checker_validate(&temp_dir.path().to_string_lossy());
    // REAL variants: NotInstalled, NotFound (Codex HIGH correction)
    assert!(
        matches!(r.binaries, ffi::EnbResult::NotInstalled),
        "expected NotInstalled variant"
    );
    assert!(
        matches!(r.config, ffi::EnbConfigResult::NotFound),
        "expected NotFound variant"
    );
}

#[test]
fn test_enb_checker_validate_present_real_variants() {
    // Mirrors classic-scangame-core/src/enb.rs::test_enb_present
    let temp_dir = TempDir::new().unwrap();
    fs::write(temp_dir.path().join("d3d11.dll"), b"x").unwrap();
    fs::write(temp_dir.path().join("d3dcompiler_46e.dll"), b"x").unwrap();
    fs::write(temp_dir.path().join("enbseries.ini"), b"[ENB]\n").unwrap();
    let r = enb_checker_validate(&temp_dir.path().to_string_lossy());
    // REAL variants: Present, Valid (Codex HIGH correction)
    assert!(
        matches!(r.binaries, ffi::EnbResult::Present),
        "expected Present variant"
    );
    assert!(
        matches!(r.config, ffi::EnbConfigResult::Valid),
        "expected Valid variant"
    );
}

#[test]
fn test_enb_checker_validate_partial_real_variant() {
    // Only d3d11.dll — missing d3dcompiler → Partial
    let temp_dir = TempDir::new().unwrap();
    fs::write(temp_dir.path().join("d3d11.dll"), b"x").unwrap();
    let r = enb_checker_validate(&temp_dir.path().to_string_lossy());
    // REAL variant: Partial (Codex HIGH correction)
    assert!(
        matches!(r.binaries, ffi::EnbResult::Partial),
        "expected Partial variant"
    );
}

#[test]
fn test_enb_checker_validate_present_no_config() {
    // Both binaries present, no enbseries.ini
    let temp_dir = TempDir::new().unwrap();
    fs::write(temp_dir.path().join("d3d11.dll"), b"x").unwrap();
    fs::write(temp_dir.path().join("d3dcompiler_46e.dll"), b"x").unwrap();
    let r = enb_checker_validate(&temp_dir.path().to_string_lossy());
    assert!(matches!(r.binaries, ffi::EnbResult::Present));
    assert!(matches!(r.config, ffi::EnbConfigResult::NotFound));
}

// ── TOML sub-domain tests ─────────────────────────────────────────────────

#[test]
fn test_crashgen_checker_check_nonexistent_returns_zero_issues() {
    let r = crashgen_checker_check("nonexistent\\plugins", "Buffout4");
    // Nonexistent path — checker returns Ok("not installed" message) or Err
    // Either way issue_count must be 0
    assert_eq!(r.issue_count, 0);
}

#[test]
fn test_crashgen_checker_get_issues_nonexistent_returns_empty() {
    assert!(crashgen_checker_get_issues("nonexistent\\plugins", "Buffout4").is_empty());
}

#[test]
fn test_crashgen_checker_check_empty_path_returns_empty_dto() {
    let r = crashgen_checker_check("", "Buffout4");
    assert_eq!(r.issue_count, 0);
    assert!(r.report_text.is_empty());
}

// ── Wrye sub-domain tests ─────────────────────────────────────────────────

#[test]
fn test_wrye_parse_html_rows_empty_html_returns_empty() {
    assert!(wrye_parse_html_rows("", &[], &[]).is_empty());
}

#[test]
fn test_wrye_parse_html_rows_warnings_length_mismatch_returns_empty() {
    assert!(wrye_parse_html_rows("<html/>", &["a".to_string()], &[]).is_empty());
}

#[test]
fn test_wrye_parse_html_rows_simple_html_no_h3_returns_empty() {
    assert!(
        wrye_parse_html_rows("<html><body><p>no issues</p></body></html>", &[], &[]).is_empty()
    );
}

#[test]
fn test_wrye_parse_html_rows_one_issue_two_plugins_produces_two_rows() {
    // Synthetic HTML with one h3 section and two plugin <p> entries
    let html = r#"<html><body>
            <h3>Missing Masters</h3>
            <p>• Plugin1.esp</p>
            <p>• Plugin2.esp</p>
        </body></html>"#;
    let rows = wrye_parse_html_rows(html, &[], &[]);
    // Should produce 2 rows for the same issue (one per plugin)
    assert_eq!(rows.len(), 2);
    // Both rows have the same issue_index (same h3 section)
    assert_eq!(rows[0].issue_index, rows[1].issue_index);
    assert_eq!(rows[0].section_title, rows[1].section_title);
    // Different plugin names
    assert_ne!(rows[0].plugin, rows[1].plugin);
}

// ── Integrity sub-domain tests ────────────────────────────────────────────

#[test]
fn test_integrity_run_all_checks_nonexistent_exe_real_field_names() {
    let r = integrity_run_all_checks("nonexistent.exe", &[], "Fallout4");
    // For nonexistent exe, run_all_checks returns at least one entry with is_valid=false
    assert!(r.iter().any(|e| !e.is_valid));
    // REAL CheckType variants — Codex HIGH correction (ExecutableVersion, not Existence)
    assert!(
        r.iter()
            .any(|e| matches!(e.check_type, ffi::CheckType::ExecutableVersion))
    );
}

#[test]
fn test_integrity_run_all_checks_no_is_valid_field_is_bool() {
    // Compile-time proof: accessing `is_valid` compiles, `passed` would not
    let r = integrity_run_all_checks("nonexistent.exe", &[], "Fallout4");
    // is_valid is the REAL field name (NOT `passed`)
    let _ = r.iter().map(|e| e.is_valid).collect::<Vec<_>>();
}

#[test]
fn test_integrity_run_all_checks_empty_path_returns_empty() {
    let r = integrity_run_all_checks("", &[], "Fallout4");
    assert!(r.is_empty());
}

// ── CrashgenOrchestrator tests ────────────────────────────────────────────

#[test]
fn test_crashgen_orchestrator_check_summary_nonexistent_real_fields() {
    let r = crashgen_orchestrator_check_summary("nonexistent\\plugins", "Buffout4");
    // REAL CrashgenReport field set: message, crashgen_name, config_path, issues, installed_plugins
    // For nonexistent path, issues = 0, installed_plugins = 0
    assert_eq!(r.issue_count, 0);
    assert_eq!(r.installed_plugin_count, 0);
    assert!(!r.has_config_path);
}

#[test]
fn test_crashgen_orchestrator_check_summary_empty_path_returns_empty_dto() {
    let r = crashgen_orchestrator_check_summary("", "Buffout4");
    assert_eq!(r.issue_count, 0);
    assert_eq!(r.installed_plugin_count, 0);
    assert!(!r.has_config_path);
}

#[test]
fn test_crashgen_orchestrator_get_issues_nonexistent_returns_empty() {
    assert!(crashgen_orchestrator_get_issues("nonexistent\\plugins", "Buffout4").is_empty());
}

#[test]
fn test_crashgen_orchestrator_get_installed_plugins_nonexistent_returns_empty() {
    assert!(
        crashgen_orchestrator_get_installed_plugins("nonexistent\\plugins", "Buffout4").is_empty()
    );
}
