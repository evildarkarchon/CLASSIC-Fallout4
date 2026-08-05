//! Thin NAPI adapter for User Settings snapshots, migration plans, updates, and commits.

use crate::shared::{JsGameId, core_to_js_game_id, js_to_core_game_id};
// The one shared casing rule this surface applies to every Vocabulary Token.
// Imported rather than path-qualified because it now wraps every enum
// projection in this module, not just the migration tracer.
use crate::vocabulary::{from_js_token, js_token};
use classic_user_settings_core::{
    GuiWindow, LegacyTuiStateImportOutcome, LegacyTuiStateImportReceipt,
    LegacyTuiStateImportRestoreOutcome, MigrationChange, MigrationChangeKind, MigrationEndpoint,
    MigrationPlanningOutcome, Revision, SourceLocation, UserSettings, UserSettingsCommitOutcome,
    UserSettingsFrontendTransitionOutcome as CoreUserSettingsFrontendTransitionOutcome,
    UserSettingsMigrationApplyOutcome, UserSettingsMigrationPlan, UserSettingsMigrationReceipt,
    UserSettingsMigrationRestoreOutcome, UserSettingsSchemaVersion, UserSettingsUpdate,
    UserSettingsUpdateField, UserSettingsUpdatePreview, WindowGeometry, import_legacy_tui_state,
};
use classic_vocabulary::Vocabulary;
use napi::bindgen_prelude::{Buffer, Either, Either5, Null};
use std::collections::HashMap;

/// One structured diagnostic produced while opening User Settings.
#[napi(object)]
pub struct JsUserSettingsDiagnostic {
    /// Stable machine-readable diagnostic code.
    pub code: String,
    /// Human-readable diagnostic context.
    pub message: String,
}

/// Update-related User Settings consumed by update-check policy and compatibility adapters.
#[napi(object)]
pub struct JsUpdatePreferences {
    /// Whether first-party update checks are enabled after safe fallback policy.
    pub update_check: bool,
    /// Provenance token: `document`, `default`, or `degradedFallback`.
    pub origin: String,
    /// Canonical compatibility update-source token: `GitHub` or `Both`.
    pub update_source: String,
    /// Provenance token for the compatibility update source.
    pub update_source_origin: String,
}

/// Typed Crash Log Scan settings together with per-field provenance.
#[napi(object)]
pub struct JsCrashLogScanSettings {
    /// Whether FCX Mode is enabled.
    pub fcx_mode: bool,
    /// Provenance token for FCX Mode.
    pub fcx_mode_origin: String,
    /// Whether Crash Logs should be simplified before analysis.
    pub simplify_logs: bool,
    /// Provenance token for Simplify Logs.
    pub simplify_logs_origin: String,
    /// Whether scan statistics should be included in output.
    pub show_statistics: bool,
    /// Provenance token for Show Statistics.
    pub show_statistics_origin: String,
    /// Whether FormID Value Lookup is enabled.
    pub formid_value_lookup: bool,
    /// Provenance token for FormID Value Lookup.
    pub formid_value_lookup_origin: String,
    /// FormID database paths keyed by managed game, preserving persisted path spelling.
    pub formid_databases: HashMap<String, Vec<String>>,
    /// Provenance token for FormID Databases.
    pub formid_databases_origin: String,
    /// Whether a standard scan may move Unsolved Logs.
    pub move_unsolved_logs: bool,
    /// Provenance token for Move Unsolved Logs.
    pub move_unsolved_logs_origin: String,
    /// Persisted Unsolved Logs destination without path normalization.
    pub unsolved_logs_destination: Option<String>,
    /// Provenance token for Unsolved Logs Destination.
    pub unsolved_logs_destination_origin: String,
    /// Persisted custom scan input without path normalization.
    pub custom_scan_input: Option<String>,
    /// Provenance token for the custom scan input.
    pub custom_scan_input_origin: String,
    /// Canonical game-version selection token.
    pub game_version_selection: String,
    /// Provenance token for game-version selection.
    pub game_version_selection_origin: String,
    /// Requested scan concurrency, where zero selects the adaptive default.
    pub max_concurrent_scans: u32,
    /// Provenance token for Max Concurrent Scans.
    pub max_concurrent_scans_origin: String,
}

/// Typed Game Setup settings together with per-field provenance.
#[napi(object)]
pub struct JsGameSetupSettings {
    /// Supported game managed by this settings document.
    pub managed_game: JsGameId,
    /// Provenance token for the managed game.
    pub managed_game_origin: String,
    /// Canonical game-version selection token.
    pub game_version_selection: String,
    /// Provenance token for game-version selection.
    pub game_version_selection_origin: String,
    /// Persisted game installation root without path normalization.
    pub game_root: Option<String>,
    /// Provenance token for the game installation root.
    pub game_root_origin: String,
    /// Persisted game executable path without path normalization.
    pub game_executable: Option<String>,
    /// Provenance token for the game executable path.
    pub game_executable_origin: String,
    /// Persisted documents root without path normalization.
    pub documents_root: Option<String>,
    /// Provenance token for the documents root.
    pub documents_root_origin: String,
    /// Persisted INI-folder compatibility fallback without path normalization.
    pub ini_folder: Option<String>,
    /// Provenance token for the INI-folder compatibility fallback.
    pub ini_folder_origin: String,
    /// Persisted mods or staging root without path normalization.
    pub mods_root: Option<String>,
    /// Provenance token for the mods or staging root.
    pub mods_root_origin: String,
    /// Persisted custom Crash Log Scan input without path normalization.
    pub custom_scan_input: Option<String>,
    /// Provenance token for the custom Crash Log Scan input.
    pub custom_scan_input_origin: String,
    /// Persisted Papyrus log path without path normalization.
    pub papyrus_log: Option<String>,
    /// Provenance token for the Papyrus log path.
    pub papyrus_log_origin: String,
}

/// Remembered presentation preferences shared by maintained frontends.
#[napi(object)]
pub struct JsFrontendPreferences {
    /// Whether successful scans should select the Results presentation.
    pub auto_switch_after_scan: bool,
    /// Provenance token for automatic result switching.
    pub auto_switch_after_scan_origin: String,
    /// Remembered refresh interval in milliseconds, represented as a JavaScript number.
    pub auto_refresh_interval_ms: f64,
    /// Provenance token for the refresh interval.
    pub auto_refresh_interval_ms_origin: String,
}

/// Widget-independent geometry for one maintained GUI tab.
#[napi(object)]
pub struct JsWindowGeometry {
    /// Whether the tab's window was maximized.
    pub maximized: bool,
    /// Provenance token for the maximized state.
    pub maximized_origin: String,
    /// Remembered normal-state width in pixels.
    pub width: u32,
    /// Provenance token for the remembered width.
    pub width_origin: String,
    /// Remembered normal-state height in pixels.
    pub height: u32,
    /// Provenance token for the remembered height.
    pub height_origin: String,
}

/// Remembered geometry for every maintained GUI tab.
#[napi(object)]
pub struct JsGuiWindowGeometry {
    /// Geometry for the Main Options tab.
    pub main_tab: JsWindowGeometry,
    /// Geometry for the File Backup tab.
    pub backups_tab: JsWindowGeometry,
    /// Geometry for the Articles tab.
    pub articles_tab: JsWindowGeometry,
    /// Geometry for the Results tab.
    pub results_tab: JsWindowGeometry,
}

/// Caller-authored geometry transition for one maintained GUI window.
#[napi(object)]
pub struct JsWindowGeometryUpdate {
    /// Whether the window should be remembered as maximized.
    pub maximized: bool,
    /// Requested normal-state width in pixels; core preview validates the numeric range.
    pub width: f64,
    /// Requested normal-state height in pixels; core preview validates the numeric range.
    pub height: f64,
}

/// Stable identity for one maintained GUI window.
#[napi(string_enum)]
pub enum JsGuiWindow {
    /// Main Options tab window.
    #[napi(value = "main_tab")]
    Main,
    /// File Backup tab window.
    #[napi(value = "backups_tab")]
    Backups,
    /// Articles tab window.
    #[napi(value = "articles_tab")]
    Articles,
    /// Results tab window.
    #[napi(value = "results_tab")]
    Results,
}

/// Selected remembered-geometry transitions keyed by maintained GUI window.
#[napi(object)]
pub struct JsGuiWindowGeometryUpdate {
    /// Optional transition for the Main Options window.
    pub main_tab: Option<JsWindowGeometryUpdate>,
    /// Optional transition for the File Backup window.
    pub backups_tab: Option<JsWindowGeometryUpdate>,
    /// Optional transition for the Articles window.
    pub articles_tab: Option<JsWindowGeometryUpdate>,
    /// Optional transition for the Results window.
    pub results_tab: Option<JsWindowGeometryUpdate>,
}

/// Remembered TUI state from the canonical `UI.tui` namespace.
#[napi(object)]
pub struct JsTuiRememberedState {
    /// Stable zero-based tab ordinal remembered by the TUI.
    pub active_tab: u8,
    /// Provenance token for the active-tab ordinal.
    pub active_tab_origin: String,
    /// Remembered Results list-panel width.
    pub results_panel_width: u16,
    /// Provenance token for the Results list-panel width.
    pub results_panel_width_origin: String,
    /// Whether Results are remembered in ascending order.
    pub sort_ascending: bool,
    /// Provenance token for the sort direction.
    pub sort_ascending_origin: String,
}

/// One complete TUI remembered-state transition for the canonical `UI.tui` namespace.
#[napi(object)]
pub struct JsTuiRememberedStateUpdate {
    /// Requested stable zero-based tab ordinal.
    pub active_tab: f64,
    /// Requested Results list-panel width.
    pub results_panel_width: f64,
    /// Requested Results sort direction.
    pub sort_ascending: bool,
}

/// Cohesive, widget-independent state remembered by CLASSIC frontends.
#[napi(object)]
pub struct JsFrontendState {
    /// Presentation preferences shared by frontends.
    pub preferences: JsFrontendPreferences,
    /// Remembered geometry for maintained GUI tabs.
    pub window_geometry: JsGuiWindowGeometry,
    /// Canonically namespaced TUI remembered state.
    pub tui: JsTuiRememberedState,
}

/// Caller-authored fields to validate as one non-persisting User Settings Update.
#[napi(object)]
pub struct JsUserSettingsUpdate {
    /// Requested Update Check preference.
    pub update_check: Option<bool>,
    /// Requested canonical or legacy-compatible update-source selection.
    pub update_source: Option<String>,
    /// Requested automatic switch to Results after a completed scan.
    pub auto_switch_after_scan: Option<bool>,
    /// Selected remembered-geometry transitions for maintained GUI windows.
    pub window_geometry: Option<JsGuiWindowGeometryUpdate>,
    /// Requested complete TUI remembered-state transition.
    pub tui: Option<JsTuiRememberedStateUpdate>,
    /// Requested managed game.
    pub managed_game: Option<JsGameId>,
    /// Requested canonical game-version selection.
    pub game_version_selection: Option<String>,
    /// Requested game installation root; `null` explicitly clears the saved path.
    pub game_root: Option<Either<String, Null>>,
    /// Requested game executable path; `null` explicitly clears the saved path.
    pub game_executable: Option<Either<String, Null>>,
    /// Requested documents root; `null` explicitly clears the saved path.
    pub documents_root: Option<Either<String, Null>>,
    /// Requested INI-folder compatibility fallback; `null` explicitly clears it.
    pub ini_folder: Option<Either<String, Null>>,
    /// Requested mods or staging folder; `null` explicitly clears the saved path.
    pub mods_folder: Option<Either<String, Null>>,
    /// Requested FCX Mode preference.
    pub fcx_mode: Option<bool>,
    /// Requested Simplify Logs preference.
    pub simplify_logs: Option<bool>,
    /// Requested Show Statistics preference.
    pub show_statistics: Option<bool>,
    /// Requested FormID Value Lookup preference.
    pub formid_value_lookup: Option<bool>,
    /// Requested replacement FormID database mapping.
    pub formid_databases: Option<HashMap<String, Vec<String>>>,
    /// Requested Move Unsolved Logs preference.
    pub move_unsolved_logs: Option<bool>,
    /// Requested Unsolved Logs destination; `null` explicitly selects the default.
    pub unsolved_logs_destination: Option<Either<String, Null>>,
    /// Requested custom scan input; `null` explicitly selects automatic discovery.
    pub custom_scan_input: Option<Either<String, Null>>,
    /// Requested Papyrus log path; `null` explicitly clears the saved path.
    pub papyrus_log_path: Option<Either<String, Null>>,
    /// Requested scan concurrency in the persisted `0..=32` range.
    pub max_concurrent_scans: Option<f64>,
}

/// One canonical field and value in an accepted User Settings Update preview.
#[napi(object)]
pub struct JsUserSettingsUpdateField {
    /// Canonical RFC 6901-style path for the requested field.
    pub field_path: String,
    /// Validated requested value.
    pub value: Either5<bool, String, HashMap<String, Vec<String>>, u32, Null>,
}

/// Field-specific reason that a User Settings Update preview was rejected.
#[napi(object)]
pub struct JsUserSettingsUpdateDiagnostic {
    /// Rejected canonical field path, absent for a preview-level failure.
    pub field_path: Option<String>,
    /// Stable machine-readable diagnostic code.
    pub code: String,
    /// Human-readable rejection context.
    pub message: String,
}

/// All-or-nothing result of validating a User Settings Update without persistence.
#[napi(object)]
pub struct JsUserSettingsUpdatePreview {
    /// Whether every requested field was accepted.
    pub accepted: bool,
    /// Revision token anchoring an accepted preview, absent when rejected.
    pub base_revision: Option<String>,
    /// Only the explicitly requested canonical fields, empty when rejected.
    pub fields: Vec<JsUserSettingsUpdateField>,
    /// All rejection diagnostics, empty when accepted.
    pub diagnostics: Vec<JsUserSettingsUpdateDiagnostic>,
}

/// Structured outcome of explicitly committing a previously accepted User Settings Update.
#[napi(object)]
pub struct JsUserSettingsCommitResult {
    /// Outcome token: `committed`, `conflict`, or `rejected`.
    pub status: String,
    /// Revision of the published document, present only when committed.
    pub revision: Option<String>,
    /// Caller-supplied revision anchoring the previously accepted preview.
    pub expected_revision: String,
    /// Latest document revision, present only when a conflict is detected.
    pub actual_revision: Option<String>,
    /// Validation diagnostics, populated only when the update is rejected.
    pub diagnostics: Vec<JsUserSettingsUpdateDiagnostic>,
}

/// Tagged result of explicitly importing retired TUI state into User Settings.
#[napi(object, object_from_js = false)]
pub struct JsLegacyTuiStateImportOutcome {
    /// Outcome token identifying the no-op, applied, or conflict case.
    pub status: String,
    /// Settings classification for migration or trust-gated outcomes.
    pub classification: Option<String>,
    /// Settings revision for migration or trust-gated outcomes.
    pub revision: Option<String>,
    /// Concrete retired state path, present only when applied.
    pub source_path: Option<String>,
    /// Verified retained backup path, present only when applied.
    pub backup_path: Option<String>,
    /// Revision of exact parsed legacy bytes, present only when applied.
    pub source_revision: Option<String>,
    /// Independently verified backup revision, present only when applied.
    pub backup_revision: Option<String>,
    /// User Settings base revision selected for an applied import.
    pub base_settings_revision: Option<String>,
    /// User Settings revision published by an applied import.
    pub published_settings_revision: Option<String>,
    /// Selected revision for either conflict outcome.
    pub expected_revision: Option<String>,
    /// Revision found at the conflicting path.
    pub actual_revision: Option<String>,
    /// Opaque verified receipt, present only after an applied import.
    pub receipt: Option<JsLegacyTuiStateImportReceipt>,
}

/// Opaque native handle to a verified legacy TUI state import receipt.
#[napi]
pub struct JsLegacyTuiStateImportReceipt {
    inner: LegacyTuiStateImportReceipt,
}

#[napi]
impl JsLegacyTuiStateImportReceipt {
    /// Returns the concrete retired `state.json` path left unchanged by import.
    #[napi(getter)]
    pub fn source_path(&self) -> String {
        self.inner.source_path().display().to_string()
    }

    /// Returns the verified content-addressed backup of exact legacy bytes.
    #[napi(getter)]
    pub fn backup_path(&self) -> String {
        self.inner.backup_path().display().to_string()
    }

    /// Returns the canonical User Settings path modified by import.
    #[napi(getter)]
    pub fn settings_path(&self) -> String {
        self.inner.settings_path().display().to_string()
    }

    /// Returns the retained pre-import settings backup path when a document existed.
    #[napi(getter)]
    pub fn settings_backup_path(&self) -> Option<String> {
        self.inner
            .settings_backup_path()
            .map(|path| path.display().to_string())
    }

    /// Returns the revision of the exact parsed legacy bytes.
    #[napi(getter)]
    pub fn source_revision(&self) -> String {
        self.inner.source_revision().token()
    }

    /// Returns the independently verified legacy backup revision.
    #[napi(getter)]
    pub fn backup_revision(&self) -> String {
        self.inner.backup_revision().token()
    }

    /// Returns the User Settings base revision selected by import.
    #[napi(getter)]
    pub fn base_settings_revision(&self) -> String {
        self.inner.base_settings_revision().token()
    }

    /// Returns the User Settings revision published by import.
    #[napi(getter)]
    pub fn published_settings_revision(&self) -> String {
        self.inner.published_settings_revision().token()
    }

    /// Restores the pre-import User Settings state through this verified receipt.
    #[napi]
    pub fn restore(
        &self,
        classic_root: String,
    ) -> napi::Result<JsLegacyTuiStateImportRestoreOutcome, String> {
        match self.inner.restore(classic_root) {
            Ok(LegacyTuiStateImportRestoreOutcome::Restored { revision }) => {
                Ok(JsLegacyTuiStateImportRestoreOutcome {
                    status: "restored".to_string(),
                    revision: Some(revision.token()),
                    expected_revision: None,
                    actual_revision: None,
                })
            }
            Ok(LegacyTuiStateImportRestoreOutcome::Conflict {
                expected_revision,
                actual_revision,
            }) => Ok(JsLegacyTuiStateImportRestoreOutcome {
                status: "conflict".to_string(),
                revision: None,
                expected_revision: Some(expected_revision.token()),
                actual_revision: Some(actual_revision.token()),
            }),
            Err(error) => Err(napi::Error::new(
                error.code().to_string(),
                error.message().to_string(),
            )),
        }
    }
}

/// Result of restoring User Settings through an applied legacy import receipt.
#[napi(object)]
pub struct JsLegacyTuiStateImportRestoreOutcome {
    /// Outcome token: `restored` or `conflict`.
    pub status: String,
    /// Restored revision, present only when restored.
    pub revision: Option<String>,
    /// Imported revision that had to remain current for restore.
    pub expected_revision: Option<String>,
    /// Latest User Settings revision, present only when conflicted.
    pub actual_revision: Option<String>,
}

/// Explicit major/minor User Settings schema version.
#[napi(object)]
pub struct JsUserSettingsSchemaVersion {
    /// Breaking-change component.
    pub major: u32,
    /// Additive-change component.
    pub minor: u32,
}

/// One endpoint in a proposed User Settings version/location transition.
#[napi(object)]
pub struct JsUserSettingsMigrationEndpoint {
    /// Root-relative location token: `canonical`, `legacy`, or `missing`.
    pub location: String,
    /// Explicit schema version, absent for a legacy unversioned form.
    pub schema_version: Option<JsUserSettingsSchemaVersion>,
}

/// One ordered, reversible change in a User Settings migration plan.
#[napi(object)]
pub struct JsUserSettingsMigrationChange {
    /// Stable change-kind token.
    pub kind: String,
    /// Source RFC 6901 pointer or relative path, when applicable.
    pub source_path: Option<String>,
    /// Target RFC 6901 pointer or relative path, when applicable.
    pub target_path: Option<String>,
    /// Deterministic YAML/text value before the change, when applicable.
    pub before: Option<String>,
    /// Deterministic YAML/text value after the change, when applicable.
    pub after: Option<String>,
}

/// Structured reason that a User Settings migration plan could not be produced.
#[napi(object)]
pub struct JsUserSettingsMigrationDiagnostic {
    /// Stable machine-readable diagnostic code.
    pub code: String,
    /// Human-readable diagnostic context.
    pub message: String,
}

/// Immutable proposal for an explicit, side-effect-free User Settings migration.
#[napi(object)]
pub struct JsUserSettingsMigrationPlan {
    /// Whether compatibility requires this plan before ordinary commits.
    pub required: bool,
    /// Revision token anchoring the plan to the opened source bytes.
    pub base_revision: String,
    /// Current version/location endpoint.
    pub source: JsUserSettingsMigrationEndpoint,
    /// Proposed version/location endpoint.
    pub target: JsUserSettingsMigrationEndpoint,
    /// Ordered review rows describing every proposed transition.
    pub changes: Vec<JsUserSettingsMigrationChange>,
    /// Exact opened bytes retained for review and reversal.
    pub original_content: Buffer,
    /// Deterministic proposed document bytes without publication.
    pub proposed_content: Buffer,
}

/// Structured outcome of side-effect-free User Settings migration planning.
#[napi(object)]
pub struct JsUserSettingsMigrationPlanningResult {
    /// Outcome token: `notRequired`, `planned`, or `unsupported`.
    pub status: String,
    /// Proposed plan, present only for the `planned` outcome.
    pub plan: Option<JsUserSettingsMigrationPlan>,
    /// Planning diagnostics, populated only for the `unsupported` outcome.
    pub diagnostics: Vec<JsUserSettingsMigrationDiagnostic>,
}

/// Result of explicitly applying a caller-approved User Settings migration.
#[napi(object, object_from_js = false)]
pub struct JsUserSettingsMigrationApplyResult {
    /// Outcome token: `applied` or `conflict`.
    pub status: String,
    /// Verified native receipt, present only after a successful apply.
    pub receipt: Option<JsUserSettingsMigrationReceipt>,
    /// Revision against which the caller approved the migration.
    pub expected_revision: String,
    /// Latest document revision, present only when a conflict is detected.
    pub actual_revision: Option<String>,
}

/// Result of explicitly restoring a successfully applied User Settings migration.
#[napi(object)]
pub struct JsUserSettingsMigrationRestoreResult {
    /// Outcome token: `restored` or `conflict`.
    pub status: String,
    /// Restored document revision, present only after successful restoration.
    pub revision: Option<String>,
    /// Migrated revision that had to remain current for restoration.
    pub expected_revision: String,
    /// Latest document revision, present only when a conflict is detected.
    pub actual_revision: Option<String>,
}

/// Opaque native handle to a verified User Settings migration receipt.
///
/// JavaScript can inspect the attested paths, endpoints, and revisions, but cannot
/// reconstruct or mutate the Rust receipt used by the conflict-safe restore seam.
#[napi]
pub struct JsUserSettingsMigrationReceipt {
    inner: UserSettingsMigrationReceipt,
}

#[napi]
impl JsUserSettingsMigrationReceipt {
    /// Returns the document path selected when the migration was applied.
    #[napi(getter)]
    pub fn source_path(&self) -> String {
        self.inner.source_path().display().to_string()
    }

    /// Returns the canonical path at which the migrated document was published.
    #[napi(getter)]
    pub fn destination_path(&self) -> String {
        self.inner.destination_path().display().to_string()
    }

    /// Returns the retained, byte-exact backup path verified before publication.
    #[napi(getter)]
    pub fn backup_path(&self) -> String {
        self.inner.backup_path().display().to_string()
    }

    /// Returns the source version/location endpoint recorded by the approved plan.
    #[napi(getter)]
    pub fn source(&self) -> JsUserSettingsMigrationEndpoint {
        migration_endpoint_to_js(self.inner.source())
    }

    /// Returns the destination version/location endpoint recorded by the approved plan.
    #[napi(getter)]
    pub fn target(&self) -> JsUserSettingsMigrationEndpoint {
        migration_endpoint_to_js(self.inner.target())
    }

    /// Returns the exact-byte revision attested by the retained backup.
    #[napi(getter)]
    pub fn backup_revision(&self) -> String {
        self.inner.backup_revision().token()
    }

    /// Returns the exact-byte revision verified after migrated publication.
    #[napi(getter)]
    pub fn published_revision(&self) -> String {
        self.inner.published_revision().token()
    }

    /// Explicitly restores this receipt's retained backup under core coordination.
    ///
    /// Conflicts are returned as data. Backup, publication, and verification failures
    /// are raised as JavaScript errors with the core's stable error code.
    #[napi]
    pub fn restore(
        &self,
        classic_root: String,
    ) -> napi::Result<JsUserSettingsMigrationRestoreResult, String> {
        let expected_revision = self.inner.published_revision().token();
        match self.inner.restore(classic_root) {
            Ok(UserSettingsMigrationRestoreOutcome::Restored { revision }) => {
                Ok(JsUserSettingsMigrationRestoreResult {
                    status: "restored".to_string(),
                    revision: Some(revision.token()),
                    expected_revision,
                    actual_revision: None,
                })
            }
            Ok(UserSettingsMigrationRestoreOutcome::Conflict {
                expected_revision,
                actual_revision,
            }) => Ok(JsUserSettingsMigrationRestoreResult {
                status: "conflict".to_string(),
                revision: None,
                expected_revision: expected_revision.token(),
                actual_revision: Some(actual_revision.token()),
            }),
            Err(error) => Err(user_settings_migration_error(error.code(), error.message())),
        }
    }
}

/// Read-only User Settings snapshot returned by `openUserSettings`.
#[napi(object)]
pub struct JsUserSettingsSnapshot {
    /// Typed update preferences.
    pub update_preferences: JsUpdatePreferences,
    /// Typed Crash Log Scan settings.
    pub crash_log_scan_settings: JsCrashLogScanSettings,
    /// Typed Game Setup settings.
    pub game_setup_settings: JsGameSetupSettings,
    /// Typed frontend presentation and remembered state.
    pub frontend_state: JsFrontendState,
    /// Selected source token: `canonical`, `legacy`, or `missing`.
    pub source_location: String,
    /// Selected source path, absent when the document is missing.
    pub source_path: Option<String>,
    /// Document format/schema classification token.
    pub classification: String,
    /// Parsed schema major, absent for missing or unversioned documents.
    pub schema_major: Option<u32>,
    /// Parsed schema minor, absent for missing or unversioned documents.
    pub schema_minor: Option<u32>,
    /// Content-derived revision token (`sha256:…`, `missing`, or `unavailable`).
    pub revision: String,
    /// Commit policy token: `eligible`, `requiresMigration`, or `blockedUntrusted`.
    pub commit_eligibility: String,
    /// Structured diagnostics in discovery and validation order.
    pub diagnostics: Vec<JsUserSettingsDiagnostic>,
    /// Exact source bytes retained for later semantic preservation.
    pub original_content: Option<Buffer>,
}

/// Opens User Settings relative to an explicit CLASSIC root without changing
/// either supported source document.
#[napi]
pub fn open_user_settings(classic_root: String) -> JsUserSettingsSnapshot {
    let settings = UserSettings::open(classic_root);
    user_settings_snapshot_to_js(&settings)
}

/// Explicitly imports one retired TUI `state.json` into the canonical User Settings store.
///
/// Expected no-op and conflict cases resolve as tagged data. Operational failures reject with
/// the stable core code in `error.code` and human-readable context in `error.message`.
#[napi]
pub fn import_legacy_tui_state_into_user_settings(
    classic_root: String,
    legacy_state_path: String,
) -> napi::Result<JsLegacyTuiStateImportOutcome, String> {
    import_legacy_tui_state(classic_root, legacy_state_path)
        .map(legacy_tui_state_import_outcome_to_js)
        .map_err(|error| napi::Error::new(error.code().to_string(), error.message().to_string()))
}

/// Converts every core import outcome into one stable JavaScript object shape.
fn legacy_tui_state_import_outcome_to_js(
    outcome: LegacyTuiStateImportOutcome,
) -> JsLegacyTuiStateImportOutcome {
    let mut result = JsLegacyTuiStateImportOutcome {
        status: String::new(),
        classification: None,
        revision: None,
        source_path: None,
        backup_path: None,
        source_revision: None,
        backup_revision: None,
        base_settings_revision: None,
        published_settings_revision: None,
        expected_revision: None,
        actual_revision: None,
        receipt: None,
    };
    match outcome {
        LegacyTuiStateImportOutcome::NoLegacySource => {
            result.status = "noLegacySource".to_string();
        }
        LegacyTuiStateImportOutcome::RequiresSettingsMigration {
            classification,
            revision,
        } => {
            result.status = "requiresSettingsMigration".to_string();
            result.classification = Some(js_token(classification.as_str()));
            result.revision = Some(revision.token());
        }
        LegacyTuiStateImportOutcome::UntrustedSettingsBase {
            classification,
            revision,
        } => {
            result.status = "untrustedSettingsBase".to_string();
            result.classification = Some(js_token(classification.as_str()));
            result.revision = Some(revision.token());
        }
        LegacyTuiStateImportOutcome::Applied(receipt) => {
            result.status = "applied".to_string();
            result.source_path = Some(receipt.source_path().display().to_string());
            result.backup_path = Some(receipt.backup_path().display().to_string());
            result.source_revision = Some(receipt.source_revision().token());
            result.backup_revision = Some(receipt.backup_revision().token());
            result.base_settings_revision = Some(receipt.base_settings_revision().token());
            result.published_settings_revision =
                Some(receipt.published_settings_revision().token());
            result.receipt = Some(JsLegacyTuiStateImportReceipt { inner: receipt });
        }
        LegacyTuiStateImportOutcome::SettingsConflict {
            expected_revision,
            actual_revision,
        } => {
            result.status = "settingsConflict".to_string();
            result.expected_revision = Some(expected_revision.token());
            result.actual_revision = Some(actual_revision.token());
        }
        LegacyTuiStateImportOutcome::LegacySourceConflict {
            expected_revision,
            actual_revision,
        } => {
            result.status = "legacySourceConflict".to_string();
            result.expected_revision = Some(expected_revision.token());
            result.actual_revision = Some(actual_revision.token());
        }
    }
    result
}

/// Returns the Rust-owned published User Settings defaults without accessing
/// the filesystem or creating a settings document.
#[napi]
pub fn published_user_settings_defaults() -> JsUserSettingsSnapshot {
    let settings = UserSettings::published_defaults();
    user_settings_snapshot_to_js(&settings)
}

/// Maps one core snapshot into the stable JavaScript snapshot shape.
fn user_settings_snapshot_to_js(settings: &UserSettings) -> JsUserSettingsSnapshot {
    let (schema_major, schema_minor) = settings
        .schema_version()
        .map_or((None, None), |(major, minor)| (Some(major), Some(minor)));

    JsUserSettingsSnapshot {
        update_preferences: JsUpdatePreferences {
            update_check: settings.update_preferences().update_check(),
            origin: js_token(settings.update_preferences().update_check_origin().as_str()),
            update_source: settings
                .update_preferences()
                .update_source()
                .as_str()
                .to_string(),
            update_source_origin: js_token(
                settings
                    .update_preferences()
                    .update_source_origin()
                    .as_str(),
            ),
        },
        crash_log_scan_settings: crash_log_scan_settings_to_js(settings),
        game_setup_settings: game_setup_settings_to_js(settings),
        frontend_state: frontend_state_to_js(settings),
        source_location: js_token(settings.source().location().as_str()),
        source_path: settings
            .source()
            .path()
            .map(|path| path.display().to_string()),
        classification: js_token(settings.classification().as_str()),
        schema_major,
        schema_minor,
        revision: settings.revision().token(),
        commit_eligibility: js_token(settings.commit_eligibility().as_str()),
        diagnostics: settings
            .diagnostics()
            .iter()
            .map(|diagnostic| JsUserSettingsDiagnostic {
                code: diagnostic.code().to_string(),
                message: diagnostic.message().to_string(),
            })
            .collect(),
        original_content: settings
            .original_bytes()
            .map(|content| Buffer::from(content.to_vec())),
    }
}

/// Produces a deterministic User Settings migration plan without changing files,
/// directories, timestamps, or backups under the supplied CLASSIC root.
#[napi]
pub fn plan_user_settings_migration(classic_root: String) -> JsUserSettingsMigrationPlanningResult {
    let settings = UserSettings::open(classic_root);
    match settings.plan_migration() {
        MigrationPlanningOutcome::NotRequired => JsUserSettingsMigrationPlanningResult {
            status: "notRequired".to_string(),
            plan: None,
            diagnostics: Vec::new(),
        },
        MigrationPlanningOutcome::Planned(plan) => JsUserSettingsMigrationPlanningResult {
            status: "planned".to_string(),
            plan: Some(user_settings_migration_plan_to_js(&plan)),
            diagnostics: Vec::new(),
        },
        MigrationPlanningOutcome::Unsupported(diagnostics) => {
            JsUserSettingsMigrationPlanningResult {
                status: "unsupported".to_string(),
                plan: None,
                diagnostics: diagnostics
                    .into_iter()
                    .map(|diagnostic| JsUserSettingsMigrationDiagnostic {
                        code: diagnostic.code().to_string(),
                        message: diagnostic.message().to_string(),
                    })
                    .collect(),
            }
        }
    }
}

/// Builds the exact inverse of a User Settings migration plan entirely in memory.
///
/// The DTO is reconstructed as an unattested core review plan, so Rust core owns endpoint,
/// byte, revision, and review-row reversal semantics while the adapter remains unable to
/// authorize persistence. The operation performs no filesystem access.
#[napi]
pub fn reverse_user_settings_migration_plan(
    plan: JsUserSettingsMigrationPlan,
) -> napi::Result<JsUserSettingsMigrationPlan, String> {
    let review_plan = user_settings_migration_plan_from_js(plan)?;
    Ok(user_settings_migration_plan_to_js(
        &review_plan.reverse_in_memory(),
    ))
}

/// Explicitly applies a caller-approved User Settings migration proposal.
///
/// The adapter reopens and re-plans from Rust-owned bytes, compares both the caller's
/// approved base revision and exact proposed content, and passes only that fresh core
/// plan to the persistence seam. Caller-owned DTO bytes are never published directly.
#[napi]
pub fn apply_user_settings_migration(
    classic_root: String,
    approved_base_revision: String,
    approved_proposed_content: Buffer,
) -> napi::Result<JsUserSettingsMigrationApplyResult, String> {
    let settings = UserSettings::open(&classic_root);
    let actual_revision = settings.revision().token();
    if actual_revision != approved_base_revision {
        return Ok(user_settings_migration_apply_conflict(
            approved_base_revision,
            actual_revision,
        ));
    }

    let plan = match settings.plan_migration() {
        MigrationPlanningOutcome::Planned(plan) => plan,
        MigrationPlanningOutcome::NotRequired => {
            return Err(user_settings_migration_error(
                "migration_plan_not_available",
                "the reopened User Settings document no longer requires or offers a migration plan",
            ));
        }
        MigrationPlanningOutcome::Unsupported(diagnostics) => {
            let message = diagnostics
                .iter()
                .map(|diagnostic| format!("{}: {}", diagnostic.code(), diagnostic.message()))
                .collect::<Vec<_>>()
                .join("; ");
            return Err(user_settings_migration_error(
                "migration_plan_not_available",
                if message.is_empty() {
                    "the reopened User Settings document cannot produce a migration plan"
                        .to_string()
                } else {
                    message
                },
            ));
        }
    };
    if plan.base_revision().token() != approved_base_revision {
        return Ok(user_settings_migration_apply_conflict(
            approved_base_revision,
            plan.base_revision().token(),
        ));
    }
    if plan.proposed_bytes() != approved_proposed_content.as_ref() {
        return Err(user_settings_migration_error(
            "migration_plan_approval_mismatch",
            "the approved proposed content does not match the fresh Rust-owned migration plan",
        ));
    }

    match plan.apply(&classic_root) {
        Ok(UserSettingsMigrationApplyOutcome::Applied(receipt)) => {
            Ok(JsUserSettingsMigrationApplyResult {
                status: "applied".to_string(),
                receipt: Some(JsUserSettingsMigrationReceipt { inner: receipt }),
                expected_revision: approved_base_revision,
                actual_revision: None,
            })
        }
        Ok(UserSettingsMigrationApplyOutcome::Conflict {
            expected_revision,
            actual_revision,
        }) => Ok(user_settings_migration_apply_conflict(
            expected_revision.token(),
            actual_revision.token(),
        )),
        Err(error) => Err(user_settings_migration_error(error.code(), error.message())),
    }
}

/// Converts an operational migration failure into an idiomatic JavaScript exception.
fn user_settings_migration_error(
    code: impl Into<String>,
    message: impl Into<String>,
) -> napi::Error<String> {
    napi::Error::new(code.into(), message.into())
}

/// Builds the shared no-write apply result for either revision comparison boundary.
fn user_settings_migration_apply_conflict(
    expected_revision: String,
    actual_revision: String,
) -> JsUserSettingsMigrationApplyResult {
    JsUserSettingsMigrationApplyResult {
        status: "conflict".to_string(),
        receipt: None,
        expected_revision,
        actual_revision: Some(actual_revision),
    }
}

/// Reconstructs a JavaScript DTO as an unattested core review plan.
///
/// The core deliberately prevents plans created through this conversion from authorizing
/// persistence; it exists only so adapters can delegate domain transformations such as reversal.
fn user_settings_migration_plan_from_js(
    plan: JsUserSettingsMigrationPlan,
) -> napi::Result<UserSettingsMigrationPlan, String> {
    let source = (
        source_location_from_token(&plan.source.location)?,
        plan.source
            .schema_version
            .map(|version| UserSettingsSchemaVersion::new(version.major, version.minor)),
    );
    let target = (
        source_location_from_token(&plan.target.location)?,
        plan.target
            .schema_version
            .map(|version| UserSettingsSchemaVersion::new(version.major, version.minor)),
    );
    let changes = plan
        .changes
        .into_iter()
        .map(|change| {
            Ok((
                migration_change_kind_from_token(&change.kind)?,
                change.source_path,
                change.target_path,
                change.before,
                change.after,
            ))
        })
        .collect::<napi::Result<Vec<_>, String>>()?;

    Ok(UserSettingsMigrationPlan::from((
        plan.required,
        source,
        target,
        changes,
        plan.original_content.to_vec(),
        plan.proposed_content.to_vec(),
    )))
}

/// Converts one core migration plan into its reviewable NAPI representation.
fn user_settings_migration_plan_to_js(
    plan: &UserSettingsMigrationPlan,
) -> JsUserSettingsMigrationPlan {
    JsUserSettingsMigrationPlan {
        required: plan.required(),
        base_revision: plan.base_revision().token(),
        source: migration_endpoint_to_js(plan.source()),
        target: migration_endpoint_to_js(plan.target()),
        changes: plan.changes().iter().map(migration_change_to_js).collect(),
        original_content: Buffer::from(plan.original_bytes().to_vec()),
        proposed_content: Buffer::from(plan.proposed_bytes().to_vec()),
    }
}

/// Converts one migration endpoint without interpreting its compatibility policy.
fn migration_endpoint_to_js(endpoint: &MigrationEndpoint) -> JsUserSettingsMigrationEndpoint {
    JsUserSettingsMigrationEndpoint {
        location: js_token(endpoint.location().as_str()),
        schema_version: endpoint.schema_version().map(schema_version_to_js),
    }
}

/// Converts an explicit core schema version into JavaScript number fields.
fn schema_version_to_js(version: UserSettingsSchemaVersion) -> JsUserSettingsSchemaVersion {
    JsUserSettingsSchemaVersion {
        major: version.major(),
        minor: version.minor(),
    }
}

/// Converts one ordered migration review row into a plain NAPI object.
fn migration_change_to_js(change: &MigrationChange) -> JsUserSettingsMigrationChange {
    JsUserSettingsMigrationChange {
        // The core token, camelized by the one shared rule this surface uses
        // for every enum.
        kind: js_token(change.kind().as_str()),
        source_path: change.source_path().map(ToOwned::to_owned),
        target_path: change.target_path().map(ToOwned::to_owned),
        before: change.before().map(ToOwned::to_owned),
        after: change.after().map(ToOwned::to_owned),
    }
}

/// Parses one stable JavaScript migration-change token for review-only core reconstruction.
///
/// Delegates to the shared casing projection rather than restating the token
/// table. The plan round-trips through JavaScript — emit tokens, hand them to
/// the caller, take them back, rebuild the plan — so a forward table and a
/// reverse table that disagreed would corrupt a reversal silently.
fn migration_change_kind_from_token(token: &str) -> napi::Result<MigrationChangeKind, String> {
    from_js_token(token).ok_or_else(|| {
        user_settings_migration_error(
            "migration_plan_review_invalid",
            format!("unsupported User Settings migration change kind: {token}"),
        )
    })
}

/// Converts the Rust-owned frontend state group into nested NAPI DTOs.
fn frontend_state_to_js(settings: &UserSettings) -> JsFrontendState {
    let frontend = settings.frontend_state();
    let preferences = frontend.preferences();
    let geometry = frontend.window_geometry();
    let tui = frontend.tui();

    JsFrontendState {
        preferences: JsFrontendPreferences {
            auto_switch_after_scan: preferences.auto_switch_after_scan(),
            auto_switch_after_scan_origin: js_token(
                preferences.auto_switch_after_scan_origin().as_str(),
            ),
            auto_refresh_interval_ms: preferences.auto_refresh_interval_ms() as f64,
            auto_refresh_interval_ms_origin: js_token(
                preferences.auto_refresh_interval_ms_origin().as_str(),
            ),
        },
        window_geometry: JsGuiWindowGeometry {
            main_tab: window_geometry_to_js(geometry.main_tab()),
            backups_tab: window_geometry_to_js(geometry.backups_tab()),
            articles_tab: window_geometry_to_js(geometry.articles_tab()),
            results_tab: window_geometry_to_js(geometry.results_tab()),
        },
        tui: JsTuiRememberedState {
            active_tab: tui.active_tab(),
            active_tab_origin: js_token(tui.active_tab_origin().as_str()),
            results_panel_width: tui.results_panel_width(),
            results_panel_width_origin: js_token(tui.results_panel_width_origin().as_str()),
            sort_ascending: tui.sort_ascending(),
            sort_ascending_origin: js_token(tui.sort_ascending_origin().as_str()),
        },
    }
}

/// Converts one core GUI-tab geometry value without interpreting widget state.
fn window_geometry_to_js(geometry: &WindowGeometry) -> JsWindowGeometry {
    JsWindowGeometry {
        maximized: geometry.maximized(),
        maximized_origin: js_token(geometry.maximized_origin().as_str()),
        width: geometry.width(),
        width_origin: js_token(geometry.width_origin().as_str()),
        height: geometry.height(),
        height_origin: js_token(geometry.height_origin().as_str()),
    }
}

/// Converts the Rust-owned Game Setup settings group into its NAPI DTO.
fn game_setup_settings_to_js(settings: &UserSettings) -> JsGameSetupSettings {
    let setup = settings.game_setup_settings();
    JsGameSetupSettings {
        managed_game: core_to_js_game_id(&setup.managed_game()),
        managed_game_origin: js_token(setup.managed_game_origin().as_str()),
        game_version_selection: setup.game_version_selection().as_str().to_string(),
        game_version_selection_origin: js_token(setup.game_version_selection_origin().as_str()),
        game_root: setup.game_root().map(ToOwned::to_owned),
        game_root_origin: js_token(setup.game_root_origin().as_str()),
        game_executable: setup.game_executable().map(ToOwned::to_owned),
        game_executable_origin: js_token(setup.game_executable_origin().as_str()),
        documents_root: setup.documents_root().map(ToOwned::to_owned),
        documents_root_origin: js_token(setup.documents_root_origin().as_str()),
        ini_folder: setup.ini_folder().map(ToOwned::to_owned),
        ini_folder_origin: js_token(setup.ini_folder_origin().as_str()),
        mods_root: setup.mods_root().map(ToOwned::to_owned),
        mods_root_origin: js_token(setup.mods_root_origin().as_str()),
        custom_scan_input: setup.custom_scan_input().map(ToOwned::to_owned),
        custom_scan_input_origin: js_token(setup.custom_scan_input_origin().as_str()),
        papyrus_log: setup.papyrus_log().map(ToOwned::to_owned),
        papyrus_log_origin: js_token(setup.papyrus_log_origin().as_str()),
    }
}

/// Opens User Settings relative to an explicit CLASSIC root and validates all
/// requested update fields as one unit without changing the source document.
#[napi]
pub fn preview_user_settings_update(
    classic_root: String,
    update: JsUserSettingsUpdate,
) -> JsUserSettingsUpdatePreview {
    let settings = UserSettings::open(classic_root);
    let preview = settings.preview_update(user_settings_update_to_core(update));
    user_settings_update_preview_to_js(preview)
}

/// Opens User Settings relative to an explicit CLASSIC root and previews an
/// explicit missing-document bootstrap without changing the filesystem.
///
/// Existing or unavailable documents are rejected with structured diagnostics;
/// callers must use the returned `missing` revision for the matching commit.
#[napi]
pub fn preview_user_settings_bootstrap(
    classic_root: String,
    update: JsUserSettingsUpdate,
) -> JsUserSettingsUpdatePreview {
    let settings = UserSettings::open(classic_root);
    let preview = settings.preview_bootstrap(user_settings_update_to_core(update));
    user_settings_update_preview_to_js(preview)
}

/// Commits an update that was previously accepted against `base_revision`.
///
/// The update is revalidated against the matching snapshot, then the core commit reopens the
/// document under cross-process coordination to close the remaining comparison/write race.
/// Revision conflicts and validation rejection are returned as structured data. Operational
/// failures throw a JavaScript `Error` whose `code` is the stable core commit error code.
///
/// @throws an `Error` with a stable `commit_*` code when the source cannot be reopened or durable
/// publication fails.
#[napi]
pub fn commit_user_settings_update(
    classic_root: String,
    base_revision: String,
    update: JsUserSettingsUpdate,
) -> napi::Result<JsUserSettingsCommitResult, String> {
    commit_user_settings(
        classic_root,
        base_revision,
        update,
        UserSettingsCommitKind::Update,
    )
}

/// Commits an explicitly previewed bootstrap against the `missing` revision.
///
/// The bootstrap publishes the complete Rust-owned defaults document plus the
/// accepted update. Existing documents return a structured revision conflict,
/// while validation rejection is returned without writing.
///
/// @throws an `Error` with a stable `commit_*` code when the source cannot be reopened or durable
/// publication fails.
#[napi]
pub fn commit_user_settings_bootstrap(
    classic_root: String,
    base_revision: String,
    update: JsUserSettingsUpdate,
) -> napi::Result<JsUserSettingsCommitResult, String> {
    commit_user_settings(
        classic_root,
        base_revision,
        update,
        UserSettingsCommitKind::Bootstrap,
    )
}

/// Publishes one GUI geometry transition with at most one Rust-owned conflict replay.
///
/// Validation rejection and a second concurrent edit return structured outcomes. Operational
/// reopen, lock, parse, and publication failures throw a JavaScript `Error` with the stable core
/// commit code and never partially persist the transition.
///
/// @throws an `Error` with a stable `commit_*` code when the transition cannot be published.
#[napi]
pub fn commit_frontend_geometry_transition(
    classic_root: String,
    expected_revision: String,
    window: JsGuiWindow,
    transition: JsWindowGeometryUpdate,
) -> napi::Result<JsUserSettingsCommitResult, String> {
    let expected = Revision::from_token(&expected_revision).ok_or_else(|| {
        user_settings_commit_error(
            "invalid_user_settings_revision",
            format!("unrecognized revision token {expected_revision:?}"),
        )
    })?;
    let window = match window {
        JsGuiWindow::Main => GuiWindow::Main,
        JsGuiWindow::Backups => GuiWindow::Backups,
        JsGuiWindow::Articles => GuiWindow::Articles,
        JsGuiWindow::Results => GuiWindow::Results,
    };
    match UserSettings::commit_frontend_geometry_transition(
        &classic_root,
        &expected,
        window,
        transition.maximized,
        geometry_dimension_to_core(transition.width),
        geometry_dimension_to_core(transition.height),
    ) {
        Ok(CoreUserSettingsFrontendTransitionOutcome::Committed { revision }) => {
            Ok(JsUserSettingsCommitResult {
                status: "committed".to_string(),
                revision: Some(revision.token()),
                expected_revision,
                actual_revision: None,
                diagnostics: Vec::new(),
            })
        }
        Ok(CoreUserSettingsFrontendTransitionOutcome::Rejected { diagnostics }) => {
            Ok(JsUserSettingsCommitResult {
                status: "rejected".to_string(),
                revision: None,
                expected_revision,
                actual_revision: None,
                diagnostics: diagnostics
                    .into_iter()
                    .map(user_settings_update_diagnostic_to_js)
                    .collect(),
            })
        }
        Ok(CoreUserSettingsFrontendTransitionOutcome::Conflict {
            expected_revision,
            actual_revision,
        }) => Ok(user_settings_commit_conflict(
            expected_revision.token(),
            actual_revision.token(),
        )),
        Err(error) => Err(user_settings_commit_error(error.code(), error.message())),
    }
}

/// Selects which core preview contract must be revalidated immediately before commit.
#[derive(Clone, Copy)]
enum UserSettingsCommitKind {
    Update,
    Bootstrap,
}

/// Reopens, revision-checks, revalidates, and commits one typed User Settings operation.
fn commit_user_settings(
    classic_root: String,
    base_revision: String,
    update: JsUserSettingsUpdate,
    kind: UserSettingsCommitKind,
) -> napi::Result<JsUserSettingsCommitResult, String> {
    let settings = UserSettings::open(&classic_root);
    let actual_revision = settings.revision().token();
    if matches!(settings.revision(), Revision::Unavailable) {
        return Err(user_settings_commit_error(
            "commit_source_unavailable",
            "User Settings could not be reopened before commit validation",
        ));
    }
    if actual_revision != base_revision {
        return Ok(user_settings_commit_conflict(
            base_revision,
            actual_revision,
        ));
    }

    let core_update = user_settings_update_to_core(update);
    let preview = match kind {
        UserSettingsCommitKind::Update => settings.preview_update(core_update),
        UserSettingsCommitKind::Bootstrap => settings.preview_bootstrap(core_update),
    };
    let accepted = match preview {
        UserSettingsUpdatePreview::Accepted(accepted) => accepted,
        UserSettingsUpdatePreview::Rejected(diagnostics) => {
            return Ok(JsUserSettingsCommitResult {
                status: "rejected".to_string(),
                revision: None,
                expected_revision: base_revision,
                actual_revision: None,
                diagnostics: diagnostics
                    .into_iter()
                    .map(user_settings_update_diagnostic_to_js)
                    .collect(),
            });
        }
    };

    match accepted.commit(&classic_root) {
        Ok(UserSettingsCommitOutcome::Committed { revision }) => Ok(JsUserSettingsCommitResult {
            status: "committed".to_string(),
            revision: Some(revision.token()),
            expected_revision: base_revision,
            actual_revision: None,
            diagnostics: Vec::new(),
        }),
        Ok(UserSettingsCommitOutcome::Conflict {
            expected_revision,
            actual_revision,
        }) => Ok(user_settings_commit_conflict(
            expected_revision.token(),
            actual_revision.token(),
        )),
        Err(error) => Err(user_settings_commit_error(error.code(), error.message())),
    }
}

/// Converts one operational commit failure into an idiomatic JavaScript exception.
fn user_settings_commit_error(
    code: impl Into<String>,
    message: impl Into<String>,
) -> napi::Error<String> {
    napi::Error::new(code.into(), message.into())
}

/// Builds the shared no-write result for either revision comparison boundary.
fn user_settings_commit_conflict(
    expected_revision: String,
    actual_revision: String,
) -> JsUserSettingsCommitResult {
    JsUserSettingsCommitResult {
        status: "conflict".to_string(),
        revision: None,
        expected_revision,
        actual_revision: Some(actual_revision),
        diagnostics: Vec::new(),
    }
}

/// Converts the Rust-owned Crash Log Scan settings group into its NAPI DTO.
fn crash_log_scan_settings_to_js(settings: &UserSettings) -> JsCrashLogScanSettings {
    let scan = settings.crash_log_scan_settings();
    JsCrashLogScanSettings {
        fcx_mode: scan.fcx_mode(),
        fcx_mode_origin: js_token(scan.fcx_mode_origin().as_str()),
        simplify_logs: scan.simplify_logs(),
        simplify_logs_origin: js_token(scan.simplify_logs_origin().as_str()),
        show_statistics: scan.show_statistics(),
        show_statistics_origin: js_token(scan.show_statistics_origin().as_str()),
        formid_value_lookup: scan.formid_value_lookup(),
        formid_value_lookup_origin: js_token(scan.formid_value_lookup_origin().as_str()),
        formid_databases: scan
            .formid_databases()
            .iter()
            .map(|(game, paths)| (game.clone(), paths.clone()))
            .collect(),
        formid_databases_origin: js_token(scan.formid_databases_origin().as_str()),
        move_unsolved_logs: scan.move_unsolved_logs(),
        move_unsolved_logs_origin: js_token(scan.move_unsolved_logs_origin().as_str()),
        unsolved_logs_destination: scan.unsolved_logs_destination().map(ToOwned::to_owned),
        unsolved_logs_destination_origin: js_token(
            scan.unsolved_logs_destination_origin().as_str(),
        ),
        custom_scan_input: scan.custom_scan_input().map(ToOwned::to_owned),
        custom_scan_input_origin: js_token(scan.custom_scan_input_origin().as_str()),
        game_version_selection: scan.game_version_selection().as_str().to_string(),
        game_version_selection_origin: js_token(scan.game_version_selection_origin().as_str()),
        max_concurrent_scans: scan.max_concurrent_scans(),
        max_concurrent_scans_origin: js_token(scan.max_concurrent_scans_origin().as_str()),
    }
}

/// Converts the typed NAPI update request into the Rust core builder.
fn user_settings_update_to_core(update: JsUserSettingsUpdate) -> UserSettingsUpdate {
    let mut core = UserSettingsUpdate::new();
    if let Some(value) = update.update_check {
        core = core.with_update_check(value);
    }
    if let Some(value) = update.update_source {
        core = core.with_update_source(value);
    }
    if let Some(value) = update.auto_switch_after_scan {
        core = core.with_auto_switch_after_scan(value);
    }
    if let Some(value) = update.window_geometry {
        let JsGuiWindowGeometryUpdate {
            main_tab,
            backups_tab,
            articles_tab,
            results_tab,
        } = value;
        for (window, geometry) in [
            (GuiWindow::Main, main_tab),
            (GuiWindow::Backups, backups_tab),
            (GuiWindow::Articles, articles_tab),
            (GuiWindow::Results, results_tab),
        ] {
            if let Some(geometry) = geometry {
                core = core.with_window_geometry(
                    window,
                    geometry.maximized,
                    geometry_dimension_to_core(geometry.width),
                    geometry_dimension_to_core(geometry.height),
                );
            }
        }
    }
    if let Some(value) = update.tui {
        core = core.with_tui_remembered_state(
            tui_integer_to_core(value.active_tab),
            tui_integer_to_core(value.results_panel_width),
            value.sort_ascending,
        );
    }
    if let Some(value) = update.managed_game {
        core = core.with_managed_game(js_to_core_game_id(&value).as_str());
    }
    if let Some(value) = update.game_version_selection {
        core = core.with_game_version_selection(value);
    }
    if let Some(value) = update.game_root {
        core = core.with_game_root(nullable_string_to_option(value));
    }
    if let Some(value) = update.game_executable {
        core = core.with_game_executable(nullable_string_to_option(value));
    }
    if let Some(value) = update.documents_root {
        core = core.with_documents_root(nullable_string_to_option(value));
    }
    if let Some(value) = update.ini_folder {
        core = core.with_ini_folder(nullable_string_to_option(value));
    }
    if let Some(value) = update.mods_folder {
        core = core.with_mods_folder(nullable_string_to_option(value));
    }
    if let Some(value) = update.fcx_mode {
        core = core.with_fcx_mode(value);
    }
    if let Some(value) = update.simplify_logs {
        core = core.with_simplify_logs(value);
    }
    if let Some(value) = update.show_statistics {
        core = core.with_show_statistics(value);
    }
    if let Some(value) = update.formid_value_lookup {
        core = core.with_formid_value_lookup(value);
    }
    if let Some(value) = update.formid_databases {
        core = core.with_formid_databases(value.into_iter().collect());
    }
    if let Some(value) = update.move_unsolved_logs {
        core = core.with_move_unsolved_logs(value);
    }
    if let Some(value) = update.unsolved_logs_destination {
        core = core.with_unsolved_logs_destination(nullable_string_to_option(value));
    }
    if let Some(value) = update.custom_scan_input {
        core = core.with_custom_scan_input(nullable_string_to_option(value));
    }
    if let Some(value) = update.papyrus_log_path {
        core = core.with_papyrus_log_path(nullable_string_to_option(value));
    }
    if let Some(value) = update.max_concurrent_scans {
        core = core.with_max_concurrent_scans(scan_concurrency_to_core(value));
    }
    core
}

/// Preserves JavaScript number range until core validation handles the request.
///
/// Non-finite and fractional numbers use a guaranteed-invalid sentinel so they
/// receive the same field-specific core rejection as other out-of-range values.
fn scan_concurrency_to_core(value: f64) -> i64 {
    if value.is_finite() && value.fract() == 0.0 {
        value as i64
    } else {
        -1
    }
}

/// Preserves one JavaScript geometry dimension until core preview validates its range.
///
/// Non-finite and fractional numbers use a guaranteed-invalid sentinel so callers receive
/// the stable width- or height-specific core diagnostic instead of a conversion failure.
fn geometry_dimension_to_core(value: f64) -> i64 {
    if value.is_finite() && value.fract() == 0.0 {
        value as i64
    } else {
        0
    }
}

/// Preserves one JavaScript TUI integer until the core validates its field-specific range.
///
/// Non-finite and fractional numbers use a guaranteed-invalid sentinel so the complete
/// transition is rejected with the same stable diagnostics as other out-of-range values.
fn tui_integer_to_core(value: f64) -> i64 {
    if value.is_finite() && value.fract() == 0.0 {
        value as i64
    } else {
        -1
    }
}

/// Converts an explicit JavaScript string-or-null input into the core optional value.
fn nullable_string_to_option(value: Either<String, Null>) -> Option<String> {
    match value {
        Either::A(value) => Some(value),
        Either::B(_) => None,
    }
}

/// Converts the Rust-owned all-or-nothing preview into its NAPI DTO.
fn user_settings_update_preview_to_js(
    preview: UserSettingsUpdatePreview,
) -> JsUserSettingsUpdatePreview {
    match preview {
        UserSettingsUpdatePreview::Accepted(accepted) => JsUserSettingsUpdatePreview {
            accepted: true,
            base_revision: Some(accepted.base_revision().token()),
            fields: accepted
                .fields()
                .iter()
                .map(user_settings_update_field_to_js)
                .collect(),
            diagnostics: Vec::new(),
        },
        UserSettingsUpdatePreview::Rejected(diagnostics) => JsUserSettingsUpdatePreview {
            accepted: false,
            base_revision: None,
            fields: Vec::new(),
            diagnostics: diagnostics
                .into_iter()
                .map(user_settings_update_diagnostic_to_js)
                .collect(),
        },
    }
}

/// Converts one core update rejection into the shared NAPI diagnostic DTO.
fn user_settings_update_diagnostic_to_js(
    diagnostic: classic_user_settings_core::UpdateDiagnostic,
) -> JsUserSettingsUpdateDiagnostic {
    JsUserSettingsUpdateDiagnostic {
        field_path: diagnostic.field_path().map(ToOwned::to_owned),
        code: diagnostic.code().to_string(),
        message: diagnostic.message().to_string(),
    }
}

/// Converts one accepted core field into a canonical path and typed JS value.
fn user_settings_update_field_to_js(field: &UserSettingsUpdateField) -> JsUserSettingsUpdateField {
    let value = match field {
        UserSettingsUpdateField::UpdateCheck(value)
        | UserSettingsUpdateField::AutoSwitchAfterScan(value)
        | UserSettingsUpdateField::WindowMaximized(_, value)
        | UserSettingsUpdateField::TuiSortAscending(value)
        | UserSettingsUpdateField::FcxMode(value)
        | UserSettingsUpdateField::SimplifyLogs(value)
        | UserSettingsUpdateField::ShowStatistics(value)
        | UserSettingsUpdateField::FormIdValueLookup(value)
        | UserSettingsUpdateField::MoveUnsolvedLogs(value) => Either5::A(*value),
        UserSettingsUpdateField::GameVersionSelection(value) => {
            Either5::B(value.as_str().to_string())
        }
        UserSettingsUpdateField::ManagedGame(value) => Either5::B(value.as_str().to_string()),
        UserSettingsUpdateField::UpdateSource(value) => Either5::B(value.as_str().to_string()),
        UserSettingsUpdateField::FormIdDatabases(value) => Either5::C(
            value
                .iter()
                .map(|(game, paths)| (game.clone(), paths.clone()))
                .collect(),
        ),
        UserSettingsUpdateField::GameRoot(value)
        | UserSettingsUpdateField::GameExecutable(value)
        | UserSettingsUpdateField::DocumentsRoot(value)
        | UserSettingsUpdateField::IniFolder(value)
        | UserSettingsUpdateField::ModsFolder(value)
        | UserSettingsUpdateField::PapyrusLogPath(value)
        | UserSettingsUpdateField::UnsolvedLogsDestination(value)
        | UserSettingsUpdateField::CustomScanInput(value) => match value {
            Some(value) => Either5::B(value.clone()),
            None => Either5::E(Null),
        },
        UserSettingsUpdateField::WindowWidth(_, value)
        | UserSettingsUpdateField::WindowHeight(_, value)
        | UserSettingsUpdateField::MaxConcurrentScans(value) => Either5::D(*value),
        UserSettingsUpdateField::TuiActiveTab(value) => Either5::D(u32::from(*value)),
        UserSettingsUpdateField::TuiResultsPanelWidth(value) => Either5::D(u32::from(*value)),
    };

    JsUserSettingsUpdateField {
        field_path: field.canonical_path().to_string(),
        value,
    }
}

// The Vocabulary Tokens for preference origin, source location, document
// classification, and commit eligibility are owned by
// `classic-user-settings-core`. This surface projects `Vocabulary::as_str`
// through `js_token`, the one shared casing rule it applies
// to every enum, so the four hand-written camelCase tables that used to live
// here are gone rather than delegating.

/// Parses one stable JavaScript source-location token for review-only core reconstruction.
///
/// Delegates to the shared casing projection rather than restating the token
/// table. The plan round-trips through JavaScript — emit tokens, hand them to
/// the caller, take them back, rebuild the plan — so a forward table and a
/// reverse table that disagreed would corrupt a reversal silently.
fn source_location_from_token(token: &str) -> napi::Result<SourceLocation, String> {
    from_js_token(token).ok_or_else(|| {
        user_settings_migration_error(
            "migration_plan_review_invalid",
            format!("unsupported User Settings source location: {token}"),
        )
    })
}

// The revision token pair is owned by `classic-user-settings-core`
// (`Revision::token` / `Revision::from_token`) so the CXX, Node, and Python
// surfaces cannot drift apart. Unlike the finite domain enums above, the
// revision token is not casing-transformed: `missing`, `unavailable`, and
// `sha256:<hex>` are already single-word or content-derived.

#[cfg(test)]
#[path = "user_settings_tests.rs"]
mod tests;
