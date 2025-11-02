//! CLASSIC CLI Library
//!
//! This library exposes the core functionality of the CLASSIC CLI
//! for use in integration tests and potentially other applications.

/// Command-line argument parsing and validation
pub mod args;
/// Configuration loading and management
pub mod config;
/// Error types and error handling utilities
pub mod error;
/// Crash log scanning execution logic
pub mod executor;
/// Output formatting and statistics
pub mod output;

// Re-export commonly used types
pub use args::CliArgs;
pub use config::{load_or_create_config, CliConfig, PathConfig};
pub use error::{print_error_detail, CliError};
pub use executor::ScanExecutor;
pub use output::{OutputFormatter, ScanStats};
