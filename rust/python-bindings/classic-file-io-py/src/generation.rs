//! Python bindings for file generation

use classic_file_io_core::FileIOError;
use classic_file_io_core::generation::{FileGenerator, FileGeneratorConfig};
use pyo3::exceptions::{PyIOError, PyPermissionError, PyRuntimeError};
use pyo3::prelude::*;
use std::path::PathBuf;

/// Python wrapper for FileGeneratorConfig
#[pyclass(name = "FileGeneratorConfig")]
pub struct PyFileGeneratorConfig {
    inner: FileGeneratorConfig,
}

#[pymethods]
impl PyFileGeneratorConfig {
    /// Create a new file generator configuration
    ///
    /// Args:
    ///     ignore_file_content: Default content for CLASSIC Ignore.yaml
    ///     local_yaml_content: Default content for local YAML file
    ///     game_name: Game name for local YAML path (e.g., "Fallout4", "Skyrim")
    #[new]
    fn new(ignore_file_content: String, local_yaml_content: String, game_name: String) -> Self {
        Self {
            inner: FileGeneratorConfig::new(ignore_file_content, local_yaml_content, game_name),
        }
    }

    /// Get ignore file content
    #[getter]
    fn ignore_file_content(&self) -> String {
        self.inner.ignore_file_content.clone()
    }

    /// Get local YAML content
    #[getter]
    fn local_yaml_content(&self) -> String {
        self.inner.local_yaml_content.clone()
    }

    /// Get game name
    #[getter]
    fn game_name(&self) -> String {
        self.inner.game_name.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "FileGeneratorConfig(game_name='{}', ignore_content_len={}, local_content_len={})",
            self.inner.game_name,
            self.inner.ignore_file_content.len(),
            self.inner.local_yaml_content.len()
        )
    }
}

/// Python wrapper for FileGenerator
#[pyclass(name = "FileGenerator")]
pub struct PyFileGenerator {
    inner: FileGenerator,
}

#[pymethods]
impl PyFileGenerator {
    /// Create a new file generator
    ///
    /// Args:
    ///     config: File generation configuration
    #[new]
    fn new(config: &PyFileGeneratorConfig) -> Self {
        Self {
            inner: FileGenerator::new(config.inner.clone()),
        }
    }

    /// Generate CLASSIC Ignore.yaml if it doesn't exist (async)
    ///
    /// Creates the ignore file with default content from configuration.
    /// The file is written in UTF-8 encoding.
    ///
    /// Returns:
    ///     bool: True if the file was generated, False if it already existed
    ///
    /// Raises:
    ///     IOError: If file I/O fails
    ///     PermissionError: If lacking permissions to write file
    fn generate_ignore_file_async<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let generator = self.inner.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            generator
                .generate_ignore_file_async()
                .await
                .map_err(convert_file_io_error)
        })
    }

    /// Generate CLASSIC Data/CLASSIC <GAME> Local.yaml if it doesn't exist (async)
    ///
    /// Creates the local YAML file with default content from configuration,
    /// where <GAME> is dynamically determined from config.
    /// The file is written in UTF-8 encoding.
    /// Creates parent directories if they don't exist.
    ///
    /// Returns:
    ///     bool: True if the file was generated, False if it already existed
    ///
    /// Raises:
    ///     IOError: If file I/O or directory creation fails
    ///     PermissionError: If lacking permissions to create directory/file
    fn generate_local_yaml_async<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let generator = self.inner.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            generator
                .generate_local_yaml_async()
                .await
                .map_err(convert_file_io_error)
        })
    }

    /// Generate all files asynchronously with concurrent execution
    ///
    /// Generates both the ignore file and local YAML file concurrently.
    /// Uses Tokio's try_join for fail-fast error handling.
    ///
    /// Returns:
    ///     tuple[bool, bool]: (ignore_generated, local_yaml_generated) indicating
    ///     which files were created
    ///
    /// Raises:
    ///     IOError: If any file generation fails
    ///     PermissionError: If lacking permissions
    fn generate_all_files_async<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let generator = self.inner.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            generator
                .generate_all_files_async()
                .await
                .map_err(convert_file_io_error)
        })
    }

    /// Get the ignore file path
    ///
    /// Returns:
    ///     Path: Path to CLASSIC Ignore.yaml
    fn ignore_file_path(&self) -> PathBuf {
        self.inner.ignore_file_path()
    }

    /// Get the local YAML file path
    ///
    /// Returns:
    ///     Path: Path to CLASSIC Data/CLASSIC <GAME> Local.yaml
    fn local_yaml_path(&self) -> PathBuf {
        self.inner.local_yaml_path()
    }

    /// Get the configuration
    fn config(&self) -> PyFileGeneratorConfig {
        PyFileGeneratorConfig {
            inner: self.inner.config().clone(),
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "FileGenerator(game_name='{}')",
            self.inner.config().game_name
        )
    }
}

/// Generate CLASSIC Ignore.yaml if it doesn't exist (async)
///
/// Standalone function that creates the ignore file with provided content.
///
/// Args:
///     content: Default content for CLASSIC Ignore.yaml
///
/// Returns:
///     bool: True if the file was generated, False if it already existed
///
/// Raises:
///     IOError: If file I/O fails
///     PermissionError: If lacking permissions to write file
///
/// Example:
///     >>> import asyncio
///     >>> from classic_file_io import generate_ignore_file_async
///     >>> result = asyncio.run(generate_ignore_file_async("# Ignore patterns\n*.tmp"))
///     >>> print(f"File generated: {result}")
#[pyfunction]
pub fn generate_ignore_file_async<'py>(
    py: Python<'py>,
    content: String,
) -> PyResult<Bound<'py, PyAny>> {
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        classic_file_io_core::generation::generate_ignore_file(content)
            .await
            .map_err(convert_file_io_error)
    })
}

/// Generate CLASSIC Data/CLASSIC <GAME> Local.yaml if it doesn't exist (async)
///
/// Standalone function that creates the local YAML file with provided content.
///
/// Args:
///     content: Default content for local YAML file
///     game_name: Game name for local YAML path (e.g., "Fallout4", "Skyrim")
///
/// Returns:
///     bool: True if the file was generated, False if it already existed
///
/// Raises:
///     IOError: If file I/O or directory creation fails
///     PermissionError: If lacking permissions
///
/// Example:
///     >>> import asyncio
///     >>> from classic_file_io import generate_local_yaml_async
///     >>> result = asyncio.run(generate_local_yaml_async("# Config", "Fallout4"))
///     >>> print(f"File generated: {result}")
#[pyfunction]
pub fn generate_local_yaml_async<'py>(
    py: Python<'py>,
    content: String,
    game_name: String,
) -> PyResult<Bound<'py, PyAny>> {
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        classic_file_io_core::generation::generate_local_yaml(content, game_name)
            .await
            .map_err(convert_file_io_error)
    })
}

/// Convert FileIOError to PyErr
fn convert_file_io_error(err: FileIOError) -> PyErr {
    match err {
        FileIOError::WriteError { path, source }
        | FileIOError::CreateDirectoryError { path, source } => {
            if source.kind() == std::io::ErrorKind::PermissionDenied {
                PyPermissionError::new_err(format!("{}: {}", path.display(), source))
            } else {
                PyIOError::new_err(format!("{}: {}", path.display(), source))
            }
        }
        FileIOError::IoError(io_err) => {
            if io_err.kind() == std::io::ErrorKind::PermissionDenied {
                PyPermissionError::new_err(io_err.to_string())
            } else {
                PyIOError::new_err(io_err.to_string())
            }
        }
        _ => PyRuntimeError::new_err(err.to_string()),
    }
}

/// Register generation types with the Python module
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyFileGeneratorConfig>()?;
    m.add_class::<PyFileGenerator>()?;
    m.add_function(wrap_pyfunction!(generate_ignore_file_async, m)?)?;
    m.add_function(wrap_pyfunction!(generate_local_yaml_async, m)?)?;
    Ok(())
}
