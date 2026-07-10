use crate::scan_settings::{is_absolute_user_path, valid_formid_databases};
use crate::{CommitEligibility, GameVersionSelection, Revision, UserSettings};
use std::collections::BTreeMap;

/// A caller-authored, non-persisting request to change one or more User Settings.
///
/// Builder methods retain raw values that require validation so `preview_update` can
/// return every field-specific rejection diagnostic in one pass.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct UserSettingsUpdate {
    update_check: Option<bool>,
    game_version_selection: Option<String>,
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

    /// Requests a canonical game-version selection string.
    pub fn with_game_version_selection(mut self, value: impl Into<String>) -> Self {
        self.game_version_selection = Some(value.into());
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
    /// `CLASSIC_Settings.Game Version`.
    GameVersionSelection(GameVersionSelection),
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
        match self {
            Self::UpdateCheck(_) => "/CLASSIC_Settings/Update Check",
            Self::GameVersionSelection(_) => "/CLASSIC_Settings/Game Version",
            Self::FcxMode(_) => "/CLASSIC_Settings/FCX Mode",
            Self::SimplifyLogs(_) => "/CLASSIC_Settings/Simplify Logs",
            Self::ShowStatistics(_) => "/CLASSIC_Settings/Show Statistics",
            Self::FormIdValueLookup(_) => "/CLASSIC_Settings/Show FormID Values",
            Self::FormIdDatabases(_) => "/CLASSIC_Settings/FormID Databases",
            Self::MoveUnsolvedLogs(_) => "/CLASSIC_Settings/Move Unsolved Logs",
            Self::UnsolvedLogsDestination(_) => "/CLASSIC_Settings/Unsolved Logs Destination",
            Self::CustomScanInput(_) => "/CLASSIC_Settings/SCAN Custom Path",
            Self::MaxConcurrentScans(_) => "/CLASSIC_Settings/Max Concurrent Scans",
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
/// This type contains no persistence operation; issue #99 consumes it for explicit commits.
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

/// Accepts native absolute paths plus Windows drive and UNC forms on every build platform.
fn valid_optional_absolute_path(path: Option<&str>) -> bool {
    let Some(path) = path else {
        return true;
    };
    if path.is_empty() {
        return true;
    }

    is_absolute_user_path(path)
}
