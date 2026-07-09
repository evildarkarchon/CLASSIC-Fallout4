use super::*;

#[test]
fn test_xse_type_as_str() {
    assert_eq!(XseType::F4SE.as_str(), "F4SE");
    assert_eq!(XseType::SKSE64.as_str(), "SKSE64");
    assert_eq!(XseType::SFSE.as_str(), "SFSE");
}

#[test]
fn test_xse_type_from_str() {
    assert_eq!("f4se".parse::<XseType>().unwrap(), XseType::F4SE);
    assert_eq!("F4SE".parse::<XseType>().unwrap(), XseType::F4SE);
    assert_eq!("skse64".parse::<XseType>().unwrap(), XseType::SKSE64);
    assert!("unknown".parse::<XseType>().is_err());
}

#[test]
fn test_xse_type_from_game_id() {
    assert_eq!(XseType::from_game_id(GameId::Fallout4), XseType::F4SE);
    assert_eq!(XseType::from_game_id(GameId::Fallout4VR), XseType::F4SEVR);
    assert_eq!(XseType::from_game_id(GameId::Skyrim), XseType::SKSE64);
    assert_eq!(XseType::from_game_id(GameId::Starfield), XseType::SFSE);
}

#[test]
fn test_xse_type_loader_name() {
    assert_eq!(XseType::F4SE.loader_name(), "f4se_loader.exe");
    assert_eq!(XseType::SKSE64.loader_name(), "skse64_loader.exe");
    assert_eq!(XseType::SFSE.loader_name(), "sfse_loader.exe");
}

#[test]
fn test_xse_type_dll_prefix() {
    assert_eq!(XseType::F4SE.dll_prefix(), "f4se_");
    assert_eq!(XseType::SKSE64.dll_prefix(), "skse64_");
    assert_eq!(XseType::SFSE.dll_prefix(), "sfse_");
}

#[test]
fn test_xse_info_new() {
    let info = XseInfo::new(XseType::F4SE, PathBuf::from("C:\\Games\\Fallout4"));
    assert_eq!(info.xse_type, XseType::F4SE);
    assert_eq!(info.path, PathBuf::from("C:\\Games\\Fallout4"));
    assert_eq!(info.version, None);
    assert!(!info.installed);
}

#[test]
fn test_xse_info_with_version() {
    let info = XseInfo::with_version(
        XseType::F4SE,
        PathBuf::from("C:\\Games\\Fallout4"),
        Some(Version::new(0, 6, 23)),
        true,
    );
    assert_eq!(info.xse_type, XseType::F4SE);
    assert_eq!(info.version, Some(Version::new(0, 6, 23)));
    assert!(info.installed);
}

#[test]
fn test_xse_info_loader_path() {
    let info = XseInfo::new(XseType::F4SE, PathBuf::from("C:\\Games\\Fallout4"));
    let loader = info.loader_path();
    assert!(loader.ends_with("f4se_loader.exe"));
}

#[test]
fn docs_relative_path_uses_proton_safe_separator() {
    assert_eq!(docs_relative_path("Fallout4"), "My Games/Fallout4");
    assert_eq!(docs_relative_path("Fallout4VR"), "My Games/Fallout4VR");
}

#[test]
fn resolve_xse_folder_prefers_explicit_local_yaml_xse_folder() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    std::fs::create_dir_all(&data).expect("create data dir");
    std::fs::write(
        data.join("CLASSIC Fallout4 Local.yaml"),
        r#"
Game_Info:
  Docs_Folder_XSE: C:\Users\Test\Documents\My Games\Fallout4\CustomXSE
  Root_Folder_Docs: C:\Users\Test\Documents\My Games\Fallout4
"#,
    )
    .expect("write local yaml");

    let folder = resolve_xse_folder_for_scan(&data, "Fallout4", "auto", None)
        .expect("expected explicit XSE Folder");

    assert_eq!(
        folder,
        PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4\CustomXSE")
    );
}

#[test]
fn resolve_xse_folder_derives_local_docs_root_from_registry_xse_acronym() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    std::fs::create_dir_all(&data).expect("create data dir");
    std::fs::write(
        data.join("CLASSIC Fallout4 Local.yaml"),
        r#"
Game_Info:
  Root_Folder_Docs: C:\Users\Test\Documents\My Games\Fallout4VR
"#,
    )
    .expect("write local yaml");

    let folder = resolve_xse_folder_for_scan(&data, "Fallout4", "VR", None)
        .expect("expected derived XSE Folder");

    assert_eq!(
        folder,
        PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4VR\F4SE")
    );
}

#[test]
fn resolve_xse_folder_treats_blank_local_values_as_missing() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    std::fs::create_dir_all(&data).expect("create data dir");
    std::fs::write(
        data.join("CLASSIC Fallout4 Local.yaml"),
        r#"
Game_Info:
  Docs_Folder_XSE: "   "
  Root_Folder_Docs: "   "
"#,
    )
    .expect("write local yaml");

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
