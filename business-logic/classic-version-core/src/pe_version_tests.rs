use super::*;

#[test]
fn test_is_valid_executable_path_nonexistent() {
    assert!(!is_valid_executable_path(Path::new("nonexistent_file.exe")));
}

#[test]
fn test_is_valid_executable_path_wrong_extension() {
    let temp = tempfile::NamedTempFile::with_suffix(".txt").unwrap();
    assert!(!is_valid_executable_path(temp.path()));
}

#[test]
fn test_is_valid_executable_path_exe() {
    let temp = tempfile::NamedTempFile::with_suffix(".exe").unwrap();
    assert!(is_valid_executable_path(temp.path()));
}

#[test]
fn test_is_valid_executable_path_dll() {
    let temp = tempfile::NamedTempFile::with_suffix(".dll").unwrap();
    assert!(is_valid_executable_path(temp.path()));
}

#[test]
fn test_is_valid_executable_path_case_insensitive() {
    let temp = tempfile::NamedTempFile::with_suffix(".EXE").unwrap();
    assert!(is_valid_executable_path(temp.path()));
}

#[test]
fn test_extract_pe_version_invalid_path() {
    let result = extract_pe_version(Path::new("nonexistent.exe"));
    assert!(matches!(result, Err(PeVersionError::InvalidPath(_))));
}

#[test]
fn test_extract_pe_version_not_a_pe() {
    let temp = tempfile::NamedTempFile::with_suffix(".exe").unwrap();
    std::fs::write(temp.path(), b"not a real PE file").unwrap();
    let result = extract_pe_version(temp.path());
    assert!(matches!(result, Err(PeVersionError::InvalidPe(_))));
}

#[test]
fn test_extract_pe_version_wrong_extension() {
    let temp = tempfile::NamedTempFile::with_suffix(".txt").unwrap();
    let result = extract_pe_version(temp.path());
    assert!(matches!(result, Err(PeVersionError::InvalidPath(_))));
}

/// Integration test: extract version from a real system DLL if available.
#[test]
#[cfg(target_os = "windows")]
fn test_extract_pe_version_real_dll() {
    // kernel32.dll should always exist on Windows
    let kernel32 = Path::new("C:\\Windows\\System32\\kernel32.dll");
    if kernel32.exists() {
        let result = extract_pe_version(kernel32);
        assert!(
            result.is_ok(),
            "Failed to extract version from kernel32.dll: {:?}",
            result.err()
        );
        let (major, minor, _patch, _build) = result.unwrap();
        // kernel32.dll version should have non-zero major
        assert!(major > 0, "Expected non-zero major version, got {}", major);
        // Windows 10+ should have major >= 10
        assert!(
            major >= 6,
            "Expected major >= 6 for modern Windows, got {}.{}",
            major,
            minor
        );
    }
}
