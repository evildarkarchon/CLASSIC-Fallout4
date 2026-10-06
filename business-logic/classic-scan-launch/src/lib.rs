//! Crash Log Scan Launch (ADR-0009).
//!
//! The read-only projection of saved User Settings, the selected game, and per-run
//! overrides into a Crash Log Scan Run request. [`prepare_launch`] is the one operation:
//! it takes the Installation Root, a [`CrashLogScanIntent`] and
//! [`CrashLogScanLaunchOverrides`], opens User Settings read-only, and returns a
//! [`CrashLogScanLaunchRequest`] carrying the request and its launch diagnostics.
//!
//! It never persists User Settings and never runs the scan. A frontend that wants to save a
//! value does so as its own User Settings Update, before or apart from launching. The rules
//! it consumes keep their owners: User Settings decides which FormID database rows apply to
//! a game ([`CrashLogScanSettings::formid_databases_for_game`]), and scanlog core owns the
//! request it builds.
//!
//! Launch owns one rule of its own, the game-differs rule: a scan of a game other than the
//! managed game never applies the managed game's saved game version, FCX Mode, custom scan
//! folder or setup folders, and reports each one withheld as a
//! [`CrashLogScanLaunchDiagnostic::SavedValueNotApplied`]. The scan presentation module
//! renders every launch diagnostic as Display Content (ADR-0007).
//!
//! [`CrashLogScanSettings::formid_databases_for_game`]:
//!     classic_user_settings_core::CrashLogScanSettings::formid_databases_for_game

#[cfg(test)]
#[path = "lib_tests.rs"]
mod tests;

mod diagnostic;
mod error;
mod launch;
mod overrides;

pub use classic_user_settings_core::GameVersionSelection;
pub use diagnostic::{
    CrashLogScanLaunchDiagnostic, CrashLogScanLaunchDiagnosticKind, SavedGameSpecificValue,
};
pub use error::{CrashLogScanLaunchError, CrashLogScanLaunchErrorKind};
pub use launch::{CrashLogScanIntent, CrashLogScanLaunchRequest, prepare_launch};
pub use overrides::{CrashLogScanLaunchOverrides, MaxConcurrency};
