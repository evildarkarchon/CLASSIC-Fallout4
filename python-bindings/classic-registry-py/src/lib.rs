//! Python bindings for the typed registry.
//!
//! This crate provides Python bindings for `classic-registry-core`, allowing
//! Python code to interact with this facade's process-wide registry for
//! singleton management.
//!
//! # Registry scope
//!
//! Every registry effect of this facade goes through
//! [`REGISTRY_FACADE_SCOPE`], never through the unscoped default-scope
//! functions. As a separate extension image that changes nothing observable,
//! but once the Python facades share one native library it keeps
//! `classic_registry`'s values, application directory, and `clear_all()`
//! separate from the registries owned by `classic_config` and
//! `classic_scanlog`.

use classic_registry_core::RegistryScope;
use pyo3::prelude::*;
use std::sync::{Arc, LazyLock};

/// `classic_registry`'s typed registry scope.
///
/// Created on first use and never replaced, so every module function sees the
/// same store for the life of the process. Lookup, default, and exact-type
/// rules come from the core scope type.
static REGISTRY_FACADE_SCOPE: LazyLock<RegistryScope> = LazyLock::new(RegistryScope::new_isolated);

/// Wrapper for Python objects that implements Clone.
///
/// This allows Python objects to be stored in the registry which requires Clone.
#[derive(Clone)]
struct PyObjectWrapper(Arc<Py<PyAny>>);

impl PyObjectWrapper {
    fn new(obj: Py<PyAny>) -> Self {
        Self(Arc::new(obj))
    }

    fn get(&self, py: Python) -> Py<PyAny> {
        self.0.clone_ref(py)
    }
}

/// Python wrapper for registry Keys.
///
/// Provides predefined registry keys as class attributes, matching the Python API.
#[pyclass]
pub struct Keys;

#[pymethods]
impl Keys {
    #[classattr]
    const YAML_CACHE: &'static str = classic_registry_core::Keys::YAML_CACHE;

    #[classattr]
    const MANUAL_DOCS_GUI: &'static str = classic_registry_core::Keys::MANUAL_DOCS_GUI;

    #[classattr]
    const GAME_PATH_GUI: &'static str = classic_registry_core::Keys::GAME_PATH_GUI;

    #[classattr]
    const GAME_PATH: &'static str = classic_registry_core::Keys::GAME_PATH;

    #[classattr]
    const DOCS_PATH: &'static str = classic_registry_core::Keys::DOCS_PATH;

    #[classattr]
    const IS_GUI_MODE: &'static str = classic_registry_core::Keys::IS_GUI_MODE;

    #[classattr]
    const OPEN_FILE_FUNC: &'static str = classic_registry_core::Keys::OPEN_FILE_FUNC;

    #[classattr]
    const GAME: &'static str = classic_registry_core::Keys::GAME;

    /// Current game version for Fallout 4 (Original, NextGen, or Vr).
    ///
    /// This is the new key for storing the detected or selected Fallout 4 version.
    /// It replaces the legacy VR mode toggle.
    #[classattr]
    const GAME_VERSION: &'static str = classic_registry_core::Keys::GAME_VERSION;

    /// Whether the game version was auto-detected.
    ///
    /// True if auto-detected from game files, False if manually selected.
    #[classattr]
    const VERSION_AUTO_DETECTED: &'static str = classic_registry_core::Keys::VERSION_AUTO_DETECTED;

    #[classattr]
    const LOCAL_DIR: &'static str = classic_registry_core::Keys::LOCAL_DIR;

    #[classattr]
    const IS_PRERELEASE: &'static str = classic_registry_core::Keys::IS_PRERELEASE;

    /// XSE validation status flag.
    #[classattr]
    const XSE_VALID: &'static str = classic_registry_core::Keys::XSE_VALID;

    /// Detected XSE version string.
    #[classattr]
    const XSE_VERSION: &'static str = classic_registry_core::Keys::XSE_VERSION;

    /// ENB binaries presence flag.
    #[classattr]
    const ENB_PRESENT: &'static str = classic_registry_core::Keys::ENB_PRESENT;

    /// Detected game executable version.
    #[classattr]
    const GAME_VERSION_DETECTED: &'static str = classic_registry_core::Keys::GAME_VERSION_DETECTED;
}

/// Register a value in this facade's registry.
///
/// # Arguments
///
/// * `key` - The registry key
/// * `value` - The value to store (any Python object)
///
/// # Python Example
///
/// ```python
/// from classic_core import registry
///
/// registry.register(registry.Keys.GAME, "Fallout4")
/// registry.register("custom_key", {"data": 123})
/// ```
#[pyfunction]
fn register(key: String, value: Py<PyAny>) -> PyResult<()> {
    // Wrap the Python object and store in the registry
    REGISTRY_FACADE_SCOPE.register(key, PyObjectWrapper::new(value));
    Ok(())
}

/// Check if a key is registered.
///
/// # Arguments
///
/// * `key` - The registry key to check
///
/// # Returns
///
/// `True` if the key exists, `False` otherwise
///
/// # Python Example
///
/// ```python
/// from classic_core import registry
///
/// if registry.is_registered(registry.Keys.GAME):
///     print("Game is registered")
/// ```
#[pyfunction]
fn is_registered(key: String) -> bool {
    REGISTRY_FACADE_SCOPE.is_registered(&key)
}

/// Retrieve a value from this facade's registry.
///
/// # Arguments
///
/// * `key` - The registry key
///
/// # Returns
///
/// The stored value, or `None` if not found
///
/// # Python Example
///
/// ```python
/// from classic_core import registry
///
/// game = registry.get(registry.Keys.GAME)
/// if game is not None:
///     print(f"Current game: {game}")
/// ```
#[pyfunction]
fn get(py: Python, key: String) -> PyResult<Option<Py<PyAny>>> {
    Ok(REGISTRY_FACADE_SCOPE
        .get::<_, PyObjectWrapper>(key)
        .map(|w| w.get(py)))
}

/// Clear all entries from the registry.
///
/// Clears only `classic_registry`'s own registry, including its application
/// directory; `classic_config` and `classic_scanlog` keep theirs.
///
/// **Warning**: This is primarily for testing. Use with caution in production.
///
/// # Python Example
///
/// ```python
/// from classic_core import registry
///
/// # In test teardown
/// registry.clear_all()
/// ```
#[pyfunction]
fn clear_all() {
    REGISTRY_FACADE_SCOPE.clear_all();
}

/// Remove a key from this facade's registry.
///
/// # Arguments
///
/// * `key` - The registry key to remove
///
/// # Returns
///
/// `True` if the key was found and removed, `False` if it was not present
#[pyfunction]
fn unregister(key: String) -> bool {
    REGISTRY_FACADE_SCOPE.unregister(key)
}

// ============================================================================
// Convenience Functions
// ============================================================================

/// Get the current game name.
///
/// # Returns
///
/// The game name, defaulting to "Fallout4" if not set
///
/// # Python Example
///
/// ```python
/// from classic_core import registry
///
/// game = registry.get_game()
/// print(f"Current game: {game}")
/// ```
#[pyfunction]
fn get_game(py: Python) -> String {
    // Try PyObjectWrapper first (Python-stored value), then native
    if let Some(wrapper) =
        REGISTRY_FACADE_SCOPE.get::<_, PyObjectWrapper>(classic_registry_core::Keys::GAME)
        && let Ok(value) = wrapper.get(py).extract::<String>(py)
        && !value.is_empty()
    {
        return value;
    }
    REGISTRY_FACADE_SCOPE.get_game()
}

/// Set the current game name.
///
/// # Arguments
///
/// * `game_name` - The game name (e.g., "Fallout4", "Skyrim")
///
/// # Python Example
///
/// ```python
/// from classic_core import registry
///
/// registry.set_game("Skyrim")
/// ```
#[pyfunction]
fn set_game(py: Python, game_name: String) -> PyResult<()> {
    // Store as PyObjectWrapper so get() and get_game() can both retrieve it
    let py_str = PyObjectWrapper::new(game_name.into_pyobject(py)?.into_any().unbind());
    REGISTRY_FACADE_SCOPE.register(classic_registry_core::Keys::GAME.to_string(), py_str);
    Ok(())
}

/// Check if the application is running in GUI mode.
///
/// # Returns
///
/// `True` if GUI mode, `False` for CLI mode
///
/// # Python Example
///
/// ```python
/// from classic_core import registry
///
/// if registry.is_gui_mode():
///     print("Running in GUI mode")
/// ```
#[pyfunction]
fn is_gui_mode(py: Python) -> bool {
    // Try to get as PyObjectWrapper first (for Python bool), then fallback to native bool
    if let Some(wrapper) = REGISTRY_FACADE_SCOPE.get::<_, PyObjectWrapper>(Keys::IS_GUI_MODE) {
        let obj = wrapper.get(py);
        if let Ok(value) = obj.extract::<bool>(py) {
            return value;
        }
    }
    // Fallback to native bool (for compatibility)
    REGISTRY_FACADE_SCOPE.is_gui_mode()
}

/// Get the YAML settings cache instance.
///
/// # Returns
///
/// The cached YAML settings object, or `None` if not registered
///
/// # Python Example
///
/// ```python
/// from classic_core import registry
///
/// cache = registry.get_yaml_cache()
/// if cache is not None:
///     settings = cache.get_settings(...)
/// ```
#[pyfunction]
fn get_yaml_cache(py: Python) -> Option<Py<PyAny>> {
    REGISTRY_FACADE_SCOPE
        .get_yaml_cache::<PyObjectWrapper>()
        .map(|w| w.get(py))
}

/// Get the manual documents GUI widget reference.
///
/// # Returns
///
/// The GUI widget, or `None` if not registered
#[pyfunction]
fn get_manual_docs_gui(py: Python) -> Option<Py<PyAny>> {
    REGISTRY_FACADE_SCOPE
        .get_manual_docs_gui::<PyObjectWrapper>()
        .map(|w| w.get(py))
}

/// Get the game path GUI widget reference.
///
/// # Returns
///
/// The GUI widget, or `None` if not registered
#[pyfunction]
fn get_game_path_gui(py: Python) -> Option<Py<PyAny>> {
    REGISTRY_FACADE_SCOPE
        .get_game_path_gui::<PyObjectWrapper>()
        .map(|w| w.get(py))
}

/// Check if the game version was auto-detected.
///
/// # Returns
///
/// `True` if the version was auto-detected from game files,
/// `False` if manually selected or not set.
///
/// # Python Example
///
/// ```python
/// from classic_core import registry
///
/// if registry.is_version_auto_detected():
///     print("Version was auto-detected")
/// ```
#[pyfunction]
fn is_version_auto_detected(py: Python) -> bool {
    // Try PyObjectWrapper first (Python-stored value), then native
    if let Some(wrapper) = REGISTRY_FACADE_SCOPE
        .get::<_, PyObjectWrapper>(classic_registry_core::Keys::VERSION_AUTO_DETECTED)
        && let Ok(value) = wrapper.get(py).extract::<bool>(py)
    {
        return value;
    }
    REGISTRY_FACADE_SCOPE.is_version_auto_detected()
}

/// Get the local application directory.
///
/// # Returns
///
/// The local directory path as a string
///
/// # Python Example
///
/// ```python
/// from classic_core import registry
///
/// local_dir = registry.get_local_dir()
/// print(f"Local directory: {local_dir}")
/// ```
#[pyfunction]
fn get_local_dir(py: Python) -> String {
    // Try PyObjectWrapper first (Python-stored value), then native
    if let Some(wrapper) =
        REGISTRY_FACADE_SCOPE.get::<_, PyObjectWrapper>(classic_registry_core::Keys::LOCAL_DIR)
        && let Ok(value) = wrapper.get(py).extract::<String>(py)
        && !value.is_empty()
    {
        return value;
    }
    REGISTRY_FACADE_SCOPE
        .get_local_dir()
        .to_string_lossy()
        .to_string()
}

/// Set ``classic_registry``'s application directory override.
///
/// The override belongs to this facade's registry scope: ``classic_registry``
/// does not auto-register one at import time, and it is independent of the
/// overrides ``classic_config`` and ``classic_scanlog`` register for
/// themselves.
///
/// # Python Example
///
/// ```python
/// from classic_core import registry
///
/// registry.set_application_dir("/my/project")
/// ```
#[pyfunction]
fn set_application_dir(path: String) {
    REGISTRY_FACADE_SCOPE.set_application_dir(std::path::PathBuf::from(path));
}

/// Return ``classic_registry``'s application directory override, or ``None``
/// if not set.
///
/// Only a native override counts; a value stored under the ``"app_dir"`` key
/// with ``register`` reads as ``None``.
///
/// # Python Example
///
/// ```python
/// from classic_core import registry
///
/// app_dir = registry.get_application_dir()
/// print(f"Application directory: {app_dir}")
/// ```
#[pyfunction]
fn get_application_dir() -> Option<String> {
    REGISTRY_FACADE_SCOPE
        .get_application_dir()
        .map(|p| p.to_string_lossy().into_owned())
}

/// Check if XSE validation passed.
#[pyfunction]
fn is_xse_valid(py: Python) -> bool {
    // Try PyObjectWrapper first, then native
    if let Some(wrapper) =
        REGISTRY_FACADE_SCOPE.get::<_, PyObjectWrapper>(classic_registry_core::Keys::XSE_VALID)
        && let Ok(value) = wrapper.get(py).extract::<bool>(py)
    {
        return value;
    }
    REGISTRY_FACADE_SCOPE.is_xse_valid()
}

/// Check if ENB binaries are present.
#[pyfunction]
fn is_enb_present(py: Python) -> bool {
    // Try PyObjectWrapper first, then native
    if let Some(wrapper) =
        REGISTRY_FACADE_SCOPE.get::<_, PyObjectWrapper>(classic_registry_core::Keys::ENB_PRESENT)
        && let Ok(value) = wrapper.get(py).extract::<bool>(py)
    {
        return value;
    }
    REGISTRY_FACADE_SCOPE.is_enb_present()
}

/// Get the game version as a string.
///
/// Returns the version string, defaulting to "auto" if not set.
#[pyfunction]
fn get_game_version_string(py: Python) -> String {
    // Try PyObjectWrapper first, then native
    if let Some(wrapper) =
        REGISTRY_FACADE_SCOPE.get::<_, PyObjectWrapper>(classic_registry_core::Keys::GAME_VERSION)
        && let Ok(value) = wrapper.get(py).extract::<String>(py)
        && !value.is_empty()
    {
        return value;
    }
    REGISTRY_FACADE_SCOPE.get_game_version_string()
}

/// Python module for registry access.
///
/// This module provides a thread-safe, process-wide registry (owned by this
/// facade) for storing and retrieving singleton instances and configuration
/// values.
///
/// # Examples
///
/// ```python
/// from classic_core import registry
///
/// # Register values
/// registry.register(registry.Keys.GAME, "Fallout4")
/// registry.register(registry.Keys.IS_GUI_MODE, True)
///
/// # Retrieve values
/// game = registry.get(registry.Keys.GAME)
/// is_gui = registry.is_gui_mode()
///
/// # Check registration
/// if registry.is_registered(registry.Keys.GAME):
///     print("Game is configured")
/// ```
#[pymodule]
fn classic_registry(m: &Bound<'_, PyModule>) -> PyResult<()> {
    classic_shared::configure_python_stdio(m.py());

    // Add the Keys class
    m.add_class::<Keys>()?;

    // Add core functions
    m.add_function(wrap_pyfunction!(register, m)?)?;
    m.add_function(wrap_pyfunction!(is_registered, m)?)?;
    m.add_function(wrap_pyfunction!(get, m)?)?;
    m.add_function(wrap_pyfunction!(clear_all, m)?)?;
    m.add_function(wrap_pyfunction!(unregister, m)?)?;

    // Add convenience functions
    m.add_function(wrap_pyfunction!(get_game, m)?)?;
    m.add_function(wrap_pyfunction!(set_game, m)?)?;
    m.add_function(wrap_pyfunction!(is_gui_mode, m)?)?;
    m.add_function(wrap_pyfunction!(get_yaml_cache, m)?)?;
    m.add_function(wrap_pyfunction!(get_manual_docs_gui, m)?)?;
    m.add_function(wrap_pyfunction!(get_game_path_gui, m)?)?;
    m.add_function(wrap_pyfunction!(get_local_dir, m)?)?;
    m.add_function(wrap_pyfunction!(set_application_dir, m)?)?;
    m.add_function(wrap_pyfunction!(get_application_dir, m)?)?;

    // Add new version-aware functions
    m.add_function(wrap_pyfunction!(is_version_auto_detected, m)?)?;
    m.add_function(wrap_pyfunction!(is_xse_valid, m)?)?;
    m.add_function(wrap_pyfunction!(is_enb_present, m)?)?;
    m.add_function(wrap_pyfunction!(get_game_version_string, m)?)?;

    // Add version
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    Ok(())
}
