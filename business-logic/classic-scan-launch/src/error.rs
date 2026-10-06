//! Typed launch errors, reserved for overrides and intents that cannot form a request.

use classic_vocabulary::Vocabulary;
use std::fmt;

/// Why a Crash Log Scan Launch could not produce a request.
///
/// Degraded User Settings are never an error: they produce a request plus diagnostics.
/// Errors are reserved for invalid caller input. Like the diagnostics, the enum is
/// deliberately exhaustive so a new error kind fails to compile in every binding until it
/// is projected there.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CrashLogScanLaunchError {
    /// A Targeted intent named no inputs, so there is nothing to scan.
    TargetedWithoutInputs,
}

impl CrashLogScanLaunchError {
    /// Returns the stable category for programmatic handling.
    #[must_use]
    pub const fn kind(&self) -> CrashLogScanLaunchErrorKind {
        match self {
            Self::TargetedWithoutInputs => CrashLogScanLaunchErrorKind::TargetedWithoutInputs,
        }
    }
}

impl fmt::Display for CrashLogScanLaunchError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::TargetedWithoutInputs => {
                formatter.write_str("a Targeted Crash Log Scan needs at least one input")
            }
        }
    }
}

impl std::error::Error for CrashLogScanLaunchError {}

/// Stable category of a [`CrashLogScanLaunchError`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum CrashLogScanLaunchErrorKind {
    /// See [`CrashLogScanLaunchError::TargetedWithoutInputs`].
    TargetedWithoutInputs,
}

impl Vocabulary for CrashLogScanLaunchErrorKind {
    const VARIANTS: &'static [Self] = &[Self::TargetedWithoutInputs];

    /// These tokens are frozen; every binding publishes them unchanged.
    fn as_str(self) -> &'static str {
        match self {
            Self::TargetedWithoutInputs => "targeted_without_inputs",
        }
    }

    /// Prose, freely rewordable.
    fn label(self) -> &'static str {
        match self {
            Self::TargetedWithoutInputs => "Targeted scan without inputs",
        }
    }
}
