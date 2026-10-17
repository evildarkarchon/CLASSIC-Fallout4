//! The local server's path mapping and the tag quoting.

use super::*;

#[test]
fn quote_matches_python_quote_with_no_safe_characters() {
    assert_eq!(
        quote("app-notification-v9.2.0-rc.1+build.5"),
        "app-notification-v9.2.0-rc.1%2Bbuild.5"
    );
    assert_eq!(quote("a b/é~"), "a%20b%2F%C3%A9~");
}

#[test]
fn local_file_decodes_escapes_and_refuses_to_leave_the_root() {
    let dir = tempfile::tempdir().expect("temp dir");
    let nested = dir.path().join("releases/download/v1+b");
    std::fs::create_dir_all(&nested).expect("mkdir");
    std::fs::write(nested.join("manifest.json"), "{}").expect("write");

    assert_eq!(
        local_file(dir.path(), "/releases/download/v1%2Bb/manifest.json?x=1"),
        Some(nested.join("manifest.json"))
    );
    assert_eq!(local_file(dir.path(), "/releases/download/v1+b"), None);
    assert_eq!(local_file(dir.path(), "/../outside.json"), None);
    assert_eq!(local_file(dir.path(), "/%2e%2e/outside.json"), None);
    assert_eq!(local_file(dir.path(), "/C:%5Cwindows"), None);
    assert_eq!(local_file(dir.path(), "/bad%zz"), None);
}
