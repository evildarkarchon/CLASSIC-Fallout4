//! classic-config-core: Pure Rust configuration loading business logic
//!
//! This crate provides high-performance YAML configuration loading with:
//! - yaml-rust2 for parsing (pure Rust, YAML 1.2 compliant)
//! - Parallel file I/O with Tokio
//! - Efficient memory representation
//! - NO PyO3 dependency - pure Rust business logic only
//!
//! ## ONE RUNTIME RULE
//! This crate uses the shared global Tokio runtime from classic-shared-core.
//! All async operations use `classic_shared_core::get_runtime().block_on()`.

pub mod config;
pub mod yamldata;

pub use config::{ClassicConfig, PathConfig, YamlSource};
pub use yamldata::{ConfigError, YamlDataCore};

// Re-export get_runtime from classic-shared-core for convenience
pub use classic_shared_core::get_runtime;
