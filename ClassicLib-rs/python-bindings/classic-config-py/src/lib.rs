//! Classic Config Python Bindings
//!
//! This crate provides thin PyO3 bindings for classic-config-core.
//! It contains ONLY type conversions and Python wrappers - all business
//! logic is in classic-config-core.
//!
//! ## Complete Usage Example
//!
//! ```python
//! from classic_core import config
//! from pathlib import Path
//!
//! # Load all configuration from YAML files
//! yaml_dirs = [
//!     Path("YAML/Main"),
//!     Path("YAML/Games"),
//!     Path("YAML/Ignore"),
//! ]
//!
//! yamldata = config.YamlData(yaml_dirs, "Fallout4", False)
//!
//! # Access game configuration
//! print(f"Game: {yamldata.crashgen_name}")
//! print(f"Version: {yamldata.game_version}")
//! print(f"XSE: {yamldata.xse_acronym}")  # "F4SE"
//!
//! # Access ignore lists for filtering
//! ignore_plugins = yamldata.game_ignore_plugins  # ["Fallout4.esm", ...]
//! ignore_records = yamldata.game_ignore_records  # ["System", ...]
//! ignore_list = yamldata.ignore_list  # User-defined ignores
//!
//! # Access mod detection databases
//! core_mods = yamldata.game_mods_core  # Essential mods
//! freq_mods = yamldata.game_mods_freq  # Frequently problematic mods
//! conf_mods = yamldata.game_mods_conf  # Conflicting mod pairs
//! solu_mods = yamldata.game_mods_solu  # Solution mods
//!
//! # Access suspect pattern dictionaries
//! error_patterns = yamldata.suspects_error_list  # Error message patterns
//! stack_patterns = yamldata.suspects_stack_list  # Stack trace patterns
//!
//! # Access CLASSIC metadata
//! print(f"CLASSIC Version: {yamldata.classic_version}")
//! print(f"Date: {yamldata.classic_version_date}")
//!
//! # Functional API (alternative to class instantiation)
//! yamldata2 = config.create_yamldata(yaml_dirs, "Skyrim", False)
//! ```
//!
//! ## Performance Characteristics
//!
//! - **YAML loading**: Uses yaml-rust2 (15-30x faster than ruamel.yaml)
//! - **Async I/O**: Non-blocking file loading with Tokio
//! - **Single load**: Configuration loaded once, cached for lifetime of object
//! - **Memory efficient**: Rust data structures with minimal Python overhead
//!
//! ## Thread Safety
//!
//! YamlData instances are immutable after creation and thread-safe. They can be
//! shared across Python threads without additional synchronization.
//!
//! ```python
//! from classic_core import config
//! from threading import Thread
//! from pathlib import Path
//!
//! # Load configuration once
//! yamldata = config.YamlData([Path("YAML/Main")], "Fallout4", False)
//!
//! def worker(thread_id):
//!     # Safe to access from multiple threads
//!     mods = yamldata.game_mods_freq
//!     print(f"Thread {thread_id}: {len(mods)} mods")
//!
//! threads = [Thread(target=worker, args=(i,)) for i in range(10)]
//! for t in threads:
//!     t.start()
//! for t in threads:
//!     t.join()
//! ```

use classic_config_core::{ConfigError, YamlDataCore};
use classic_crashgen_settings_core::{
    CheckRule, ExpectedValue, Predicate, PreflightRule, RuleSeverity, TargetValueType,
};
use classic_shared::{ResultExt, ToPyErr, define_exceptions, register_exceptions, without_gil};
use classic_shared_core::get_runtime;
use pyo3::exceptions::{PyIOError, PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PySet};
use std::path::PathBuf;

fn severity_to_str(severity: RuleSeverity) -> &'static str {
    match severity {
        RuleSeverity::Info => "info",
        RuleSeverity::Warning => "warning",
        RuleSeverity::Error => "error",
    }
}

fn predicate_to_pydict(py: Python<'_>, predicate: &Predicate) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    match predicate {
        Predicate::Always => {}
        Predicate::PluginAny(plugins) => {
            out.set_item("plugin_any", PyList::new(py, plugins)?)?;
        }
        Predicate::ConfigLayoutIs(layout) => {
            let layout_str = match layout {
                classic_crashgen_settings_core::ConfigLayout::Og => "og",
                classic_crashgen_settings_core::ConfigLayout::Vr => "vr",
                classic_crashgen_settings_core::ConfigLayout::Unknown => "unknown",
            };
            out.set_item("config_layout_is", layout_str)?;
        }
        Predicate::CrashgenVersionLt((a, b, c)) => {
            out.set_item("crashgen_version_lt", format!("{a}.{b}.{c}"))?;
        }
        Predicate::All(items) => {
            let mut py_items = Vec::with_capacity(items.len());
            for item in items {
                py_items.push(predicate_to_pydict(py, item)?);
            }
            out.set_item("all", PyList::new(py, &py_items)?)?;
        }
        Predicate::Any(items) => {
            let mut py_items = Vec::with_capacity(items.len());
            for item in items {
                py_items.push(predicate_to_pydict(py, item)?);
            }
            out.set_item("any", PyList::new(py, &py_items)?)?;
        }
        Predicate::Not(item) => {
            out.set_item("not", predicate_to_pydict(py, item)?)?;
        }
    }
    Ok(out.unbind())
}

fn preflight_rule_to_pydict(py: Python<'_>, rule: &PreflightRule) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    out.set_item("id", &rule.id)?;
    out.set_item("when", predicate_to_pydict(py, &rule.when)?)?;
    let action = PyDict::new(py);
    let kind = match rule.action.kind {
        classic_crashgen_settings_core::PreflightActionKind::NoticeAndSkipRemaining => {
            "notice_and_skip_remaining"
        }
        classic_crashgen_settings_core::PreflightActionKind::Notice => "notice",
        classic_crashgen_settings_core::PreflightActionKind::Issue => "issue",
    };
    action.set_item("kind", kind)?;
    action.set_item("severity", severity_to_str(rule.action.severity))?;
    action.set_item("message", &rule.action.message)?;
    action.set_item("fix", &rule.action.fix)?;
    out.set_item("action", action)?;
    Ok(out.unbind())
}

fn check_rule_to_pydict(py: Python<'_>, rule: &CheckRule) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    out.set_item("id", &rule.id)?;
    let target = PyDict::new(py);
    target.set_item("section", &rule.target.section)?;
    target.set_item("key", &rule.target.key)?;
    let value_type = match rule.target.value_type {
        TargetValueType::Bool => "bool",
        TargetValueType::Int => "int",
        TargetValueType::String => "string",
    };
    target.set_item("value_type", value_type)?;
    out.set_item("target", target)?;
    out.set_item("when", predicate_to_pydict(py, &rule.when)?)?;

    let expect = PyDict::new(py);
    match &rule.expect {
        ExpectedValue::Bool(v) => expect.set_item("equals", *v)?,
        ExpectedValue::Int(v) => expect.set_item("equals", *v)?,
        ExpectedValue::String(v) => expect.set_item("equals", v)?,
    }
    out.set_item("expect", expect)?;

    let messages = PyDict::new(py);
    messages.set_item("fail", &rule.messages.fail)?;
    messages.set_item("fix", &rule.messages.fix)?;
    messages.set_item("pass", &rule.messages.pass)?;
    out.set_item("messages", messages)?;

    out.set_item("severity", severity_to_str(rule.severity))?;
    Ok(out.unbind())
}

// Define the standard 3-tier exception hierarchy using the shared macro
define_exceptions!(
    module: classic_config,
    base: RustConfigError,
    io: RustConfigIOError,
    parse: RustConfigParseError
);

// Wrapper to satisfy orphan rules
struct PyConfigError(ConfigError);

// Implement ToPyErr for the local wrapper
impl ToPyErr for PyConfigError {
    type BaseException = PyRuntimeError;
    type IOException = PyIOError;
    type ParseException = PyValueError;

    fn to_pyerr(self) -> PyErr {
        match self.0 {
            ConfigError::IOError { context, source } => {
                Self::io_err(format!("{}: {}", context, source))
            }
            ConfigError::ParseError { context, source } => {
                Self::parse_err(format!("{}: {}", context, source))
            }
            ConfigError::EmptyDocument(doc_name) => {
                Self::parse_err(format!("Empty YAML document: {}", doc_name))
            }
            ConfigError::InvalidInput(msg) => Self::parse_err(format!("Invalid input: {}", msg)),
            ConfigError::RuntimeError(msg) => Self::base_err(format!("Runtime error: {}", msg)),
        }
    }
}

/// Python wrapper for YamlDataCore
///
/// This is a thin adapter that:
/// 1. Calls YamlDataCore::load_from_yaml_files (business logic)
/// 2. Converts Rust types (Vec, HashMap) to Python types (PyList, PyDict)
/// 3. Exposes fields as Python properties
#[pyclass(name = "YamlData")]
pub struct PyYamlData {
    /// The inner pure Rust data structure
    inner: YamlDataCore,
}

#[pymethods]
impl PyYamlData {
    #[new]
    #[pyo3(signature = (yaml_dirs, game, game_version))]
    fn new(
        py: Python<'_>,
        yaml_dirs: Vec<PathBuf>,
        game: String,
        game_version: String,
    ) -> PyResult<Self> {
        // Call pure Rust core using shared runtime, releasing GIL during blocking I/O
        let core = without_gil(py, || {
            get_runtime().block_on(async {
                YamlDataCore::load_from_yaml_files(yaml_dirs, game, game_version).await
            })
        })
        .map_err(PyConfigError)
        .map_pyerr()?;

        Ok(Self { inner: core })
    }

    /// Create YamlData from YAML content strings (for testing without file I/O).
    ///
    /// This constructor is useful for unit tests and integration tests where you want
    /// to test YamlData parsing without needing actual YAML files on disk.
    ///
    /// Args:
    ///     main_content: Content of the main YAML configuration file
    ///     game_content: Content of the game-specific YAML configuration file
    ///     ignore_content: Content of the ignore list YAML configuration file
    ///     game: Game identifier (e.g., "Fallout4", "Skyrim")
    ///     game_version: Selected mode
    ///         ("auto", "Original", "NextGen", "AnniversaryEdition"/"AE", "VR")
    ///
    /// Returns:
    ///     YamlData instance with parsed configuration
    ///
    /// Raises:
    ///     RustConfigParseError: If any YAML content fails to parse
    #[staticmethod]
    #[pyo3(name = "from_yaml_content")]
    fn py_from_yaml_content(
        main_content: String,
        game_content: String,
        ignore_content: String,
        game: String,
        game_version: String,
    ) -> PyResult<Self> {
        let inner = YamlDataCore::from_yaml_content(
            &main_content,
            &game_content,
            &ignore_content,
            game,
            game_version,
        )
        .map_err(PyConfigError)
        .map_pyerr()?;

        Ok(Self { inner })
    }

    // ========================================================================
    // Game Configuration Properties
    // ========================================================================

    #[getter]
    fn classic_game_hints(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let list = PyList::new(py, &self.inner.classic_game_hints)?;
        Ok(list.into())
    }

    #[getter]
    fn classic_records_list(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let list = PyList::new(py, &self.inner.classic_records_list)?;
        Ok(list.into())
    }

    #[getter]
    fn classic_version(&self) -> String {
        self.inner.classic_version.clone()
    }

    #[getter]
    fn classic_version_date(&self) -> String {
        self.inner.classic_version_date.clone()
    }

    // ========================================================================
    // Crashgen Configuration Properties
    // ========================================================================

    #[getter]
    fn crashgen_name(&self) -> String {
        self.inner.crashgen_name.clone()
    }

    #[getter]
    fn crashgen_latest_og(&self) -> String {
        self.inner.crashgen_latest_og.clone()
    }

    #[getter]
    fn crashgen_ignore(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        // Convert Vec<String> to PySet (was a set in original Python)
        let list = PyList::new(py, &self.inner.crashgen_ignore)?;
        let py_set = PySet::new(py, list.iter())?;
        Ok(py_set.unbind().into())
    }

    #[getter]
    fn crashgen_registry(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let registry = PyDict::new(py);

        for (name, entry) in &self.inner.crashgen_registry {
            let entry_dict = PyDict::new(py);
            entry_dict.set_item("display_section", &entry.display_section)?;

            // Sort ignore keys for deterministic Python output across runs.
            let mut ignore_keys: Vec<&str> = entry.ignore_keys.iter().map(String::as_str).collect();
            ignore_keys.sort_unstable();
            entry_dict.set_item("ignore_keys", PyList::new(py, &ignore_keys)?)?;

            entry_dict.set_item("checks", PyList::new(py, &entry.checks)?)?;
            entry_dict.set_item("settings_rules_version", entry.settings_rules_version)?;
            if let Some(rules) = &entry.settings_rules {
                let rules_dict = PyDict::new(py);
                rules_dict.set_item("version", rules.version)?;

                let mut preflight = Vec::with_capacity(rules.preflight.len());
                for rule in &rules.preflight {
                    preflight.push(preflight_rule_to_pydict(py, rule)?);
                }
                rules_dict.set_item("preflight", PyList::new(py, &preflight)?)?;

                let mut checks = Vec::with_capacity(rules.checks.len());
                for rule in &rules.checks {
                    checks.push(check_rule_to_pydict(py, rule)?);
                }
                rules_dict.set_item("checks", PyList::new(py, &checks)?)?;
                entry_dict.set_item("settings_rules", rules_dict)?;
            } else {
                entry_dict.set_item("settings_rules", py.None())?;
            }
            registry.set_item(name, entry_dict)?;
        }

        Ok(registry.unbind())
    }

    // ========================================================================
    // Warning Properties
    // ========================================================================

    #[getter]
    fn warn_noplugins(&self) -> String {
        self.inner.warn_noplugins.clone()
    }

    #[getter]
    fn warn_outdated(&self) -> String {
        self.inner.warn_outdated.clone()
    }

    // ========================================================================
    // XSE Configuration
    // ========================================================================

    #[getter]
    fn xse_acronym(&self) -> String {
        self.inner.xse_acronym.clone()
    }

    // ========================================================================
    // Ignore Lists
    // ========================================================================

    #[getter]
    fn game_ignore_plugins(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let list = PyList::new(py, &self.inner.game_ignore_plugins)?;
        Ok(list.into())
    }

    #[getter]
    fn game_ignore_records(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let list = PyList::new(py, &self.inner.game_ignore_records)?;
        Ok(list.into())
    }

    #[getter]
    fn ignore_list(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let list = PyList::new(py, &self.inner.ignore_list)?;
        Ok(list.into())
    }

    // ========================================================================
    // Suspect Pattern Dictionaries
    // ========================================================================

    #[getter]
    fn suspects_error_list(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        for (k, v) in &self.inner.suspects_error_list {
            dict.set_item(k, v)?;
        }
        Ok(dict.unbind())
    }

    #[getter]
    fn suspects_stack_list(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        for (k, v) in &self.inner.suspects_stack_list {
            dict.set_item(k, v)?;
        }
        Ok(dict.unbind())
    }

    // ========================================================================
    // Mod Database Dictionaries
    // ========================================================================

    #[getter]
    fn game_mods_conf(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        for (k, v) in &self.inner.game_mods_conf {
            dict.set_item(k, v)?;
        }
        Ok(dict.unbind())
    }

    #[getter]
    fn game_mods_core(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        for (k, v) in &self.inner.game_mods_core {
            dict.set_item(k, v)?;
        }
        Ok(dict.unbind())
    }

    #[getter]
    fn game_mods_core_folon(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        for (k, v) in &self.inner.game_mods_core_folon {
            dict.set_item(k, v)?;
        }
        Ok(dict.unbind())
    }

    #[getter]
    fn game_mods_freq(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        for (k, v) in &self.inner.game_mods_freq {
            dict.set_item(k, v)?;
        }
        Ok(dict.unbind())
    }

    #[getter]
    fn game_mods_opc2(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        for (k, v) in &self.inner.game_mods_opc2 {
            dict.set_item(k, v)?;
        }
        Ok(dict.unbind())
    }

    #[getter]
    fn game_mods_solu(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        for (k, v) in &self.inner.game_mods_solu {
            dict.set_item(k, v)?;
        }
        Ok(dict.unbind())
    }

    // ========================================================================
    // UI Configuration
    // ========================================================================

    #[getter]
    fn autoscan_text(&self) -> String {
        self.inner.autoscan_text.clone()
    }

    // ========================================================================
    // Game Versions
    // ========================================================================

    #[getter]
    fn game_version(&self) -> String {
        self.inner.game_version.clone()
    }

    // ========================================================================
    // Game Root Names
    // ========================================================================

    #[getter]
    fn game_root_name(&self) -> String {
        self.inner.game_root_name.clone()
    }

    // ========================================================================
    // Python Special Methods
    // ========================================================================

    fn __repr__(&self) -> String {
        format!(
            "YamlData(game={}, version={})",
            self.inner
                .crashgen_name
                .split('_')
                .next()
                .unwrap_or("unknown"),
            self.inner.classic_version,
        )
    }
}

/// Python API function to create YamlData
///
/// This is a convenience function for Python code that wants to
/// use a functional style instead of instantiating the class.
#[pyfunction]
#[pyo3(signature = (yaml_dirs, game, game_version))]
pub fn create_yamldata(
    py: Python<'_>,
    yaml_dirs: Vec<PathBuf>,
    game: String,
    game_version: String,
) -> PyResult<PyYamlData> {
    PyYamlData::new(py, yaml_dirs, game, game_version)
}

/// Clear the global YAML cache
///
/// This function clears all cached YAML data. It's primarily useful for
/// testing to ensure clean state between test runs.
#[pyfunction]
pub fn clear_yaml_cache() {
    classic_config_core::clear_global_yaml_cache();
}

/// Initialize the classic_config Python module
#[pymodule]
fn classic_config(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyYamlData>()?;
    m.add_function(wrap_pyfunction!(create_yamldata, m)?)?;
    m.add_function(wrap_pyfunction!(clear_yaml_cache, m)?)?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    // Register custom exception types using the shared macro
    register_exceptions!(m, RustConfigError, RustConfigIOError, RustConfigParseError);

    Ok(())
}

/// Public registration function for use by facade modules
/// This allows classic-core to include config components in its submodule
pub fn register_config_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyYamlData>()?;
    m.add_function(wrap_pyfunction!(create_yamldata, m)?)?;
    m.add_function(wrap_pyfunction!(clear_yaml_cache, m)?)?;

    // Register custom exception types using the shared macro
    register_exceptions!(m, RustConfigError, RustConfigIOError, RustConfigParseError);

    Ok(())
}
