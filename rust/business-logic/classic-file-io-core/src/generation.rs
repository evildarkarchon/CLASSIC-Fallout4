//! File generation module for CLASSIC configuration files
//!
//! This module provides functionality for generating essential configuration files
//! required by the CLASSIC application, including:
//! - CLASSIC Ignore.yaml (ignore patterns)
//! - CLASSIC Data/CLASSIC <GAME> Local.yaml (game-specific local config)

use crate::error::FileIOError;
use std::path::PathBuf;
use tokio::fs;

/// Configuration for file generation
#[derive(Debug, Clone)]
pub struct FileGeneratorConfig {
    /// Content for the ignore file
    pub ignore_file_content: String,

    /// Content for the local YAML file
    pub local_yaml_content: String,

    /// Game name (e.g., "Fallout4", "Skyrim")
    pub game_name: String,
}

impl FileGeneratorConfig {
    /// Create a new file generator configuration
    ///
    /// # Arguments
    ///
    /// * `ignore_file_content` - Default content for CLASSIC Ignore.yaml
    /// * `local_yaml_content` - Default content for local YAML file
    /// * `game_name` - Game name for local YAML path
    pub fn new(ignore_file_content: String, local_yaml_content: String, game_name: String) -> Self {
        Self {
            ignore_file_content,
            local_yaml_content,
            game_name,
        }
    }
}

/// File generator for CLASSIC configuration files
#[derive(Clone)]
pub struct FileGenerator {
    /// Configuration for file generation
    config: FileGeneratorConfig,
}

impl FileGenerator {
    /// Create a new file generator
    ///
    /// # Arguments
    ///
    /// * `config` - File generation configuration
    pub fn new(config: FileGeneratorConfig) -> Self {
        Self { config }
    }

    /// Generate CLASSIC Ignore.yaml if it doesn't exist (async)
    ///
    /// Creates the ignore file with default content from configuration.
    /// The file is written in UTF-8 encoding.
    ///
    /// # Returns
    ///
    /// `true` if the file was generated, `false` if it already existed
    ///
    /// # Errors
    ///
    /// Returns error if file I/O fails
    pub async fn generate_ignore_file_async(&self) -> Result<bool, FileIOError> {
        let ignore_path = PathBuf::from("CLASSIC Ignore.yaml");

        // Check if file already exists
        if fs::try_exists(&ignore_path).await.unwrap_or(false) {
            return Ok(false);
        }

        // Write ignore file content
        fs::write(&ignore_path, &self.config.ignore_file_content)
            .await
            .map_err(|e| FileIOError::WriteError {
                path: ignore_path.clone(),
                source: e,
            })?;

        log::debug!("Generated CLASSIC Ignore.yaml at {}", ignore_path.display());
        Ok(true)
    }

    /// Generate CLASSIC Data/CLASSIC <GAME> Local.yaml if it doesn't exist (async)
    ///
    /// Creates the local YAML file with default content from configuration,
    /// where <GAME> is dynamically determined from config.
    /// The file is written in UTF-8 encoding.
    /// Creates parent directories if they don't exist.
    ///
    /// # Returns
    ///
    /// `true` if the file was generated, `false` if it already existed
    ///
    /// # Errors
    ///
    /// Returns error if file I/O or directory creation fails
    pub async fn generate_local_yaml_async(&self) -> Result<bool, FileIOError> {
        let local_path = PathBuf::from(format!(
            "CLASSIC Data/CLASSIC {} Local.yaml",
            self.config.game_name
        ));

        // Check if file already exists
        if fs::try_exists(&local_path).await.unwrap_or(false) {
            return Ok(false);
        }

        // Create parent directory if it doesn't exist
        if let Some(parent) = local_path.parent() {
            fs::create_dir_all(parent)
                .await
                .map_err(|e| FileIOError::CreateDirectoryError {
                    path: parent.to_path_buf(),
                    source: e,
                })?;
        }

        // Write local YAML content
        fs::write(&local_path, &self.config.local_yaml_content)
            .await
            .map_err(|e| FileIOError::WriteError {
                path: local_path.clone(),
                source: e,
            })?;

        log::debug!("Generated local YAML at {}", local_path.display());
        Ok(true)
    }

    /// Generate all files asynchronously with concurrent execution
    ///
    /// Generates both the ignore file and local YAML file concurrently.
    /// Uses Tokio's `try_join!` for fail-fast error handling.
    ///
    /// # Returns
    ///
    /// Tuple of (ignore_generated, local_yaml_generated) indicating which files were created
    ///
    /// # Errors
    ///
    /// Returns error if any file generation fails
    pub async fn generate_all_files_async(&self) -> Result<(bool, bool), FileIOError> {
        let start = std::time::Instant::now();

        // Generate files concurrently with fail-fast behavior
        let (ignore_result, local_result) = tokio::try_join!(
            self.generate_ignore_file_async(),
            self.generate_local_yaml_async()
        )?;

        let elapsed = start.elapsed();
        log::info!(
            "File generation completed successfully in {:.3}s",
            elapsed.as_secs_f64()
        );

        Ok((ignore_result, local_result))
    }

    /// Get the ignore file path
    pub fn ignore_file_path(&self) -> PathBuf {
        PathBuf::from("CLASSIC Ignore.yaml")
    }

    /// Get the local YAML file path
    pub fn local_yaml_path(&self) -> PathBuf {
        PathBuf::from(format!(
            "CLASSIC Data/CLASSIC {} Local.yaml",
            self.config.game_name
        ))
    }

    /// Get the configuration
    pub fn config(&self) -> &FileGeneratorConfig {
        &self.config
    }
}

/// Standalone function to generate ignore file
///
/// Convenience function that creates a generator and generates the ignore file.
///
/// # Arguments
///
/// * `content` - Default content for CLASSIC Ignore.yaml
///
/// # Returns
///
/// `true` if the file was generated, `false` if it already existed
///
/// # Errors
///
/// Returns error if file I/O fails
pub async fn generate_ignore_file(content: impl Into<String>) -> Result<bool, FileIOError> {
    let ignore_path = PathBuf::from("CLASSIC Ignore.yaml");

    // Check if file already exists
    if fs::try_exists(&ignore_path).await.unwrap_or(false) {
        return Ok(false);
    }

    // Write ignore file content
    let content_str = content.into();
    fs::write(&ignore_path, content_str)
        .await
        .map_err(|e| FileIOError::WriteError {
            path: ignore_path.clone(),
            source: e,
        })?;

    log::debug!("Generated CLASSIC Ignore.yaml at {}", ignore_path.display());
    Ok(true)
}

/// Standalone function to generate local YAML file
///
/// Convenience function that creates a generator and generates the local YAML file.
///
/// # Arguments
///
/// * `content` - Default content for local YAML file
/// * `game_name` - Game name for local YAML path
///
/// # Returns
///
/// `true` if the file was generated, `false` if it already existed
///
/// # Errors
///
/// Returns error if file I/O or directory creation fails
pub async fn generate_local_yaml(
    content: impl Into<String>,
    game_name: impl Into<String>,
) -> Result<bool, FileIOError> {
    let game_name_str = game_name.into();
    let local_path = PathBuf::from(format!("CLASSIC Data/CLASSIC {} Local.yaml", game_name_str));

    // Check if file already exists
    if fs::try_exists(&local_path).await.unwrap_or(false) {
        return Ok(false);
    }

    // Create parent directory if it doesn't exist
    if let Some(parent) = local_path.parent() {
        fs::create_dir_all(parent)
            .await
            .map_err(|e| FileIOError::CreateDirectoryError {
                path: parent.to_path_buf(),
                source: e,
            })?;
    }

    // Write local YAML content
    let content_str = content.into();
    fs::write(&local_path, content_str)
        .await
        .map_err(|e| FileIOError::WriteError {
            path: local_path.clone(),
            source: e,
        })?;

    log::debug!("Generated local YAML at {}", local_path.display());
    Ok(true)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;
    use tempfile::TempDir;

    #[tokio::test]
    #[serial]
    async fn test_generate_ignore_file() {
        let temp_dir = TempDir::new().unwrap();
        let original_dir = std::env::current_dir().unwrap();

        // Change to temp directory for test
        std::env::set_current_dir(&temp_dir).unwrap();

        let config = FileGeneratorConfig::new(
            "# Test ignore file\n*.tmp".to_string(),
            "# Test local yaml".to_string(),
            "TestGame".to_string(),
        );

        let generator = FileGenerator::new(config);

        // First generation should succeed
        let result = generator.generate_ignore_file_async().await.unwrap();
        assert!(result, "File should be generated on first call");

        // Verify file exists and has correct content
        let ignore_path = PathBuf::from("CLASSIC Ignore.yaml");
        assert!(ignore_path.exists());
        let content = fs::read_to_string(&ignore_path).await.unwrap();
        assert_eq!(content, "# Test ignore file\n*.tmp");

        // Second generation should return false (file already exists)
        let result = generator.generate_ignore_file_async().await.unwrap();
        assert!(!result, "File should not be regenerated");

        // Restore original directory
        std::env::set_current_dir(original_dir).unwrap();
    }

    #[tokio::test]
    #[serial]
    async fn test_generate_local_yaml() {
        let temp_dir = TempDir::new().unwrap();
        let original_dir = std::env::current_dir().unwrap();

        // Change to temp directory for test
        std::env::set_current_dir(&temp_dir).unwrap();

        let config = FileGeneratorConfig::new(
            "# Test ignore".to_string(),
            "# Test local yaml\ngame: TestGame".to_string(),
            "TestGame".to_string(),
        );

        let generator = FileGenerator::new(config);

        // First generation should succeed
        let result = generator.generate_local_yaml_async().await.unwrap();
        assert!(result, "File should be generated on first call");

        // Verify file exists and has correct content
        let local_path = PathBuf::from("CLASSIC Data/CLASSIC TestGame Local.yaml");
        assert!(local_path.exists());
        let content = fs::read_to_string(&local_path).await.unwrap();
        assert_eq!(content, "# Test local yaml\ngame: TestGame");

        // Verify parent directory was created
        assert!(local_path.parent().unwrap().exists());

        // Second generation should return false (file already exists)
        let result = generator.generate_local_yaml_async().await.unwrap();
        assert!(!result, "File should not be regenerated");

        // Restore original directory
        std::env::set_current_dir(original_dir).unwrap();
    }

    #[tokio::test]
    #[serial]
    async fn test_generate_all_files() {
        let temp_dir = TempDir::new().unwrap();
        let original_dir = std::env::current_dir().unwrap();

        // Change to temp directory for test
        std::env::set_current_dir(&temp_dir).unwrap();

        let config = FileGeneratorConfig::new(
            "# Test ignore file".to_string(),
            "# Test local yaml".to_string(),
            "TestGame".to_string(),
        );

        let generator = FileGenerator::new(config);

        // Generate all files
        let (ignore_generated, local_generated) =
            generator.generate_all_files_async().await.unwrap();

        assert!(ignore_generated, "Ignore file should be generated");
        assert!(local_generated, "Local YAML should be generated");

        // Verify both files exist
        assert!(PathBuf::from("CLASSIC Ignore.yaml").exists());
        assert!(PathBuf::from("CLASSIC Data/CLASSIC TestGame Local.yaml").exists());

        // Second generation should return false for both
        let (ignore_generated, local_generated) =
            generator.generate_all_files_async().await.unwrap();

        assert!(!ignore_generated, "Ignore file should not be regenerated");
        assert!(!local_generated, "Local YAML should not be regenerated");

        // Restore original directory
        std::env::set_current_dir(original_dir).unwrap();
    }

    #[tokio::test]
    #[serial]
    async fn test_standalone_functions() {
        let temp_dir = TempDir::new().unwrap();
        let original_dir = std::env::current_dir().unwrap();

        // Change to temp directory for test
        std::env::set_current_dir(&temp_dir).unwrap();

        // Test standalone generate_ignore_file
        let result = generate_ignore_file("# Standalone test").await.unwrap();
        assert!(result);
        assert!(PathBuf::from("CLASSIC Ignore.yaml").exists());

        // Test standalone generate_local_yaml
        let result = generate_local_yaml("# Local test", "StandaloneGame")
            .await
            .unwrap();
        assert!(result);
        assert!(PathBuf::from("CLASSIC Data/CLASSIC StandaloneGame Local.yaml").exists());

        // Restore original directory
        std::env::set_current_dir(original_dir).unwrap();
    }

    #[tokio::test]
    async fn test_file_paths() {
        let config = FileGeneratorConfig::new(
            "content".to_string(),
            "content".to_string(),
            "TestGame".to_string(),
        );

        let generator = FileGenerator::new(config);

        assert_eq!(
            generator.ignore_file_path(),
            PathBuf::from("CLASSIC Ignore.yaml")
        );
        assert_eq!(
            generator.local_yaml_path(),
            PathBuf::from("CLASSIC Data/CLASSIC TestGame Local.yaml")
        );
    }
}
