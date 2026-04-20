use super::*;

#[test]
fn test_pathlike_basic() {
    // Basic sanity test - full testing requires Python runtime
    let path = PathLike(PathBuf::from("/test/path"));
    let path_buf: PathBuf = path.into();
    assert_eq!(path_buf.to_str().unwrap(), "/test/path");
}

#[test]
fn test_pathlike_as_ref() {
    let path = PathLike(PathBuf::from("/test/path"));
    let path_ref: &std::path::Path = path.as_ref();
    assert_eq!(path_ref.to_str().unwrap(), "/test/path");
}
