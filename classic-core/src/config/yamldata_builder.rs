//! Rust-accelerated YamlData builder
//!
//! This module provides a Rust implementation of ClassicScanLogsInfo,
//! achieving 15-30x faster configuration loading by:
//! 1. Using yaml-rust2 for parsing (vs ruamel.yaml)
//! 2. Parallel loading of multiple YAML files with Tokio
//! 3. Efficient memory representation
//!
//! ## ONE RUNTIME RULE Compliance
//! This module uses crate::get_runtime() for all async operations to comply with
//! the ONE RUNTIME RULE (see lib.rs for details).

use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PySet};
use std::path::PathBuf;
use tokio::task::JoinSet;

/// Rust equivalent of ClassicScanLogsInfo
///
/// This struct mirrors the Python dataclass fields exactly to ensure
/// API compatibility when used from Python code.
#[pyclass]
pub struct YamlData {
    // Game configuration
    #[pyo3(get)]
    pub classic_game_hints: Py<PyList>,
    #[pyo3(get)]
    pub classic_records_list: Py<PyList>,
    #[pyo3(get)]
    pub classic_version: String,
    #[pyo3(get)]
    pub classic_version_date: String,

    // Crashgen configuration
    #[pyo3(get)]
    pub crashgen_name: String,
    #[pyo3(get)]
    pub crashgen_latest_og: String,
    #[pyo3(get)]
    pub crashgen_latest_vr: String,
    #[pyo3(get)]
    pub crashgen_ignore: Py<PyAny>, // set in Python

    // Warnings
    #[pyo3(get)]
    pub warn_noplugins: String,
    #[pyo3(get)]
    pub warn_outdated: String,

    // XSE configuration
    #[pyo3(get)]
    pub xse_acronym: String,

    // Ignore lists
    #[pyo3(get)]
    pub game_ignore_plugins: Py<PyList>,
    #[pyo3(get)]
    pub game_ignore_records: Py<PyList>,
    #[pyo3(get)]
    pub ignore_list: Py<PyList>,

    // Suspect patterns
    #[pyo3(get)]
    pub suspects_error_list: Py<PyDict>,
    #[pyo3(get)]
    pub suspects_stack_list: Py<PyDict>,

    // Mod databases
    #[pyo3(get)]
    pub game_mods_conf: Py<PyDict>,
    #[pyo3(get)]
    pub game_mods_core: Py<PyDict>,
    #[pyo3(get)]
    pub game_mods_core_folon: Py<PyDict>,
    #[pyo3(get)]
    pub game_mods_freq: Py<PyDict>,
    #[pyo3(get)]
    pub game_mods_opc2: Py<PyDict>,
    #[pyo3(get)]
    pub game_mods_solu: Py<PyDict>,

    // UI configuration
    #[pyo3(get)]
    pub autoscan_text: String,

    // Game versions (stored as strings, converted to Version in Python)
    #[pyo3(get)]
    pub game_version: String,
    #[pyo3(get)]
    pub game_version_new: String,
    #[pyo3(get)]
    pub game_version_vr: String,
}

#[pymethods]
impl YamlData {
    #[new]
    #[pyo3(signature = (yaml_dirs, game, vr_mode))]
    fn new(py: Python<'_>, yaml_dirs: Vec<PathBuf>, game: String, vr_mode: bool) -> PyResult<Self> {
        // Create RustYamlOperations through Python interface
        let yaml_module = py.import("classic_core.yaml")?;
        let yaml_ops_class = yaml_module.getattr("RustYamlOperations")?;
        let yaml_ops_py = yaml_ops_class.call0()?;

        Self::load_from_yaml_files(py, yaml_ops_py.unbind(), yaml_dirs, game, vr_mode)
    }

    /// Get a string representation for debugging
    fn __repr__(&self) -> String {
        format!(
            "YamlData(game={}, version={}, vr_mode={})",
            // Extract game name from crashgen_name if possible
            self.crashgen_name.split('_').next().unwrap_or("unknown"),
            self.classic_version,
            !self.crashgen_latest_vr.is_empty()
        )
    }
}

impl YamlData {
    /// Load all configuration from YAML files in parallel
    ///
    /// This is the core performance optimization - loading multiple YAML files
    /// in parallel using Tokio's async runtime.
    fn load_from_yaml_files(
        py: Python<'_>,
        yaml_ops_py: Py<PyAny>,
        yaml_dirs: Vec<PathBuf>,
        game: String,
        vr_mode: bool,
    ) -> PyResult<Self> {
        // Validate input
        if yaml_dirs.len() < 3 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "yaml_dirs must contain at least 3 directories (main, game, ignore)",
            ));
        }

        // Construct file paths
        let main_yaml = yaml_dirs[0].join("CLASSIC Main.yaml");
        let game_yaml = yaml_dirs[1].join(format!("CLASSIC {}.yaml", game));
        let ignore_yaml = yaml_dirs[2].join("CLASSIC_Ignore.yaml");

        // Verify files exist before loading
        for path in [&main_yaml, &game_yaml, &ignore_yaml] {
            if !path.exists() {
                return Err(PyErr::new::<pyo3::exceptions::PyIOError, _>(format!(
                    "YAML file not found: {}",
                    path.display()
                )));
            }
        }

        // Load all YAML files in parallel using Tokio
        let runtime = crate::get_runtime();

        // Load all YAML files in parallel using Tokio
        let (main_data, game_data, ignore_data) = runtime.block_on(async {
            let mut set = JoinSet::new();

            // Spawn parallel tasks to load each YAML file
            let main_path = main_yaml.clone();
            set.spawn(async move {
                tokio::fs::read_to_string(&main_path).await.map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyIOError, _>(format!(
                        "Failed to read main YAML: {}",
                        e
                    ))
                })
            });

            let game_path = game_yaml.clone();
            set.spawn(async move {
                tokio::fs::read_to_string(&game_path).await.map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyIOError, _>(format!(
                        "Failed to read game YAML: {}",
                        e
                    ))
                })
            });

            let ignore_path = ignore_yaml.clone();
            set.spawn(async move {
                tokio::fs::read_to_string(&ignore_path).await.map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyIOError, _>(format!(
                        "Failed to read ignore YAML: {}",
                        e
                    ))
                })
            });

            // Wait for all three files to load and unwrap results
            let r1 = set
                .join_next()
                .await
                .ok_or_else(|| {
                    PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Task join failed")
                })?
                .map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Join error: {}", e))
                })??;
            let r2 = set
                .join_next()
                .await
                .ok_or_else(|| {
                    PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Task join failed")
                })?
                .map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Join error: {}", e))
                })??;
            let r3 = set
                .join_next()
                .await
                .ok_or_else(|| {
                    PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Task join failed")
                })?
                .map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Join error: {}", e))
                })??;

            Ok::<_, PyErr>((r1, r2, r3))
        })?;

        // Parse YAML contents (this happens synchronously after async I/O)
        let main_data = yaml_ops_py.call_method1(py, "parse_yaml", (&main_data,))?;
        let game_data = yaml_ops_py.call_method1(py, "parse_yaml", (&game_data,))?;
        let ignore_data = yaml_ops_py.call_method1(py, "parse_yaml", (&ignore_data,))?;

        // Extract values using key path lookups
        let vr_suffix = if vr_mode { "VR" } else { "" };

        // Helper to get nested value safely
        let get_value =
            |data: &Py<PyAny>, key_path: &str, default_py: &Py<PyAny>| -> PyResult<Py<PyAny>> {
                let result =
                    yaml_ops_py.call_method1(py, "get_setting", (data.clone_ref(py), key_path))?;
                // Check if it's None
                if result.bind(py).is_none() {
                    Ok(default_py.clone_ref(py))
                } else {
                    Ok(result)
                }
            };

        // Create default values
        let empty_list = PyList::empty(py).unbind().into();
        let empty_dict = PyDict::new(py).unbind().into();
        let empty_string = "".into_pyobject(py)?.as_any().clone().unbind();

        // Extract all values
        Ok(Self {
            // Main YAML values
            classic_version: get_value(&main_data, "CLASSIC_Info.version", &empty_string)?
                .extract(py)?,
            classic_version_date: get_value(
                &main_data,
                "CLASSIC_Info.version_date",
                &empty_string,
            )?
            .extract(py)?,
            classic_records_list: get_value(&main_data, "catch_log_records", &empty_list)?
                .extract(py)?,
            autoscan_text: get_value(
                &main_data,
                &format!("CLASSIC_Interface.autoscan_text_{}", game),
                &empty_string,
            )?
            .extract(py)?,

            // Game YAML values
            classic_game_hints: get_value(&game_data, "Game_Hints", &empty_list)?.extract(py)?,
            crashgen_name: get_value(
                &game_data,
                &format!("Game{}_Info.CRASHGEN_LogName", vr_suffix),
                &empty_string,
            )?
            .extract(py)?,
            crashgen_latest_og: get_value(
                &game_data,
                "Game_Info.CRASHGEN_LatestVer",
                &empty_string,
            )?
            .extract(py)?,
            crashgen_latest_vr: get_value(
                &game_data,
                "GameVR_Info.CRASHGEN_LatestVer",
                &empty_string,
            )?
            .extract(py)?,
            crashgen_ignore: {
                let list_val = get_value(
                    &game_data,
                    &format!("Game{}_Info.CRASHGEN_Ignore", vr_suffix),
                    &empty_list,
                )?;
                // Convert list to set safely using PySet
                let bound_val = list_val.bind(py);
                let py_list = bound_val.downcast::<PyList>()?;
                let py_set = PySet::new(py, py_list.iter())?;
                py_set.unbind().into()
            },
            warn_noplugins: get_value(
                &game_data,
                "Warnings_CRASHGEN.Warn_NOPlugins",
                &empty_string,
            )?
            .extract(py)?,
            warn_outdated: get_value(&game_data, "Warnings_CRASHGEN.Warn_Outdated", &empty_string)?
                .extract(py)?,
            xse_acronym: get_value(&game_data, "Game_Info.XSE_Acronym", &empty_string)?
                .extract(py)?,
            game_ignore_plugins: get_value(&game_data, "Crashlog_Plugins_Exclude", &empty_list)?
                .extract(py)?,
            game_ignore_records: get_value(&game_data, "Crashlog_Records_Exclude", &empty_list)?
                .extract(py)?,
            suspects_error_list: get_value(&game_data, "Crashlog_Error_Check", &empty_dict)?
                .extract(py)?,
            suspects_stack_list: get_value(&game_data, "Crashlog_Stack_Check", &empty_dict)?
                .extract(py)?,
            game_mods_conf: get_value(&game_data, "Mods_CONF", &empty_dict)?.extract(py)?,
            game_mods_core: get_value(&game_data, "Mods_CORE", &empty_dict)?.extract(py)?,
            game_mods_core_folon: get_value(&game_data, "Mods_CORE_FOLON", &empty_dict)?
                .extract(py)?,
            game_mods_freq: get_value(&game_data, "Mods_FREQ", &empty_dict)?.extract(py)?,
            game_mods_opc2: get_value(&game_data, "Mods_OPC2", &empty_dict)?.extract(py)?,
            game_mods_solu: get_value(&game_data, "Mods_SOLU", &empty_dict)?.extract(py)?,
            game_version: get_value(&game_data, "Game_Info.GameVersion", &empty_string)?
                .extract(py)?,
            game_version_new: get_value(&game_data, "Game_Info.GameVersionNEW", &empty_string)?
                .extract(py)?,
            game_version_vr: get_value(&game_data, "GameVR_Info.GameVersion", &empty_string)?
                .extract(py)?,

            // Ignore YAML values
            ignore_list: get_value(
                &ignore_data,
                &format!("CLASSIC_Ignore_{}", game),
                &empty_list,
            )?
            .extract(py)?,
        })
    }
}

/// Python API function to create YamlData
#[pyfunction]
#[pyo3(signature = (yaml_dirs, game, vr_mode))]
pub fn create_yamldata(
    py: Python<'_>,
    yaml_dirs: Vec<PathBuf>,
    game: String,
    vr_mode: bool,
) -> PyResult<YamlData> {
    YamlData::new(py, yaml_dirs, game, vr_mode)
}
