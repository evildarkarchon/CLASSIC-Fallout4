//! Python binding for the schema-gated `CLASSIC Main.yaml` version reader.
//!
//! Mirrors `classic::config::load_main_yaml_version` on the C++ bridge and
//! `classicNode.loadMainYamlVersion` on the Node binding. Exists as its own
//! module (instead of an inline `#[pyfunction]` in `lib.rs`) because the
//! variant-keyed exception hierarchy would otherwise dilute the module's
//! general-purpose `RustConfig*` exception surface — consumers need a
//! distinct discriminator per `MainYamlVersionError` variant so the
//! "schema_version incompatible" recovery advice is not conflated with
//! "CLASSIC_Info.version missing".
//!
//! # Error contract
//!
//! Per `docs/api/error-contract.md`, the Python surface raises typed
//! exceptions. The hierarchy mirrors the notification binding precedent:
//!
//! - `ClassicMainYamlVersionError` (subclass of `Exception`) — common
//!   supertype for every failure of [`load_main_yaml_version`].
//! - Four variant-discriminating subclasses, one per
//!   `MainYamlVersionError` variant. Consumers that want to catch any
//!   failure use `except ClassicMainYamlVersionError`; callers that want
//!   to branch on the specific cause catch the subclass.

use classic_config_core as core;
use pyo3::create_exception;
use pyo3::exceptions::PyException;
use pyo3::prelude::*;

// ---------------------------------------------------------------------------
// Exception hierarchy
// ---------------------------------------------------------------------------

create_exception!(
    classic_config,
    ClassicMainYamlVersionError,
    PyException,
    "Base class for load_main_yaml_version failures."
);

create_exception!(
    classic_config,
    ClassicMainYamlVersionLoadError,
    ClassicMainYamlVersionError,
    "Raised when CLASSIC Main.yaml is missing, unparseable, or carries an \
     incompatible `schema_version` header (neither the cache nor bundled \
     copy satisfies MAIN_YAML)."
);

create_exception!(
    classic_config,
    ClassicMainYamlVersionKeyMissingError,
    ClassicMainYamlVersionError,
    "Raised when `CLASSIC_Info.version` (or the `CLASSIC_Info` section) \
     is absent from CLASSIC Main.yaml."
);

create_exception!(
    classic_config,
    ClassicMainYamlVersionEmptyError,
    ClassicMainYamlVersionError,
    "Raised when `CLASSIC_Info.version` is present but empty or \
     whitespace-only in CLASSIC Main.yaml."
);

create_exception!(
    classic_config,
    ClassicMainYamlVersionNotStringError,
    ClassicMainYamlVersionError,
    "Raised when `CLASSIC_Info.version` is present but not a YAML scalar \
     string (e.g. a sequence or mapping)."
);

create_exception!(
    classic_config,
    ClassicMainYamlVersionInvalidError,
    ClassicMainYamlVersionError,
    "Raised when `CLASSIC_Info.version` is a non-empty string but its \
     shape does not match the schema-2.0 contract: an optional leading \
     `v`/`V` followed by strict release SemVer (`MAJOR.MINOR.PATCH`, no \
     prerelease suffix, no build metadata, no legacy `CLASSIC ` \
     decoration)."
);

fn main_yaml_version_error_to_py(err: core::MainYamlVersionError) -> PyErr {
    let display = err.to_string();
    match err {
        core::MainYamlVersionError::Load(_) => ClassicMainYamlVersionLoadError::new_err(display),
        core::MainYamlVersionError::VersionKeyMissing { .. } => {
            ClassicMainYamlVersionKeyMissingError::new_err(display)
        }
        core::MainYamlVersionError::VersionEmpty { .. } => {
            ClassicMainYamlVersionEmptyError::new_err(display)
        }
        core::MainYamlVersionError::VersionNotString { .. } => {
            ClassicMainYamlVersionNotStringError::new_err(display)
        }
        core::MainYamlVersionError::VersionInvalid { .. } => {
            ClassicMainYamlVersionInvalidError::new_err(display)
        }
        // `MainYamlVersionError` is `#[non_exhaustive]`; a future core-
        // side variant surfaces as the base class until this module
        // grows a dedicated subclass for it.
        _ => ClassicMainYamlVersionError::new_err(display),
    }
}

/// Load ``CLASSIC Main.yaml`` schema-gated by :data:`client_schemas.MAIN_YAML`
/// and return the trimmed ``CLASSIC_Info.version`` value.
///
/// The schema gate rejects stale ``schema_version: 1.x`` files (which still
/// carry the legacy ``CLASSIC v…`` decoration) *before* the version reaches
/// downstream update-check classification — that's the whole reason this
/// reader exists. Callers MUST NOT fall back to a raw YAML read on error,
/// since doing so reintroduces the silent-degradation behavior the gate
/// prevents.
///
/// Args:
///     bundled_yaml_dir: Directory that contains ``CLASSIC Main.yaml``
///         (typically ``<install>/CLASSIC Data/databases``). Passing
///         ``None`` or an empty string keeps the default relative path
///         resolved against the process working directory. Python hosts
///         often run the interpreter from a directory unrelated to the
///         CLASSIC install, so prefer an explicit path in that case.
///
/// Returns:
///     str: the trimmed ``CLASSIC_Info.version`` value (never empty).
///
/// Raises:
///     ClassicMainYamlVersionLoadError: both the cache and bundled
///         copies failed to load or passed the schema gate — e.g. the
///         file is missing, unparseable, or its ``schema_version`` does
///         not satisfy ``MAIN_YAML``.
///     ClassicMainYamlVersionKeyMissingError: ``CLASSIC_Info.version``
///         (or the ``CLASSIC_Info`` section) is absent.
///     ClassicMainYamlVersionEmptyError: ``CLASSIC_Info.version`` is
///         present but empty or whitespace-only.
///     ClassicMainYamlVersionNotStringError: ``CLASSIC_Info.version`` is
///         present but not a YAML scalar string.
///     ClassicMainYamlVersionInvalidError: ``CLASSIC_Info.version`` is a
///         non-empty string but its shape does not match the schema-2.0
///         contract (legacy ``CLASSIC `` prefix, prerelease suffix,
///         build metadata, or non-semver garbage).
#[pyfunction]
#[pyo3(signature = (bundled_yaml_dir=None))]
fn load_main_yaml_version(bundled_yaml_dir: Option<String>) -> PyResult<String> {
    let bundled = bundled_yaml_dir.and_then(|s| {
        if s.is_empty() {
            None
        } else {
            Some(std::path::PathBuf::from(s))
        }
    });
    classic_shared_core::get_runtime()
        .block_on(async { core::load_main_yaml_version_with_bundled_dir(bundled.as_deref()).await })
        .map_err(main_yaml_version_error_to_py)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add(
        "ClassicMainYamlVersionError",
        m.py().get_type::<ClassicMainYamlVersionError>(),
    )?;
    m.add(
        "ClassicMainYamlVersionLoadError",
        m.py().get_type::<ClassicMainYamlVersionLoadError>(),
    )?;
    m.add(
        "ClassicMainYamlVersionKeyMissingError",
        m.py().get_type::<ClassicMainYamlVersionKeyMissingError>(),
    )?;
    m.add(
        "ClassicMainYamlVersionEmptyError",
        m.py().get_type::<ClassicMainYamlVersionEmptyError>(),
    )?;
    m.add(
        "ClassicMainYamlVersionNotStringError",
        m.py().get_type::<ClassicMainYamlVersionNotStringError>(),
    )?;
    m.add(
        "ClassicMainYamlVersionInvalidError",
        m.py().get_type::<ClassicMainYamlVersionInvalidError>(),
    )?;
    m.add_function(wrap_pyfunction!(load_main_yaml_version, m)?)?;
    Ok(())
}
