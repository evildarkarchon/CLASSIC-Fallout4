//! YAML file loading with sync and async APIs.

use crate::error::{Result, SettingsError, SettingsSource};
use std::fs;
use std::path::{Path, PathBuf};
use tokio::fs as async_fs;
use tokio::task::JoinHandle;
use yaml_rust2::{Yaml, YamlLoader};

/// Parse YAML content from a logical source name.
pub fn parse_yaml_content(source: impl Into<String>, content: &str) -> Result<Vec<Yaml>> {
    parse_yaml_content_with_source(SettingsSource::from(source.into()), content)
}

fn parse_yaml_content_with_source(
    source: impl Into<SettingsSource>,
    content: &str,
) -> Result<Vec<Yaml>> {
    let source = source.into();

    YamlLoader::load_from_str(content).map_err(|e| SettingsError::YamlParseError {
        source,
        message: e.to_string(),
    })
}

/// Merge a YAML document stream into a single mapping.
pub fn merge_yaml_documents(source: impl Into<String>, docs: &[Yaml]) -> Result<Yaml> {
    merge_yaml_documents_with_source(SettingsSource::from(source.into()), docs)
}

fn merge_yaml_documents_with_source(
    source: impl Into<SettingsSource>,
    docs: &[Yaml],
) -> Result<Yaml> {
    let source = source.into();

    if docs.is_empty() || docs.iter().all(Yaml::is_badvalue) {
        return Err(SettingsError::EmptyDocument { source });
    }

    let mut merged = None;

    for (index, doc) in docs.iter().enumerate() {
        let Yaml::Hash(_) = doc else {
            return Err(SettingsError::InvalidYamlStructure {
                source,
                index,
                found: yaml_kind(doc),
            });
        };

        merged = Some(match merged {
            Some(current) => merge_yaml_values(current, doc.clone()),
            None => doc.clone(),
        });
    }

    merged.ok_or(SettingsError::EmptyDocument { source })
}

fn merge_yaml_values(base: Yaml, overlay: Yaml) -> Yaml {
    match (base, overlay) {
        (Yaml::Hash(mut left), Yaml::Hash(right)) => {
            for (key, right_value) in right {
                let merged = match left.remove(&key) {
                    Some(left_value) => merge_yaml_values(left_value, right_value),
                    None => right_value,
                };
                left.insert(key, merged);
            }
            Yaml::Hash(left)
        }
        (_, replacement) => replacement,
    }
}

fn yaml_kind(value: &Yaml) -> String {
    match value {
        Yaml::Array(_) => "sequence",
        Yaml::BadValue => "bad value",
        Yaml::Boolean(_) => "boolean",
        Yaml::Hash(_) => "mapping",
        Yaml::Integer(_) => "integer",
        Yaml::Null => "null",
        Yaml::Real(_) => "real",
        Yaml::String(_) => "string",
        Yaml::Alias(_) => "alias",
    }
    .to_string()
}

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

    parse_yaml_content_with_source(path, &content)
}

/// Load and merge a YAML file synchronously.
pub fn load_yaml_merged_sync(path: &Path) -> Result<Yaml> {
    let docs = load_yaml_sync(path)?;
    merge_yaml_documents_with_source(path, &docs)
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

    parse_yaml_content_with_source(path, &content)
}

/// Load and merge a YAML file asynchronously.
pub async fn load_yaml_merged_async(path: &Path) -> Result<Yaml> {
    let docs = load_yaml_async(path).await?;
    merge_yaml_documents_with_source(path, &docs)
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
        let task_path = path_owned.clone();
        let handle = tokio::spawn(async move {
            let docs = load_yaml_async(&task_path).await?;
            Ok::<_, SettingsError>((task_path.display().to_string(), docs))
        });
        handles.push((path_owned, handle));
    }

    let mut results = Vec::with_capacity(paths.len());
    for (path, handle) in handles {
        let result = await_batch_result(path, handle).await?;
        results.push(result);
    }

    Ok(results)
}

async fn await_batch_result(
    path: PathBuf,
    handle: JoinHandle<Result<(String, Vec<Yaml>)>>,
) -> Result<(String, Vec<Yaml>)> {
    handle
        .await
        .map_err(|source| SettingsError::TaskJoinError { path, source })?
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

        let err = result.unwrap_err();
        match err {
            SettingsError::YamlParseError { source, message: _ } => {
                assert_eq!(source.path().map(PathBuf::as_path), Some(file.path()));
            }
            _ => panic!("Expected YamlParseError, got {:?}", err),
        }
    }

    #[test]
    fn test_parse_yaml_content_reports_source_label_on_parse_error() {
        let err = parse_yaml_content(
            "memory://settings.yaml",
            "key: value\n\tinvalid: tabs_not_allowed\n",
        )
        .unwrap_err();

        match err {
            SettingsError::YamlParseError { source, message: _ } => {
                assert_eq!(source.label(), Some("memory://settings.yaml"))
            }
            _ => panic!("Expected YamlParseError, got {:?}", err),
        }
    }

    #[test]
    fn test_merge_yaml_documents_recursively_merges_nested_maps() {
        let docs = parse_yaml_content(
            "memory://settings.yaml",
            "paths:\n  game_root: C:/Games/Fallout4\n  nested:\n    a: 1\n---\npaths:\n  nested:\n    b: 2\n",
        )
        .unwrap();

        let merged = merge_yaml_documents("memory://settings.yaml", &docs).unwrap();

        assert_eq!(
            merged["paths"]["game_root"].as_str(),
            Some("C:/Games/Fallout4")
        );
        assert_eq!(merged["paths"]["nested"]["a"].as_i64(), Some(1));
        assert_eq!(merged["paths"]["nested"]["b"].as_i64(), Some(2));
    }

    #[test]
    fn test_merge_yaml_documents_replaces_sequences_and_type_conflicts() {
        let docs = parse_yaml_content(
            "memory://settings.yaml",
            "items:\n  - a\nvalue:\n  nested: true\n---\nitems:\n  - b\nvalue: replaced\n",
        )
        .unwrap();

        let merged = merge_yaml_documents("memory://settings.yaml", &docs).unwrap();

        assert_eq!(merged["items"][0].as_str(), Some("b"));
        assert_eq!(merged["items"][1].as_str(), None);
        assert_eq!(merged["value"].as_str(), Some("replaced"));
    }

    #[test]
    fn test_merge_yaml_documents_empty_stream_is_error() {
        let err = merge_yaml_documents("memory://settings.yaml", &[]).unwrap_err();

        match err {
            SettingsError::EmptyDocument { source } => {
                assert_eq!(source.label(), Some("memory://settings.yaml"))
            }
            _ => panic!("Expected EmptyDocument, got {:?}", err),
        }
    }

    #[test]
    fn test_merge_yaml_documents_rejects_non_mapping_documents() {
        let docs =
            parse_yaml_content("memory://settings.yaml", "key: value\n---\n- item\n").unwrap();

        let err = merge_yaml_documents("memory://settings.yaml", &docs).unwrap_err();

        match err {
            SettingsError::InvalidYamlStructure {
                source,
                index,
                found,
            } => {
                assert_eq!(source.label(), Some("memory://settings.yaml"));
                assert_eq!(index, 1);
                assert_eq!(found, "sequence");
            }
            _ => panic!("Expected InvalidYamlStructure, got {:?}", err),
        }
    }

    #[tokio::test]
    async fn test_await_batch_result_reports_join_error_with_path() {
        let file = create_test_yaml("key: value\n");
        let handle = tokio::spawn(async move {
            panic!("boom");
            #[allow(unreachable_code)]
            Ok::<_, SettingsError>(("unused".to_string(), Vec::new()))
        });

        let err = await_batch_result(file.path().to_path_buf(), handle)
            .await
            .unwrap_err();

        match err {
            SettingsError::TaskJoinError { path, source: _ } => {
                assert_eq!(path, file.path());
            }
            _ => panic!("Expected TaskJoinError, got {:?}", err),
        }
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
    fn test_load_yaml_merged_sync_merges_multiple_documents() {
        let file = create_test_yaml("a: 1\n---\nb: 2\n");

        let merged = load_yaml_merged_sync(file.path()).unwrap();

        assert_eq!(merged["a"].as_i64(), Some(1));
        assert_eq!(merged["b"].as_i64(), Some(2));
    }

    #[tokio::test]
    async fn test_load_yaml_merged_async_merges_multiple_documents() {
        let file = create_test_yaml("a: 1\n---\nb: 2\n");

        let merged = load_yaml_merged_async(file.path()).await.unwrap();

        assert_eq!(merged["a"].as_i64(), Some(1));
        assert_eq!(merged["b"].as_i64(), Some(2));
    }

    #[test]
    fn test_load_yaml_merged_sync_rejects_non_mapping_later_document() {
        let file = create_test_yaml("key: value\n---\n- item\n");

        let err = load_yaml_merged_sync(file.path()).unwrap_err();

        match err {
            SettingsError::InvalidYamlStructure {
                source,
                index,
                found,
            } => {
                assert_eq!(source.path().map(PathBuf::as_path), Some(file.path()));
                assert_eq!(index, 1);
                assert_eq!(found, "sequence");
            }
            _ => panic!("Expected InvalidYamlStructure, got {:?}", err),
        }
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
