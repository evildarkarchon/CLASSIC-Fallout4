//! Python bindings for the yaml-update-delivery orchestrator.
//!
//! Mirrors `classic_update_core::yaml_update::{check_yaml_update,
//! apply_yaml_update, rollback_yaml_update}` as three synchronous PyO3
//! functions plus their supporting DTO pyclasses. The functions block on
//! the shared Tokio runtime internally, so Python callers do not need to
//! use `asyncio`.
//!
//! Synchronous (blocking) was chosen over `async def` here because:
//! - The existing GUI and TUI wrappers currently call into the update
//!   subsystem synchronously via `get_runtime().block_on()`.
//! - Exposing both sync and async surfaces would double the binding
//!   footprint without adding value for the Python consumers.
//! - The pytest smoke test (Section 10.3) only needs the `Update Check:
//!   false` short-circuit, which is trivially synchronous.

use classic_settings_core::{SchemaCompat, SchemaVersion};
use classic_update_core as core;
use pyo3::prelude::*;
use std::path::PathBuf;

/// Build a core `UpdateCheckConfig` from the Python-facing enabled flag and
/// an optional explicit bundled-YAML root.
///
/// When the Python host runs inside `python.exe`, the core fallback that
/// probes `std::env::current_exe()` for `CLASSIC Data/databases/` cannot
/// find the install-tree copy — `current_exe()` points at the interpreter.
/// Passing the package-local directory here is the only way a clean Python
/// install whose bundled bytes already match the manifest can be classified
/// as `upToDate` instead of false-positive `updateAvailable`. See the
/// `bundled_yaml_dir` doc on [`core::UpdateCheckConfig`] for the full
/// failure-mode rationale.
fn build_config(enabled: bool, bundled_yaml_dir: Option<&str>) -> core::UpdateCheckConfig {
    let mut cfg = if enabled {
        core::UpdateCheckConfig::enabled()
    } else {
        core::UpdateCheckConfig::disabled()
    };
    if let Some(dir) = bundled_yaml_dir {
        if !dir.is_empty() {
            cfg = cfg.with_bundled_yaml_dir(PathBuf::from(dir));
        }
    }
    cfg
}

/// Tag string for `PyYamlUpdateStatus.tag`. Parallels the NAPI binding's
/// constants so Python and JS consumers see identical discriminator strings.
const TAG_DISABLED: &str = "disabled";
const TAG_UPDATE_AVAILABLE: &str = "updateAvailable";
const TAG_UP_TO_DATE: &str = "upToDate";
const TAG_UNKNOWN: &str = "unknown";

fn runtime_error<T: std::fmt::Display>(e: T) -> PyErr {
    pyo3::exceptions::PyRuntimeError::new_err(format!("{e}"))
}

/// Per-file schema entry passed into `check_yaml_update` /
/// `apply_yaml_update`. Equivalent to `JsYamlClientSchemaEntry` in the
/// Node binding.
#[pyclass(name = "YamlClientSchemaEntry", from_py_object)]
#[derive(Clone)]
pub struct PyYamlClientSchemaEntry {
    #[pyo3(get, set)]
    pub name: String,
    #[pyo3(get, set)]
    pub accepted_major: u32,
    #[pyo3(get, set)]
    pub accepted_minimum_minor: u32,
    #[pyo3(get, set)]
    pub has_installed: bool,
    #[pyo3(get, set)]
    pub installed_major: u32,
    #[pyo3(get, set)]
    pub installed_minor: u32,
}

#[pymethods]
impl PyYamlClientSchemaEntry {
    #[new]
    #[pyo3(signature = (
        name,
        accepted_major,
        accepted_minimum_minor,
        has_installed = false,
        installed_major = 0,
        installed_minor = 0,
    ))]
    fn new(
        name: String,
        accepted_major: u32,
        accepted_minimum_minor: u32,
        has_installed: bool,
        installed_major: u32,
        installed_minor: u32,
    ) -> Self {
        Self {
            name,
            accepted_major,
            accepted_minimum_minor,
            has_installed,
            installed_major,
            installed_minor,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "YamlClientSchemaEntry(name={:?}, accepted={}.{}, installed={})",
            self.name,
            self.accepted_major,
            self.accepted_minimum_minor,
            if self.has_installed {
                format!("{}.{}", self.installed_major, self.installed_minor)
            } else {
                "None".to_string()
            },
        )
    }
}

/// One file inside `PyYamlUpdateStatus` or `PyYamlUpdateReport`.
#[pyclass(name = "YamlUpdateFile", from_py_object)]
#[derive(Clone)]
pub struct PyYamlUpdateFile {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub schema_version: String,
    #[pyo3(get)]
    pub sha256: String,
    #[pyo3(get)]
    pub size_bytes: u64,
    #[pyo3(get)]
    pub download_url: String,
}

/// One rejection inside `PyYamlUpdateStatus.incompatible_files`.
#[pyclass(name = "YamlRejectedFile", from_py_object)]
#[derive(Clone)]
pub struct PyYamlRejectedFile {
    #[pyo3(get)]
    pub file: PyYamlUpdateFile,
    #[pyo3(get)]
    pub reason: String,
}

/// Discriminated status DTO returned by `check_yaml_update`.
#[pyclass(name = "YamlUpdateStatus", from_py_object)]
#[derive(Clone)]
pub struct PyYamlUpdateStatus {
    #[pyo3(get)]
    pub tag: String,
    #[pyo3(get)]
    pub release_tag: String,
    #[pyo3(get)]
    pub published_at: String,
    #[pyo3(get)]
    pub compatible_files: Vec<PyYamlUpdateFile>,
    #[pyo3(get)]
    pub incompatible_files: Vec<PyYamlRejectedFile>,
    #[pyo3(get)]
    pub unknown_reason: String,
}

/// Per-file install outcome inside `PyYamlUpdateReport`.
#[pyclass(name = "YamlUpdateFileOutcome", from_py_object)]
#[derive(Clone)]
pub struct PyYamlUpdateFileOutcome {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub installed: bool,
    #[pyo3(get)]
    pub schema_version: String,
    #[pyo3(get)]
    pub created_prev: bool,
    #[pyo3(get)]
    pub failure_reason: String,
}

/// Aggregate report returned by `apply_yaml_update`.
#[pyclass(name = "YamlUpdateReport", from_py_object)]
#[derive(Clone)]
pub struct PyYamlUpdateReport {
    #[pyo3(get)]
    pub installed: Vec<PyYamlUpdateFileOutcome>,
    #[pyo3(get)]
    pub failed: Vec<PyYamlUpdateFileOutcome>,
}

/// Result of `rollback_yaml_update`.
#[pyclass(name = "YamlRollbackOutcome", from_py_object)]
#[derive(Clone)]
pub struct PyYamlRollbackOutcome {
    #[pyo3(get)]
    pub rolled_back: bool,
    #[pyo3(get)]
    pub file_name: String,
}

fn entries_to_core(entries: &[PyYamlClientSchemaEntry]) -> core::ClientSchemaSet {
    let mut set = core::ClientSchemaSet::new();
    for entry in entries {
        let accepted = SchemaCompat::new(entry.accepted_major, entry.accepted_minimum_minor);
        let installed = if entry.has_installed {
            Some(SchemaVersion::new(
                entry.installed_major,
                entry.installed_minor,
            ))
        } else {
            None
        };
        set.insert(entry.name.clone(), accepted, installed);
    }
    set
}

fn core_file_to_py(f: &core::YamlManifestFile) -> PyYamlUpdateFile {
    PyYamlUpdateFile {
        name: f.name.clone(),
        schema_version: f.schema_version.clone(),
        sha256: f.sha256.clone(),
        size_bytes: f.size_bytes,
        download_url: f.download_url.clone(),
    }
}

fn core_status_to_py(status: core::YamlUpdateStatus) -> PyYamlUpdateStatus {
    let mut dto = PyYamlUpdateStatus {
        tag: TAG_DISABLED.to_string(),
        release_tag: String::new(),
        published_at: String::new(),
        compatible_files: Vec::new(),
        incompatible_files: Vec::new(),
        unknown_reason: String::new(),
    };
    match status {
        core::YamlUpdateStatus::Disabled => dto.tag = TAG_DISABLED.into(),
        core::YamlUpdateStatus::UpToDate {
            manifest,
            incompatible_files,
        } => {
            dto.tag = TAG_UP_TO_DATE.into();
            dto.release_tag = manifest.release_tag;
            dto.published_at = manifest.published_at;
            // Surface rejection diagnostics through the same DTO field used
            // by UpdateAvailable so Python consumers see a uniform shape.
            dto.incompatible_files = incompatible_files
                .into_iter()
                .map(|r| PyYamlRejectedFile {
                    file: core_file_to_py(&r.file),
                    reason: r.reason,
                })
                .collect();
        }
        core::YamlUpdateStatus::UpdateAvailable {
            manifest,
            compatible_files,
            incompatible_files,
        } => {
            dto.tag = TAG_UPDATE_AVAILABLE.into();
            dto.release_tag = manifest.release_tag;
            dto.published_at = manifest.published_at;
            dto.compatible_files = compatible_files.iter().map(core_file_to_py).collect();
            dto.incompatible_files = incompatible_files
                .into_iter()
                .map(|r| PyYamlRejectedFile {
                    file: core_file_to_py(&r.file),
                    reason: r.reason,
                })
                .collect();
        }
        core::YamlUpdateStatus::Unknown { reason } => {
            dto.tag = TAG_UNKNOWN.into();
            dto.unknown_reason = reason;
        }
    }
    dto
}

fn core_outcome_to_py(outcome: &core::FileInstallOutcome) -> PyYamlUpdateFileOutcome {
    match outcome {
        core::FileInstallOutcome::Installed {
            name,
            schema_version,
            created_prev,
        } => PyYamlUpdateFileOutcome {
            name: name.clone(),
            installed: true,
            schema_version: schema_version.clone(),
            created_prev: *created_prev,
            failure_reason: String::new(),
        },
        core::FileInstallOutcome::Failed { name, reason } => PyYamlUpdateFileOutcome {
            name: name.clone(),
            installed: false,
            schema_version: String::new(),
            created_prev: false,
            failure_reason: reason.clone(),
        },
    }
}

/// Check for a YAML data update.
///
/// Synchronous wrapper around `classic_update_core::check_yaml_update`.
/// Runs the Pages-first manifest fetch + classification on the shared
/// Tokio runtime and returns a `YamlUpdateStatus`. When `enabled` is
/// `False`, short-circuits with `YamlUpdateStatus(tag="disabled")`
/// without any HTTP call.
///
/// Args:
///     pages_url: Absolute HTTPS URL of the Pages manifest.
///     tag_prefix: Release-tag prefix for the anonymous API fallback
///         (e.g. `"yaml-data-v"`).
///     entries: Per-file schema entries (each with accepted compat range
///         and optional installed version).
///     enabled: When `False`, return `tag="disabled"` without HTTP.
///
/// Raises:
///     RuntimeError: on network failures the fallback cannot recover from.
#[pyfunction]
#[pyo3(signature = (pages_url, tag_prefix, entries, enabled, bundled_yaml_dir=None))]
fn check_yaml_update(
    pages_url: &str,
    tag_prefix: &str,
    entries: Vec<PyYamlClientSchemaEntry>,
    enabled: bool,
    bundled_yaml_dir: Option<&str>,
) -> PyResult<PyYamlUpdateStatus> {
    let client =
        core::GithubClient::new("evildarkarchon", "CLASSIC-Fallout4").map_err(runtime_error)?;
    let set = entries_to_core(&entries);
    let config = build_config(enabled, bundled_yaml_dir);

    let status = classic_shared_core::get_runtime()
        .block_on(core::check_yaml_update(
            &client, pages_url, tag_prefix, &set, config,
        ))
        .map_err(runtime_error)?;
    Ok(core_status_to_py(status))
}

/// Fetch + download + atomically install the files the user approved at
/// check time.
///
/// This is the reviewed-decision form of apply. It takes three decision
/// arguments in addition to the check inputs:
///
/// - ``enabled``: mirrors the ``Update Check`` settings toggle. Pass
///   ``False`` to refuse the apply without issuing any HTTP — the user's
///   opt-out survives between check and apply.
/// - ``approved_release_tag``: the ``release_tag`` field of the
///   ``YamlUpdateStatus`` the user confirmed.
/// - ``approved_file_names``: the ``name`` of each entry in that status's
///   ``compatible_files``.
///
/// When the live manifest has rotated to a different tag in the meantime,
/// the call raises ``RuntimeError('approved release ... does not match
/// current manifest release ...; re-check required')`` instead of
/// silently installing the newer release.
///
/// Args:
///     pages_url: Absolute HTTPS URL of the Pages manifest.
///     tag_prefix: Release-tag prefix for the anonymous API fallback.
///     entries: Per-file schema entries.
///     enabled: Honors ``Update Check: false`` end-to-end.
///     approved_release_tag: Release tag the user reviewed.
///     approved_file_names: File names the user reviewed.
///
/// Raises:
///     RuntimeError: when the whole batch fails, when the update check is
///         disabled, or when the approved decision is stale.
#[pyfunction]
#[pyo3(signature = (
    pages_url,
    tag_prefix,
    entries,
    enabled,
    approved_release_tag,
    approved_file_names,
    bundled_yaml_dir=None,
))]
fn apply_yaml_update(
    pages_url: &str,
    tag_prefix: &str,
    entries: Vec<PyYamlClientSchemaEntry>,
    enabled: bool,
    approved_release_tag: String,
    approved_file_names: Vec<String>,
    bundled_yaml_dir: Option<&str>,
) -> PyResult<PyYamlUpdateReport> {
    let client =
        core::GithubClient::new("evildarkarchon", "CLASSIC-Fallout4").map_err(runtime_error)?;
    let set = entries_to_core(&entries);
    let config = build_config(enabled, bundled_yaml_dir);
    let approved = core::ApprovedUpdate {
        release_tag: approved_release_tag,
        file_names: approved_file_names,
    };
    let report = classic_shared_core::get_runtime()
        .block_on(core::apply_yaml_update_with_decision(
            &client, pages_url, tag_prefix, &set, config, &approved,
        ))
        .map_err(runtime_error)?;
    Ok(PyYamlUpdateReport {
        installed: report.installed.iter().map(core_outcome_to_py).collect(),
        failed: report.failed.iter().map(core_outcome_to_py).collect(),
    })
}

/// Swap the cached YAML file with its `.prev` sibling (if any).
///
/// Returns a `YamlRollbackOutcome` with `rolled_back=False` when the file
/// has no `.prev` (steady-state after a fresh install). Not an error.
///
/// Args:
///     file_name: Canonical file name (e.g. `"CLASSIC Main.yaml"`).
///
/// Raises:
///     RuntimeError: when the yaml-cache directory cannot be resolved.
#[pyfunction]
fn rollback_yaml_update(file_name: &str) -> PyResult<PyYamlRollbackOutcome> {
    let outcome = core::rollback_yaml_update(file_name).map_err(runtime_error)?;
    Ok(match outcome {
        core::RollbackOutcome::RolledBack { file_name } => PyYamlRollbackOutcome {
            rolled_back: true,
            file_name,
        },
        core::RollbackOutcome::NoPreviousVersion { file_name } => PyYamlRollbackOutcome {
            rolled_back: false,
            file_name,
        },
    })
}

/// Register the yaml-update-delivery surface on the Python module.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyYamlClientSchemaEntry>()?;
    m.add_class::<PyYamlUpdateFile>()?;
    m.add_class::<PyYamlRejectedFile>()?;
    m.add_class::<PyYamlUpdateStatus>()?;
    m.add_class::<PyYamlUpdateFileOutcome>()?;
    m.add_class::<PyYamlUpdateReport>()?;
    m.add_class::<PyYamlRollbackOutcome>()?;
    m.add_function(wrap_pyfunction!(check_yaml_update, m)?)?;
    m.add_function(wrap_pyfunction!(apply_yaml_update, m)?)?;
    m.add_function(wrap_pyfunction!(rollback_yaml_update, m)?)?;
    Ok(())
}
