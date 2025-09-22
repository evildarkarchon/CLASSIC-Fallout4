//! Scan log module - High-performance log parsing and pattern matching

use pyo3::prelude::*;

pub mod formid;
pub mod parser;
pub mod patterns;

pub use formid::FormIDAnalyzer;
pub use parser::LogParser;
pub use patterns::PatternMatcher;

/// Register the scanlog module with Python
pub fn register_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<FormIDAnalyzer>()?;
    m.add_class::<LogParser>()?;
    m.add_class::<PatternMatcher>()?;
    Ok(())
}
