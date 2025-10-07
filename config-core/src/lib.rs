//! classic-config: Rust-accelerated configuration loading for CLASSIC
//!
//! This standalone module provides high-performance YAML configuration loading
//! with 15-30x speedup over Python's ruamel.yaml through:
//! - yaml-rust2 for parsing (pure Rust, YAML 1.2 compliant)
//! - Parallel file I/O with Tokio
//! - Efficient memory representation
//!
//! ## ONE RUNTIME RULE
//! This crate uses the shared global Tokio runtime from classic-shared.
//! All async operations use `classic_shared::get_runtime().block_on()`.

use pyo3::prelude::*;

mod yamldata;
pub use yamldata::{YamlData, create_yamldata};

// Re-export get_runtime from classic-shared for convenience
pub use classic_shared::get_runtime;

/// Initialize the classic_config Python module
#[pymodule]
fn classic_config(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<YamlData>()?;
    m.add_function(wrap_pyfunction!(create_yamldata, m)?)?;
    Ok(())
}
