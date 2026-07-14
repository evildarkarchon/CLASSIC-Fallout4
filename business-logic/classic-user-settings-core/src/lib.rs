//! Typed, preservation-aware ownership of CLASSIC User Settings.
//!
//! The crate opens User Settings relative to an explicit CLASSIC root and
//! returns typed preference groups without changing the source document.

mod commit;
mod default_settings;
mod document;
mod frontend_state;
mod game_setup_settings;
mod migration;
mod migration_persistence;
mod preference;
mod scan_settings;
mod update;

pub use commit::{UserSettingsCommitError, UserSettingsCommitOutcome};
pub use document::{
    CommitEligibility, Diagnostic, DocumentClassification, PreferenceOrigin, Revision,
    SettingsSource, SourceLocation, UpdatePreferences, UpdateSource, UserSettings,
};
pub use frontend_state::{
    FrontendPreferences, FrontendState, GuiWindowGeometry, TuiRememberedState, WindowGeometry,
};
pub use game_setup_settings::GameSetupSettings;
pub use migration::{
    CURRENT_USER_SETTINGS_SCHEMA_VERSION, MigrationChange, MigrationChangeKind,
    MigrationDiagnostic, MigrationEndpoint, MigrationPlanningOutcome, UserSettingsMigrationPlan,
    UserSettingsSchemaVersion,
};
pub use migration_persistence::{
    UserSettingsMigrationApplyOutcome, UserSettingsMigrationError, UserSettingsMigrationReceipt,
    UserSettingsMigrationRestoreOutcome,
};
pub use scan_settings::{CrashLogScanSettings, GameVersionSelection};
pub use update::{
    AcceptedUserSettingsUpdate, UpdateDiagnostic, UserSettingsUpdate, UserSettingsUpdateField,
    UserSettingsUpdatePreview,
};
