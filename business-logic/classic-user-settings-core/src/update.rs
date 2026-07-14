use crate::game_setup_settings::parse_managed_game;
use crate::preference::is_absolute_user_path;
use crate::scan_settings::valid_formid_databases;
use crate::{CommitEligibility, GameVersionSelection, Revision, UserSettings};
use classic_shared_core::GameId;
use std::collections::BTreeMap;

/// A caller-authored, non-persisting request to change one or more User Settings.
///
/// Builder methods retain raw values that require validation so `preview_update` can
/// return every field-specific rejection diagnostic in one pass.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct UserSettingsUpdate {
    update_check: Option<bool>,
    managed_game: Option<String>,
    game_version_selection: Option<String>,
    game_root: Option<Option<String>>,
    game_executable: Option<Option<String>>,
    documents_root: Option<Option<String>>,
    ini_folder: Option<Option<String>>,
    mods_folder: Option<Option<String>>,
    papyrus_log_path: Option<Option<String>>,
    fcx_mode: Option<bool>,
    simplify_logs: Option<bool>,
    show_statistics: Option<bool>,
    formid_value_lookup: Option<bool>,
    formid_databases: Option<BTreeMap<String, Vec<String>>>,
    move_unsolved_logs: Option<bool>,
    unsolved_logs_destination: Option<Option<String>>,
    custom_scan_input: Option<Option<String>>,
    max_concurrent_scans: Option<i64>,
}

impl UserSettingsUpdate {
    /// Creates an empty update request.
    pub fn new() -> Self {
        Self::default()
    }

    /// Requests a new Update Check preference.
    pub fn with_update_check(mut self, value: bool) -> Self {
        self.update_check = Some(value);
        self
    }

    /// Requests a new managed game.
    pub fn with_managed_game(mut self, value: impl Into<String>) -> Self {
        self.managed_game = Some(value.into());
        self
    }

    /// Requests a canonical game-version selection string.
    pub fn with_game_version_selection(mut self, value: impl Into<String>) -> Self {
        self.game_version_selection = Some(value.into());
        self
    }

    /// Requests an optional game installation root.
    pub fn with_game_root(mut self, value: Option<String>) -> Self {
        self.game_root = Some(value);
        self
    }

    /// Requests an optional game executable path.
    pub fn with_game_executable(mut self, value: Option<String>) -> Self {
        self.game_executable = Some(value);
        self
    }

    /// Requests an optional saved documents root.
    pub fn with_documents_root(mut self, value: Option<String>) -> Self {
        self.documents_root = Some(value);
        self
    }

    /// Requests an optional INI-folder compatibility fallback.
    pub fn with_ini_folder(mut self, value: Option<String>) -> Self {
        self.ini_folder = Some(value);
        self
    }

    /// Requests an optional mods or staging folder.
    pub fn with_mods_folder(mut self, value: Option<String>) -> Self {
        self.mods_folder = Some(value);
        self
    }

    /// Requests an optional Papyrus log path.
    pub fn with_papyrus_log_path(mut self, value: Option<String>) -> Self {
        self.papyrus_log_path = Some(value);
        self
    }

    /// Requests a new FCX Mode preference.
    pub fn with_fcx_mode(mut self, value: bool) -> Self {
        self.fcx_mode = Some(value);
        self
    }

    /// Requests a new Simplify Logs preference.
    pub fn with_simplify_logs(mut self, value: bool) -> Self {
        self.simplify_logs = Some(value);
        self
    }

    /// Requests a new Show Statistics preference.
    pub fn with_show_statistics(mut self, value: bool) -> Self {
        self.show_statistics = Some(value);
        self
    }

    /// Requests a new FormID Value Lookup preference.
    pub fn with_formid_value_lookup(mut self, value: bool) -> Self {
        self.formid_value_lookup = Some(value);
        self
    }

    /// Requests replacement FormID database path lists keyed by managed game.
    pub fn with_formid_databases(mut self, value: BTreeMap<String, Vec<String>>) -> Self {
        self.formid_databases = Some(value);
        self
    }

    /// Requests a new Move Unsolved Logs preference.
    pub fn with_move_unsolved_logs(mut self, value: bool) -> Self {
        self.move_unsolved_logs = Some(value);
        self
    }

    /// Requests an optional Unsolved Logs Destination.
    ///
    /// `None` explicitly requests the canonical default destination.
    pub fn with_unsolved_logs_destination(mut self, value: Option<String>) -> Self {
        self.unsolved_logs_destination = Some(value);
        self
    }

    /// Requests an optional custom Crash Log Scan input.
    ///
    /// `None` explicitly requests automatic Crash Log discovery.
    pub fn with_custom_scan_input(mut self, value: Option<String>) -> Self {
        self.custom_scan_input = Some(value);
        self
    }

    /// Requests scan concurrency in the persisted `0..=32` range.
    ///
    /// The signed input intentionally retains out-of-range adapter values for preview validation.
    pub fn with_max_concurrent_scans(mut self, value: i64) -> Self {
        self.max_concurrent_scans = Some(value);
        self
    }
}

/// One validated canonical field in an accepted User Settings Update preview.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum UserSettingsUpdateField {
    /// `CLASSIC_Settings.Update Check`.
    UpdateCheck(bool),
    /// `CLASSIC_Settings.Managed Game`.
    ManagedGame(GameId),
    /// `CLASSIC_Settings.Game Version`.
    GameVersionSelection(GameVersionSelection),
    /// `CLASSIC_Settings.Game Folder Path`.
    GameRoot(Option<String>),
    /// `CLASSIC_Settings.Game EXE Path`.
    GameExecutable(Option<String>),
    /// `CLASSIC_Settings.Documents Folder Path`.
    DocumentsRoot(Option<String>),
    /// `CLASSIC_Settings.INI Folder Path`.
    IniFolder(Option<String>),
    /// `CLASSIC_Settings.MODS Folder Path`.
    ModsFolder(Option<String>),
    /// `CLASSIC_Settings.Papyrus Log Path`.
    PapyrusLogPath(Option<String>),
    /// `CLASSIC_Settings.FCX Mode`.
    FcxMode(bool),
    /// `CLASSIC_Settings.Simplify Logs`.
    SimplifyLogs(bool),
    /// `CLASSIC_Settings.Show Statistics`.
    ShowStatistics(bool),
    /// `CLASSIC_Settings.Show FormID Values`.
    FormIdValueLookup(bool),
    /// `CLASSIC_Settings.FormID Databases`.
    FormIdDatabases(BTreeMap<String, Vec<String>>),
    /// `CLASSIC_Settings.Move Unsolved Logs`.
    MoveUnsolvedLogs(bool),
    /// `CLASSIC_Settings.Unsolved Logs Destination`.
    UnsolvedLogsDestination(Option<String>),
    /// `CLASSIC_Settings.SCAN Custom Path`.
    CustomScanInput(Option<String>),
    /// `CLASSIC_Settings.Max Concurrent Scans`.
    MaxConcurrentScans(u32),
}

impl UserSettingsUpdateField {
    /// Returns the canonical RFC 6901-style path named by this accepted field.
    pub fn canonical_path(&self) -> &'static str {
        self.canonical_paths().0
    }

    /// Returns the dot-separated path used by the shared YAML patch helper.
    pub(crate) fn canonical_key_path(&self) -> &'static str {
        self.canonical_paths().1
    }

    /// Keeps the public pointer and internal YAML path paired in one exhaustive mapping.
    fn canonical_paths(&self) -> (&'static str, &'static str) {
        match self {
            Self::UpdateCheck(_) => (
                "/CLASSIC_Settings/Update Check",
                "CLASSIC_Settings.Update Check",
            ),
            Self::ManagedGame(_) => (
                "/CLASSIC_Settings/Managed Game",
                "CLASSIC_Settings.Managed Game",
            ),
            Self::GameVersionSelection(_) => (
                "/CLASSIC_Settings/Game Version",
                "CLASSIC_Settings.Game Version",
            ),
            Self::GameRoot(_) => (
                "/CLASSIC_Settings/Game Folder Path",
                "CLASSIC_Settings.Game Folder Path",
            ),
            Self::GameExecutable(_) => (
                "/CLASSIC_Settings/Game EXE Path",
                "CLASSIC_Settings.Game EXE Path",
            ),
            Self::DocumentsRoot(_) => (
                "/CLASSIC_Settings/Documents Folder Path",
                "CLASSIC_Settings.Documents Folder Path",
            ),
            Self::IniFolder(_) => (
                "/CLASSIC_Settings/INI Folder Path",
                "CLASSIC_Settings.INI Folder Path",
            ),
            Self::ModsFolder(_) => (
                "/CLASSIC_Settings/MODS Folder Path",
                "CLASSIC_Settings.MODS Folder Path",
            ),
            Self::PapyrusLogPath(_) => (
                "/CLASSIC_Settings/Papyrus Log Path",
                "CLASSIC_Settings.Papyrus Log Path",
            ),
            Self::FcxMode(_) => ("/CLASSIC_Settings/FCX Mode", "CLASSIC_Settings.FCX Mode"),
            Self::SimplifyLogs(_) => (
                "/CLASSIC_Settings/Simplify Logs",
                "CLASSIC_Settings.Simplify Logs",
            ),
            Self::ShowStatistics(_) => (
                "/CLASSIC_Settings/Show Statistics",
                "CLASSIC_Settings.Show Statistics",
            ),
            Self::FormIdValueLookup(_) => (
                "/CLASSIC_Settings/Show FormID Values",
                "CLASSIC_Settings.Show FormID Values",
            ),
            Self::FormIdDatabases(_) => (
                "/CLASSIC_Settings/FormID Databases",
                "CLASSIC_Settings.FormID Databases",
            ),
            Self::MoveUnsolvedLogs(_) => (
                "/CLASSIC_Settings/Move Unsolved Logs",
                "CLASSIC_Settings.Move Unsolved Logs",
            ),
            Self::UnsolvedLogsDestination(_) => (
                "/CLASSIC_Settings/Unsolved Logs Destination",
                "CLASSIC_Settings.Unsolved Logs Destination",
            ),
            Self::CustomScanInput(_) => (
                "/CLASSIC_Settings/SCAN Custom Path",
                "CLASSIC_Settings.SCAN Custom Path",
            ),
            Self::MaxConcurrentScans(_) => (
                "/CLASSIC_Settings/Max Concurrent Scans",
                "CLASSIC_Settings.Max Concurrent Scans",
            ),
        }
    }
}

/// Field-specific reason that a User Settings Update preview was rejected.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UpdateDiagnostic {
    field_path: Option<&'static str>,
    code: &'static str,
    message: String,
}

impl UpdateDiagnostic {
    /// Creates a diagnostic for one requested canonical field.
    fn for_field(field_path: &'static str, code: &'static str, message: impl Into<String>) -> Self {
        Self {
            field_path: Some(field_path),
            code,
            message: message.into(),
        }
    }

    /// Creates a preview-level diagnostic not attributable to one requested field.
    fn for_preview(code: &'static str, message: impl Into<String>) -> Self {
        Self {
            field_path: None,
            code,
            message: message.into(),
        }
    }

    /// Returns the rejected canonical field path, or `None` for a preview-level failure.
    pub fn field_path(&self) -> Option<&'static str> {
        self.field_path
    }

    /// Returns the stable diagnostic code used for programmatic handling.
    pub fn code(&self) -> &'static str {
        self.code
    }

    /// Returns human-readable rejection context.
    pub fn message(&self) -> &str {
        &self.message
    }
}

/// A validated update plan anchored to the source revision opened by the caller.
///
/// This is the only Rust artifact that can enter the explicit commit operation; callers cannot
/// publish a raw or rejected [`UserSettingsUpdate`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AcceptedUserSettingsUpdate {
    base_revision: Revision,
    fields: Vec<UserSettingsUpdateField>,
}

impl AcceptedUserSettingsUpdate {
    /// Returns the content revision against which this update was validated.
    pub fn base_revision(&self) -> &Revision {
        &self.base_revision
    }

    /// Returns only the canonical fields explicitly requested and accepted by the preview.
    pub fn fields(&self) -> &[UserSettingsUpdateField] {
        &self.fields
    }
}

/// All-or-nothing result of validating a User Settings Update without persistence.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum UserSettingsUpdatePreview {
    /// Every requested field is valid and represented in one revision-anchored preview.
    Accepted(AcceptedUserSettingsUpdate),
    /// No partial preview was produced; every discovered rejection is returned.
    Rejected(Vec<UpdateDiagnostic>),
}

impl UserSettings {
    /// Validates a multi-field User Settings Update without changing the snapshot or disk.
    ///
    /// Every requested field is checked in one pass. Any rejection discards all otherwise-valid
    /// fields so callers can only accept a complete, revision-anchored update.
    pub fn preview_update(&self, update: UserSettingsUpdate) -> UserSettingsUpdatePreview {
        if self.commit_eligibility() != CommitEligibility::Eligible {
            return UserSettingsUpdatePreview::Rejected(vec![UpdateDiagnostic::for_preview(
                "update_base_not_commit_eligible",
                "User Settings must be current and trusted before an update can be previewed",
            )]);
        }

        let mut fields = Vec::new();
        let mut diagnostics = Vec::new();

        if let Some(value) = update.update_check {
            fields.push(UserSettingsUpdateField::UpdateCheck(value));
        }
        if let Some(value) = update.managed_game {
            match parse_managed_game(&value) {
                Some(value) => fields.push(UserSettingsUpdateField::ManagedGame(value)),
                None => diagnostics.push(UpdateDiagnostic::for_field(
                    "/CLASSIC_Settings/Managed Game",
                    "invalid_enum_managed_game",
                    "Managed Game must be Fallout 4, Fallout 4 VR, Skyrim SE, or Starfield",
                )),
            }
        }
        if let Some(value) = update.game_version_selection {
            match GameVersionSelection::parse_canonical(&value) {
                Some(value) => {
                    fields.push(UserSettingsUpdateField::GameVersionSelection(value));
                }
                None => diagnostics.push(UpdateDiagnostic::for_field(
                    "/CLASSIC_Settings/Game Version",
                    "invalid_enum_game_version",
                    "Game Version must be auto, Original, NextGen, AnniversaryEdition, or VR",
                )),
            }
        }
        validate_optional_path_update(
            update.game_root,
            "/CLASSIC_Settings/Game Folder Path",
            "invalid_path_game_root",
            "Game Folder Path must be empty or an absolute path",
            UserSettingsUpdateField::GameRoot,
            &mut fields,
            &mut diagnostics,
        );
        validate_optional_path_update(
            update.game_executable,
            "/CLASSIC_Settings/Game EXE Path",
            "invalid_path_game_executable",
            "Game EXE Path must be empty or an absolute path",
            UserSettingsUpdateField::GameExecutable,
            &mut fields,
            &mut diagnostics,
        );
        validate_optional_path_update(
            update.documents_root,
            "/CLASSIC_Settings/Documents Folder Path",
            "invalid_path_documents_root",
            "Documents Folder Path must be empty or an absolute path",
            UserSettingsUpdateField::DocumentsRoot,
            &mut fields,
            &mut diagnostics,
        );
        validate_optional_path_update(
            update.ini_folder,
            "/CLASSIC_Settings/INI Folder Path",
            "invalid_path_ini_folder",
            "INI Folder Path must be empty or an absolute path",
            UserSettingsUpdateField::IniFolder,
            &mut fields,
            &mut diagnostics,
        );
        validate_optional_path_update(
            update.mods_folder,
            "/CLASSIC_Settings/MODS Folder Path",
            "invalid_path_mods_folder",
            "MODS Folder Path must be empty or an absolute path",
            UserSettingsUpdateField::ModsFolder,
            &mut fields,
            &mut diagnostics,
        );
        if let Some(value) = update.fcx_mode {
            fields.push(UserSettingsUpdateField::FcxMode(value));
        }
        if let Some(value) = update.simplify_logs {
            fields.push(UserSettingsUpdateField::SimplifyLogs(value));
        }
        if let Some(value) = update.show_statistics {
            fields.push(UserSettingsUpdateField::ShowStatistics(value));
        }
        if let Some(value) = update.formid_value_lookup {
            fields.push(UserSettingsUpdateField::FormIdValueLookup(value));
        }
        if let Some(value) = update.formid_databases {
            if valid_formid_databases(&value) {
                fields.push(UserSettingsUpdateField::FormIdDatabases(value));
            } else {
                diagnostics.push(UpdateDiagnostic::for_field(
                    "/CLASSIC_Settings/FormID Databases",
                    "invalid_value_formid_databases",
                    "FormID Databases game names and path strings must not be empty",
                ));
            }
        }
        if let Some(value) = update.move_unsolved_logs {
            fields.push(UserSettingsUpdateField::MoveUnsolvedLogs(value));
        }
        if let Some(value) = update.unsolved_logs_destination {
            if valid_optional_absolute_path(value.as_deref()) {
                fields.push(UserSettingsUpdateField::UnsolvedLogsDestination(value));
            } else {
                diagnostics.push(UpdateDiagnostic::for_field(
                    "/CLASSIC_Settings/Unsolved Logs Destination",
                    "invalid_path_unsolved_logs_destination",
                    "Unsolved Logs Destination must be empty or an absolute path",
                ));
            }
        }
        if let Some(value) = update.custom_scan_input {
            if valid_optional_absolute_path(value.as_deref()) {
                fields.push(UserSettingsUpdateField::CustomScanInput(value));
            } else {
                diagnostics.push(UpdateDiagnostic::for_field(
                    "/CLASSIC_Settings/SCAN Custom Path",
                    "invalid_path_custom_scan_input",
                    "SCAN Custom Path must be empty or an absolute path",
                ));
            }
        }
        validate_optional_path_update(
            update.papyrus_log_path,
            "/CLASSIC_Settings/Papyrus Log Path",
            "invalid_path_papyrus_log",
            "Papyrus Log Path must be empty or an absolute path",
            UserSettingsUpdateField::PapyrusLogPath,
            &mut fields,
            &mut diagnostics,
        );
        if let Some(value) = update.max_concurrent_scans {
            if let Ok(value) = u32::try_from(value)
                && value <= 32
            {
                fields.push(UserSettingsUpdateField::MaxConcurrentScans(value));
            } else {
                diagnostics.push(UpdateDiagnostic::for_field(
                    "/CLASSIC_Settings/Max Concurrent Scans",
                    "invalid_range_max_concurrent_scans",
                    "Max Concurrent Scans must be between 0 and 32",
                ));
            }
        }

        if diagnostics.is_empty() {
            UserSettingsUpdatePreview::Accepted(AcceptedUserSettingsUpdate {
                base_revision: self.revision().clone(),
                fields,
            })
        } else {
            UserSettingsUpdatePreview::Rejected(diagnostics)
        }
    }
}

/// Validates one optional path update and appends either its field or diagnostic.
fn validate_optional_path_update(
    value: Option<Option<String>>,
    field_path: &'static str,
    code: &'static str,
    message: &'static str,
    field: impl FnOnce(Option<String>) -> UserSettingsUpdateField,
    fields: &mut Vec<UserSettingsUpdateField>,
    diagnostics: &mut Vec<UpdateDiagnostic>,
) {
    let Some(value) = value else {
        return;
    };
    if valid_optional_absolute_path(value.as_deref()) {
        fields.push(field(value));
    } else {
        diagnostics.push(UpdateDiagnostic::for_field(field_path, code, message));
    }
}

/// Accepts native, Unix/Proton, Windows drive, and UNC forms on every build platform.
fn valid_optional_absolute_path(path: Option<&str>) -> bool {
    let Some(path) = path else {
        return true;
    };
    if path.is_empty() {
        return true;
    }

    is_absolute_user_path(path)
}
