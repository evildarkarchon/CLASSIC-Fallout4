//! Error types for the version registry.
//!
//! This module defines the error types that can occur during version registry
//! operations, including version parsing, YAML loading, and registry access.

use thiserror::Error;

/// Errors that can occur during version registry operations.
#[derive(Debug, Error)]
pub enum VersionRegistryError {
    /// Failed to parse a version string.
    ///
    /// The string could not be parsed as a valid 4-component version.
    /// Expected format: "major.minor.patch.build" (e.g., "1.10.163.0").
    #[error("Invalid version string: {0}")]
    InvalidVersion(String),

    /// Version was not found in the registry.
    #[error("Version not found: {0}")]
    NotFound(String),

    /// Error loading or parsing YAML configuration.
    #[error("YAML loading error: {0}")]
    YamlError(#[from] classic_yaml_core::YamlError),

    /// Registry has not been initialized.
    ///
    /// This should not occur in normal usage as the registry is
    /// automatically initialized on first access.
    #[error("Registry not initialized")]
    NotInitialized,

    /// Invalid configuration data in YAML.
    #[error("Invalid configuration: {0}")]
    InvalidConfig(String),
}
