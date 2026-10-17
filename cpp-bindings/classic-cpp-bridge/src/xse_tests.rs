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
    }
}

#[test]
fn test_resolve_xse_log_for_scan_bridges_the_located_vr_log() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    std::fs::create_dir_all(&data).expect("create data dir");
    let xse_folder = temp.path().join("docs").join("F4SE");
    std::fs::create_dir_all(&xse_folder).expect("create XSE folder");
    std::fs::write(xse_folder.join("f4se.log"), b"").expect("write log");
    std::fs::write(xse_folder.join("f4sevr.log"), b"").expect("write VR log");

    let located = resolve_xse_log_for_scan(
        &data.to_string_lossy(),
        "Fallout4VR",
        "auto",
        &temp.path().join("docs").to_string_lossy(),
    )
    .expect("probe succeeds");

    assert_eq!(located, xse_folder.join("f4sevr.log").to_string_lossy());
}

#[test]
fn test_resolve_xse_log_for_scan_returns_empty_when_the_log_is_missing() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    std::fs::create_dir_all(&data).expect("create data dir");

    let located = resolve_xse_log_for_scan(
        &data.to_string_lossy(),
        "Fallout4",
        "Original",
        &temp.path().join("docs").to_string_lossy(),
    )
    .expect("absence is not a failure");

    assert_eq!(located, "");
}

#[test]
fn test_resolve_xse_log_for_scan_raises_operational_failures() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    std::fs::create_dir_all(&data).expect("create data dir");
    std::fs::write(
        data.join("CLASSIC Fallout4 Local.yaml"),
        "Game_Info:\n  Docs_Folder_XSE: \"bad\\0xse\"\n",
    )
    .expect("write Local.yaml");

    let error = resolve_xse_log_for_scan(&data.to_string_lossy(), "Fallout4", "Original", "")
        .expect_err("an uninspectable log is an operational failure");

    assert!(error.starts_with("cannot inspect XSE log "), "{error}");
}
