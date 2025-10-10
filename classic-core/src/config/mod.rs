//! Configuration management module
//!
//! This module provides Rust-accelerated configuration loading
//! for CLASSIC, achieving 15-30x speedup over Python's ruamel.yaml.

mod yamldata_builder_new;
pub use yamldata_builder_new::{create_yamldata, YamlData};

use pyo3::prelude::*;

/// Initialize the config module
pub fn init_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<YamlData>()?;
    m.add_function(wrap_pyfunction!(create_yamldata, m)?)?;
    Ok(())
}
