use super::*;
use std::fs;
use tempfile::TempDir;

fn create_test_docs_structure(temp_dir: &Path, relative_path: &str) -> PathBuf {
    let docs_path = temp_dir.join(relative_path);
    fs::create_dir_all(&docs_path).unwrap();
    docs_path
}

fn create_test_ini(docs_path: &Path, ini_name: &str) {
    let ini_path = docs_path.join(ini_name);
    fs::write(&ini_path, "[General]\nkey=value\n").unwrap();
}

#[test]
fn test_new() {
    let finder = DocsPathFinder::new("My Games\\Fallout4");
    assert_eq!(finder.relative_path(), "My Games\\Fallout4");
}

#[test]
fn test_validate_docs_path_success() {
    let temp_dir = TempDir::new().unwrap();
    let docs_path = create_test_docs_structure(temp_dir.path(), "My Games/Fallout4");

    let finder = DocsPathFinder::new("My Games/Fallout4");
    assert!(finder.validate_docs_path(&docs_path).is_ok());
}

#[test]
fn test_validate_docs_path_not_found() {
    let finder = DocsPathFinder::new("My Games/Fallout4");
    let result = finder.validate_docs_path(Path::new("/nonexistent/path"));

    assert!(result.is_err());
    assert!(matches!(
        result,
        Err(DocsPathError::PathError(crate::error::PathError::NotFound(
            _
        )))
    ));
}

#[test]
fn test_validate_ini_files_success() {
    let temp_dir = TempDir::new().unwrap();
    let docs_path = create_test_docs_structure(temp_dir.path(), "My Games/Fallout4");

    create_test_ini(&docs_path, "Fallout4.ini");
    create_test_ini(&docs_path, "Fallout4Prefs.ini");

    let finder = DocsPathFinder::new("My Games/Fallout4");
    assert!(
        finder
            .validate_ini_files(&docs_path, &["Fallout4.ini", "Fallout4Prefs.ini"])
            .is_ok()
    );
}

#[test]
fn test_validate_ini_files_missing() {
    let temp_dir = TempDir::new().unwrap();
    let docs_path = create_test_docs_structure(temp_dir.path(), "My Games/Fallout4");

    create_test_ini(&docs_path, "Fallout4.ini");
    // Missing Fallout4Prefs.ini

    let finder = DocsPathFinder::new("My Games/Fallout4");
    let result = finder.validate_ini_files(&docs_path, &["Fallout4.ini", "Fallout4Prefs.ini"]);

    assert!(result.is_err());
    assert!(matches!(
        result,
        Err(DocsPathError::IniValidationFailed { .. })
    ));
}

#[test]
fn test_find_docs_path_with_valid_cache() {
    let temp_dir = TempDir::new().unwrap();
    let docs_path = create_test_docs_structure(temp_dir.path(), "My Games/Fallout4");

    let finder = DocsPathFinder::new("My Games/Fallout4");
    let result = finder.find_docs_path(Some(docs_path.to_str().unwrap()));

    assert!(result.is_ok());
    assert_eq!(result.unwrap(), docs_path);
}

#[test]
fn test_find_docs_path_fallback_to_platform_detection() {
    // Use a relative path that's very unlikely to exist
    let finder = DocsPathFinder::new("NonExistentGame/VeryUnlikelyTestPath");
    let result = finder.find_docs_path(Some("/invalid/cache/path"));

    // The cache is invalid, so it should fall back to platform detection
    // On Windows: might find Documents via registry, but path won't exist
    // On Linux: might find home directory, but path won't exist
    // Either way, this specific path is very unlikely to exist

    // We accept both outcomes:
    // - Error if the path doesn't exist (expected)
    // - Ok if someone actually created this exact path (very unlikely but valid)
    match result {
        Ok(path) => {
            // If found, verify it's a directory
            assert!(path.is_dir());
        }
        Err(e) => {
            // Expected error: NotFound or PathError::NotFound
            assert!(
                matches!(e, DocsPathError::NotFound)
                    || matches!(
                        e,
                        DocsPathError::PathError(crate::error::PathError::NotFound(_))
                    )
            );
        }
    }
}
