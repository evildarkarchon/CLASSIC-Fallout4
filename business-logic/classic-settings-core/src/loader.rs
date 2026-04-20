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
#[path = "loader_tests.rs"]
mod tests;
