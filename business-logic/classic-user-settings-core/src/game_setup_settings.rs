use crate::default_settings::{
    DOCUMENTS_FOLDER_PATH, GAME_EXE_PATH, GAME_FOLDER_PATH, INI_FOLDER_PATH, MANAGED_GAME,
    MODS_FOLDER_PATH, PAPYRUS_LOG_PATH, SCAN_CUSTOM_PATH, SettingMetadata,
};
use crate::document::{Diagnostic, PreferenceOrigin};
use crate::preference::{
    OptionalPathField, Preference, aliased_optional_absolute_path_preference,
    optional_absolute_path_preference,
};
use crate::scan_settings::{CrashLogScanSettings, GameVersionSelection};
use classic_settings_core::Yaml;
use classic_shared_core::GameId;

/// Cohesive, read-only User Settings facts used to prepare Game Setup Intake.
///
/// Persisted paths remain strings so opening settings never normalizes separators or
/// rewrites spelling chosen by the user.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameSetupSettings {
    managed_game: Preference<GameId>,
    game_version_selection: Preference<GameVersionSelection>,
    game_root: Preference<Option<String>>,
    game_executable: Preference<Option<String>>,
    documents_root: Preference<Option<String>>,
    ini_folder: Preference<Option<String>>,
    mods_root: Preference<Option<String>>,
    custom_scan_input: Preference<Option<String>>,
    papyrus_log: Preference<Option<String>>,
}

impl GameSetupSettings {
    /// Returns the managed game used to prepare Game Setup Intake.
    pub fn managed_game(&self) -> GameId {
        self.managed_game.value
    }

    /// Returns the source of the managed-game value.
    pub fn managed_game_origin(&self) -> PreferenceOrigin {
        self.managed_game.origin
    }

    /// Returns the saved game-version selection.
    pub fn game_version_selection(&self) -> GameVersionSelection {
        self.game_version_selection.value
    }

    /// Returns the source of the game-version selection.
    pub fn game_version_selection_origin(&self) -> PreferenceOrigin {
        self.game_version_selection.origin
    }

    /// Returns the optional persisted game installation root without normalization.
    pub fn game_root(&self) -> Option<&str> {
        self.game_root.value.as_deref()
    }

    /// Returns the source of the game installation root.
    pub fn game_root_origin(&self) -> PreferenceOrigin {
        self.game_root.origin
    }

    /// Returns the optional persisted game executable without normalization.
    pub fn game_executable(&self) -> Option<&str> {
        self.game_executable.value.as_deref()
    }

    /// Returns the source of the game executable path.
    pub fn game_executable_origin(&self) -> PreferenceOrigin {
        self.game_executable.origin
    }

    /// Returns the optional persisted documents root without normalization.
    pub fn documents_root(&self) -> Option<&str> {
        self.documents_root.value.as_deref()
    }

    /// Returns the source of the documents root.
    pub fn documents_root_origin(&self) -> PreferenceOrigin {
        self.documents_root.origin
    }

    /// Returns the optional persisted INI-folder override without normalization.
    pub fn ini_folder(&self) -> Option<&str> {
        self.ini_folder.value.as_deref()
    }

    /// Returns the source of the INI-folder override.
    pub fn ini_folder_origin(&self) -> PreferenceOrigin {
        self.ini_folder.origin
    }

    /// Returns the optional persisted mods or staging root without normalization.
    pub fn mods_root(&self) -> Option<&str> {
        self.mods_root.value.as_deref()
    }

    /// Returns the source of the mods or staging root.
    pub fn mods_root_origin(&self) -> PreferenceOrigin {
        self.mods_root.origin
    }

    /// Returns the optional custom Crash Log Scan input without normalization.
    pub fn custom_scan_input(&self) -> Option<&str> {
        self.custom_scan_input.value.as_deref()
    }

    /// Returns the source of the custom Crash Log Scan input.
    pub fn custom_scan_input_origin(&self) -> PreferenceOrigin {
        self.custom_scan_input.origin
    }

    /// Returns the optional persisted Papyrus log path without normalization.
    pub fn papyrus_log(&self) -> Option<&str> {
        self.papyrus_log.value.as_deref()
    }

    /// Returns the source of the Papyrus log path.
    pub fn papyrus_log_origin(&self) -> PreferenceOrigin {
        self.papyrus_log.origin
    }

    /// Builds the group from Rust-owned published defaults.
    pub(crate) fn published_defaults() -> Self {
        Self::with_origin(PreferenceOrigin::Default)
    }

    /// Builds the group from safety-oriented fallbacks for an untrusted document.
    pub(crate) fn degraded_fallbacks() -> Self {
        Self::with_origin(PreferenceOrigin::DegradedFallback)
    }

    /// Projects a trusted nested document together with already-parsed shared scan facts.
    pub(crate) fn from_nested_document(
        document: &Yaml,
        scan: &CrashLogScanSettings,
    ) -> (Self, Vec<Diagnostic>) {
        let group = &document[MANAGED_GAME.path()[0]];
        let mut diagnostics = Vec::new();
        let managed_game = managed_game_preference(&group[MANAGED_GAME.label()], &mut diagnostics);
        let game_root = optional_absolute_path_preference(
            &group[GAME_FOLDER_PATH.label()],
            OptionalPathField::new(
                "CLASSIC_Settings.Game Folder Path",
                "invalid_type_game_root",
                "invalid_path_game_root",
            ),
            &mut diagnostics,
        );
        let game_executable = optional_absolute_path_preference(
            &group[GAME_EXE_PATH.label()],
            OptionalPathField::new(
                "CLASSIC_Settings.Game EXE Path",
                "invalid_type_game_executable",
                "invalid_path_game_executable",
            ),
            &mut diagnostics,
        );
        let documents_paths = aliased_optional_absolute_path_preference(
            &group[DOCUMENTS_FOLDER_PATH.label()],
            &group[INI_FOLDER_PATH.label()],
            OptionalPathField::new(
                "CLASSIC_Settings.Documents Folder Path",
                "invalid_type_documents_root",
                "invalid_path_documents_root",
            ),
            OptionalPathField::new(
                "CLASSIC_Settings.INI Folder Path",
                "invalid_type_ini_folder",
                "invalid_path_ini_folder",
            ),
            "canonical_alias_conflict_ini_folder",
            "CLASSIC_Settings.Documents Folder Path overrides conflicting INI Folder Path",
            &mut diagnostics,
        );
        let mods_root = aliased_optional_absolute_path_preference(
            &group[MODS_FOLDER_PATH.label()],
            &group["Staging Mods Folder"],
            OptionalPathField::new(
                "CLASSIC_Settings.MODS Folder Path",
                "invalid_type_mods_folder",
                "invalid_path_mods_folder",
            ),
            OptionalPathField::new(
                "CLASSIC_Settings.Staging Mods Folder",
                "invalid_type_mods_folder",
                "invalid_path_mods_folder",
            ),
            "canonical_alias_conflict_mods_folder",
            "CLASSIC_Settings.MODS Folder Path overrides conflicting Staging Mods Folder",
            &mut diagnostics,
        )
        .resolved;
        let papyrus_log = optional_absolute_path_preference(
            &group[PAPYRUS_LOG_PATH.label()],
            OptionalPathField::new(
                "CLASSIC_Settings.Papyrus Log Path",
                "invalid_type_papyrus_log",
                "invalid_path_papyrus_log",
            ),
            &mut diagnostics,
        );

        (
            Self {
                managed_game,
                game_version_selection: Preference::new(
                    scan.game_version_selection(),
                    scan.game_version_selection_origin(),
                ),
                game_root,
                game_executable,
                documents_root: documents_paths.resolved,
                ini_folder: documents_paths.alias,
                mods_root,
                custom_scan_input: Preference::new(
                    scan.custom_scan_input().map(str::to_string),
                    scan.custom_scan_input_origin(),
                ),
                papyrus_log,
            },
            diagnostics,
        )
    }

    /// Projects the recognized flat ClassicConfig shape pending explicit migration.
    pub(crate) fn from_legacy_flat_document(
        document: &Yaml,
        scan: &CrashLogScanSettings,
    ) -> (Self, Vec<Diagnostic>) {
        let mut diagnostics = Vec::new();
        let paths = &document["paths"];
        let game_root = optional_absolute_path_preference(
            &paths["game_root"],
            OptionalPathField::new(
                "paths.game_root",
                "invalid_type_game_root",
                "invalid_path_game_root",
            ),
            &mut diagnostics,
        );
        let documents_paths = aliased_optional_absolute_path_preference(
            &paths["docs_root"],
            &paths["ini_folder"],
            OptionalPathField::new(
                "paths.docs_root",
                "invalid_type_documents_root",
                "invalid_path_documents_root",
            ),
            OptionalPathField::new(
                "paths.ini_folder",
                "invalid_type_ini_folder",
                "invalid_path_ini_folder",
            ),
            "canonical_alias_conflict_ini_folder",
            "paths.docs_root overrides conflicting paths.ini_folder",
            &mut diagnostics,
        );
        let mods_root = optional_absolute_path_preference(
            &paths["mods_folder"],
            OptionalPathField::new(
                "paths.mods_folder",
                "invalid_type_mods_folder",
                "invalid_path_mods_folder",
            ),
            &mut diagnostics,
        );

        (
            Self {
                managed_game: Preference::new(published_managed_game(), PreferenceOrigin::Default),
                game_version_selection: Preference::new(
                    scan.game_version_selection(),
                    scan.game_version_selection_origin(),
                ),
                game_root,
                game_executable: Preference::new(
                    published_optional_string(GAME_EXE_PATH),
                    PreferenceOrigin::Default,
                ),
                documents_root: documents_paths.resolved,
                ini_folder: documents_paths.alias,
                mods_root,
                custom_scan_input: Preference::new(
                    scan.custom_scan_input().map(str::to_string),
                    scan.custom_scan_input_origin(),
                ),
                papyrus_log: Preference::new(
                    published_optional_string(PAPYRUS_LOG_PATH),
                    PreferenceOrigin::Default,
                ),
            },
            diagnostics,
        )
    }

    /// Builds a complete group whose fields share one provenance.
    fn with_origin(origin: PreferenceOrigin) -> Self {
        Self {
            managed_game: Preference::new(published_managed_game(), origin),
            game_version_selection: Preference::new(
                GameVersionSelection::published_default(),
                origin,
            ),
            game_root: Preference::new(published_optional_string(GAME_FOLDER_PATH), origin),
            game_executable: Preference::new(published_optional_string(GAME_EXE_PATH), origin),
            documents_root: Preference::new(
                published_optional_string(DOCUMENTS_FOLDER_PATH),
                origin,
            ),
            ini_folder: Preference::new(published_optional_string(INI_FOLDER_PATH), origin),
            mods_root: Preference::new(published_optional_string(MODS_FOLDER_PATH), origin),
            custom_scan_input: Preference::new(published_optional_string(SCAN_CUSTOM_PATH), origin),
            papyrus_log: Preference::new(published_optional_string(PAPYRUS_LOG_PATH), origin),
        }
    }
}

/// Projects a supported managed-game label with a safe Fallout 4 fallback.
fn managed_game_preference(node: &Yaml, diagnostics: &mut Vec<Diagnostic>) -> Preference<GameId> {
    if let Some(game) = node.as_str().and_then(parse_managed_game) {
        return Preference::new(game, PreferenceOrigin::Document);
    }
    if matches!(node, Yaml::BadValue) {
        return Preference::new(published_managed_game(), PreferenceOrigin::Default);
    }

    diagnostics.push(Diagnostic::new(
        "invalid_enum_managed_game",
        "CLASSIC_Settings.Managed Game is not a supported game",
    ));
    Preference::new(published_managed_game(), PreferenceOrigin::DegradedFallback)
}

/// Converts the registry's stable managed-game label into the typed published default.
fn published_managed_game() -> GameId {
    parse_managed_game(MANAGED_GAME.default().as_str())
        .expect("Rust-owned Managed Game default must remain supported")
}

/// Converts one registry string/null value into an owned optional runtime default.
fn published_optional_string(setting: SettingMetadata) -> Option<String> {
    setting.default().as_optional_str().map(str::to_string)
}

/// Parses supported human-facing and stable managed-game identifiers.
pub(crate) fn parse_managed_game(value: &str) -> Option<GameId> {
    match value {
        "Fallout 4" | "Fallout4" => Some(GameId::Fallout4),
        "Fallout 4 VR" | "Fallout4VR" => Some(GameId::Fallout4VR),
        "Skyrim SE" | "Skyrim" => Some(GameId::Skyrim),
        "Starfield" => Some(GameId::Starfield),
        _ => None,
    }
}
