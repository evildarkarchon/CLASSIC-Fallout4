use super::*;

#[test]
fn test_resolve_fallout4_exe_name_uses_registry_metadata() {
    assert_eq!(resolve_fallout4_exe_name("Original"), "Fallout4.exe");
    assert_eq!(resolve_fallout4_exe_name("VR"), "Fallout4VR.exe");
}

#[test]
fn test_check_restricted_path_false_on_manifest_dir() {
    let p = env!("CARGO_MANIFEST_DIR");
    assert!(!check_restricted_path(p));
}

#[test]
fn test_check_restricted_path_true_on_windows_dir() {
    assert!(check_restricted_path("C:\\Windows"));
    assert!(check_restricted_path("C:\\Program Files\\SomeGame"));
}
