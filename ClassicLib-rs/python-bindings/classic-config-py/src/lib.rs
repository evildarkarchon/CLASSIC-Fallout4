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

use classic_config_core::{
    ClassicConfig as CoreClassicConfig, ConfigError, CoreModExclude, PathConfig as CorePathConfig,
    YamlDataCore, YamlSource as CoreYamlSource,
};
use classic_crashgen_settings_core::{
    CheckRule, ExpectedValue, Predicate, PreflightRule, RuleSeverity, TargetValueType,
};
use classic_settings_core::SettingsError;
use classic_shared::{ResultExt, ToPyErr, define_exceptions, register_exceptions, without_gil};
use classic_shared_core::get_runtime;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PySet};
use std::collections::HashMap;
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

fn config_error_to_pyerr(err: &ConfigError) -> PyErr {
    match err {
        ConfigError::IOError { context, source } => {
            RustConfigIOError::new_err(format!("{}: {}", context, source))
        }
        ConfigError::ParseError { context, message } => {
            RustConfigParseError::new_err(format!("{}: {}", context, message))
        }
        ConfigError::EmptyDocument(doc_name) => {
            RustConfigParseError::new_err(format!("Empty YAML document: {}", doc_name))
        }
        ConfigError::InvalidInput(msg) => {
            RustConfigParseError::new_err(format!("Invalid input: {}", msg))
        }
    }
}

fn settings_error_to_pyerr(err: &SettingsError, message: &str) -> PyErr {
    match err {
        SettingsError::IoError { .. } => RustConfigIOError::new_err(message.to_string()),
        SettingsError::YamlParseError { .. }
        | SettingsError::EmptyDocument { .. }
        | SettingsError::InvalidYamlStructure { .. }
        | SettingsError::KeyNotFound(_) => RustConfigParseError::new_err(message.to_string()),
        SettingsError::TaskJoinError { .. } => RustConfigError::new_err(message.to_string()),
    }
}

// Implement ToPyErr for the local wrapper
impl ToPyErr for PyConfigError {
    type BaseException = RustConfigError;
    type IOException = RustConfigIOError;
    type ParseException = RustConfigParseError;

    fn to_pyerr(self) -> PyErr {
        config_error_to_pyerr(&self.0)
    }
}

fn runtime_to_pyerr(err: anyhow::Error) -> PyErr {
    let display = format!("{err:#}");
    let mut current: Option<&(dyn std::error::Error + 'static)> = Some(err.as_ref());

    while let Some(cause) = current {
        if let Some(config_err) = cause.downcast_ref::<ConfigError>() {
            return config_error_to_pyerr(config_err);
        }
        if let Some(settings_err) = cause.downcast_ref::<SettingsError>() {
            return settings_error_to_pyerr(settings_err, &display);
        }
        if cause.downcast_ref::<std::io::Error>().is_some() {
            return RustConfigIOError::new_err(display);
        }
        current = cause.source();
    }

    RustConfigError::new_err(display)
}

fn pathbuf_to_string(path: &std::path::Path) -> String {
    path.to_string_lossy().to_string()
}

fn option_pathbuf_to_string(path: &Option<PathBuf>) -> Option<String> {
    path.as_ref()
        .map(|value| pathbuf_to_string(value.as_path()))
}

/// Python wrapper for runtime path configuration settings.
#[pyclass(name = "PathConfig")]
#[derive(Clone)]
pub struct PyPathConfig {
    inner: CorePathConfig,
}

impl From<CorePathConfig> for PyPathConfig {
    fn from(inner: CorePathConfig) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyPathConfig {
    #[new]
    #[pyo3(signature = (ini_folder=None, scan_custom=None, mods_folder=None, game_root=None, docs_root=None))]
    fn new(
        ini_folder: Option<String>,
        scan_custom: Option<String>,
        mods_folder: Option<String>,
        game_root: Option<String>,
        docs_root: Option<String>,
    ) -> Self {
        Self {
            inner: CorePathConfig {
                ini_folder: ini_folder.map(PathBuf::from),
                scan_custom: scan_custom.map(PathBuf::from),
                mods_folder: mods_folder.map(PathBuf::from),
                game_root: PathBuf::from(game_root.unwrap_or_default()),
                docs_root: docs_root.map(PathBuf::from),
            },
        }
    }

    #[getter]
    fn ini_folder(&self) -> Option<String> {
        option_pathbuf_to_string(&self.inner.ini_folder)
    }

    #[setter]
    fn set_ini_folder(&mut self, value: Option<String>) {
        self.inner.ini_folder = value.map(PathBuf::from);
    }

    #[getter]
    fn scan_custom(&self) -> Option<String> {
        option_pathbuf_to_string(&self.inner.scan_custom)
    }

    #[setter]
    fn set_scan_custom(&mut self, value: Option<String>) {
        self.inner.scan_custom = value.map(PathBuf::from);
    }

    #[getter]
    fn mods_folder(&self) -> Option<String> {
        option_pathbuf_to_string(&self.inner.mods_folder)
    }

    #[setter]
    fn set_mods_folder(&mut self, value: Option<String>) {
        self.inner.mods_folder = value.map(PathBuf::from);
    }

    #[getter]
    fn game_root(&self) -> String {
        pathbuf_to_string(self.inner.game_root.as_path())
    }

    #[setter]
    fn set_game_root(&mut self, value: String) {
        self.inner.game_root = PathBuf::from(value);
    }

    #[getter]
    fn docs_root(&self) -> Option<String> {
        option_pathbuf_to_string(&self.inner.docs_root)
    }

    #[setter]
    fn set_docs_root(&mut self, value: Option<String>) {
        self.inner.docs_root = value.map(PathBuf::from);
    }

    fn __repr__(&self) -> String {
        format!(
            "PathConfig(game_root='{}')",
            pathbuf_to_string(self.inner.game_root.as_path())
        )
    }
}

/// Python enum-like wrapper for YAML source identifiers.
#[pyclass(name = "YamlSource")]
#[derive(Clone, Copy, PartialEq, Eq)]
pub struct PyYamlSource {
    inner: CoreYamlSource,
}

#[pymethods]
#[allow(non_snake_case)]
impl PyYamlSource {
    #[classattr]
    fn MAIN() -> Self {
        Self {
            inner: CoreYamlSource::Main,
        }
    }

    #[classattr]
    fn SETTINGS() -> Self {
        Self {
            inner: CoreYamlSource::Settings,
        }
    }

    #[classattr]
    fn IGNORE() -> Self {
        Self {
            inner: CoreYamlSource::Ignore,
        }
    }

    #[classattr]
    fn GAME() -> Self {
        Self {
            inner: CoreYamlSource::Game,
        }
    }

    #[classattr]
    fn GAME_LOCAL() -> Self {
        Self {
            inner: CoreYamlSource::GameLocal,
        }
    }

    #[classattr]
    fn TEST() -> Self {
        Self {
            inner: CoreYamlSource::Test,
        }
    }

    #[classattr]
    fn CACHE() -> Self {
        Self {
            inner: CoreYamlSource::Cache,
        }
    }

    fn path(&self, game: &str) -> String {
        pathbuf_to_string(self.inner.path(game).as_path())
    }

    fn display_name(&self) -> &'static str {
        self.inner.display_name()
    }

    fn display_name_with_game(&self, game: &str) -> String {
        self.inner.display_name_with_game(game)
    }

    fn __repr__(&self) -> String {
        format!("YamlSource.{}", self.variant_name())
    }

    fn __str__(&self) -> &'static str {
        self.variant_name()
    }

    fn __hash__(&self) -> usize {
        match self.inner {
            CoreYamlSource::Main => 0,
            CoreYamlSource::Settings => 1,
            CoreYamlSource::Ignore => 2,
            CoreYamlSource::Game => 3,
            CoreYamlSource::GameLocal => 4,
            CoreYamlSource::Test => 5,
            CoreYamlSource::Cache => 6,
        }
    }

    fn __eq__(&self, other: &PyYamlSource) -> bool {
        self.inner == other.inner
    }
}

impl PyYamlSource {
    fn variant_name(&self) -> &'static str {
        match self.inner {
            CoreYamlSource::Main => "MAIN",
            CoreYamlSource::Settings => "SETTINGS",
            CoreYamlSource::Ignore => "IGNORE",
            CoreYamlSource::Game => "GAME",
            CoreYamlSource::GameLocal => "GAME_LOCAL",
            CoreYamlSource::Test => "TEST",
            CoreYamlSource::Cache => "CACHE",
        }
    }
}

/// Python wrapper for the runtime CLASSIC configuration model.
#[pyclass(name = "ClassicConfig")]
#[derive(Clone)]
pub struct PyClassicConfig {
    inner: CoreClassicConfig,
}

#[pymethods]
impl PyClassicConfig {
    #[new]
    fn new() -> Self {
        Self {
            inner: CoreClassicConfig::default(),
        }
    }

    #[staticmethod]
    fn load_from_yaml(py: Python<'_>, path: String) -> PyResult<Self> {
        let path_buf = PathBuf::from(path);
        let inner = without_gil(py, || {
            get_runtime().block_on(async { CoreClassicConfig::load_from_yaml(&path_buf).await })
        })
        .map_err(runtime_to_pyerr)?;
        Ok(Self { inner })
    }

    #[staticmethod]
    fn load_or_default(py: Python<'_>) -> PyResult<Self> {
        let inner = without_gil(py, || {
            get_runtime().block_on(async { CoreClassicConfig::load_or_default().await })
        })
        .map_err(runtime_to_pyerr)?;
        Ok(Self { inner })
    }

    fn save_to_yaml(&self, py: Python<'_>, path: String) -> PyResult<()> {
        let path_buf = PathBuf::from(path);
        without_gil(py, || {
            get_runtime().block_on(async { self.inner.save_to_yaml(&path_buf).await })
        })
        .map_err(runtime_to_pyerr)
    }

    fn get_config_path(&self) -> String {
        pathbuf_to_string(self.inner.get_config_path().as_path())
    }

    fn validate_paths(&self) -> PyResult<()> {
        self.inner.validate_paths().map_err(runtime_to_pyerr)
    }

    fn load_local_yaml_paths(&mut self, py: Python<'_>, game: String) -> PyResult<()> {
        without_gil(py, || {
            get_runtime().block_on(async { self.inner.load_local_yaml_paths(&game).await })
        })
        .map_err(runtime_to_pyerr)
    }

    #[getter]
    fn fcx_mode(&self) -> bool {
        self.inner.fcx_mode
    }

    #[setter]
    fn set_fcx_mode(&mut self, value: bool) {
        self.inner.fcx_mode = value;
    }

    #[getter]
    fn show_formid_values(&self) -> bool {
        self.inner.show_formid_values
    }

    #[setter]
    fn set_show_formid_values(&mut self, value: bool) {
        self.inner.show_formid_values = value;
    }

    #[getter]
    fn stat_logging(&self) -> bool {
        self.inner.stat_logging
    }

    #[setter]
    fn set_stat_logging(&mut self, value: bool) {
        self.inner.stat_logging = value;
    }

    #[getter]
    fn move_unsolved_logs(&self) -> bool {
        self.inner.move_unsolved_logs
    }

    #[setter]
    fn set_move_unsolved_logs(&mut self, value: bool) {
        self.inner.move_unsolved_logs = value;
    }

    #[getter]
    fn simplify_logs(&self) -> bool {
        self.inner.simplify_logs
    }

    #[setter]
    fn set_simplify_logs(&mut self, value: bool) {
        self.inner.simplify_logs = value;
    }

    #[getter]
    fn update_check(&self) -> bool {
        self.inner.update_check
    }

    #[setter]
    fn set_update_check(&mut self, value: bool) {
        self.inner.update_check = value;
    }

    #[getter]
    fn game_version(&self) -> String {
        self.inner.game_version.clone()
    }

    #[setter]
    fn set_game_version(&mut self, value: String) {
        self.inner.game_version = value;
    }

    #[getter]
    fn update_source(&self) -> String {
        self.inner.update_source.clone()
    }

    #[setter]
    fn set_update_source(&mut self, value: String) {
        self.inner.update_source = value;
    }

    #[getter]
    fn auto_switch_to_results(&self) -> bool {
        self.inner.auto_switch_to_results
    }

    #[setter]
    fn set_auto_switch_to_results(&mut self, value: bool) {
        self.inner.auto_switch_to_results = value;
    }

    #[getter]
    fn auto_refresh_interval_ms(&self) -> u64 {
        self.inner.auto_refresh_interval_ms
    }

    #[setter]
    fn set_auto_refresh_interval_ms(&mut self, value: u64) {
        self.inner.auto_refresh_interval_ms = value;
    }

    #[getter]
    fn paths(&self) -> PyPathConfig {
        PyPathConfig::from(self.inner.paths.clone())
    }

    #[setter]
    fn set_paths(&mut self, value: PyRef<'_, PyPathConfig>) {
        self.inner.paths = value.inner.clone();
    }

    #[getter]
    fn formid_databases(&self) -> HashMap<String, Vec<String>> {
        self.inner
            .formid_databases
            .iter()
            .map(|(game, paths)| {
                (
                    game.clone(),
                    paths
                        .iter()
                        .map(|path| pathbuf_to_string(path.as_path()))
                        .collect(),
                )
            })
            .collect()
    }

    #[setter]
    fn set_formid_databases(&mut self, value: HashMap<String, Vec<String>>) {
        self.inner.formid_databases = value
            .into_iter()
            .map(|(game, paths)| {
                (
                    game,
                    paths.into_iter().map(PathBuf::from).collect::<Vec<_>>(),
                )
            })
            .collect();
    }

    fn __repr__(&self) -> String {
        format!("ClassicConfig(game_version='{}')", self.inner.game_version)
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
    fn game_mods_conf(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let list = PyList::empty(py);
        for entry in &self.inner.game_mods_conf {
            let dict = PyDict::new(py);
            dict.set_item("mod_a", &entry.mod_a)?;
            dict.set_item("mod_b", &entry.mod_b)?;
            dict.set_item("name_a", &entry.name_a)?;
            dict.set_item("name_b", &entry.name_b)?;
            dict.set_item("description", &entry.description)?;
            dict.set_item("fix", &entry.fix)?;
            dict.set_item("link", &entry.link)?;
            list.append(dict)?;
        }
        Ok(list.unbind())
    }

    #[getter]
    fn game_mods_core(&self, py: Python<'_>) -> PyResult<Py<pyo3::types::PyList>> {
        let list = pyo3::types::PyList::empty(py);
        for entry in &self.inner.game_mods_core {
            let dict = PyDict::new(py);
            dict.set_item("detect", &entry.detect)?;
            dict.set_item("name", &entry.name)?;
            dict.set_item("description", &entry.description)?;
            dict.set_item("gpu", &entry.gpu)?;
            dict.set_item("gpu_mismatch_warning", &entry.gpu_mismatch_warning)?;
            if let Some(CoreModExclude::PluginAny(ref plugins)) = entry.exclude_when {
                let ew_dict = PyDict::new(py);
                ew_dict.set_item("plugin_any", plugins)?;
                dict.set_item("exclude_when", ew_dict)?;
            }
            list.append(dict)?;
        }
        Ok(list.unbind())
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
    m.add_class::<PyPathConfig>()?;
    m.add_class::<PyYamlSource>()?;
    m.add_class::<PyClassicConfig>()?;
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
    m.add_class::<PyPathConfig>()?;
    m.add_class::<PyYamlSource>()?;
    m.add_class::<PyClassicConfig>()?;
    m.add_function(wrap_pyfunction!(create_yamldata, m)?)?;
    m.add_function(wrap_pyfunction!(clear_yaml_cache, m)?)?;

    // Register custom exception types using the shared macro
    register_exceptions!(m, RustConfigError, RustConfigIOError, RustConfigParseError);

    Ok(())
}
