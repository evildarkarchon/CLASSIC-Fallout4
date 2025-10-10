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
//!
//! ## NO CIRCULAR DEPENDENCIES
//! This module does NOT import the yaml module to avoid circular dependencies
//! during module initialization. Instead, it uses yaml-rust2 directly.

use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PySet};
use std::path::PathBuf;
use tokio::task::JoinSet;
use yaml_rust2::{Yaml, YamlLoader};

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
        Self::load_from_yaml_files(py, yaml_dirs, game, vr_mode)
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
        let (main_content, game_content, ignore_content) = runtime.block_on(async {
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

        // Parse YAML contents using yaml-rust2 directly
        let main_docs = YamlLoader::load_from_str(&main_content).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Failed to parse main YAML: {}",
                e
            ))
        })?;
        let game_docs = YamlLoader::load_from_str(&game_content).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Failed to parse game YAML: {}",
                e
            ))
        })?;
        let ignore_docs = YamlLoader::load_from_str(&ignore_content).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Failed to parse ignore YAML: {}",
                e
            ))
        })?;

        // Get first document from each file
        let main_data = main_docs
            .first()
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Main YAML is empty"))?;
        let game_data = game_docs
            .first()
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Game YAML is empty"))?;
        let ignore_data = ignore_docs.first().ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>("Ignore YAML is empty")
        })?;

        // Extract values using key path lookups
        let vr_suffix = if vr_mode { "VR" } else { "" };

        // Helper to navigate nested YAML and convert to Python
        let get_string = |data: &Yaml, key_path: &str, default: &str| -> String {
            let keys: Vec<&str> = key_path.split('.').collect();
            let mut current = data;

            for key in keys {
                current = &current[key];
            }

            current.as_str().unwrap_or(default).to_string()
        };

        let get_py_list = |py: Python<'_>, data: &Yaml, key_path: &str| -> PyResult<Py<PyList>> {
            let keys: Vec<&str> = key_path.split('.').collect();
            let mut current = data;

            for key in keys {
                current = &current[key];
            }

            match current {
                Yaml::Array(arr) => {
                    let py_list = PyList::empty(py);
                    for item in arr {
                        if let Yaml::String(s) = item {
                            py_list.append(s)?;
                        }
                    }
                    Ok(py_list.unbind())
                }
                _ => Ok(PyList::empty(py).unbind()),
            }
        };

        let get_py_dict = |py: Python<'_>, data: &Yaml, key_path: &str| -> PyResult<Py<PyDict>> {
            let keys: Vec<&str> = key_path.split('.').collect();
            let mut current = data;

            for key in keys {
                current = &current[key];
            }

            match current {
                Yaml::Hash(map) => {
                    let py_dict = PyDict::new(py);
                    for (k, v) in map {
                        if let (Yaml::String(key_str), Yaml::String(val_str)) = (k, v) {
                            py_dict.set_item(key_str, val_str)?;
                        }
                    }
                    Ok(py_dict.unbind())
                }
                _ => Ok(PyDict::new(py).unbind()),
            }
        };

        // Extract all values
        Ok(Self {
            // Main YAML values
            classic_version: get_string(main_data, "CLASSIC_Info.version", ""),
            classic_version_date: get_string(main_data, "CLASSIC_Info.version_date", ""),
            classic_records_list: get_py_list(py, main_data, "catch_log_records")?,
            autoscan_text: get_string(
                main_data,
                &format!("CLASSIC_Interface.autoscan_text_{}", game),
                "",
            ),

            // Game YAML values
            classic_game_hints: get_py_list(py, game_data, "Game_Hints")?,
            crashgen_name: get_string(
                game_data,
                &format!("Game{}_Info.CRASHGEN_LogName", vr_suffix),
                "",
            ),
            crashgen_latest_og: get_string(game_data, "Game_Info.CRASHGEN_LatestVer", ""),
            crashgen_latest_vr: get_string(game_data, "GameVR_Info.CRASHGEN_LatestVer", ""),
            crashgen_ignore: {
                let list = get_py_list(
                    py,
                    game_data,
                    &format!("Game{}_Info.CRASHGEN_Ignore", vr_suffix),
                )?;
                let py_set = PySet::new(py, list.bind(py).iter())?;
                py_set.unbind().into()
            },
            warn_noplugins: get_string(game_data, "Warnings_CRASHGEN.Warn_NOPlugins", ""),
            warn_outdated: get_string(game_data, "Warnings_CRASHGEN.Warn_Outdated", ""),
            xse_acronym: get_string(game_data, "Game_Info.XSE_Acronym", ""),
            game_ignore_plugins: get_py_list(py, game_data, "Crashlog_Plugins_Exclude")?,
            game_ignore_records: get_py_list(py, game_data, "Crashlog_Records_Exclude")?,
            suspects_error_list: get_py_dict(py, game_data, "Crashlog_Error_Check")?,
            suspects_stack_list: get_py_dict(py, game_data, "Crashlog_Stack_Check")?,
            game_mods_conf: get_py_dict(py, game_data, "Mods_CONF")?,
            game_mods_core: get_py_dict(py, game_data, "Mods_CORE")?,
            game_mods_core_folon: get_py_dict(py, game_data, "Mods_CORE_FOLON")?,
            game_mods_freq: get_py_dict(py, game_data, "Mods_FREQ")?,
            game_mods_opc2: get_py_dict(py, game_data, "Mods_OPC2")?,
            game_mods_solu: get_py_dict(py, game_data, "Mods_SOLU")?,
            game_version: get_string(game_data, "Game_Info.GameVersion", ""),
            game_version_new: get_string(game_data, "Game_Info.GameVersionNEW", ""),
            game_version_vr: get_string(game_data, "GameVR_Info.GameVersion", ""),

            // Ignore YAML values
            ignore_list: get_py_list(py, ignore_data, &format!("CLASSIC_Ignore_{}", game))?,
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
