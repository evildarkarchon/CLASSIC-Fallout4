//! Thin NAPI adapter for read-only User Settings and non-persisting update previews.

use crate::shared::{JsGameId, core_to_js_game_id, js_to_core_game_id};
use classic_user_settings_core::{
    CommitEligibility, DocumentClassification, PreferenceOrigin, Revision, SourceLocation,
    UserSettings, UserSettingsUpdate, UserSettingsUpdateField, UserSettingsUpdatePreview,
    WindowGeometry,
};
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

/// Update-related User Settings consumed by update-check policy.
#[napi(object)]
pub struct JsUpdatePreferences {
    /// Whether first-party update checks are enabled after safe fallback policy.
    pub update_check: bool,
    /// Provenance token: `document`, `default`, or `degradedFallback`.
    pub origin: String,
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
    let (schema_major, schema_minor) = settings
        .schema_version()
        .map_or((None, None), |(major, minor)| (Some(major), Some(minor)));

    JsUserSettingsSnapshot {
        update_preferences: JsUpdatePreferences {
            update_check: settings.update_preferences().update_check(),
            origin: preference_origin_token(settings.update_preferences().update_check_origin())
                .to_string(),
        },
        crash_log_scan_settings: crash_log_scan_settings_to_js(&settings),
        game_setup_settings: game_setup_settings_to_js(&settings),
        frontend_state: frontend_state_to_js(&settings),
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

/// Converts the Rust-owned frontend state group into nested NAPI DTOs.
fn frontend_state_to_js(settings: &UserSettings) -> JsFrontendState {
    let frontend = settings.frontend_state();
    let preferences = frontend.preferences();
    let geometry = frontend.window_geometry();
    let tui = frontend.tui();

    JsFrontendState {
        preferences: JsFrontendPreferences {
            auto_switch_after_scan: preferences.auto_switch_after_scan(),
            auto_switch_after_scan_origin: preference_origin_token(
                preferences.auto_switch_after_scan_origin(),
            )
            .to_string(),
            auto_refresh_interval_ms: preferences.auto_refresh_interval_ms() as f64,
            auto_refresh_interval_ms_origin: preference_origin_token(
                preferences.auto_refresh_interval_ms_origin(),
            )
            .to_string(),
        },
        window_geometry: JsGuiWindowGeometry {
            main_tab: window_geometry_to_js(geometry.main_tab()),
            backups_tab: window_geometry_to_js(geometry.backups_tab()),
            articles_tab: window_geometry_to_js(geometry.articles_tab()),
            results_tab: window_geometry_to_js(geometry.results_tab()),
        },
        tui: JsTuiRememberedState {
            active_tab: tui.active_tab(),
            active_tab_origin: preference_origin_token(tui.active_tab_origin()).to_string(),
            results_panel_width: tui.results_panel_width(),
            results_panel_width_origin: preference_origin_token(tui.results_panel_width_origin())
                .to_string(),
            sort_ascending: tui.sort_ascending(),
            sort_ascending_origin: preference_origin_token(tui.sort_ascending_origin()).to_string(),
        },
    }
}

/// Converts one core GUI-tab geometry value without interpreting widget state.
fn window_geometry_to_js(geometry: &WindowGeometry) -> JsWindowGeometry {
    JsWindowGeometry {
        maximized: geometry.maximized(),
        maximized_origin: preference_origin_token(geometry.maximized_origin()).to_string(),
        width: geometry.width(),
        width_origin: preference_origin_token(geometry.width_origin()).to_string(),
        height: geometry.height(),
        height_origin: preference_origin_token(geometry.height_origin()).to_string(),
    }
}

/// Converts the Rust-owned Game Setup settings group into its NAPI DTO.
fn game_setup_settings_to_js(settings: &UserSettings) -> JsGameSetupSettings {
    let setup = settings.game_setup_settings();
    JsGameSetupSettings {
        managed_game: core_to_js_game_id(&setup.managed_game()),
        managed_game_origin: preference_origin_token(setup.managed_game_origin()).to_string(),
        game_version_selection: setup.game_version_selection().as_str().to_string(),
        game_version_selection_origin: preference_origin_token(
            setup.game_version_selection_origin(),
        )
        .to_string(),
        game_root: setup.game_root().map(ToOwned::to_owned),
        game_root_origin: preference_origin_token(setup.game_root_origin()).to_string(),
        game_executable: setup.game_executable().map(ToOwned::to_owned),
        game_executable_origin: preference_origin_token(setup.game_executable_origin()).to_string(),
        documents_root: setup.documents_root().map(ToOwned::to_owned),
        documents_root_origin: preference_origin_token(setup.documents_root_origin()).to_string(),
        ini_folder: setup.ini_folder().map(ToOwned::to_owned),
        ini_folder_origin: preference_origin_token(setup.ini_folder_origin()).to_string(),
        mods_root: setup.mods_root().map(ToOwned::to_owned),
        mods_root_origin: preference_origin_token(setup.mods_root_origin()).to_string(),
        custom_scan_input: setup.custom_scan_input().map(ToOwned::to_owned),
        custom_scan_input_origin: preference_origin_token(setup.custom_scan_input_origin())
            .to_string(),
        papyrus_log: setup.papyrus_log().map(ToOwned::to_owned),
        papyrus_log_origin: preference_origin_token(setup.papyrus_log_origin()).to_string(),
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

/// Converts the Rust-owned Crash Log Scan settings group into its NAPI DTO.
fn crash_log_scan_settings_to_js(settings: &UserSettings) -> JsCrashLogScanSettings {
    let scan = settings.crash_log_scan_settings();
    JsCrashLogScanSettings {
        fcx_mode: scan.fcx_mode(),
        fcx_mode_origin: preference_origin_token(scan.fcx_mode_origin()).to_string(),
        simplify_logs: scan.simplify_logs(),
        simplify_logs_origin: preference_origin_token(scan.simplify_logs_origin()).to_string(),
        show_statistics: scan.show_statistics(),
        show_statistics_origin: preference_origin_token(scan.show_statistics_origin()).to_string(),
        formid_value_lookup: scan.formid_value_lookup(),
        formid_value_lookup_origin: preference_origin_token(scan.formid_value_lookup_origin())
            .to_string(),
        formid_databases: scan
            .formid_databases()
            .iter()
            .map(|(game, paths)| (game.clone(), paths.clone()))
            .collect(),
        formid_databases_origin: preference_origin_token(scan.formid_databases_origin())
            .to_string(),
        move_unsolved_logs: scan.move_unsolved_logs(),
        move_unsolved_logs_origin: preference_origin_token(scan.move_unsolved_logs_origin())
            .to_string(),
        unsolved_logs_destination: scan.unsolved_logs_destination().map(ToOwned::to_owned),
        unsolved_logs_destination_origin: preference_origin_token(
            scan.unsolved_logs_destination_origin(),
        )
        .to_string(),
        custom_scan_input: scan.custom_scan_input().map(ToOwned::to_owned),
        custom_scan_input_origin: preference_origin_token(scan.custom_scan_input_origin())
            .to_string(),
        game_version_selection: scan.game_version_selection().as_str().to_string(),
        game_version_selection_origin: preference_origin_token(
            scan.game_version_selection_origin(),
        )
        .to_string(),
        max_concurrent_scans: scan.max_concurrent_scans(),
        max_concurrent_scans_origin: preference_origin_token(scan.max_concurrent_scans_origin())
            .to_string(),
    }
}

/// Converts the typed NAPI update request into the Rust core builder.
fn user_settings_update_to_core(update: JsUserSettingsUpdate) -> UserSettingsUpdate {
    let mut core = UserSettingsUpdate::new();
    if let Some(value) = update.update_check {
        core = core.with_update_check(value);
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
            base_revision: Some(revision_token(accepted.base_revision())),
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
                .map(|diagnostic| JsUserSettingsUpdateDiagnostic {
                    field_path: diagnostic.field_path().map(ToOwned::to_owned),
                    code: diagnostic.code().to_string(),
                    message: diagnostic.message().to_string(),
                })
                .collect(),
        },
    }
}

/// Converts one accepted core field into a canonical path and typed JS value.
fn user_settings_update_field_to_js(field: &UserSettingsUpdateField) -> JsUserSettingsUpdateField {
    let value = match field {
        UserSettingsUpdateField::UpdateCheck(value)
        | UserSettingsUpdateField::FcxMode(value)
        | UserSettingsUpdateField::SimplifyLogs(value)
        | UserSettingsUpdateField::ShowStatistics(value)
        | UserSettingsUpdateField::FormIdValueLookup(value)
        | UserSettingsUpdateField::MoveUnsolvedLogs(value) => Either5::A(*value),
        UserSettingsUpdateField::GameVersionSelection(value) => {
            Either5::B(value.as_str().to_string())
        }
        UserSettingsUpdateField::ManagedGame(value) => Either5::B(value.as_str().to_string()),
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
        UserSettingsUpdateField::MaxConcurrentScans(value) => Either5::D(*value),
    };

    JsUserSettingsUpdateField {
        field_path: field.canonical_path().to_string(),
        value,
    }
}

/// Returns the JavaScript token for preference provenance.
fn preference_origin_token(origin: PreferenceOrigin) -> &'static str {
    match origin {
        PreferenceOrigin::Document => "document",
        PreferenceOrigin::Default => "default",
        PreferenceOrigin::DegradedFallback => "degradedFallback",
    }
}

/// Returns the JavaScript token for source location.
fn source_location_token(location: SourceLocation) -> &'static str {
    match location {
        SourceLocation::Canonical => "canonical",
        SourceLocation::Legacy => "legacy",
        SourceLocation::Missing => "missing",
    }
}

/// Returns the JavaScript token for document classification.
fn classification_token(classification: DocumentClassification) -> &'static str {
    match classification {
        DocumentClassification::Current => "current",
        DocumentClassification::Unversioned => "unversioned",
        DocumentClassification::Older => "older",
        DocumentClassification::NewerCompatible => "newerCompatible",
        DocumentClassification::FutureMajor => "futureMajor",
        DocumentClassification::LegacyFlat => "legacyFlat",
        DocumentClassification::Malformed => "malformed",
        DocumentClassification::Missing => "missing",
    }
}

/// Returns the JavaScript token for commit eligibility.
fn commit_eligibility_token(eligibility: CommitEligibility) -> &'static str {
    match eligibility {
        CommitEligibility::Eligible => "eligible",
        CommitEligibility::RequiresMigration => "requiresMigration",
        CommitEligibility::BlockedUntrusted => "blockedUntrusted",
    }
}

/// Formats the content revision for JavaScript consumers.
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
