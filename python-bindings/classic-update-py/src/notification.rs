//! Python bindings for the app-notification check.
//!
//! Mirrors `classic_update_core::notification::{check_app_notification,
//! NotificationStatus, AppNotificationDisplay, Classification}` as a
//! single synchronous PyO3 function plus its supporting DTO pyclasses
//! and a typed exception hierarchy.
//!
//! Synchronous (blocking-on-shared-runtime) rather than `async def`
//! because the consumer call sites (CLI diagnostics, TUI startup check)
//! are themselves synchronous and the Node/CLI/TUI binding story on
//! this channel doesn't use asyncio.
//!
//! # Error contract
//!
//! Per `docs/api/error-contract.md`, the Python surface raises typed
//! exceptions rather than returning sentinel values. The hierarchy is:
//!
//! - `ClassicUpdateError` (subclass of `Exception`) — base for every
//!   `classic_update_core::UpdateError` that bubbles through the
//!   Python binding. Introduced by this change so future update-related
//!   bindings can extend it without rewriting their error shape.
//! - `ClassicNotificationError` (subclass of `ClassicUpdateError`) —
//!   common supertype for every notification-channel failure.
//! - Four variant-discriminating subclasses under
//!   `ClassicNotificationError`, one per `UpdateError::Notification*`
//!   variant. Shared manifest-validation variants (`ManifestInvalid` and
//!   `ManifestUnsupportedVersion`) also map to `ClassicNotificationError`
//!   when surfaced by this notification check, because they are
//!   notification-channel manifest failures. Consumers that want to catch
//!   any notification failure use
//!   `except ClassicNotificationError`; callers that want to
//!   discriminate (e.g., "show a retry button only on FetchFailed")
//!   catch the specific subclass.

use classic_shared::without_gil_block_on;
use classic_update_core as core;
use pyo3::create_exception;
use pyo3::exceptions::PyException;
use pyo3::prelude::*;
use std::future::Future;

#[cfg(test)]
#[path = "notification_tests.rs"]
mod tests;

// ---------------------------------------------------------------------------
// Exception hierarchy
// ---------------------------------------------------------------------------

create_exception!(
    classic_update,
    ClassicUpdateError,
    PyException,
    "Base class for all classic_update binding errors."
);

create_exception!(
    classic_update,
    ClassicNotificationError,
    ClassicUpdateError,
    "Base class for app-notification check failures."
);

create_exception!(
    classic_update,
    ClassicNotificationFetchFailed,
    ClassicNotificationError,
    "Raised when both Pages and Releases fallback channels failed."
);

create_exception!(
    classic_update,
    ClassicNotificationDecodeError,
    ClassicNotificationError,
    "Raised when the fetched manifest body is missing a required field or otherwise malformed."
);

create_exception!(
    classic_update,
    ClassicNotificationInstalledVersionParseError,
    ClassicNotificationError,
    "Raised when the caller-supplied installed_version fails semver parsing."
);

create_exception!(
    classic_update,
    ClassicNotificationCacheIoError,
    ClassicNotificationError,
    "Raised when the notification cache file (body or ETag) cannot be read, written, or created."
);

// ---------------------------------------------------------------------------
// Classification tags (string discriminator)
// ---------------------------------------------------------------------------

// Matches the NAPI binding's tag strings so Python and JS consumers see
// identical discriminator values on the notification channel.
const CLASSIFICATION_UP_TO_DATE: &str = "upToDate";
const CLASSIFICATION_UPDATE_AVAILABLE: &str = "updateAvailable";
const CLASSIFICATION_DEPRECATED_CLIENT: &str = "deprecatedClient";
const CLASSIFICATION_UNKNOWN: &str = "unknown";

fn classification_tag(c: core::Classification) -> &'static str {
    match c {
        core::Classification::UpToDate => CLASSIFICATION_UP_TO_DATE,
        core::Classification::UpdateAvailable => CLASSIFICATION_UPDATE_AVAILABLE,
        core::Classification::DeprecatedClient => CLASSIFICATION_DEPRECATED_CLIENT,
        core::Classification::Unknown => CLASSIFICATION_UNKNOWN,
    }
}

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

/// Optional display payload attached to a notification manifest.
#[pyclass(name = "AppNotificationDisplay", from_py_object)]
#[derive(Clone)]
pub struct PyAppNotificationDisplay {
    #[pyo3(get)]
    pub title: String,
    #[pyo3(get)]
    pub body: String,
    #[pyo3(get)]
    pub cta_url: Option<String>,
}

#[pymethods]
impl PyAppNotificationDisplay {
    fn __repr__(&self) -> String {
        format!(
            "AppNotificationDisplay(title={:?}, body={:?}, cta_url={:?})",
            self.title, self.body, self.cta_url,
        )
    }
}

/// Result of `check_app_notification`. `classification` is one of:
/// `"upToDate"`, `"updateAvailable"`, `"deprecatedClient"`, `"unknown"`.
/// Error outcomes are raised as `ClassicNotificationError` or one of its
/// subclasses, not as an additional classification value.
#[pyclass(name = "NotificationStatus", from_py_object)]
#[derive(Clone)]
pub struct PyNotificationStatus {
    #[pyo3(get)]
    pub classification: String,
    #[pyo3(get)]
    pub latest_version: String,
    #[pyo3(get)]
    pub published_at: String,
    #[pyo3(get)]
    pub min_supported_version: Option<String>,
    #[pyo3(get)]
    pub display: Option<PyAppNotificationDisplay>,
    /// When `classification == "unknown"`, a human-readable description
    /// of the installed-version parse failure. `None` otherwise.
    #[pyo3(get)]
    pub parse_error: Option<String>,
}

#[pymethods]
impl PyNotificationStatus {
    fn __repr__(&self) -> String {
        format!(
            "NotificationStatus(classification={:?}, latest_version={:?}, min_supported_version={:?})",
            self.classification, self.latest_version, self.min_supported_version,
        )
    }
}

fn core_status_to_py(status: core::NotificationStatus) -> PyNotificationStatus {
    PyNotificationStatus {
        classification: classification_tag(status.classification).to_string(),
        latest_version: status.latest_version,
        published_at: status.published_at,
        min_supported_version: status.min_supported_version,
        display: status.display.map(|d| PyAppNotificationDisplay {
            title: d.title,
            body: d.body,
            cta_url: d.cta_url,
        }),
        parse_error: status.parse_error,
    }
}

fn update_error_to_py(err: core::UpdateError) -> PyErr {
    let display = err.to_string();
    match err {
        core::UpdateError::NotificationFetchFailed { .. } => {
            ClassicNotificationFetchFailed::new_err(display)
        }
        core::UpdateError::NotificationDecode { .. } => {
            ClassicNotificationDecodeError::new_err(display)
        }
        core::UpdateError::NotificationInstalledVersionParse { .. } => {
            ClassicNotificationInstalledVersionParseError::new_err(display)
        }
        core::UpdateError::NotificationCacheIo { .. } => {
            ClassicNotificationCacheIoError::new_err(display)
        }
        core::UpdateError::ManifestInvalid { .. }
        | core::UpdateError::ManifestUnsupportedVersion { .. } => {
            ClassicNotificationError::new_err(display)
        }
        // Non-notification error variants still bubble through
        // ClassicUpdateError so a consumer catching the base class
        // receives every update-subsystem failure.
        _ => ClassicUpdateError::new_err(display),
    }
}

/// Run a notification future on the shared runtime without holding Python's GIL.
///
/// Notification checks can wait on network timeouts and API fallback calls, so
/// synchronous Python callers must not block unrelated Python threads while the
/// Rust future is pending.
fn block_on_notification_future<F, Fut, R>(py: Python<'_>, f: F) -> R
where
    F: FnOnce() -> Fut + Send,
    Fut: Future<Output = R>,
    R: Send,
{
    without_gil_block_on(py, f)
}

/// Check for a published CLASSIC binary-release notification.
///
/// Drives the Pages-first manifest fetch with ETag caching, falling back
/// to listing releases filtered by the ``app-notification-v*`` tag prefix.
/// On success returns a :class:`NotificationStatus`; on failure raises a
/// :class:`ClassicNotificationError` directly for shared manifest-validation
/// failures, or a subclass keyed to the underlying notification-channel
/// failure.
///
/// Args:
///     owner: GitHub org / repo slug (e.g. ``"evildarkarchon"``).
///     repo: Repository name (e.g. ``"CLASSIC-Fallout4"``).
///     installed_version: Caller's current client semver; a leading
///         ``v`` or ``V`` is tolerated.
///
/// Returns:
///     NotificationStatus: structured classification + display payload.
///
/// Raises:
///     ClassicNotificationFetchFailed: both channels failed.
///     ClassicNotificationDecodeError: manifest is missing a required field.
///     ClassicNotificationInstalledVersionParseError: ``installed_version``
///         could not be parsed as semver (spec classifies this as
///         ``"unknown"`` when it happens *during* classify; this exception
///         is reserved for explicit parse-failure paths).
///     ClassicNotificationCacheIoError: cache I/O failure.
///     ClassicNotificationError: invalid or unsupported notification manifest.
///     ClassicUpdateError: non-notification update-subsystem error.
#[pyfunction]
fn check_app_notification(
    py: Python<'_>,
    owner: &str,
    repo: &str,
    installed_version: &str,
) -> PyResult<PyNotificationStatus> {
    let status = block_on_notification_future(py, || async {
        core::check_app_notification(owner, repo, installed_version).await
    })
    .map_err(update_error_to_py)?;
    Ok(core_status_to_py(status))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add(
        "ClassicUpdateError",
        m.py().get_type::<ClassicUpdateError>(),
    )?;
    m.add(
        "ClassicNotificationError",
        m.py().get_type::<ClassicNotificationError>(),
    )?;
    m.add(
        "ClassicNotificationFetchFailed",
        m.py().get_type::<ClassicNotificationFetchFailed>(),
    )?;
    m.add(
        "ClassicNotificationDecodeError",
        m.py().get_type::<ClassicNotificationDecodeError>(),
    )?;
    m.add(
        "ClassicNotificationInstalledVersionParseError",
        m.py()
            .get_type::<ClassicNotificationInstalledVersionParseError>(),
    )?;
    m.add(
        "ClassicNotificationCacheIoError",
        m.py().get_type::<ClassicNotificationCacheIoError>(),
    )?;
    m.add_class::<PyAppNotificationDisplay>()?;
    m.add_class::<PyNotificationStatus>()?;
    m.add_function(wrap_pyfunction!(check_app_notification, m)?)?;
    Ok(())
}
