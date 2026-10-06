//! Path handling utilities for Python-Rust interop.
//!
//! Provides PathLike type that accepts both string paths and pathlib.Path objects,
//! eliminating the need for manual str() conversions in Python code.
//!
//! # Overview
//!
//! The `PathLike` type implements Python's path protocol by checking for the `__fspath__()`
//! method, allowing seamless use of pathlib.Path objects without manual conversions.
//!
//! # Examples
//!
//! ```python
//! # Both work without conversion
//! ops.load_file("config.yaml")          # str
//! ops.load_file(Path("config.yaml"))    # pathlib.Path
//! ```
//!
//! # Python Path Protocol
//!
//! This module implements Python's path protocol (PEP 519) which requires checking for
//! the `__fspath__()` method on objects. This allows any path-like object to work
//! seamlessly with Rust code.

use pyo3::Borrowed;
use pyo3::exceptions::PyTypeError;
use pyo3::prelude::*;
use std::path::PathBuf;

/// A path-like type that accepts both str and pathlib.Path objects.
///
/// This type implements Python's path protocol (PEP 519) by checking for the `__fspath__()`
/// method, allowing seamless use of pathlib.Path objects without manual conversions.
///
/// # Supported Types
///
/// - `str` - Direct string paths
/// - `pathlib.Path` - Python pathlib objects
/// - `os.PathLike` - Any object implementing `__fspath__()`
/// - `bytes` - On Unix systems only (for `os.fsencode()` paths)
///
/// # Examples
///
/// ```python
/// from pathlib import Path
/// import classic_yaml
///
/// ops = classic_yaml.YamlOperations()
///
/// # All of these work without manual conversion:
/// ops.load_yaml_file("config.yaml")           # str
/// ops.load_yaml_file(Path("config.yaml"))     # pathlib.Path
/// ops.load_yaml_file(Path.cwd() / "config")   # Path with operators
/// ```
///
/// # Implementation Details
///
/// The extraction order is:
/// 1. Try `__fspath__()` method (pathlib.Path, os.PathLike)
/// 2. Fall back to direct string extraction
/// 3. On Unix: Fall back to bytes (for os.fsencode paths)
/// 4. Raise TypeError if none work
#[derive(Debug, Clone)]
pub struct PathLike(pub PathBuf);

impl<'py> FromPyObject<'_, 'py> for PathLike {
    type Error = PyErr;

    fn extract(ob: Borrowed<'_, 'py, PyAny>) -> Result<Self, Self::Error> {
        // Try __fspath__() protocol first (pathlib.Path, os.PathLike)
        if let Ok(path_method) = ob.call_method0("__fspath__") {
            let path_str: String = path_method.extract()?;
            return Ok(PathLike(PathBuf::from(path_str)));
        }

        // Fall back to direct string extraction
        if let Ok(s) = ob.extract::<String>() {
            return Ok(PathLike(PathBuf::from(s)));
        }

        // Fall back to bytes on Unix (for os.fsencode paths)
        #[cfg(unix)]
        if let Ok(b) = ob.extract::<&[u8]>() {
            use std::os::unix::ffi::OsStrExt;
            return Ok(PathLike(PathBuf::from(std::ffi::OsStr::from_bytes(b))));
        }

        Err(PyTypeError::new_err(
            "Expected str, bytes, or path-like object (implementing __fspath__)",
        ))
    }
}

impl From<PathLike> for PathBuf {
    fn from(p: PathLike) -> Self {
        p.0
    }
}

impl AsRef<std::path::Path> for PathLike {
    fn as_ref(&self) -> &std::path::Path {
        &self.0
    }
}

#[cfg(test)]
#[path = "path_tests.rs"]
mod tests;
