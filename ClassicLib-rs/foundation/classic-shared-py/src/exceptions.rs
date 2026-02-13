//! Standard exception patterns for CLASSIC Python bindings
//!
//! This module provides macros and traits for creating consistent exception
//! hierarchies across all CLASSIC Python binding crates.
//!
//! # Architecture
//!
//! Each Python binding crate should define a 3-tier exception hierarchy:
//! - `Rust<Module>Error` - Base exception for all module errors
//! - `Rust<Module>IOError` - I/O related errors (file, network, etc.)
//! - `Rust<Module>ParseError` - Parsing/validation errors
//!
//! # Example
//!
//! ```rust,ignore
//! use classic_shared::define_exceptions;
//!
//! // Define the standard exception hierarchy
//! define_exceptions!(
//!     module: classic_yaml,
//!     base: RustYamlError,
//!     io: RustYamlIOError,
//!     parse: RustYamlParseError
//! );
//!
//! // Register exceptions in the Python module
//! #[pymodule]
//! fn classic_yaml(m: &Bound<'_, PyModule>) -> PyResult<()> {
//!     register_exceptions!(m, RustYamlError, RustYamlIOError, RustYamlParseError);
//!     Ok(())
//! }
//! ```

/// Macro to define the standard CLASSIC 3-tier exception hierarchy
///
/// This macro creates three exception types following the CLASSIC convention:
/// - A base exception that inherits from `PyException`
/// - An IO exception that inherits from the base
/// - A parse exception that inherits from the base
///
/// # Arguments
///
/// - `module`: The Python module identifier (e.g., `classic_yaml`)
/// - `base`: The base exception type name (e.g., `RustYamlError`)
/// - `io`: The IO exception type name (e.g., `RustYamlIOError`)
/// - `parse`: The parse exception type name (e.g., `RustYamlParseError`)
///
/// # Example
///
/// ```rust,ignore
/// define_exceptions!(
///     module: classic_yaml,
///     base: RustYamlError,
///     io: RustYamlIOError,
///     parse: RustYamlParseError
/// );
/// ```
#[macro_export]
macro_rules! define_exceptions {
    (
        module: $module:ident,
        base: $base:ident,
        io: $io:ident,
        parse: $parse:ident
    ) => {
        pyo3::create_exception!(
            $module,
            $base,
            pyo3::exceptions::PyException,
            concat!("Base exception for ", stringify!($module), " Rust errors")
        );

        pyo3::create_exception!(
            $module,
            $io,
            $base,
            concat!(stringify!($module), " I/O errors")
        );

        pyo3::create_exception!(
            $module,
            $parse,
            $base,
            concat!(stringify!($module), " parse/validation errors")
        );
    };
}

/// Macro to register exception types in a Python module
///
/// This is a convenience macro to add all three standard exception types
/// to a PyO3 module in a single call.
///
/// # Example
///
/// ```rust,ignore
/// #[pymodule]
/// fn classic_yaml(m: &Bound<'_, PyModule>) -> PyResult<()> {
///     register_exceptions!(m, RustYamlError, RustYamlIOError, RustYamlParseError);
///     Ok(())
/// }
/// ```
#[macro_export]
macro_rules! register_exceptions {
    ($m:expr, $base:ident, $io:ident, $parse:ident) => {{
        $m.add(stringify!($base), $m.py().get_type::<$base>())?;
        $m.add(stringify!($io), $m.py().get_type::<$io>())?;
        $m.add(stringify!($parse), $m.py().get_type::<$parse>())?;
    }};
}

#[cfg(test)]
mod tests {
    // Tests would require a full PyO3 test environment
    // The macros are tested implicitly by the consuming crates
}
