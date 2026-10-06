//! Typed launch errors, reserved for overrides and intents that cannot form a request, and
//! for operational failures while gathering the facts a request needs.

use classic_scangame_core::XseLogError;
use classic_vocabulary::Vocabulary;
use std::fmt;
use std::path::PathBuf;

/// Why a Crash Log Scan Launch could not produce a request.
///
/// Degraded User Settings are never an error: they produce a request plus diagnostics.
/// Missing setup folders are not an error either; FCX setup validation reports them.
/// Errors are reserved for invalid caller input and for operational failures the launch
/// cannot decide past. Like the diagnostics, the enum is deliberately exhaustive so a new
/// error kind fails to compile in every binding until it is projected there.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CrashLogScanLaunchError {
    /// A Targeted intent named no inputs, so there is nothing to scan.
    TargetedWithoutInputs,
    /// FCX Mode is on and the XSE log location could not be inspected for a reason other
    /// than absence (for example, access was denied or the path is not a valid file name),
    /// so the launch cannot tell whether the log exists.
    ///
    /// A missing XSE Folder or log is not this error; the setup context simply has no XSE
    /// log.
    XseLogInspect {
        /// The candidate XSE log path that could not be inspected.
        path: PathBuf,
        /// The underlying I/O failure, as text. Prose; branch on [`Self::kind`] instead.
        message: String,
    },
}

impl CrashLogScanLaunchError {
    /// Returns the stable category for programmatic handling.
    #[must_use]
    pub const fn kind(&self) -> CrashLogScanLaunchErrorKind {
        match self {
            Self::TargetedWithoutInputs => CrashLogScanLaunchErrorKind::TargetedWithoutInputs,
            Self::XseLogInspect { .. } => CrashLogScanLaunchErrorKind::XseLogInspect,
        }
    }

    /// Carries an XSE log failure's path and I/O text. The I/O error itself is not kept:
    /// it is neither `Clone` nor `Eq`, which this error type promises its bindings.
    pub(crate) fn from_xse_log_error(error: XseLogError) -> Self {
        match error {
            XseLogError::Inspect { path, source } => Self::XseLogInspect {
                path,
                message: source.to_string(),
            },
        }
    }
}

impl fmt::Display for CrashLogScanLaunchError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::TargetedWithoutInputs => {
                formatter.write_str("a Targeted Crash Log Scan needs at least one input")
            }
            Self::XseLogInspect { path, message } => write!(
                formatter,
                "cannot inspect the XSE log {}: {message}",
                path.display()
            ),
        }
    }
}

impl std::error::Error for CrashLogScanLaunchError {}

/// Stable category of a [`CrashLogScanLaunchError`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum CrashLogScanLaunchErrorKind {
    /// See [`CrashLogScanLaunchError::TargetedWithoutInputs`].
    TargetedWithoutInputs,
    /// See [`CrashLogScanLaunchError::XseLogInspect`].
    XseLogInspect,
}

impl Vocabulary for CrashLogScanLaunchErrorKind {
    const VARIANTS: &'static [Self] = &[Self::TargetedWithoutInputs, Self::XseLogInspect];

    /// These tokens are frozen; every binding publishes them unchanged.
    fn as_str(self) -> &'static str {
        match self {
            Self::TargetedWithoutInputs => "targeted_without_inputs",
            Self::XseLogInspect => "xse_log_inspect",
        }
    }

    /// Prose, freely rewordable.
    fn label(self) -> &'static str {
        match self {
            Self::TargetedWithoutInputs => "Targeted scan without inputs",
            Self::XseLogInspect => "XSE log could not be inspected",
        }
    }
}
