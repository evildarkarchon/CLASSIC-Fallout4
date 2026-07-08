use super::*;

#[test]
fn test_xse_get_loader_name_f4se_exact_string() {
    // Codex LOW correction: verified literal at classic-xse-core/src/lib.rs:169
    assert_eq!(xse_get_loader_name(ffi::XseType::F4SE), "f4se_loader.exe");
}

#[test]
fn test_xse_get_loader_name_skse64_exact_string() {
    assert_eq!(
        xse_get_loader_name(ffi::XseType::SKSE64),
        "skse64_loader.exe"
    );
}

#[test]
fn test_xse_get_loader_name_all_variants_nonempty() {
    for t in [
        ffi::XseType::F4SE,
        ffi::XseType::F4SEVR,
        ffi::XseType::SKSE,
        ffi::XseType::SKSE64,
        ffi::XseType::SKSEVR,
        ffi::XseType::SFSE,
    ] {
        assert!(!xse_get_loader_name(t).is_empty());
        assert!(!xse_get_dll_prefix(t).is_empty());
    }
}

#[test]
fn test_xse_get_dll_prefix_has_trailing_underscore() {
    // Codex LOW correction: dll_prefix returns "f4se_" / "skse64_" — with trailing underscore
    assert_eq!(xse_get_dll_prefix(ffi::XseType::F4SE), "f4se_");
    assert_eq!(xse_get_dll_prefix(ffi::XseType::SKSE64), "skse64_");
    assert_eq!(xse_get_dll_prefix(ffi::XseType::SFSE), "sfse_");
}

#[test]
fn test_xse_get_type_from_game_id_total_mapping() {
    // Codex LOW correction: XseType::from_game_id is INFALLIBLE
    // Verified at classic-xse-core/src/lib.rs:143-150
    assert_eq!(xse_get_type_from_game_id("Fallout4"), "F4SE");
    assert_eq!(xse_get_type_from_game_id("Fallout4VR"), "F4SEVR");
    assert_eq!(xse_get_type_from_game_id("Skyrim"), "SKSE64");
    assert_eq!(xse_get_type_from_game_id("Starfield"), "SFSE");
}

#[test]
fn test_xse_get_type_from_game_id_unknown_game_returns_empty() {
    // The only failure mode is the string-decoding step
    assert_eq!(xse_get_type_from_game_id("InvalidGame"), "");
}

#[test]
fn test_is_xse_installed_nonexistent_returns_false() {
    assert!(!is_xse_installed("nonexistent\\path", ffi::XseType::F4SE));
}

#[test]
fn test_is_xse_installed_empty_returns_false() {
    assert!(!is_xse_installed("", ffi::XseType::F4SE));
}

#[test]
fn test_xse_get_info_nonexistent_returns_not_installed() {
    let info = xse_get_info("nonexistent\\path", ffi::XseType::F4SE);
    assert!(!info.installed);
    assert!(info.version.is_empty());
    assert_eq!(info.xse_type, "F4SE");
}

#[test]
fn test_detect_xse_version_string_empty_returns_empty() {
    assert_eq!(detect_xse_version_string("", "F4SE"), "");
}

#[test]
fn test_is_xse_installed_check_empty_returns_false() {
    assert!(!is_xse_installed_check("", "F4SE"));
}

#[test]
fn test_xse_type_from_str_internal_known_and_unknown() {
    assert!(xse_type_from_str_internal("F4SE").is_some());
    assert!(xse_type_from_str_internal("f4se").is_some()); // case-insensitive
    assert!(xse_type_from_str_internal("SFSE").is_some());
    assert!(xse_type_from_str_internal("BOGUS").is_none());
}

#[test]
fn test_resolve_xse_folder_for_scan_bridges_configured_docs_root() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    std::fs::create_dir_all(&data).expect("create data dir");

    let resolved = resolve_xse_folder_for_scan(
        &data.to_string_lossy(),
        "Fallout4",
        "VR",
        r"C:\Users\Test\Documents\My Games\Fallout4VR",
    );

    assert_eq!(
        resolved,
        r"C:\Users\Test\Documents\My Games\Fallout4VR\F4SE"
    );
}

#[test]
fn test_resolve_xse_folder_for_scan_returns_empty_for_missing_inputs() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    std::fs::create_dir_all(&data).expect("create data dir");

    assert_eq!(
        resolve_xse_folder_for_scan(&data.to_string_lossy(), "Unknown", "auto", ""),
        ""
    );
}
