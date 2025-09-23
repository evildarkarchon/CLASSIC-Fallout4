//! Utils module - High-performance utilities for CLASSIC
//!
//! This module provides foundational utilities optimized for crash log processing,
//! including path handling with caching, specialized string operations, error handling,
//! and performance monitoring integration.

use pyo3::prelude::*;

pub mod errors;
pub mod log_processing;
pub mod path;
pub mod performance;
pub mod strings;

pub use errors::{ClassicError, ClassicResult};
pub use log_processing::LogProcessor;
pub use path::PathHandler;
pub use performance::RustPerformanceMonitor;
pub use strings::StringProcessor;

/// Register the utils module with Python
pub fn register_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add all utility classes
    m.add_class::<StringProcessor>()?;
    m.add_class::<PathHandler>()?;
    m.add_class::<LogProcessor>()?;
    m.add_class::<RustPerformanceMonitor>()?;

    Ok(())
}
