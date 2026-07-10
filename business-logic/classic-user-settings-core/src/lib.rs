//! Typed, preservation-aware ownership of CLASSIC User Settings.
//!
//! The crate opens User Settings relative to an explicit CLASSIC root and
//! returns typed preference groups without changing the source document.

mod document;
mod scan_settings;
mod update;

pub use document::{
    CommitEligibility, Diagnostic, DocumentClassification, PreferenceOrigin, Revision,
    SettingsSource, SourceLocation, UpdatePreferences, UserSettings,
};
pub use scan_settings::{CrashLogScanSettings, GameVersionSelection};
pub use update::{
    AcceptedUserSettingsUpdate, UpdateDiagnostic, UserSettingsUpdate, UserSettingsUpdateField,
    UserSettingsUpdatePreview,
};
