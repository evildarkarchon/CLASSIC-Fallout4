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
        let result = handle
            .await
            .map_err(|e| SettingsError::YamlParseError {
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
}
