//! Typed, preservation-aware ownership of CLASSIC User Settings.
//!
//! The crate opens User Settings relative to an explicit CLASSIC root and
//! returns typed preference groups without changing the source document.

mod document;

pub use document::{
    CommitEligibility, Diagnostic, DocumentClassification, PreferenceOrigin, Revision,
    SettingsSource, SourceLocation, UpdatePreferences, UserSettings,
};
