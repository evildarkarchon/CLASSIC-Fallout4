//! CLASSIC CLI Library
//!
//! This library exposes the core functionality of the CLASSIC CLI
//! for use in integration tests and potentially other applications.

pub mod args;
pub mod config;
pub mod error;
pub mod executor;
pub mod output;

// Re-export commonly used types
pub use args::CliArgs;
pub use config::{load_or_create_config, CliConfig, PathConfig};
pub use error::{print_error_detail, CliError};
pub use executor::ScanExecutor;
pub use output::{OutputFormatter, ScanStats};
