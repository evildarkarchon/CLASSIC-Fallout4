use super::*;
use std::path::PathBuf;

/// Writes `CLASSIC {game} Local.yaml` under a fresh `CLASSIC Data` directory.
fn write_local(data: &Path, game: &str, contents: &str) {
    std::fs::create_dir_all(data).expect("create CLASSIC Data");
    std::fs::write(data.join(format!("CLASSIC {game} Local.yaml")), contents)
        .expect("write Local.yaml");
}

#[test]
fn resolve_xse_folder_prefers_explicit_local_yaml_xse_folder() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    write_local(
        &data,
        "Fallout4",
        r#"
Game_Info:
  Docs_Folder_XSE: C:\Users\Test\Documents\My Games\Fallout4\CustomXSE
  Root_Folder_Docs: C:\Users\Test\Documents\My Games\Fallout4
"#,
    );

    let folder = resolve_xse_folder_for_scan(&data, "Fallout4", "auto", None)
        .expect("expected explicit XSE Folder");

    assert_eq!(
        folder,
        PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4\CustomXSE")
    );
}

#[test]
fn resolve_xse_folder_trims_the_explicit_xse_folder() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    write_local(
        &data,
        "Fallout4",
        "Game_Info:\n  Docs_Folder_XSE: \"  D:/Custom/XSE  \"\n  Root_Folder_Docs: C:/Docs/Fallout4\n",
    );

    let folder = resolve_xse_folder_for_scan(&data, "Fallout4", "auto", None);

    assert_eq!(folder, Some(PathBuf::from("D:/Custom/XSE")));
}

#[test]
fn resolve_xse_folder_derives_local_docs_root_from_registry_xse_acronym() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    write_local(
        &data,
        "Fallout4",
        r#"
Game_Info:
  Root_Folder_Docs: C:\Users\Test\Documents\My Games\Fallout4VR
"#,
    );

    let folder = resolve_xse_folder_for_scan(&data, "Fallout4", "VR", None)
        .expect("expected derived XSE Folder");

    // F4SEVR writes crash logs under F4SE.
    assert_eq!(
        folder,
        PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4VR\F4SE")
    );
}

#[test]
fn resolve_xse_folder_treats_blank_local_values_as_missing() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    write_local(
        &data,
        "Fallout4",
        r#"
Game_Info:
  Docs_Folder_XSE: "   "
  Root_Folder_Docs: "   "
"#,
    );

    let configured_docs_root = PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4");
    let folder = resolve_xse_folder_for_scan(
        &data,
        "Fallout4",
        "Original",
        Some(configured_docs_root.as_path()),
    )
    .expect("expected configured docs root fallback");

    assert_eq!(
        folder,
        PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4\F4SE")
    );
}

#[test]
fn resolve_xse_folder_uses_configured_docs_root_when_local_yaml_missing() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    std::fs::create_dir_all(&data).expect("create data dir");
    let configured_docs_root = PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4VR");

    let folder = resolve_xse_folder_for_scan(
        &data,
        "Fallout4",
        "VR",
        Some(configured_docs_root.as_path()),
    )
    .expect("expected configured docs root fallback");

    assert_eq!(
        folder,
        PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4VR\F4SE")
    );
}

#[test]
fn resolve_xse_folder_ignores_malformed_local_yaml() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    write_local(&data, "Fallout4", "[invalid: yaml");
    let configured_docs_root = PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4");

    let folder = resolve_xse_folder_for_scan(
        &data,
        "Fallout4",
        "Original",
        Some(configured_docs_root.as_path()),
    );

    assert_eq!(
        folder,
        Some(PathBuf::from(
            r"C:\Users\Test\Documents\My Games\Fallout4\F4SE"
        ))
    );
}

#[test]
fn resolve_xse_folder_treats_fallout4vr_auto_as_vr() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    std::fs::create_dir_all(&data).expect("create data dir");
    let configured_docs_root = PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4VR");

    let folder = resolve_xse_folder_for_scan(
        &data,
        "Fallout4VR",
        "auto",
        Some(configured_docs_root.as_path()),
    )
    .expect("expected Fallout4VR auto fallback");

    assert_eq!(
        folder,
        PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4VR\F4SE")
    );
}

#[test]
fn resolve_xse_folder_reads_only_the_named_games_local_yaml() {
    // Fallout 4 VR keeps its own `CLASSIC Fallout4VR Local.yaml`; the flat
    // Fallout 4 document must not leak into a VR resolution.
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    write_local(
        &data,
        "Fallout4",
        "Game_Info:\n  Docs_Folder_XSE: D:/Flat/XSE\n",
    );
    let configured_docs_root = PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4VR");

    let folder = resolve_xse_folder_for_scan(
        &data,
        "Fallout4VR",
        "auto",
        Some(configured_docs_root.as_path()),
    );

    assert_eq!(
        folder,
        Some(PathBuf::from(
            r"C:\Users\Test\Documents\My Games\Fallout4VR\F4SE"
        ))
    );
}

#[test]
fn resolve_xse_folder_returns_none_for_unknown_games_without_local_facts() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    std::fs::create_dir_all(&data).expect("create data dir");

    assert_eq!(
        resolve_xse_folder_for_scan(&data, "Unknown", "auto", None),
        None
    );
}

/// Creates `<root>/<relative>` as an empty file, creating its parent folders.
fn touch(root: &Path, relative: &str) -> PathBuf {
    let path = root.join(relative);
    std::fs::create_dir_all(path.parent().expect("log has a parent")).expect("create folder");
    std::fs::write(&path, b"").expect("write log");
    path
}

#[test]
fn resolve_xse_log_uses_the_recorded_game_local_xse_folder() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    let explicit = temp.path().join("explicit");
    let log = touch(&explicit, "f4se.log");
    touch(temp.path(), "configured/F4SE/f4se.log");
    write_local(
        &data,
        "Fallout4",
        &format!("Game_Info:\n  Docs_Folder_XSE: '{}'\n", explicit.display()),
    );
    let configured = temp.path().join("configured");

    let located = resolve_xse_log_for_scan(&data, "Fallout4", "Original", Some(&configured))
        .expect("probe succeeds");

    assert_eq!(located, Some(log));
}

#[test]
fn resolve_xse_log_reads_fallout4_vr_from_its_own_local_yaml_and_log() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    let vr_docs = temp.path().join("vr-docs");
    touch(&vr_docs, "F4SE/f4se.log");
    let vr_log = touch(&vr_docs, "F4SE/f4sevr.log");
    write_local(
        &data,
        "Fallout4VR",
        &format!("Game_Info:\n  Root_Folder_Docs: '{}'\n", vr_docs.display()),
    );

    let located =
        resolve_xse_log_for_scan(&data, "Fallout4VR", "auto", None).expect("probe succeeds");

    assert_eq!(located, Some(vr_log));
}

#[test]
fn resolve_xse_log_returns_nothing_when_the_log_is_missing() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    std::fs::create_dir_all(&data).expect("create data dir");
    let configured = temp.path().join("configured");
    std::fs::create_dir_all(configured.join("F4SE")).expect("create XSE folder");

    let located = resolve_xse_log_for_scan(&data, "Fallout4", "Original", Some(&configured))
        .expect("absence is not a failure");

    assert_eq!(located, None);
}

#[test]
fn resolve_xse_log_reports_an_uninspectable_recorded_folder_as_a_typed_error() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    // The YAML `\0` escape records a folder no platform can inspect.
    write_local(
        &data,
        "Fallout4",
        "Game_Info:\n  Docs_Folder_XSE: \"bad\\0xse\"\n",
    );

    let error = resolve_xse_log_for_scan(&data, "Fallout4", "Original", None)
        .expect_err("an uninspectable log is an operational failure");

    assert!(matches!(error, XseLogError::Inspect { .. }), "{error}");
}
