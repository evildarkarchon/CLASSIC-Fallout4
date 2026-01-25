//! YAML file loading with sync and async APIs.

use crate::error::{Result, SettingsError};
use std::fs;
use std::path::Path;
use tokio::fs as async_fs;
use yaml_rust2::{Yaml, YamlLoader};

/// Load YAML file synchronously.
///
/// Reads a YAML file from disk and parses it into a Vec of Yaml documents.
///
/// # Arguments
///
/// * `path` - Path to the YAML file
///
/// # Returns
///
/// A vector of parsed YAML documents (most files have one document).
///
/// # Errors
///
/// Returns an error if:
/// - The file cannot be read
/// - The YAML content is invalid
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::load_yaml_sync;
/// use std::path::Path;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let docs = load_yaml_sync(Path::new("config.yaml"))?;
/// # Ok(())
/// # }
/// ```
pub fn load_yaml_sync(path: &Path) -> Result<Vec<Yaml>> {
    let content = fs::read_to_string(path).map_err(|e| SettingsError::IoError {
        path: path.to_path_buf(),
        source: e,
    })?;

    YamlLoader::load_from_str(&content).map_err(|e| SettingsError::YamlParseError {
        path: path.to_path_buf(),
        message: e.to_string(),
    })
}

/// Load YAML file asynchronously.
///
/// Reads a YAML file from disk asynchronously and parses it into a Vec of Yaml documents.
/// Uses the shared global Tokio runtime per ONE RUNTIME RULE.
///
/// # Arguments
///
/// * `path` - Path to the YAML file
///
/// # Returns
///
/// A vector of parsed YAML documents (most files have one document).
///
/// # Errors
///
/// Returns an error if:
/// - The file cannot be read
/// - The YAML content is invalid
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::load_yaml_async;
/// use std::path::Path;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let docs = load_yaml_async(Path::new("config.yaml")).await?;
/// # Ok(())
/// # }
/// ```
pub async fn load_yaml_async(path: &Path) -> Result<Vec<Yaml>> {
    let content = async_fs::read_to_string(path)
        .await
        .map_err(|e| SettingsError::IoError {
            path: path.to_path_buf(),
            source: e,
        })?;

    YamlLoader::load_from_str(&content).map_err(|e| SettingsError::YamlParseError {
        path: path.to_path_buf(),
        message: e.to_string(),
    })
}

/// Load multiple YAML files in batch (synchronous).
///
/// Loads multiple YAML files in sequence. If any file fails to load,
/// the error is returned immediately.
///
/// # Arguments
///
/// * `paths` - Slice of paths to load
///
/// # Returns
///
/// A vector of tuples, each containing (path, parsed_documents).
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::load_yaml_batch_sync;
/// use std::path::Path;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let paths = vec![Path::new("config1.yaml"), Path::new("config2.yaml")];
/// let results = load_yaml_batch_sync(&paths)?;
/// # Ok(())
/// # }
/// ```
pub fn load_yaml_batch_sync(paths: &[&Path]) -> Result<Vec<(String, Vec<Yaml>)>> {
    let mut results = Vec::with_capacity(paths.len());

    for path in paths {
        let docs = load_yaml_sync(path)?;
        results.push((path.display().to_string(), docs));
    }

    Ok(results)
}

/// Load multiple YAML files in batch (asynchronous).
///
/// Loads multiple YAML files concurrently for better performance.
/// If any file fails to load, the error is returned.
///
/// # Arguments
///
/// * `paths` - Slice of paths to load
///
/// # Returns
///
/// A vector of tuples, each containing (path, parsed_documents).
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::load_yaml_batch_async;
/// use std::path::Path;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let paths = vec![Path::new("config1.yaml"), Path::new("config2.yaml")];
/// let results = load_yaml_batch_async(&paths).await?;
/// # Ok(())
/// # }
/// ```
pub async fn load_yaml_batch_async(paths: &[&Path]) -> Result<Vec<(String, Vec<Yaml>)>> {
    let mut handles = Vec::with_capacity(paths.len());

    for &path in paths {
        let path_owned = path.to_path_buf();
        let handle = tokio::spawn(async move {
            let docs = load_yaml_async(&path_owned).await?;
            Ok::<_, SettingsError>((path_owned.display().to_string(), docs))
        });
        handles.push(handle);
    }

    let mut results = Vec::with_capacity(paths.len());
    for handle in handles {
        let result = handle.await.map_err(|e| SettingsError::YamlParseError {
            path: "unknown".into(),
            message: format!("Task join error: {}", e),
        })??;
        results.push(result);
    }

    Ok(results)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    fn create_test_yaml(content: &str) -> NamedTempFile {
        let mut file = NamedTempFile::new().unwrap();
        file.write_all(content.as_bytes()).unwrap();
        file.flush().unwrap();
        file
    }

    #[test]
    fn test_load_yaml_sync_success() {
        let yaml_content = "key: value\nnumber: 42\n";
        let file = create_test_yaml(yaml_content);

        let result = load_yaml_sync(file.path());
        assert!(result.is_ok());

        let docs = result.unwrap();
        assert_eq!(docs.len(), 1);
    }

    #[test]
    fn test_load_yaml_sync_invalid() {
        // Use actually invalid YAML syntax (tabs in indentation)
        let yaml_content = "key: value\n\tinvalid: tabs_not_allowed\n";
        let file = create_test_yaml(yaml_content);

        let result = load_yaml_sync(file.path());
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_load_yaml_async_success() {
        let yaml_content = "key: value\nnumber: 42\n";
        let file = create_test_yaml(yaml_content);

        let result = load_yaml_async(file.path()).await;
        assert!(result.is_ok());

        let docs = result.unwrap();
        assert_eq!(docs.len(), 1);
    }

    #[test]
    fn test_load_yaml_batch_sync() {
        let yaml1 = create_test_yaml("key1: value1\n");
        let yaml2 = create_test_yaml("key2: value2\n");

        let paths = vec![yaml1.path(), yaml2.path()];
        let result = load_yaml_batch_sync(&paths);

        assert!(result.is_ok());
        let results = result.unwrap();
        assert_eq!(results.len(), 2);
    }

    #[tokio::test]
    async fn test_load_yaml_batch_async() {
        let yaml1 = create_test_yaml("key1: value1\n");
        let yaml2 = create_test_yaml("key2: value2\n");

        let paths = vec![yaml1.path(), yaml2.path()];
        let result = load_yaml_batch_async(&paths).await;

        assert!(result.is_ok());
        let results = result.unwrap();
        assert_eq!(results.len(), 2);
    }

    // ========================================================================
    // Additional Tests for Improved Coverage
    // ========================================================================

    #[test]
    fn test_load_yaml_sync_file_not_found() {
        let result = load_yaml_sync(Path::new("/nonexistent/path/to/file.yaml"));
        assert!(result.is_err());

        let err = result.unwrap_err();
        match err {
            SettingsError::IoError { path, source } => {
                assert!(path.to_string_lossy().contains("nonexistent"));
                assert!(source.kind() == std::io::ErrorKind::NotFound);
            }
            _ => panic!("Expected IoError, got {:?}", err),
        }
    }

    #[tokio::test]
    async fn test_load_yaml_async_file_not_found() {
        let result = load_yaml_async(Path::new("/nonexistent/path/to/file.yaml")).await;
        assert!(result.is_err());

        let err = result.unwrap_err();
        assert!(matches!(err, SettingsError::IoError { .. }));
    }

    #[test]
    fn test_load_yaml_sync_multi_document() {
        // Multiple YAML documents in one file
        let yaml_content = "doc1: value1\n---\ndoc2: value2\n---\ndoc3: value3\n";
        let file = create_test_yaml(yaml_content);

        let docs = load_yaml_sync(file.path()).unwrap();
        assert_eq!(docs.len(), 3);
        assert_eq!(docs[0]["doc1"].as_str(), Some("value1"));
        assert_eq!(docs[1]["doc2"].as_str(), Some("value2"));
        assert_eq!(docs[2]["doc3"].as_str(), Some("value3"));
    }

    #[tokio::test]
    async fn test_load_yaml_async_multi_document() {
        let yaml_content = "async_doc1: value1\n---\nasync_doc2: value2\n";
        let file = create_test_yaml(yaml_content);

        let docs = load_yaml_async(file.path()).await.unwrap();
        assert_eq!(docs.len(), 2);
        assert_eq!(docs[0]["async_doc1"].as_str(), Some("value1"));
        assert_eq!(docs[1]["async_doc2"].as_str(), Some("value2"));
    }

    #[test]
    fn test_load_yaml_sync_empty_file() {
        let file = create_test_yaml("");
        let docs = load_yaml_sync(file.path()).unwrap();
        // Empty file should parse without error
        assert!(docs.is_empty() || (docs.len() == 1 && docs[0].is_badvalue()));
    }

    #[tokio::test]
    async fn test_load_yaml_async_empty_file() {
        let file = create_test_yaml("");
        let docs = load_yaml_async(file.path()).await.unwrap();
        assert!(docs.is_empty() || (docs.len() == 1 && docs[0].is_badvalue()));
    }

    #[test]
    fn test_load_yaml_batch_sync_empty_list() {
        let paths: Vec<&Path> = vec![];
        let result = load_yaml_batch_sync(&paths);
        assert!(result.is_ok());
        assert!(result.unwrap().is_empty());
    }

    #[tokio::test]
    async fn test_load_yaml_batch_async_empty_list() {
        let paths: Vec<&Path> = vec![];
        let result = load_yaml_batch_async(&paths).await;
        assert!(result.is_ok());
        assert!(result.unwrap().is_empty());
    }

    #[test]
    fn test_load_yaml_batch_sync_with_invalid_file() {
        let yaml1 = create_test_yaml("valid: file\n");

        let paths = vec![yaml1.path(), Path::new("/nonexistent.yaml")];
        let result = load_yaml_batch_sync(&paths);
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_load_yaml_batch_async_with_invalid_file() {
        let yaml1 = create_test_yaml("valid: file\n");

        let paths = vec![yaml1.path(), Path::new("/nonexistent.yaml")];
        let result = load_yaml_batch_async(&paths).await;
        assert!(result.is_err());
    }

    #[test]
    fn test_load_yaml_sync_complex_structures() {
        let yaml_content = r#"
root:
  nested:
    level1:
      level2:
        deep: "deeply nested value"
  array:
    - item1
    - item2
    - key: value
      nested_key: nested_value
  types:
    string: "hello"
    integer: 42
    float: 3.14159
    boolean_true: true
    boolean_false: false
    null_value: null
"#;
        let file = create_test_yaml(yaml_content);

        let docs = load_yaml_sync(file.path()).unwrap();
        assert_eq!(docs.len(), 1);

        let root = &docs[0]["root"];
        assert_eq!(
            root["nested"]["level1"]["level2"]["deep"].as_str(),
            Some("deeply nested value")
        );
        assert_eq!(root["types"]["integer"].as_i64(), Some(42));
        assert_eq!(root["types"]["boolean_true"].as_bool(), Some(true));
        assert!(root["types"]["null_value"].is_null());
    }

    #[tokio::test]
    async fn test_load_yaml_async_complex_structures() {
        let yaml_content = r#"
async_root:
  list:
    - a
    - b
    - c
  map:
    key1: value1
    key2: value2
"#;
        let file = create_test_yaml(yaml_content);

        let docs = load_yaml_async(file.path()).await.unwrap();
        assert_eq!(docs.len(), 1);

        let root = &docs[0]["async_root"];
        assert!(root["list"].is_array());
        assert!(root["map"].is_hash());
    }

    #[test]
    fn test_load_yaml_sync_unicode_content() {
        let yaml_content = "emoji: 🎮🕹️\njapanese: 日本語\narabic: العربية\n";
        let file = create_test_yaml(yaml_content);

        let docs = load_yaml_sync(file.path()).unwrap();
        assert_eq!(docs.len(), 1);
        assert_eq!(docs[0]["emoji"].as_str(), Some("🎮🕹️"));
        assert_eq!(docs[0]["japanese"].as_str(), Some("日本語"));
        assert_eq!(docs[0]["arabic"].as_str(), Some("العربية"));
    }

    #[tokio::test]
    async fn test_load_yaml_async_unicode_content() {
        let yaml_content = "unicode: 中文测试\n";
        let file = create_test_yaml(yaml_content);

        let docs = load_yaml_async(file.path()).await.unwrap();
        assert_eq!(docs[0]["unicode"].as_str(), Some("中文测试"));
    }

    #[test]
    fn test_load_yaml_batch_sync_preserves_path_info() {
        let yaml1 = create_test_yaml("file: one\n");
        let yaml2 = create_test_yaml("file: two\n");

        let paths = vec![yaml1.path(), yaml2.path()];
        let results = load_yaml_batch_sync(&paths).unwrap();

        // Each result should contain path string
        assert_eq!(results.len(), 2);
        for (path_str, docs) in &results {
            assert!(!path_str.is_empty());
            assert!(!docs.is_empty());
        }
    }

    #[tokio::test]
    async fn test_load_yaml_batch_async_preserves_path_info() {
        let yaml1 = create_test_yaml("async_file: one\n");
        let yaml2 = create_test_yaml("async_file: two\n");

        let paths = vec![yaml1.path(), yaml2.path()];
        let results = load_yaml_batch_async(&paths).await.unwrap();

        assert_eq!(results.len(), 2);
        for (path_str, docs) in &results {
            assert!(!path_str.is_empty());
            assert!(!docs.is_empty());
        }
    }

    #[test]
    fn test_load_yaml_sync_with_anchors_and_aliases() {
        // Test basic anchor and alias (not merge keys which yaml-rust2 may not support)
        let yaml_content = r#"
defaults: &defaults
  adapter: postgres
  host: localhost

development:
  settings: *defaults
  database: dev_db
"#;
        let file = create_test_yaml(yaml_content);

        let docs = load_yaml_sync(file.path()).unwrap();
        assert_eq!(docs.len(), 1);

        // The anchor itself should be accessible
        let doc = &docs[0];
        assert_eq!(doc["defaults"]["adapter"].as_str(), Some("postgres"));
        assert_eq!(doc["defaults"]["host"].as_str(), Some("localhost"));
        assert_eq!(doc["development"]["database"].as_str(), Some("dev_db"));

        // The alias should reference the same structure
        assert_eq!(
            doc["development"]["settings"]["adapter"].as_str(),
            Some("postgres")
        );
    }

    #[test]
    fn test_load_yaml_sync_multiline_strings() {
        let yaml_content = r#"
literal: |
  This is a literal block
  with multiple lines
  preserved exactly.
folded: >
  This is a folded block
  that collapses newlines
  into spaces.
"#;
        let file = create_test_yaml(yaml_content);

        let docs = load_yaml_sync(file.path()).unwrap();
        let doc = &docs[0];

        let literal = doc["literal"].as_str().unwrap();
        assert!(literal.contains('\n'));
        assert!(literal.contains("literal block"));

        let folded = doc["folded"].as_str().unwrap();
        assert!(folded.contains("folded block"));
    }
}
