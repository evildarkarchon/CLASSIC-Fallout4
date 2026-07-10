use crate::document::{Diagnostic, PreferenceOrigin};
use crate::preference::{
    OptionalPathField, Preference, aliased_optional_absolute_path_preference,
    optional_absolute_path_preference,
};
use classic_settings_core::Yaml;
use std::collections::BTreeMap;

const DEFAULT_FCX_MODE: bool = false;
const DEFAULT_SIMPLIFY_LOGS: bool = false;
const DEFAULT_SHOW_STATISTICS: bool = false;
const DEFAULT_FORMID_VALUE_LOOKUP: bool = false;
const DEFAULT_MOVE_UNSOLVED_LOGS: bool = true;
const DEFAULT_MAX_CONCURRENT_SCANS: u32 = 0;

/// Saved game-version selection used while preparing a Crash Log Scan.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GameVersionSelection {
    /// Detect the installed game version at runtime.
    Auto,
    /// Use the pre-next-generation Fallout 4 data set.
    Original,
    /// Use the next-generation Fallout 4 data set.
    NextGen,
    /// Use the Fallout 4 Anniversary Edition data set.
    AnniversaryEdition,
    /// Use the Fallout 4 VR data set.
    Vr,
}

impl GameVersionSelection {
    /// Returns the canonical User Settings scalar for this selection.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Auto => "auto",
            Self::Original => "Original",
            Self::NextGen => "NextGen",
            Self::AnniversaryEdition => "AnniversaryEdition",
            Self::Vr => "VR",
        }
    }

    /// Parses a supported User Settings value without collapsing `auto` into a concrete version.
    pub fn parse(value: &str) -> Option<Self> {
        Self::parse_canonical(value).or(match value {
            "Auto" => Some(Self::Auto),
            "AE" => Some(Self::AnniversaryEdition),
            _ => None,
        })
    }

    /// Parses only canonical persisted values for accepted update previews.
    pub(crate) fn parse_canonical(value: &str) -> Option<Self> {
        match value {
            "auto" => Some(Self::Auto),
            "Original" => Some(Self::Original),
            "NextGen" => Some(Self::NextGen),
            "AnniversaryEdition" => Some(Self::AnniversaryEdition),
            "VR" => Some(Self::Vr),
            _ => None,
        }
    }
}

/// Cohesive, safety-adjusted User Settings used by Crash Log Scan preparation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CrashLogScanSettings {
    fcx_mode: Preference<bool>,
    simplify_logs: Preference<bool>,
    show_statistics: Preference<bool>,
    formid_value_lookup: Preference<bool>,
    formid_databases: Preference<BTreeMap<String, Vec<String>>>,
    move_unsolved_logs: Preference<bool>,
    unsolved_logs_destination: Preference<Option<String>>,
    custom_scan_input: Preference<Option<String>>,
    game_version_selection: Preference<GameVersionSelection>,
    max_concurrent_scans: Preference<u32>,
}

impl CrashLogScanSettings {
    /// Returns whether FCX Mode is enabled.
    pub fn fcx_mode(&self) -> bool {
        self.fcx_mode.value
    }

    /// Returns the source of the FCX Mode value.
    pub fn fcx_mode_origin(&self) -> PreferenceOrigin {
        self.fcx_mode.origin
    }

    /// Returns whether Crash Logs should be simplified before analysis.
    pub fn simplify_logs(&self) -> bool {
        self.simplify_logs.value
    }

    /// Returns the source of the Simplify Logs value.
    pub fn simplify_logs_origin(&self) -> PreferenceOrigin {
        self.simplify_logs.origin
    }

    /// Returns whether scan statistics should be included in output.
    pub fn show_statistics(&self) -> bool {
        self.show_statistics.value
    }

    /// Returns the source of the Show Statistics value.
    pub fn show_statistics_origin(&self) -> PreferenceOrigin {
        self.show_statistics.origin
    }

    /// Returns whether FormID Value Lookup is enabled.
    pub fn formid_value_lookup(&self) -> bool {
        self.formid_value_lookup.value
    }

    /// Returns the source of the FormID Value Lookup value.
    pub fn formid_value_lookup_origin(&self) -> PreferenceOrigin {
        self.formid_value_lookup.origin
    }

    /// Returns additional FormID database paths keyed by managed game.
    ///
    /// Paths remain exactly as persisted; scan preparation resolves relative paths later.
    pub fn formid_databases(&self) -> &BTreeMap<String, Vec<String>> {
        &self.formid_databases.value
    }

    /// Returns the source of the FormID Databases mapping.
    pub fn formid_databases_origin(&self) -> PreferenceOrigin {
        self.formid_databases.origin
    }

    /// Returns whether a Standard Crash Log Scan Run may move Unsolved Logs.
    pub fn move_unsolved_logs(&self) -> bool {
        self.move_unsolved_logs.value
    }

    /// Returns the source of the Move Unsolved Logs value.
    pub fn move_unsolved_logs_origin(&self) -> PreferenceOrigin {
        self.move_unsolved_logs.origin
    }

    /// Returns the optional persisted Unsolved Logs Destination without path normalization.
    pub fn unsolved_logs_destination(&self) -> Option<&str> {
        self.unsolved_logs_destination.value.as_deref()
    }

    /// Returns the source of the Unsolved Logs Destination value.
    pub fn unsolved_logs_destination_origin(&self) -> PreferenceOrigin {
        self.unsolved_logs_destination.origin
    }

    /// Returns the optional custom Crash Log Scan input without path normalization.
    pub fn custom_scan_input(&self) -> Option<&str> {
        self.custom_scan_input.value.as_deref()
    }

    /// Returns the source of the custom Crash Log Scan input.
    pub fn custom_scan_input_origin(&self) -> PreferenceOrigin {
        self.custom_scan_input.origin
    }

    /// Returns the saved game-version selection.
    pub fn game_version_selection(&self) -> GameVersionSelection {
        self.game_version_selection.value
    }

    /// Returns the source of the game-version selection.
    pub fn game_version_selection_origin(&self) -> PreferenceOrigin {
        self.game_version_selection.origin
    }

    /// Returns the requested scan concurrency, where zero selects the adaptive default.
    pub fn max_concurrent_scans(&self) -> u32 {
        self.max_concurrent_scans.value
    }

    /// Returns the source of the requested scan concurrency.
    pub fn max_concurrent_scans_origin(&self) -> PreferenceOrigin {
        self.max_concurrent_scans.origin
    }

    /// Builds the group from the Rust-owned published defaults.
    pub(crate) fn published_defaults() -> Self {
        Self::with_origin(PreferenceOrigin::Default, DEFAULT_MOVE_UNSOLVED_LOGS)
    }

    /// Builds the group from risk-sensitive fallbacks for an untrusted document.
    pub(crate) fn degraded_fallbacks() -> Self {
        Self::with_origin(PreferenceOrigin::DegradedFallback, false)
    }

    /// Projects a trusted nested User Settings mapping and returns per-field diagnostics.
    pub(crate) fn from_nested_document(document: &Yaml) -> (Self, Vec<Diagnostic>) {
        let group = &document["CLASSIC_Settings"];
        let mut diagnostics = Vec::new();
        let game_version_selection =
            game_version_preference(&group["Game Version"], &mut diagnostics);
        let fcx_mode = bool_preference(
            &group["FCX Mode"],
            DEFAULT_FCX_MODE,
            false,
            "invalid_type_fcx_mode",
            "CLASSIC_Settings.FCX Mode must be a boolean",
            &mut diagnostics,
        );
        let simplify_logs = bool_preference(
            &group["Simplify Logs"],
            DEFAULT_SIMPLIFY_LOGS,
            false,
            "invalid_type_simplify_logs",
            "CLASSIC_Settings.Simplify Logs must be a boolean",
            &mut diagnostics,
        );
        let show_statistics = bool_preference(
            &group["Show Statistics"],
            DEFAULT_SHOW_STATISTICS,
            false,
            "invalid_type_show_statistics",
            "CLASSIC_Settings.Show Statistics must be a boolean",
            &mut diagnostics,
        );
        let formid_value_lookup = bool_preference(
            &group["Show FormID Values"],
            DEFAULT_FORMID_VALUE_LOOKUP,
            false,
            "invalid_type_show_formid_values",
            "CLASSIC_Settings.Show FormID Values must be a boolean",
            &mut diagnostics,
        );
        let move_unsolved_logs = bool_preference(
            &group["Move Unsolved Logs"],
            DEFAULT_MOVE_UNSOLVED_LOGS,
            false,
            "invalid_type_move_unsolved_logs",
            "CLASSIC_Settings.Move Unsolved Logs must be a boolean",
            &mut diagnostics,
        );
        let unsolved_logs_destination = optional_absolute_path_preference(
            &group["Unsolved Logs Destination"],
            OptionalPathField::new(
                "CLASSIC_Settings.Unsolved Logs Destination",
                "invalid_type_unsolved_logs_destination",
                "invalid_path_unsolved_logs_destination",
            ),
            &mut diagnostics,
        );
        let custom_scan_input = custom_scan_input_preference(group, &mut diagnostics);
        let max_concurrent_scans =
            concurrency_preference(&group["Max Concurrent Scans"], &mut diagnostics);
        let formid_databases =
            formid_databases_preference(&group["FormID Databases"], &mut diagnostics);

        (
            Self {
                fcx_mode,
                simplify_logs,
                show_statistics,
                formid_value_lookup,
                formid_databases,
                move_unsolved_logs,
                unsolved_logs_destination,
                custom_scan_input,
                game_version_selection,
                max_concurrent_scans,
            },
            diagnostics,
        )
    }

    /// Projects the recognized flat ClassicConfig shape pending explicit migration.
    pub(crate) fn from_legacy_flat_document(document: &Yaml) -> (Self, Vec<Diagnostic>) {
        let mut diagnostics = Vec::new();
        let fcx_mode = bool_preference(
            &document["fcx_mode"],
            DEFAULT_FCX_MODE,
            false,
            "invalid_type_fcx_mode",
            "fcx_mode must be a boolean",
            &mut diagnostics,
        );
        let simplify_logs = bool_preference(
            &document["simplify_logs"],
            DEFAULT_SIMPLIFY_LOGS,
            false,
            "invalid_type_simplify_logs",
            "simplify_logs must be a boolean",
            &mut diagnostics,
        );
        let show_statistics = bool_preference(
            &document["stat_logging"],
            DEFAULT_SHOW_STATISTICS,
            false,
            "invalid_type_show_statistics",
            "stat_logging must be a boolean",
            &mut diagnostics,
        );
        let formid_value_lookup = bool_preference(
            &document["show_formid_values"],
            DEFAULT_FORMID_VALUE_LOOKUP,
            false,
            "invalid_type_show_formid_values",
            "show_formid_values must be a boolean",
            &mut diagnostics,
        );
        let move_unsolved_logs = bool_preference(
            &document["move_unsolved_logs"],
            DEFAULT_MOVE_UNSOLVED_LOGS,
            false,
            "invalid_type_move_unsolved_logs",
            "move_unsolved_logs must be a boolean",
            &mut diagnostics,
        );
        let unsolved_logs_destination = optional_absolute_path_preference(
            &document["unsolved_logs_destination"],
            OptionalPathField::new(
                "unsolved_logs_destination",
                "invalid_type_unsolved_logs_destination",
                "invalid_path_unsolved_logs_destination",
            ),
            &mut diagnostics,
        );
        let custom_scan_input = optional_absolute_path_preference(
            &document["paths"]["scan_custom"],
            OptionalPathField::new(
                "paths.scan_custom",
                "invalid_type_custom_scan_input",
                "invalid_path_custom_scan_input",
            ),
            &mut diagnostics,
        );
        let game_version_selection =
            game_version_preference(&document["game_version"], &mut diagnostics);
        let max_concurrent_scans =
            Preference::new(DEFAULT_MAX_CONCURRENT_SCANS, PreferenceOrigin::Default);
        let formid_databases =
            formid_databases_preference(&document["formid_databases"], &mut diagnostics);

        (
            Self {
                fcx_mode,
                simplify_logs,
                show_statistics,
                formid_value_lookup,
                formid_databases,
                move_unsolved_logs,
                unsolved_logs_destination,
                custom_scan_input,
                game_version_selection,
                max_concurrent_scans,
            },
            diagnostics,
        )
    }

    /// Builds a complete group whose fields share one provenance.
    fn with_origin(origin: PreferenceOrigin, move_unsolved_logs: bool) -> Self {
        Self {
            fcx_mode: Preference::new(false, origin),
            simplify_logs: Preference::new(false, origin),
            show_statistics: Preference::new(false, origin),
            formid_value_lookup: Preference::new(false, origin),
            formid_databases: Preference::new(BTreeMap::new(), origin),
            move_unsolved_logs: Preference::new(move_unsolved_logs, origin),
            unsolved_logs_destination: Preference::new(None, origin),
            custom_scan_input: Preference::new(None, origin),
            game_version_selection: Preference::new(GameVersionSelection::Auto, origin),
            max_concurrent_scans: Preference::new(DEFAULT_MAX_CONCURRENT_SCANS, origin),
        }
    }
}

/// Projects a boolean preference with distinct published and degraded fallbacks.
fn bool_preference(
    node: &Yaml,
    default: bool,
    degraded: bool,
    code: &'static str,
    message: &'static str,
    diagnostics: &mut Vec<Diagnostic>,
) -> Preference<bool> {
    match node {
        Yaml::Boolean(value) => Preference::new(*value, PreferenceOrigin::Document),
        Yaml::BadValue => Preference::new(default, PreferenceOrigin::Default),
        _ => {
            diagnostics.push(Diagnostic::new(code, message));
            Preference::new(degraded, PreferenceOrigin::DegradedFallback)
        }
    }
}

/// Resolves the canonical custom-scan label ahead of its GUI-era alias.
fn custom_scan_input_preference(
    group: &Yaml,
    diagnostics: &mut Vec<Diagnostic>,
) -> Preference<Option<String>> {
    aliased_optional_absolute_path_preference(
        &group["SCAN Custom Path"],
        &group["Custom Scan Folder"],
        OptionalPathField::new(
            "CLASSIC_Settings.SCAN Custom Path",
            "invalid_type_custom_scan_input",
            "invalid_path_custom_scan_input",
        ),
        OptionalPathField::new(
            "CLASSIC_Settings.Custom Scan Folder",
            "invalid_type_custom_scan_input",
            "invalid_path_custom_scan_input",
        ),
        "canonical_alias_conflict_custom_scan_folder",
        "CLASSIC_Settings.SCAN Custom Path overrides conflicting Custom Scan Folder",
        diagnostics,
    )
    .resolved
}

/// Projects the game-version selection with `auto` as its safe fallback.
fn game_version_preference(
    node: &Yaml,
    diagnostics: &mut Vec<Diagnostic>,
) -> Preference<GameVersionSelection> {
    match node {
        Yaml::String(value) => match GameVersionSelection::parse(value) {
            Some(selection) => Preference::new(selection, PreferenceOrigin::Document),
            None => {
                diagnostics.push(Diagnostic::new(
                    "invalid_enum_game_version",
                    "CLASSIC_Settings.Game Version is not a supported selection",
                ));
                Preference::new(
                    GameVersionSelection::Auto,
                    PreferenceOrigin::DegradedFallback,
                )
            }
        },
        Yaml::BadValue => Preference::new(GameVersionSelection::Auto, PreferenceOrigin::Default),
        _ => {
            diagnostics.push(Diagnostic::new(
                "invalid_enum_game_version",
                "CLASSIC_Settings.Game Version is not a supported selection",
            ));
            Preference::new(
                GameVersionSelection::Auto,
                PreferenceOrigin::DegradedFallback,
            )
        }
    }
}

/// Projects the bounded Crash Log Scan concurrency setting.
fn concurrency_preference(node: &Yaml, diagnostics: &mut Vec<Diagnostic>) -> Preference<u32> {
    match node {
        Yaml::Integer(value) if (0..=32).contains(value) => {
            Preference::new(*value as u32, PreferenceOrigin::Document)
        }
        Yaml::Integer(_) => {
            diagnostics.push(Diagnostic::new(
                "invalid_range_max_concurrent_scans",
                "CLASSIC_Settings.Max Concurrent Scans must be between 0 and 32",
            ));
            Preference::new(
                DEFAULT_MAX_CONCURRENT_SCANS,
                PreferenceOrigin::DegradedFallback,
            )
        }
        Yaml::BadValue => Preference::new(DEFAULT_MAX_CONCURRENT_SCANS, PreferenceOrigin::Default),
        _ => {
            diagnostics.push(Diagnostic::new(
                "invalid_type_max_concurrent_scans",
                "CLASSIC_Settings.Max Concurrent Scans must be an integer",
            ));
            Preference::new(
                DEFAULT_MAX_CONCURRENT_SCANS,
                PreferenceOrigin::DegradedFallback,
            )
        }
    }
}

/// Projects game-keyed FormID database path lists as one trusted preference.
fn formid_databases_preference(
    node: &Yaml,
    diagnostics: &mut Vec<Diagnostic>,
) -> Preference<BTreeMap<String, Vec<String>>> {
    let Yaml::Hash(mapping) = node else {
        if matches!(node, Yaml::BadValue) {
            return Preference::new(BTreeMap::new(), PreferenceOrigin::Default);
        }
        diagnostics.push(Diagnostic::new(
            "invalid_type_formid_databases",
            "CLASSIC_Settings.FormID Databases must map game names to string lists",
        ));
        return Preference::new(BTreeMap::new(), PreferenceOrigin::DegradedFallback);
    };

    let mut databases = BTreeMap::new();
    for (game, paths) in mapping {
        let (Some(game), Yaml::Array(paths)) = (game.as_str(), paths) else {
            diagnostics.push(Diagnostic::new(
                "invalid_type_formid_databases",
                "CLASSIC_Settings.FormID Databases must map game names to string lists",
            ));
            return Preference::new(BTreeMap::new(), PreferenceOrigin::DegradedFallback);
        };
        let Some(paths) = paths
            .iter()
            .map(Yaml::as_str)
            .map(|path| path.map(str::to_string))
            .collect::<Option<Vec<_>>>()
        else {
            diagnostics.push(Diagnostic::new(
                "invalid_type_formid_databases",
                "CLASSIC_Settings.FormID Databases must map game names to string lists",
            ));
            return Preference::new(BTreeMap::new(), PreferenceOrigin::DegradedFallback);
        };
        databases.insert(game.to_string(), paths);
    }

    if valid_formid_databases(&databases) {
        Preference::new(databases, PreferenceOrigin::Document)
    } else {
        diagnostics.push(Diagnostic::new(
            "invalid_value_formid_databases",
            "CLASSIC_Settings.FormID Databases game names and path strings must not be empty",
        ));
        Preference::new(BTreeMap::new(), PreferenceOrigin::DegradedFallback)
    }
}

/// Returns whether a FormID database mapping contains usable game names and paths.
pub(crate) fn valid_formid_databases(databases: &BTreeMap<String, Vec<String>>) -> bool {
    databases
        .iter()
        .all(|(game, paths)| !game.is_empty() && paths.iter().all(|path| !path.is_empty()))
}
