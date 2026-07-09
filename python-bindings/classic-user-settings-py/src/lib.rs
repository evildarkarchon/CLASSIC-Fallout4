//! Thin PyO3 adapter for the read-only User Settings open interface.

use classic_user_settings_core::{
    CommitEligibility, DocumentClassification, PreferenceOrigin, Revision, SourceLocation,
    UserSettings,
};
use pyo3::prelude::*;
use pyo3::types::PyBytes;

/// One structured diagnostic produced while opening User Settings.
#[pyclass(name = "UserSettingsDiagnostic", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyUserSettingsDiagnostic {
    /// Stable machine-readable diagnostic code.
    #[pyo3(get)]
    code: String,
    /// Human-readable diagnostic context.
    #[pyo3(get)]
    message: String,
}

/// Update-related User Settings consumed by update-check policy.
#[pyclass(name = "UpdatePreferences", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyUpdatePreferences {
    /// Whether first-party update checks are enabled after safe fallback policy.
    #[pyo3(get)]
    update_check: bool,
    /// Provenance token: `document`, `default`, or `degraded_fallback`.
    #[pyo3(get)]
    origin: String,
}

/// Read-only User Settings snapshot returned by `open_user_settings`.
#[pyclass(name = "UserSettingsSnapshot", frozen)]
pub struct PyUserSettingsSnapshot {
    /// Typed update preferences.
    #[pyo3(get)]
    update_preferences: PyUpdatePreferences,
    /// Selected source token: `canonical`, `legacy`, or `missing`.
    #[pyo3(get)]
    source_location: String,
    /// Selected source path, absent when the document is missing.
    #[pyo3(get)]
    source_path: Option<String>,
    /// Document format/schema classification token.
    #[pyo3(get)]
    classification: String,
    /// Parsed schema major, absent for missing or unversioned documents.
    #[pyo3(get)]
    schema_major: Option<u32>,
    /// Parsed schema minor, absent for missing or unversioned documents.
    #[pyo3(get)]
    schema_minor: Option<u32>,
    /// Content-derived revision token (`sha256:…`, `missing`, or `unavailable`).
    #[pyo3(get)]
    revision: String,
    /// Commit policy token: `eligible`, `requires_migration`, or `blocked_untrusted`.
    #[pyo3(get)]
    commit_eligibility: String,
    /// Structured diagnostics in discovery and validation order.
    #[pyo3(get)]
    diagnostics: Vec<PyUserSettingsDiagnostic>,
    /// Exact source bytes retained for later semantic preservation.
    original_content: Option<Vec<u8>>,
}

#[pymethods]
impl PyUserSettingsSnapshot {
    /// Returns the exact source bytes, or `None` when no bytes were available.
    #[getter]
    fn original_content<'py>(&self, py: Python<'py>) -> Option<Bound<'py, PyBytes>> {
        self.original_content
            .as_deref()
            .map(|content| PyBytes::new(py, content))
    }
}

/// Opens User Settings relative to an explicit CLASSIC root without changing
/// either supported source document.
#[pyfunction]
pub fn open_user_settings(classic_root: String) -> PyUserSettingsSnapshot {
    let settings = UserSettings::open(classic_root);
    let (schema_major, schema_minor) = settings
        .schema_version()
        .map_or((None, None), |(major, minor)| (Some(major), Some(minor)));

    PyUserSettingsSnapshot {
        update_preferences: PyUpdatePreferences {
            update_check: settings.update_preferences().update_check(),
            origin: preference_origin_token(settings.update_preferences().update_check_origin())
                .to_string(),
        },
        source_location: source_location_token(settings.source().location()).to_string(),
        source_path: settings
            .source()
            .path()
            .map(|path| path.display().to_string()),
        classification: classification_token(settings.classification()).to_string(),
        schema_major,
        schema_minor,
        revision: revision_token(settings.revision()),
        commit_eligibility: commit_eligibility_token(settings.commit_eligibility()).to_string(),
        diagnostics: settings
            .diagnostics()
            .iter()
            .map(|diagnostic| PyUserSettingsDiagnostic {
                code: diagnostic.code().to_string(),
                message: diagnostic.message().to_string(),
            })
            .collect(),
        original_content: settings.original_bytes().map(<[u8]>::to_vec),
    }
}

/// Returns the Python token for preference provenance.
fn preference_origin_token(origin: PreferenceOrigin) -> &'static str {
    match origin {
        PreferenceOrigin::Document => "document",
        PreferenceOrigin::Default => "default",
        PreferenceOrigin::DegradedFallback => "degraded_fallback",
    }
}

/// Returns the Python token for source location.
fn source_location_token(location: SourceLocation) -> &'static str {
    match location {
        SourceLocation::Canonical => "canonical",
        SourceLocation::Legacy => "legacy",
        SourceLocation::Missing => "missing",
    }
}

/// Returns the Python token for document classification.
fn classification_token(classification: DocumentClassification) -> &'static str {
    match classification {
        DocumentClassification::Current => "current",
        DocumentClassification::Unversioned => "unversioned",
        DocumentClassification::Older => "older",
        DocumentClassification::NewerCompatible => "newer_compatible",
        DocumentClassification::FutureMajor => "future_major",
        DocumentClassification::LegacyFlat => "legacy_flat",
        DocumentClassification::Malformed => "malformed",
        DocumentClassification::Missing => "missing",
    }
}

/// Returns the Python token for commit eligibility.
fn commit_eligibility_token(eligibility: CommitEligibility) -> &'static str {
    match eligibility {
        CommitEligibility::Eligible => "eligible",
        CommitEligibility::RequiresMigration => "requires_migration",
        CommitEligibility::BlockedUntrusted => "blocked_untrusted",
    }
}

/// Formats the content revision for Python consumers.
fn revision_token(revision: &Revision) -> String {
    match revision {
        Revision::Missing => "missing".to_string(),
        Revision::Unavailable => "unavailable".to_string(),
        Revision::ContentSha256(digest) => {
            let mut token = String::with_capacity("sha256:".len() + digest.len() * 2);
            token.push_str("sha256:");
            for byte in digest {
                use std::fmt::Write as _;
                write!(&mut token, "{byte:02x}").expect("writing to a String cannot fail");
            }
            token
        }
    }
}

/// Python module for typed, read-only User Settings access.
#[pymodule]
fn classic_user_settings(module: &Bound<'_, PyModule>) -> PyResult<()> {
    classic_shared::configure_python_stdio(module.py());
    module.add("__version__", env!("CARGO_PKG_VERSION"))?;
    module.add_class::<PyUserSettingsDiagnostic>()?;
    module.add_class::<PyUpdatePreferences>()?;
    module.add_class::<PyUserSettingsSnapshot>()?;
    module.add_function(wrap_pyfunction!(open_user_settings, module)?)?;
    Ok(())
}
