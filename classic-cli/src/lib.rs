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
pub use config::{CliConfig, PathConfig};
pub use error::{CliError, print_error_detail};
pub use executor::ScanExecutor;
pub use output::{OutputFormatter, ScanStats};
