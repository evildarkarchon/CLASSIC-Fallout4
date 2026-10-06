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
