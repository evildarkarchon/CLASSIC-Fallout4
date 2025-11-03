//! Python bindings for the global registry.
//!
//! This crate provides Python bindings for `classic-registry-core`, allowing
//! Python code to interact with the global registry for singleton management.

use pyo3::prelude::*;
use std::sync::Arc;

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
    const VR: &'static str = classic_registry_core::Keys::VR;

    #[classattr]
    const GAME: &'static str = classic_registry_core::Keys::GAME;

    #[classattr]
    const LOCAL_DIR: &'static str = classic_registry_core::Keys::LOCAL_DIR;

    #[classattr]
    const IS_PRERELEASE: &'static str = classic_registry_core::Keys::IS_PRERELEASE;
}

/// Register a value in the global registry.
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
    classic_registry_core::register(key, PyObjectWrapper::new(value));
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
    classic_registry_core::is_registered(&key)
}

/// Retrieve a value from the global registry.
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
    Ok(classic_registry_core::get::<_, PyObjectWrapper>(key).map(|w| w.get(py)))
}

/// Clear all entries from the registry.
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
    classic_registry_core::clear_all();
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
fn get_game() -> String {
    classic_registry_core::get_game()
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
fn set_game(game_name: String) {
    classic_registry_core::set_game(game_name);
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
    if let Some(wrapper) = classic_registry_core::get::<_, PyObjectWrapper>(Keys::IS_GUI_MODE) {
        let obj = wrapper.get(py);
        if let Ok(value) = obj.extract::<bool>(py) {
            return value;
        }
    }
    // Fallback to native bool (for compatibility)
    classic_registry_core::is_gui_mode()
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
    classic_registry_core::get_yaml_cache::<PyObjectWrapper>().map(|w| w.get(py))
}

/// Get the manual documents GUI widget reference.
///
/// # Returns
///
/// The GUI widget, or `None` if not registered
#[pyfunction]
fn get_manual_docs_gui(py: Python) -> Option<Py<PyAny>> {
    classic_registry_core::get_manual_docs_gui::<PyObjectWrapper>().map(|w| w.get(py))
}

/// Get the game path GUI widget reference.
///
/// # Returns
///
/// The GUI widget, or `None` if not registered
#[pyfunction]
fn get_game_path_gui(py: Python) -> Option<Py<PyAny>> {
    classic_registry_core::get_game_path_gui::<PyObjectWrapper>().map(|w| w.get(py))
}

/// Get the VR game variant identifier.
///
/// # Returns
///
/// The VR variant name, or empty string if not set
///
/// # Python Example
///
/// ```python
/// from classic_core import registry
///
/// vr = registry.get_vr()
/// if vr:
///     print(f"VR variant: {vr}")
/// ```
#[pyfunction]
fn get_vr(py: Python) -> String {
    // Try to get as PyObjectWrapper first (for Python string), then fallback to native string
    if let Some(wrapper) = classic_registry_core::get::<_, PyObjectWrapper>(Keys::VR) {
        let obj = wrapper.get(py);
        if let Ok(value) = obj.extract::<String>(py) {
            return value;
        }
    }
    // Fallback to native string (for compatibility)
    classic_registry_core::get_vr()
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
fn get_local_dir() -> String {
    classic_registry_core::get_local_dir()
        .to_string_lossy()
        .to_string()
}

/// Python module for global registry access.
///
/// This module provides a thread-safe global registry for storing and retrieving
/// singleton instances and configuration values.
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
    // Add the Keys class
    m.add_class::<Keys>()?;

    // Add core functions
    m.add_function(wrap_pyfunction!(register, m)?)?;
    m.add_function(wrap_pyfunction!(is_registered, m)?)?;
    m.add_function(wrap_pyfunction!(get, m)?)?;
    m.add_function(wrap_pyfunction!(clear_all, m)?)?;

    // Add convenience functions
    m.add_function(wrap_pyfunction!(get_game, m)?)?;
    m.add_function(wrap_pyfunction!(set_game, m)?)?;
    m.add_function(wrap_pyfunction!(is_gui_mode, m)?)?;
    m.add_function(wrap_pyfunction!(get_yaml_cache, m)?)?;
    m.add_function(wrap_pyfunction!(get_manual_docs_gui, m)?)?;
    m.add_function(wrap_pyfunction!(get_game_path_gui, m)?)?;
    m.add_function(wrap_pyfunction!(get_vr, m)?)?;
    m.add_function(wrap_pyfunction!(get_local_dir, m)?)?;

    // Add version
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    Ok(())
}
