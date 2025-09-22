//! Utils module - String and path utilities optimized for performance

use pyo3::prelude::*;

pub mod strings;

pub use strings::StringProcessor;

/// Register the utils module with Python
pub fn register_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<StringProcessor>()?;
    Ok(())
}
