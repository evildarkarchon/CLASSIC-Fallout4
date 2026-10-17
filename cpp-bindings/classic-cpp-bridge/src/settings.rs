//! Settings operations bridge for CXX FFI.
//!
//! Bridges the surfaces the CLI and GUI call. The bridge is consumer-driven, so
//! the rest of the YAML and User Settings surface stays Rust-only until a
//! frontend calls it.
//!
//! 1. **YAML operations**: File loading and string settings access via
//!    dot-notation keys. Delegates to `classic_shared_core::yaml::YamlOperations`,
//!    which uses the default (unscoped) path/mtime-aware YAML-file cache of this
//!    linked library.
//! 2. **User Settings**: Opens the deep User Settings module from an explicit
//!    CLASSIC root, returns typed Update, Crash Log Scan, and Game Setup groups,
//!    previews and commits caller-authored updates, and silently applies a
//!    required migration at frontend startup.

use classic_shared_core::yaml::YamlOperations;
use classic_user_settings_core::{
    AutomaticMigrationOutcome, GuiWindow, Revision, UserSettings,
    UserSettingsCommitOutcome as CoreUserSettingsCommitOutcome,
    UserSettingsFrontendTransitionOutcome as CoreUserSettingsFrontendTransitionOutcome,
    UserSettingsUpdate as CoreUserSettingsUpdate,
    UserSettingsUpdateField as CoreUserSettingsUpdateField,
    UserSettingsUpdatePreview as CoreUserSettingsUpdatePreview, WindowGeometry,
    migrate_if_required,
};
use classic_vocabulary::Vocabulary;
use std::{collections::BTreeMap, path::Path};
use yaml_rust2::Yaml;

/// Opaque wrapper around `YamlOperations` + a loaded YAML document.
pub struct YamlOps {
    ops: YamlOperations,
    doc: Option<Yaml>,
}

// ── Typed User Settings ─────────────────────────────────────────────

/// Opens User Settings at an explicit CLASSIC root and flattens the typed
/// Update Preferences view into a CXX-compatible diagnostic DTO.
fn user_settings_open_update_preferences(classic_root: &str) -> ffi::UpdatePreferencesDto {
    let settings = UserSettings::open(Path::new(classic_root));
    user_settings_update_preferences_dto(&settings)
}

/// Projects Update Preferences from an already-opened cohesive User Settings snapshot.
fn user_settings_update_preferences_dto(settings: &UserSettings) -> ffi::UpdatePreferencesDto {
    let source = settings.source();
    let (has_schema_version, schema_major, schema_minor) = settings
        .schema_version()
        .map_or((false, 0, 0), |(major, minor)| (true, major, minor));
    let (has_original_content, original_content) = settings
        .original_bytes()
        .map_or((false, Vec::new()), |content| (true, content.to_vec()));

    ffi::UpdatePreferencesDto {
        update_check_enabled: settings.update_preferences().update_check(),
        update_check_origin: settings
            .update_preferences()
            .update_check_origin()
            .as_str()
            .to_string(),
        update_source: settings
            .update_preferences()
            .update_source()
            .as_str()
            .to_string(),
        update_source_origin: settings
            .update_preferences()
            .update_source_origin()
            .as_str()
            .to_string(),
        source_location: source.location().as_str().to_string(),
        source_path: source
            .path()
            .map_or_else(String::new, |path| path.display().to_string()),
        classification: settings.classification().as_str().to_string(),
        has_schema_version,
        schema_major,
        schema_minor,
        revision: settings.revision().token(),
        commit_eligibility: settings.commit_eligibility().as_str().to_string(),
        diagnostics: settings
            .diagnostics()
            .iter()
            .map(|diagnostic| ffi::UserSettingsDiagnosticDto {
                code: diagnostic.code().to_string(),
                message: diagnostic.message().to_string(),
            })
            .collect(),
        has_original_content,
        original_content,
    }
}

/// Silently applies a required User Settings migration before the frontend first opens settings.
///
/// The Rust core decides whether a migration is required and owns backup, publication, and
/// rollback; this adapter only flattens the outcome. `status` is `not_required`, `applied`,
/// `unavailable`, `conflict`, or `failed`. Only `applied` changes the filesystem, so callers
/// continue with an ordinary open whatever the status, and may surface `diagnostics` without
/// interrupting the user.
fn user_settings_migrate_if_required(classic_root: &str) -> ffi::UserSettingsAutomaticMigrationDto {
    let diagnostic = |code: &str, message: String| ffi::UserSettingsDiagnosticDto {
        code: code.to_string(),
        message,
    };
    let (status, backup_path, diagnostics) = match migrate_if_required(Path::new(classic_root)) {
        AutomaticMigrationOutcome::NotRequired => ("not_required", String::new(), Vec::new()),
        AutomaticMigrationOutcome::Applied(receipt) => (
            "applied",
            receipt.backup_path().display().to_string(),
            Vec::new(),
        ),
        AutomaticMigrationOutcome::Unavailable(diagnostics) => (
            "unavailable",
            String::new(),
            diagnostics
                .iter()
                .map(|item| diagnostic(item.code(), item.message().to_string()))
                .collect(),
        ),
        AutomaticMigrationOutcome::Conflict {
            expected_revision,
            actual_revision,
        } => (
            "conflict",
            String::new(),
            vec![diagnostic(
                "migration_conflict",
                format!(
                    "User Settings changed while migrating (expected {}, found {}); \
                     migration will be retried on the next start",
                    expected_revision.token(),
                    actual_revision.token()
                ),
            )],
        ),
        AutomaticMigrationOutcome::Failed(error) => (
            "failed",
            String::new(),
            vec![diagnostic(error.code(), error.message().to_string())],
        ),
    };
    ffi::UserSettingsAutomaticMigrationDto {
        status: status.to_string(),
        backup_path,
        diagnostics,
    }
}

/// Opens User Settings at an explicit CLASSIC root and returns the safety-adjusted
/// Crash Log Scan settings group without exposing or reinterpreting raw YAML.
fn user_settings_open_crash_log_scan_settings(classic_root: &str) -> ffi::CrashLogScanSettingsDto {
    let settings = UserSettings::open(Path::new(classic_root));
    user_settings_crash_log_scan_settings_dto(&settings)
}

/// Projects Crash Log Scan settings from an already-opened cohesive User Settings snapshot.
fn user_settings_crash_log_scan_settings_dto(
    settings: &UserSettings,
) -> ffi::CrashLogScanSettingsDto {
    let scan = settings.crash_log_scan_settings();
    let (formid_database_games, formid_database_paths) =
        flatten_formid_databases(scan.formid_databases());
    let (has_unsolved_logs_destination, unsolved_logs_destination) = scan
        .unsolved_logs_destination()
        .map_or((false, String::new()), |value| (true, value.to_string()));
    let (has_custom_scan_input, custom_scan_input) = scan
        .custom_scan_input()
        .map_or((false, String::new()), |value| (true, value.to_string()));

    ffi::CrashLogScanSettingsDto {
        fcx_mode: scan.fcx_mode(),
        fcx_mode_origin: scan.fcx_mode_origin().as_str().to_string(),
        simplify_logs: scan.simplify_logs(),
        simplify_logs_origin: scan.simplify_logs_origin().as_str().to_string(),
        show_statistics: scan.show_statistics(),
        show_statistics_origin: scan.show_statistics_origin().as_str().to_string(),
        formid_value_lookup: scan.formid_value_lookup(),
        formid_value_lookup_origin: scan.formid_value_lookup_origin().as_str().to_string(),
        formid_database_games,
        formid_database_paths,
        formid_databases_origin: scan.formid_databases_origin().as_str().to_string(),
        scan_formid_database_paths: scan_formid_database_paths(scan),
        move_unsolved_logs: scan.move_unsolved_logs(),
        move_unsolved_logs_origin: scan.move_unsolved_logs_origin().as_str().to_string(),
        has_unsolved_logs_destination,
        unsolved_logs_destination,
        unsolved_logs_destination_origin: scan
            .unsolved_logs_destination_origin()
            .as_str()
            .to_string(),
        has_custom_scan_input,
        custom_scan_input,
        custom_scan_input_origin: scan.custom_scan_input_origin().as_str().to_string(),
        game_version_selection: scan.game_version_selection().as_str().to_string(),
        game_version_selection_origin: scan.game_version_selection_origin().as_str().to_string(),
        max_concurrent_scans: scan.max_concurrent_scans(),
        max_concurrent_scans_origin: scan.max_concurrent_scans_origin().as_str().to_string(),
        classification: settings.classification().as_str().to_string(),
        revision: settings.revision().token(),
        commit_eligibility: settings.commit_eligibility().as_str().to_string(),
        diagnostics: settings
            .diagnostics()
            .iter()
            .map(user_settings_diagnostic_dto)
            .collect(),
    }
}

/// Opens User Settings at an explicit CLASSIC root and returns the cohesive,
/// preservation-aware Game Setup group with per-field provenance.
fn user_settings_open_game_setup_settings(classic_root: &str) -> ffi::GameSetupSettingsDto {
    let settings = UserSettings::open(Path::new(classic_root));
    user_settings_game_setup_settings_dto(&settings)
}

/// Projects Game Setup settings from an already-opened cohesive User Settings snapshot.
fn user_settings_game_setup_settings_dto(settings: &UserSettings) -> ffi::GameSetupSettingsDto {
    let setup = settings.game_setup_settings();
    let (has_game_root, game_root) = setup
        .game_root()
        .map_or((false, String::new()), |value| (true, value.to_string()));
    let (has_game_executable, game_executable) = setup
        .game_executable()
        .map_or((false, String::new()), |value| (true, value.to_string()));
    let (has_documents_root, documents_root) = setup
        .documents_root()
        .map_or((false, String::new()), |value| (true, value.to_string()));
    let (has_ini_folder, ini_folder) = setup
        .ini_folder()
        .map_or((false, String::new()), |value| (true, value.to_string()));
    let (has_mods_root, mods_root) = setup
        .mods_root()
        .map_or((false, String::new()), |value| (true, value.to_string()));
    let (has_custom_scan_input, custom_scan_input) = setup
        .custom_scan_input()
        .map_or((false, String::new()), |value| (true, value.to_string()));
    let (has_papyrus_log, papyrus_log) = setup
        .papyrus_log()
        .map_or((false, String::new()), |value| (true, value.to_string()));

    ffi::GameSetupSettingsDto {
        managed_game: setup.managed_game().as_str().to_string(),
        managed_game_origin: setup.managed_game_origin().as_str().to_string(),
        game_version_selection: setup.game_version_selection().as_str().to_string(),
        game_version_selection_origin: setup.game_version_selection_origin().as_str().to_string(),
        has_game_root,
        game_root,
        game_root_origin: setup.game_root_origin().as_str().to_string(),
        has_game_executable,
        game_executable,
        game_executable_origin: setup.game_executable_origin().as_str().to_string(),
        has_documents_root,
        documents_root,
        documents_root_origin: setup.documents_root_origin().as_str().to_string(),
        has_ini_folder,
        ini_folder,
        ini_folder_origin: setup.ini_folder_origin().as_str().to_string(),
        has_mods_root,
        mods_root,
        mods_root_origin: setup.mods_root_origin().as_str().to_string(),
        has_custom_scan_input,
        custom_scan_input,
        custom_scan_input_origin: setup.custom_scan_input_origin().as_str().to_string(),
        has_papyrus_log,
        papyrus_log,
        papyrus_log_origin: setup.papyrus_log_origin().as_str().to_string(),
        classification: settings.classification().as_str().to_string(),
        revision: settings.revision().token(),
        commit_eligibility: settings.commit_eligibility().as_str().to_string(),
        diagnostics: settings
            .diagnostics()
            .iter()
            .map(user_settings_diagnostic_dto)
            .collect(),
    }
}

/// Projects frontend state from an already-opened cohesive User Settings snapshot.
fn user_settings_frontend_state_dto(settings: &UserSettings) -> ffi::FrontendStateDto {
    let frontend = settings.frontend_state();
    let preferences = frontend.preferences();
    let geometry = frontend.window_geometry();
    let tui = frontend.tui();

    ffi::FrontendStateDto {
        auto_switch_after_scan: preferences.auto_switch_after_scan(),
        auto_switch_after_scan_origin: preferences
            .auto_switch_after_scan_origin()
            .as_str()
            .to_string(),
        auto_refresh_interval_ms: preferences.auto_refresh_interval_ms(),
        auto_refresh_interval_ms_origin: preferences
            .auto_refresh_interval_ms_origin()
            .as_str()
            .to_string(),
        window_geometry: vec![
            frontend_window_geometry_dto("main_tab", geometry.main_tab()),
            frontend_window_geometry_dto("backups_tab", geometry.backups_tab()),
            frontend_window_geometry_dto("articles_tab", geometry.articles_tab()),
            frontend_window_geometry_dto("results_tab", geometry.results_tab()),
        ],
        tui_active_tab: tui.active_tab(),
        tui_active_tab_origin: tui.active_tab_origin().as_str().to_string(),
        tui_results_panel_width: tui.results_panel_width(),
        tui_results_panel_width_origin: tui.results_panel_width_origin().as_str().to_string(),
        tui_sort_ascending: tui.sort_ascending(),
        tui_sort_ascending_origin: tui.sort_ascending_origin().as_str().to_string(),
        classification: settings.classification().as_str().to_string(),
        revision: settings.revision().token(),
        commit_eligibility: settings.commit_eligibility().as_str().to_string(),
        diagnostics: settings
            .diagnostics()
            .iter()
            .map(user_settings_diagnostic_dto)
            .collect(),
    }
}

/// Opens every GUI-consumed typed group from one revision-cohesive User Settings snapshot.
fn user_settings_open_gui_settings(classic_root: &str) -> ffi::GuiSettingsSnapshotDto {
    let settings = UserSettings::open(Path::new(classic_root));
    user_settings_gui_snapshot_dto(&settings)
}

/// Returns every GUI-consumed published default without reading or creating User Settings.
fn user_settings_gui_published_defaults() -> ffi::GuiSettingsSnapshotDto {
    let settings = UserSettings::published_defaults();
    user_settings_gui_snapshot_dto(&settings)
}

/// Projects the GUI aggregate from one already-opened or default-only core snapshot.
fn user_settings_gui_snapshot_dto(settings: &UserSettings) -> ffi::GuiSettingsSnapshotDto {
    ffi::GuiSettingsSnapshotDto {
        update_preferences: user_settings_update_preferences_dto(settings),
        crash_log_scan: user_settings_crash_log_scan_settings_dto(settings),
        game_setup: user_settings_game_setup_settings_dto(settings),
        frontend_state: user_settings_frontend_state_dto(settings),
    }
}

/// Converts one named, widget-independent geometry entry into its CXX DTO.
fn frontend_window_geometry_dto(tab: &str, geometry: &WindowGeometry) -> ffi::WindowGeometryDto {
    ffi::WindowGeometryDto {
        tab: tab.to_string(),
        maximized: geometry.maximized(),
        maximized_origin: geometry.maximized_origin().as_str().to_string(),
        width: geometry.width(),
        width_origin: geometry.width_origin().as_str().to_string(),
        height: geometry.height(),
        height_origin: geometry.height_origin().as_str().to_string(),
    }
}

/// Validates a caller-authored User Settings Update against the current on-disk snapshot
/// and returns an all-or-nothing preview without persisting any changes.
fn user_settings_preview_update(
    classic_root: &str,
    update: &ffi::UserSettingsUpdateDto,
) -> ffi::UserSettingsUpdatePreviewDto {
    let settings = UserSettings::open(Path::new(classic_root));
    let (update, bridge_diagnostics) = core_user_settings_update(update);
    user_settings_update_preview_dto(settings.preview_update(update), bridge_diagnostics)
}

/// Explicitly previews first-run User Settings creation from Rust-owned published defaults.
///
/// This operation never persists the missing document. The returned accepted preview remains
/// revision-anchored and must be passed through the explicit bootstrap commit operation.
fn user_settings_preview_bootstrap(
    classic_root: &str,
    update: &ffi::UserSettingsUpdateDto,
) -> ffi::UserSettingsUpdatePreviewDto {
    let settings = UserSettings::open(Path::new(classic_root));
    let (update, bridge_diagnostics) = core_user_settings_update(update);
    user_settings_update_preview_dto(settings.preview_bootstrap(update), bridge_diagnostics)
}

/// Flattens a core update preview into the shared CXX representation.
fn user_settings_update_preview_dto(
    preview: CoreUserSettingsUpdatePreview,
    mut bridge_diagnostics: Vec<ffi::UserSettingsUpdateDiagnosticDto>,
) -> ffi::UserSettingsUpdatePreviewDto {
    match preview {
        CoreUserSettingsUpdatePreview::Accepted(_) if !bridge_diagnostics.is_empty() => {
            ffi::UserSettingsUpdatePreviewDto {
                accepted: false,
                base_revision: String::new(),
                accepted_fields: Vec::new(),
                formid_database_games: Vec::new(),
                formid_database_paths: Vec::new(),
                diagnostics: bridge_diagnostics,
            }
        }
        CoreUserSettingsUpdatePreview::Accepted(accepted) => {
            let databases = accepted.fields().iter().find_map(|field| match field {
                CoreUserSettingsUpdateField::FormIdDatabases(databases) => Some(databases),
                _ => None,
            });
            let (formid_database_games, formid_database_paths) =
                databases.map(flatten_formid_databases).unwrap_or_default();

            ffi::UserSettingsUpdatePreviewDto {
                accepted: true,
                base_revision: accepted.base_revision().token(),
                accepted_fields: accepted
                    .fields()
                    .iter()
                    .map(user_settings_update_field_dto)
                    .collect(),
                formid_database_games,
                formid_database_paths,
                diagnostics: accepted
                    .diagnostics()
                    .iter()
                    .map(update_diagnostic_dto)
                    .collect(),
            }
        }
        CoreUserSettingsUpdatePreview::Rejected(diagnostics) => {
            bridge_diagnostics.extend(diagnostics.iter().map(update_diagnostic_dto));
            ffi::UserSettingsUpdatePreviewDto {
                accepted: false,
                base_revision: String::new(),
                accepted_fields: Vec::new(),
                formid_database_games: Vec::new(),
                formid_database_paths: Vec::new(),
                diagnostics: bridge_diagnostics,
            }
        }
    }
}

/// Commits a previously previewed User Settings Update against its accepted base revision.
///
/// The request is revalidated in Rust after confirming the supplied revision still identifies
/// the current document. The core then reopens under its commit lock to close the remaining race.
fn user_settings_commit_update(
    classic_root: &str,
    base_revision: &str,
    update: &ffi::UserSettingsUpdateDto,
) -> Result<ffi::UserSettingsCommitResultDto, String> {
    commit_user_settings_update(classic_root, base_revision, update, false)
}

/// Publishes one replay-safe frontend geometry transition through the Rust-owned retry policy.
fn user_settings_commit_frontend_geometry_transition(
    classic_root: &str,
    base_revision: &str,
    transition: &ffi::UserSettingsWindowGeometryUpdateDto,
) -> Result<ffi::UserSettingsCommitResultDto, String> {
    let Some(expected_revision) = Revision::from_token(base_revision) else {
        return Err(format!(
            "invalid_user_settings_revision: unrecognized revision token {base_revision:?}"
        ));
    };
    let Some(window) = GuiWindow::parse(&transition.tab) else {
        return Ok(ffi::UserSettingsCommitResultDto {
            status: "rejected".to_string(),
            revision: String::new(),
            expected_revision: base_revision.to_string(),
            actual_revision: String::new(),
            diagnostics: vec![invalid_gui_window_diagnostic(&transition.tab)],
        });
    };

    match UserSettings::commit_frontend_geometry_transition(
        Path::new(classic_root),
        &expected_revision,
        window,
        transition.maximized,
        transition.width,
        transition.height,
    ) {
        Ok(CoreUserSettingsFrontendTransitionOutcome::Committed { revision }) => {
            Ok(ffi::UserSettingsCommitResultDto {
                status: "committed".to_string(),
                revision: revision.token(),
                expected_revision: base_revision.to_string(),
                actual_revision: String::new(),
                diagnostics: Vec::new(),
            })
        }
        Ok(CoreUserSettingsFrontendTransitionOutcome::Rejected { diagnostics }) => {
            Ok(ffi::UserSettingsCommitResultDto {
                status: "rejected".to_string(),
                revision: String::new(),
                expected_revision: base_revision.to_string(),
                actual_revision: String::new(),
                diagnostics: diagnostics.iter().map(update_diagnostic_dto).collect(),
            })
        }
        Ok(CoreUserSettingsFrontendTransitionOutcome::Conflict {
            expected_revision,
            actual_revision,
        }) => Ok(ffi::UserSettingsCommitResultDto {
            status: "conflict".to_string(),
            revision: String::new(),
            expected_revision: expected_revision.token(),
            actual_revision: actual_revision.token(),
            diagnostics: Vec::new(),
        }),
        Err(error) => Err(error.to_string()),
    }
}

/// Commits an explicitly previewed first-run bootstrap against a missing revision.
///
/// Keeping this operation separate prevents an ordinary CXX update commit from creating a
/// missing document merely because the caller supplied the `missing` revision token.
fn user_settings_commit_bootstrap(
    classic_root: &str,
    base_revision: &str,
    update: &ffi::UserSettingsUpdateDto,
) -> Result<ffi::UserSettingsCommitResultDto, String> {
    commit_user_settings_update(classic_root, base_revision, update, true)
}

/// Reopens, revalidates, and commits one ordinary or bootstrap update request.
fn commit_user_settings_update(
    classic_root: &str,
    base_revision: &str,
    update: &ffi::UserSettingsUpdateDto,
    bootstrap: bool,
) -> Result<ffi::UserSettingsCommitResultDto, String> {
    let settings = UserSettings::open(Path::new(classic_root));
    if matches!(settings.revision(), Revision::Unavailable) {
        return Err(
            "commit_source_unavailable: User Settings could not be reopened before commit"
                .to_string(),
        );
    }
    let actual_revision = settings.revision().token();
    if actual_revision != base_revision {
        return Ok(ffi::UserSettingsCommitResultDto {
            status: "conflict".to_string(),
            revision: String::new(),
            expected_revision: base_revision.to_string(),
            actual_revision,
            diagnostics: Vec::new(),
        });
    }

    let (update, mut bridge_diagnostics) = core_user_settings_update(update);
    let preview = if bootstrap {
        settings.preview_bootstrap(update)
    } else {
        settings.preview_update(update)
    };
    let accepted = match preview {
        CoreUserSettingsUpdatePreview::Accepted(accepted) if bridge_diagnostics.is_empty() => {
            accepted
        }
        CoreUserSettingsUpdatePreview::Accepted(_) => {
            return Ok(ffi::UserSettingsCommitResultDto {
                status: "rejected".to_string(),
                revision: String::new(),
                expected_revision: base_revision.to_string(),
                actual_revision: String::new(),
                diagnostics: bridge_diagnostics,
            });
        }
        CoreUserSettingsUpdatePreview::Rejected(diagnostics) => {
            bridge_diagnostics.extend(diagnostics.iter().map(update_diagnostic_dto));
            return Ok(ffi::UserSettingsCommitResultDto {
                status: "rejected".to_string(),
                revision: String::new(),
                expected_revision: base_revision.to_string(),
                actual_revision: String::new(),
                diagnostics: bridge_diagnostics,
            });
        }
    };

    match accepted.commit(Path::new(classic_root)) {
        Ok(CoreUserSettingsCommitOutcome::Committed {
            revision,
            diagnostics,
        }) => Ok(ffi::UserSettingsCommitResultDto {
            status: "committed".to_string(),
            revision: revision.token(),
            expected_revision: base_revision.to_string(),
            actual_revision: String::new(),
            diagnostics: diagnostics.iter().map(update_diagnostic_dto).collect(),
        }),
        Ok(CoreUserSettingsCommitOutcome::Conflict {
            expected_revision,
            actual_revision,
        }) => Ok(ffi::UserSettingsCommitResultDto {
            status: "conflict".to_string(),
            revision: String::new(),
            expected_revision: expected_revision.token(),
            actual_revision: actual_revision.token(),
            diagnostics: Vec::new(),
        }),
        Err(error) => Err(error.to_string()),
    }
}

/// Converts one update diagnostic, a rejection reason or an accepted update's non-blocking
/// effect report, into its shared CXX representation.
fn update_diagnostic_dto(
    diagnostic: &classic_user_settings_core::UpdateDiagnostic,
) -> ffi::UserSettingsUpdateDiagnosticDto {
    ffi::UserSettingsUpdateDiagnosticDto {
        has_field_path: diagnostic.field_path().is_some(),
        field_path: diagnostic.field_path().unwrap_or_default().to_string(),
        code: diagnostic.code().to_string(),
        message: diagnostic.message().to_string(),
    }
}

/// Converts the CXX request DTO into the Rust-owned update builder without validation.
///
/// Raw domain strings remain unchanged so `UserSettings::preview_update` can validate
/// every requested field in one pass and return all diagnostics together. Geometry tab
/// tokens are the one adapter-owned enum boundary; unknown tokens are returned alongside
/// the core request as structured diagnostics so neither preview nor commit can accept them.
fn core_user_settings_update(
    update: &ffi::UserSettingsUpdateDto,
) -> (
    CoreUserSettingsUpdate,
    Vec<ffi::UserSettingsUpdateDiagnosticDto>,
) {
    let mut core = CoreUserSettingsUpdate::new();
    let mut diagnostics = Vec::new();
    if update.has_update_check {
        core = core.with_update_check(update.update_check);
    }
    if update.has_update_source {
        core = core.with_update_source(update.update_source.clone());
    }
    if update.has_auto_switch_after_scan {
        core = core.with_auto_switch_after_scan(update.auto_switch_after_scan);
    }
    for geometry in &update.window_geometry_updates {
        let Some(window) = GuiWindow::parse(&geometry.tab) else {
            diagnostics.push(invalid_gui_window_diagnostic(&geometry.tab));
            continue;
        };
        core =
            core.with_window_geometry(window, geometry.maximized, geometry.width, geometry.height);
    }
    if update.has_tui_remembered_state {
        core = core.with_tui_remembered_state(
            update.tui_active_tab,
            update.tui_results_panel_width,
            update.tui_sort_ascending,
        );
    }
    if update.has_managed_game {
        core = core.with_managed_game(update.managed_game.clone());
    }
    if update.has_game_version_selection {
        core = core.with_game_version_selection(update.game_version_selection.clone());
    }
    if update.has_game_root {
        core = core.with_game_root(update.has_game_root_value.then(|| update.game_root.clone()));
    }
    if update.has_game_executable {
        core = core.with_game_executable(
            update
                .has_game_executable_value
                .then(|| update.game_executable.clone()),
        );
    }
    if update.has_documents_root {
        core = core.with_documents_root(
            update
                .has_documents_root_value
                .then(|| update.documents_root.clone()),
        );
    }
    if update.has_ini_folder {
        core = core.with_ini_folder(
            update
                .has_ini_folder_value
                .then(|| update.ini_folder.clone()),
        );
    }
    if update.has_mods_folder {
        core = core.with_mods_folder(
            update
                .has_mods_folder_value
                .then(|| update.mods_folder.clone()),
        );
    }
    if update.has_fcx_mode {
        core = core.with_fcx_mode(update.fcx_mode);
    }
    if update.has_simplify_logs {
        core = core.with_simplify_logs(update.simplify_logs);
    }
    if update.has_show_statistics {
        core = core.with_show_statistics(update.show_statistics);
    }
    if update.has_formid_value_lookup {
        core = core.with_formid_value_lookup(update.formid_value_lookup);
    }
    if update.has_formid_databases {
        let mut databases = update
            .formid_database_games
            .iter()
            .cloned()
            .map(|game| (game, Vec::new()))
            .collect::<BTreeMap<_, _>>();
        for entry in &update.formid_database_paths {
            databases
                .entry(entry.game.clone())
                .or_default()
                .push(entry.path.clone());
        }
        core = core.with_formid_databases(databases);
    }
    if update.has_formid_database_save {
        core = core.with_formid_databases_for_game(
            update.formid_database_save_game.clone(),
            update.formid_database_save_paths.clone(),
        );
    }
    if update.has_move_unsolved_logs {
        core = core.with_move_unsolved_logs(update.move_unsolved_logs);
    }
    if update.has_unsolved_logs_destination {
        core = core.with_unsolved_logs_destination(
            update
                .has_unsolved_logs_destination_value
                .then(|| update.unsolved_logs_destination.clone()),
        );
    }
    if update.has_custom_scan_input {
        core = core.with_custom_scan_input(
            update
                .has_custom_scan_input_value
                .then(|| update.custom_scan_input.clone()),
        );
    }
    if update.has_papyrus_log_path {
        core = core.with_papyrus_log_path(
            update
                .has_papyrus_log_path_value
                .then(|| update.papyrus_log_path.clone()),
        );
    }
    if update.has_max_concurrent_scans {
        core = core.with_max_concurrent_scans(update.max_concurrent_scans);
    }
    (core, diagnostics)
}

/// Returns a structured bridge-level rejection for a geometry tab token the core cannot name.
fn invalid_gui_window_diagnostic(tab: &str) -> ffi::UserSettingsUpdateDiagnosticDto {
    ffi::UserSettingsUpdateDiagnosticDto {
        has_field_path: true,
        field_path: "/UI/window_geometry".to_string(),
        code: "invalid_enum_gui_window".to_string(),
        message: format!(
            "GUI window tab must be main_tab, backups_tab, articles_tab, or results_tab; found {tab:?}"
        ),
    }
}

/// Flattens game-keyed FormID paths into CXX-safe rows while retaining games whose
/// configured path list is empty.
fn flatten_formid_databases(
    databases: &BTreeMap<String, Vec<String>>,
) -> (Vec<String>, Vec<ffi::FormIdDatabasePathDto>) {
    let games = databases.keys().cloned().collect();
    let paths = databases
        .iter()
        .flat_map(|(game, paths)| {
            paths.iter().map(|path| ffi::FormIdDatabasePathDto {
                game: game.clone(),
                path: path.clone(),
            })
        })
        .collect();
    (games, paths)
}

/// Projects the Rust-owned game-aware scan read for every supported game as CXX-safe rows.
///
/// Each game's rows come from `CrashLogScanSettings::formid_databases_for_game`, so the
/// Fallout 4 VR read rule stays in Rust and C++ frontends only filter by the scanned game.
fn scan_formid_database_paths(
    scan: &classic_user_settings_core::CrashLogScanSettings,
) -> Vec<ffi::FormIdDatabasePathDto> {
    classic_shared_core::GameId::all()
        .into_iter()
        .flat_map(|game| {
            scan.formid_databases_for_game(game)
                .into_iter()
                .map(move |path| ffi::FormIdDatabasePathDto {
                    game: game.as_str().to_string(),
                    path: path.to_string(),
                })
        })
        .collect()
}

/// Converts one accepted typed field into a flat tagged DTO suitable for a CXX vector.
fn user_settings_update_field_dto(
    field: &CoreUserSettingsUpdateField,
) -> ffi::UserSettingsUpdateFieldDto {
    let (value_kind, bool_value, has_string_value, string_value, u32_value) = match field {
        CoreUserSettingsUpdateField::UpdateCheck(value)
        | CoreUserSettingsUpdateField::AutoSwitchAfterScan(value)
        | CoreUserSettingsUpdateField::WindowMaximized(_, value)
        | CoreUserSettingsUpdateField::TuiSortAscending(value)
        | CoreUserSettingsUpdateField::FcxMode(value)
        | CoreUserSettingsUpdateField::SimplifyLogs(value)
        | CoreUserSettingsUpdateField::ShowStatistics(value)
        | CoreUserSettingsUpdateField::FormIdValueLookup(value)
        | CoreUserSettingsUpdateField::MoveUnsolvedLogs(value) => {
            ("bool", *value, false, String::new(), 0)
        }
        CoreUserSettingsUpdateField::ManagedGame(value) => {
            ("string", false, true, value.as_str().to_string(), 0)
        }
        CoreUserSettingsUpdateField::UpdateSource(value) => {
            ("string", false, true, value.as_str().to_string(), 0)
        }
        CoreUserSettingsUpdateField::GameVersionSelection(value) => {
            ("string", false, true, value.as_str().to_string(), 0)
        }
        CoreUserSettingsUpdateField::FormIdDatabases(_) => {
            ("formid_databases", false, false, String::new(), 0)
        }
        CoreUserSettingsUpdateField::GameRoot(value)
        | CoreUserSettingsUpdateField::GameExecutable(value)
        | CoreUserSettingsUpdateField::DocumentsRoot(value)
        | CoreUserSettingsUpdateField::IniFolder(value)
        | CoreUserSettingsUpdateField::ModsFolder(value)
        | CoreUserSettingsUpdateField::PapyrusLogPath(value)
        | CoreUserSettingsUpdateField::UnsolvedLogsDestination(value)
        | CoreUserSettingsUpdateField::CustomScanInput(value) => (
            "optional_string",
            false,
            value.is_some(),
            value.clone().unwrap_or_default(),
            0,
        ),
        CoreUserSettingsUpdateField::MaxConcurrentScans(value)
        | CoreUserSettingsUpdateField::WindowWidth(_, value)
        | CoreUserSettingsUpdateField::WindowHeight(_, value) => {
            ("u32", false, false, String::new(), *value)
        }
        CoreUserSettingsUpdateField::TuiActiveTab(value) => {
            ("u32", false, false, String::new(), u32::from(*value))
        }
        CoreUserSettingsUpdateField::TuiResultsPanelWidth(value) => {
            ("u32", false, false, String::new(), u32::from(*value))
        }
    };

    ffi::UserSettingsUpdateFieldDto {
        field_path: field.canonical_path().to_string(),
        value_kind: value_kind.to_string(),
        bool_value,
        has_string_value,
        string_value,
        u32_value,
    }
}

/// Converts one open-time User Settings diagnostic into the shared CXX DTO.
fn user_settings_diagnostic_dto(
    diagnostic: &classic_user_settings_core::Diagnostic,
) -> ffi::UserSettingsDiagnosticDto {
    ffi::UserSettingsDiagnosticDto {
        code: diagnostic.code().to_string(),
        message: diagnostic.message().to_string(),
    }
}

// The Vocabulary Tokens for preference origin, source location, document
// classification, and commit eligibility are owned by
// `classic-user-settings-core`. This bridge projects `Vocabulary::as_str`
// directly — the CXX surface publishes the canonical snake_case spelling
// unchanged — so the four hand-written token tables that used to live here are
// gone rather than delegating.

// The revision token pair is owned by `classic-user-settings-core`
// (`Revision::token` / `Revision::from_token`) so no binding surface keeps its
// own copy (originally so the CXX, Node, and Python surfaces could not drift
// apart). This bridge projects it without exposing the
// Rust-only enum layout through CXX.

// ── Construction ────────────────────────────────────────────────────

fn yaml_ops_new() -> Box<YamlOps> {
    Box::new(YamlOps {
        ops: YamlOperations::new(),
        doc: None,
    })
}

// ── File operations ─────────────────────────────────────────────────

fn yaml_ops_load_file(ops: &mut YamlOps, path: &str) -> Result<(), String> {
    let yaml = ops
        .ops
        .load_yaml_file(Path::new(path))
        .map_err(|e| format!("{e}"))?;
    ops.doc = Some(yaml);
    Ok(())
}

// ── Settings access ─────────────────────────────────────────────────

fn yaml_ops_get_string(ops: &YamlOps, key_path: &str, default_val: &str) -> String {
    match &ops.doc {
        Some(doc) => ops.ops.get_string_value(doc, key_path, default_val),
        None => default_val.to_string(),
    }
}

#[cxx::bridge(namespace = "classic::settings")]
mod ffi {
    /// One structured diagnostic produced while opening User Settings.
    struct UserSettingsDiagnosticDto {
        code: String,
        message: String,
    }

    /// Result of silently applying a required User Settings migration at startup.
    ///
    /// `status` is `not_required`, `applied`, `unavailable`, `conflict`, or `failed`.
    /// `backup_path` is populated only for `applied`; `diagnostics` explains the
    /// non-applied failure statuses and is empty otherwise.
    struct UserSettingsAutomaticMigrationDto {
        status: String,
        backup_path: String,
        diagnostics: Vec<UserSettingsDiagnosticDto>,
    }

    /// Typed Update Preferences plus User Settings source and diagnostic metadata.
    ///
    /// The boolean is already safety-adjusted by Rust: missing settings use the
    /// published default, while malformed, incompatible, or invalid values are
    /// fail-closed. C++ callers must not reinterpret raw YAML.
    struct UpdatePreferencesDto {
        update_check_enabled: bool,
        update_check_origin: String,
        update_source: String,
        update_source_origin: String,
        source_location: String,
        source_path: String,
        classification: String,
        has_schema_version: bool,
        schema_major: u32,
        schema_minor: u32,
        revision: String,
        commit_eligibility: String,
        diagnostics: Vec<UserSettingsDiagnosticDto>,
        has_original_content: bool,
        original_content: Vec<u8>,
    }

    /// One flattened FormID database path row.
    ///
    /// `CrashLogScanSettingsDto::formid_database_games` separately retains
    /// configured games whose path list is empty. This avoids CXX's unsupported
    /// `Vec<StructWithVec>` shape while preserving the complete Rust mapping.
    struct FormIdDatabasePathDto {
        game: String,
        path: String,
    }

    /// Safety-adjusted Crash Log Scan settings plus their source provenance.
    ///
    /// Optional strings use explicit presence flags. Open-time diagnostics are
    /// returned unchanged so C++ callers can surface canonical/alias conflicts
    /// and degraded fallbacks without parsing raw YAML.
    struct CrashLogScanSettingsDto {
        fcx_mode: bool,
        fcx_mode_origin: String,
        simplify_logs: bool,
        simplify_logs_origin: String,
        show_statistics: bool,
        show_statistics_origin: String,
        formid_value_lookup: bool,
        formid_value_lookup_origin: String,
        formid_database_games: Vec<String>,
        formid_database_paths: Vec<FormIdDatabasePathDto>,
        formid_databases_origin: String,
        /// FormID database rows that apply to each supported game's Crash Log Scan.
        ///
        /// Rust applies the game-aware read rule (`formid_databases_for_game`): a Fallout 4 VR
        /// row set is the shared `Fallout4` rows followed by legacy `Fallout4VR` rows,
        /// de-duplicated; every other game carries its own rows exactly. Rows are grouped in
        /// supported-game order. Scan launch selects rows whose `game` equals the scanned game
        /// and must never read `formid_database_paths` for that purpose.
        scan_formid_database_paths: Vec<FormIdDatabasePathDto>,
        move_unsolved_logs: bool,
        move_unsolved_logs_origin: String,
        has_unsolved_logs_destination: bool,
        unsolved_logs_destination: String,
        unsolved_logs_destination_origin: String,
        has_custom_scan_input: bool,
        custom_scan_input: String,
        custom_scan_input_origin: String,
        game_version_selection: String,
        game_version_selection_origin: String,
        max_concurrent_scans: u32,
        max_concurrent_scans_origin: String,
        classification: String,
        revision: String,
        commit_eligibility: String,
        diagnostics: Vec<UserSettingsDiagnosticDto>,
    }

    /// Preservation-aware Game Setup settings plus per-field source provenance.
    ///
    /// Optional path strings use explicit presence flags, remain byte-for-byte
    /// unchanged from valid persisted YAML, and are never normalized by the bridge.
    struct GameSetupSettingsDto {
        managed_game: String,
        managed_game_origin: String,
        game_version_selection: String,
        game_version_selection_origin: String,
        has_game_root: bool,
        game_root: String,
        game_root_origin: String,
        has_game_executable: bool,
        game_executable: String,
        game_executable_origin: String,
        has_documents_root: bool,
        documents_root: String,
        documents_root_origin: String,
        has_ini_folder: bool,
        ini_folder: String,
        ini_folder_origin: String,
        has_mods_root: bool,
        mods_root: String,
        mods_root_origin: String,
        has_custom_scan_input: bool,
        custom_scan_input: String,
        custom_scan_input_origin: String,
        has_papyrus_log: bool,
        papyrus_log: String,
        papyrus_log_origin: String,
        classification: String,
        revision: String,
        commit_eligibility: String,
        diagnostics: Vec<UserSettingsDiagnosticDto>,
    }

    /// Widget-independent geometry for one maintained GUI tab.
    ///
    /// `tab` is one of `main_tab`, `backups_tab`, `articles_tab`, or
    /// `results_tab`. Each value is already defaulted or safely degraded by Rust;
    /// the origin token tells C++ whether it came from the document.
    struct WindowGeometryDto {
        tab: String,
        maximized: bool,
        maximized_origin: String,
        width: u32,
        width_origin: String,
        height: u32,
        height_origin: String,
    }

    /// Typed frontend preferences, GUI geometry, and remembered TUI state.
    ///
    /// Geometry entries are returned in maintained GUI tab order. All scalar
    /// values have a matching provenance token; document metadata and open-time
    /// diagnostics follow the other typed User Settings DTOs.
    struct FrontendStateDto {
        auto_switch_after_scan: bool,
        auto_switch_after_scan_origin: String,
        auto_refresh_interval_ms: u64,
        auto_refresh_interval_ms_origin: String,
        window_geometry: Vec<WindowGeometryDto>,
        tui_active_tab: u8,
        tui_active_tab_origin: String,
        tui_results_panel_width: u16,
        tui_results_panel_width_origin: String,
        tui_sort_ascending: bool,
        tui_sort_ascending_origin: String,
        classification: String,
        revision: String,
        commit_eligibility: String,
        diagnostics: Vec<UserSettingsDiagnosticDto>,
    }

    /// Revision-cohesive typed groups consumed by the native GUI settings and scan flows.
    ///
    /// Every nested DTO is projected from one `UserSettings::open`, so their revision and
    /// diagnostics describe the same source bytes even when another process edits concurrently.
    struct GuiSettingsSnapshotDto {
        update_preferences: UpdatePreferencesDto,
        crash_log_scan: CrashLogScanSettingsDto,
        game_setup: GameSetupSettingsDto,
        frontend_state: FrontendStateDto,
    }

    /// Caller-authored geometry transition for one maintained GUI window.
    ///
    /// `tab` uses one of the stable `main_tab`, `backups_tab`, `articles_tab`, or
    /// `results_tab` tokens. Signed dimensions are retained for Rust-owned validation.
    struct UserSettingsWindowGeometryUpdateDto {
        tab: String,
        maximized: bool,
        width: i64,
        height: i64,
    }

    /// Caller-authored multi-field User Settings Update request.
    ///
    /// Each `has_*` flag distinguishes an omitted field from a requested false,
    /// zero, empty mapping, or null optional string. FormID mappings are flattened
    /// into game names plus path rows to avoid nested-vector CXX layouts.
    struct UserSettingsUpdateDto {
        has_update_check: bool,
        update_check: bool,
        has_update_source: bool,
        update_source: String,
        has_auto_switch_after_scan: bool,
        auto_switch_after_scan: bool,
        window_geometry_updates: Vec<UserSettingsWindowGeometryUpdateDto>,
        has_tui_remembered_state: bool,
        tui_active_tab: i64,
        tui_results_panel_width: i64,
        tui_sort_ascending: bool,
        has_managed_game: bool,
        managed_game: String,
        has_game_version_selection: bool,
        game_version_selection: String,
        has_game_root: bool,
        has_game_root_value: bool,
        game_root: String,
        has_game_executable: bool,
        has_game_executable_value: bool,
        game_executable: String,
        has_documents_root: bool,
        has_documents_root_value: bool,
        documents_root: String,
        has_ini_folder: bool,
        has_ini_folder_value: bool,
        ini_folder: String,
        has_mods_folder: bool,
        has_mods_folder_value: bool,
        mods_folder: String,
        has_papyrus_log_path: bool,
        has_papyrus_log_path_value: bool,
        papyrus_log_path: String,
        has_fcx_mode: bool,
        fcx_mode: bool,
        has_simplify_logs: bool,
        simplify_logs: bool,
        has_show_statistics: bool,
        show_statistics: bool,
        has_formid_value_lookup: bool,
        formid_value_lookup: bool,
        has_formid_databases: bool,
        formid_database_games: Vec<String>,
        formid_database_paths: Vec<FormIdDatabasePathDto>,
        /// Requests the game-aware FormID database save
        /// (`UserSettingsUpdate::with_formid_databases_for_game`) for
        /// `formid_database_save_game`, replacing that game's rows with
        /// `formid_database_save_paths`. Rust stores Fallout 4 VR rows under `Fallout4` and
        /// removes a legacy `Fallout4VR` key, reporting the removal as a diagnostic.
        has_formid_database_save: bool,
        formid_database_save_game: String,
        formid_database_save_paths: Vec<String>,
        has_move_unsolved_logs: bool,
        move_unsolved_logs: bool,
        has_unsolved_logs_destination: bool,
        has_unsolved_logs_destination_value: bool,
        unsolved_logs_destination: String,
        has_custom_scan_input: bool,
        has_custom_scan_input_value: bool,
        custom_scan_input: String,
        has_max_concurrent_scans: bool,
        max_concurrent_scans: i64,
    }

    /// One typed canonical field in an accepted update preview.
    ///
    /// `value_kind` is `bool`, `string`, `optional_string`, `u32`, or
    /// `formid_databases`. FormID mapping values live on the containing preview
    /// so this DTO remains safe as an element of `Vec<UserSettingsUpdateFieldDto>`.
    struct UserSettingsUpdateFieldDto {
        field_path: String,
        value_kind: String,
        bool_value: bool,
        has_string_value: bool,
        string_value: String,
        u32_value: u32,
    }

    /// One field-specific or preview-level update diagnostic: a rejection reason, or a
    /// non-rejecting effect report on an accepted preview or committed result.
    struct UserSettingsUpdateDiagnosticDto {
        has_field_path: bool,
        field_path: String,
        code: String,
        message: String,
    }

    /// All-or-nothing result of validating a User Settings Update without persistence.
    ///
    /// Accepted previews contain a base revision and only explicitly requested
    /// fields. Rejected previews contain no partial fields or base revision.
    /// `diagnostics` holds the rejection reasons when rejected, and the non-rejecting
    /// effect diagnostics (such as `legacy_formid_databases_key_removed`) when accepted.
    struct UserSettingsUpdatePreviewDto {
        accepted: bool,
        base_revision: String,
        accepted_fields: Vec<UserSettingsUpdateFieldDto>,
        formid_database_games: Vec<String>,
        formid_database_paths: Vec<FormIdDatabasePathDto>,
        diagnostics: Vec<UserSettingsUpdateDiagnosticDto>,
    }

    /// Structured result of committing a previously accepted User Settings Update.
    ///
    /// `status` is `committed`, `conflict`, or `rejected`; fields unrelated to the selected
    /// status are returned empty. `diagnostics` holds rejection reasons for `rejected` and the
    /// accepted preview's effect diagnostics for `committed`. Operational failures propagate
    /// as `rust::Error`.
    struct UserSettingsCommitResultDto {
        status: String,
        revision: String,
        expected_revision: String,
        actual_revision: String,
        diagnostics: Vec<UserSettingsUpdateDiagnosticDto>,
    }

    extern "Rust" {
        type YamlOps;

        /// Open User Settings from an explicit CLASSIC root and return the
        /// typed Update Preferences view used by native update-check policy.
        fn user_settings_open_update_preferences(classic_root: &str) -> UpdatePreferencesDto;

        /// Silently apply a required User Settings migration; call before the first open.
        fn user_settings_migrate_if_required(
            classic_root: &str,
        ) -> UserSettingsAutomaticMigrationDto;

        /// Open User Settings and return the complete typed Crash Log Scan group.
        fn user_settings_open_crash_log_scan_settings(
            classic_root: &str,
        ) -> CrashLogScanSettingsDto;

        /// Open User Settings and return the complete typed Game Setup group.
        fn user_settings_open_game_setup_settings(classic_root: &str) -> GameSetupSettingsDto;

        /// Open every GUI-consumed typed group from one revision-cohesive snapshot.
        fn user_settings_open_gui_settings(classic_root: &str) -> GuiSettingsSnapshotDto;

        /// Return every GUI-consumed Rust-owned published default without filesystem access.
        fn user_settings_gui_published_defaults() -> GuiSettingsSnapshotDto;

        /// Validate a multi-field User Settings Update without writing to disk.
        fn user_settings_preview_update(
            classic_root: &str,
            update: &UserSettingsUpdateDto,
        ) -> UserSettingsUpdatePreviewDto;

        /// Preview explicit first-run creation from Rust-owned defaults without writing.
        fn user_settings_preview_bootstrap(
            classic_root: &str,
            update: &UserSettingsUpdateDto,
        ) -> UserSettingsUpdatePreviewDto;

        /// Commit a previously accepted User Settings Update under cross-process coordination.
        fn user_settings_commit_update(
            classic_root: &str,
            base_revision: &str,
            update: &UserSettingsUpdateDto,
        ) -> Result<UserSettingsCommitResultDto>;

        /// Commit one replay-safe frontend geometry transition with one Rust-owned retry.
        fn user_settings_commit_frontend_geometry_transition(
            classic_root: &str,
            base_revision: &str,
            transition: &UserSettingsWindowGeometryUpdateDto,
        ) -> Result<UserSettingsCommitResultDto>;

        /// Commit an explicitly previewed missing-document bootstrap.
        fn user_settings_commit_bootstrap(
            classic_root: &str,
            base_revision: &str,
            update: &UserSettingsUpdateDto,
        ) -> Result<UserSettingsCommitResultDto>;

        // Construction
        fn yaml_ops_new() -> Box<YamlOps>;

        // File operations
        fn yaml_ops_load_file(ops: &mut YamlOps, path: &str) -> Result<()>;

        // Settings access
        fn yaml_ops_get_string(ops: &YamlOps, key_path: &str, default_val: &str) -> String;
    }
}

#[cfg(test)]
#[path = "settings_tests.rs"]
mod tests;
