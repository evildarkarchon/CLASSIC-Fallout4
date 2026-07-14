//! Rust-owned User Settings metadata shared by runtime projection and mirror generation.

use std::collections::BTreeSet;

pub(crate) const USER_SETTINGS_SCHEMA_MAJOR: u32 = 1;
pub(crate) const USER_SETTINGS_SCHEMA_MINOR: u32 = 0;

/// One const-friendly YAML value used by the published-default registry.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum PublishedDefault {
    Bool(bool),
    Integer(i64),
    String(&'static str),
    Null,
    EmptyMapping,
}

impl PublishedDefault {
    /// Returns the boolean default expected by a typed runtime field.
    pub(crate) const fn as_bool(self) -> bool {
        match self {
            Self::Bool(value) => value,
            _ => panic!("published default is not a boolean"),
        }
    }

    /// Returns the integer default expected by a typed runtime field.
    pub(crate) const fn as_integer(self) -> i64 {
        match self {
            Self::Integer(value) => value,
            _ => panic!("published default is not an integer"),
        }
    }

    /// Returns the string default expected by a typed runtime field.
    pub(crate) const fn as_str(self) -> &'static str {
        match self {
            Self::String(value) => value,
            _ => panic!("published default is not a string"),
        }
    }

    /// Returns an optional string default, preserving explicit YAML null as `None`.
    pub(crate) const fn as_optional_str(self) -> Option<&'static str> {
        match self {
            Self::String(value) => Some(value),
            Self::Null => None,
            _ => panic!("published default is not a string or null"),
        }
    }

    /// Asserts that a typed collection is backed by the registry's empty-mapping default.
    pub(crate) const fn assert_empty_mapping(self) {
        if !matches!(self, Self::EmptyMapping) {
            panic!("published default is not an empty mapping");
        }
    }
}

/// Canonical label, published default, and user-facing guidance for one known setting.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct SettingMetadata {
    pub(crate) path: &'static [&'static str],
    pub(crate) dotted_path: &'static str,
    pub(crate) pointer_path: &'static str,
    pub(crate) default: PublishedDefault,
    pub(crate) guidance: &'static [&'static str],
    pub(crate) canonical: bool,
}

impl SettingMetadata {
    /// Returns the canonical or compatibility path from the document root.
    pub(crate) const fn path(self) -> &'static [&'static str] {
        self.path
    }

    /// Returns the leaf label used by runtime projection and mirror generation.
    pub(crate) const fn label(self) -> &'static str {
        self.path[self.path.len() - 1]
    }

    /// Returns the Rust-owned published default.
    pub(crate) const fn default(self) -> PublishedDefault {
        self.default
    }
}

macro_rules! setting {
    ($name:ident, [$first:literal $(, $path:literal)*], $default:expr, [$($guidance:literal),*], $canonical:literal) => {
        pub(crate) const $name: SettingMetadata = SettingMetadata {
            path: &[$first $(, $path)*],
            dotted_path: concat!($first $(, ".", $path)*),
            pointer_path: concat!("/", $first $(, "/", $path)*),
            default: $default,
            guidance: &[$($guidance),*],
            canonical: $canonical,
        };
    };
}

setting!(
    MANAGED_GAME,
    ["CLASSIC_Settings", "Managed Game"],
    PublishedDefault::String("Fallout 4"),
    ["Set the game that CLASSIC should currently manage."],
    true
);
setting!(
    UPDATE_CHECK,
    ["CLASSIC_Settings", "Update Check"],
    PublishedDefault::Bool(true),
    ["Periodically check GitHub for first-party CLASSIC updates."],
    true
);
setting!(
    GAME_VERSION,
    ["CLASSIC_Settings", "Game Version"],
    PublishedDefault::String("auto"),
    ["Select the managed game version mode: auto, Original, NextGen, AnniversaryEdition, or VR."],
    true
);
setting!(
    GAME_FOLDER_PATH,
    ["CLASSIC_Settings", "Game Folder Path"],
    PublishedDefault::Null,
    ["Optional absolute path to the managed game installation folder."],
    true
);
setting!(
    GAME_EXE_PATH,
    ["CLASSIC_Settings", "Game EXE Path"],
    PublishedDefault::Null,
    ["Optional absolute path to a managed game executable override."],
    true
);
setting!(
    DOCUMENTS_FOLDER_PATH,
    ["CLASSIC_Settings", "Documents Folder Path"],
    PublishedDefault::Null,
    ["Optional absolute path to the managed game's Documents folder."],
    true
);
setting!(
    INI_FOLDER_PATH,
    ["CLASSIC_Settings", "INI Folder Path"],
    PublishedDefault::Null,
    ["Compatibility alias for Documents Folder Path used by older clients."],
    false
);
setting!(
    MODS_FOLDER_PATH,
    ["CLASSIC_Settings", "MODS Folder Path"],
    PublishedDefault::Null,
    ["Optional absolute path to the mod-manager staging or extracted-mods folder."],
    true
);
setting!(
    SCAN_CUSTOM_PATH,
    ["CLASSIC_Settings", "SCAN Custom Path"],
    PublishedDefault::Null,
    ["Optional absolute folder containing Crash Logs to scan."],
    true
);
setting!(
    PAPYRUS_LOG_PATH,
    ["CLASSIC_Settings", "Papyrus Log Path"],
    PublishedDefault::Null,
    ["Optional absolute path to the managed game's Papyrus log."],
    true
);
setting!(
    FCX_MODE,
    ["CLASSIC_Settings", "FCX Mode"],
    PublishedDefault::Bool(false),
    ["Enable File Check eXtended integrity checks for game files and core mods."],
    true
);
setting!(
    SIMPLIFY_LOGS,
    ["CLASSIC_Settings", "Simplify Logs"],
    PublishedDefault::Bool(false),
    [
        "Remove redundant Crash Log lines before analysis.",
        "Caution: simplifying changes each scanned Crash Log permanently."
    ],
    true
);
setting!(
    SHOW_STATISTICS,
    ["CLASSIC_Settings", "Show Statistics"],
    PublishedDefault::Bool(false),
    ["Show additional Crash Log Scan statistics when supported by the frontend."],
    true
);
setting!(
    SHOW_FORMID_VALUES,
    ["CLASSIC_Settings", "Show FormID Values"],
    PublishedDefault::Bool(false),
    ["Look up FormID value names while scanning at the cost of additional work."],
    true
);
setting!(
    FORMID_DATABASES,
    ["CLASSIC_Settings", "FormID Databases"],
    PublishedDefault::EmptyMapping,
    ["Optional game-keyed lists of additional FormID database paths."],
    true
);
setting!(
    MOVE_UNSOLVED_LOGS,
    ["CLASSIC_Settings", "Move Unsolved Logs"],
    PublishedDefault::Bool(true),
    ["Move Unsolved Logs and their Autoscan Reports after Standard scans."],
    true
);
setting!(
    UNSOLVED_LOGS_DESTINATION,
    ["CLASSIC_Settings", "Unsolved Logs Destination"],
    PublishedDefault::Null,
    ["Optional absolute destination; null uses CLASSIC Backup/Unsolved Logs."],
    true
);
setting!(
    AUDIO_NOTIFICATIONS,
    ["CLASSIC_Settings", "Audio Notifications"],
    PublishedDefault::Bool(false),
    ["Compatibility default for older clients that play scan-completion audio."],
    false
);
setting!(
    UPDATE_SOURCE,
    ["CLASSIC_Settings", "Update Source"],
    PublishedDefault::String("GitHub"),
    ["Compatibility default for older clients that select an update source."],
    false
);
setting!(
    DISABLE_CLI_PROGRESS,
    ["CLASSIC_Settings", "Disable CLI Progress"],
    PublishedDefault::Bool(false),
    ["Compatibility default for older clients that suppress terminal progress bars."],
    false
);
setting!(
    MAX_CONCURRENT_SCANS,
    ["CLASSIC_Settings", "Max Concurrent Scans"],
    PublishedDefault::Integer(0),
    ["Maximum concurrent scans; zero selects adaptive CPU-based detection."],
    true
);
setting!(
    AUTO_SWITCH_AFTER_SCAN,
    ["UI", "preferences", "auto_switch_after_scan"],
    PublishedDefault::Bool(true),
    ["Select the Results presentation after a successful scan."],
    true
);
setting!(
    AUTO_REFRESH_INTERVAL_MS,
    ["UI", "preferences", "auto_refresh_interval_ms"],
    PublishedDefault::Integer(5_000),
    ["Frontend refresh interval in milliseconds."],
    true
);

macro_rules! geometry_settings {
    ($maximized:ident, $width_name:ident, $height_name:ident, $tab:literal, $width:literal, $height:literal) => {
        setting!(
            $maximized,
            ["UI", "window_geometry", $tab, "maximized"],
            PublishedDefault::Bool(false),
            ["Remember whether this GUI tab was maximized."],
            true
        );
        setting!(
            $width_name,
            ["UI", "window_geometry", $tab, "width"],
            PublishedDefault::Integer($width),
            ["Remember this GUI tab's normal-state width in pixels."],
            true
        );
        setting!(
            $height_name,
            ["UI", "window_geometry", $tab, "height"],
            PublishedDefault::Integer($height),
            ["Remember this GUI tab's normal-state height in pixels."],
            true
        );
    };
}

geometry_settings!(
    MAIN_TAB_MAXIMIZED,
    MAIN_TAB_WIDTH,
    MAIN_TAB_HEIGHT,
    "main_tab",
    640,
    500
);
geometry_settings!(
    BACKUPS_TAB_MAXIMIZED,
    BACKUPS_TAB_WIDTH,
    BACKUPS_TAB_HEIGHT,
    "backups_tab",
    750,
    580
);
geometry_settings!(
    ARTICLES_TAB_MAXIMIZED,
    ARTICLES_TAB_WIDTH,
    ARTICLES_TAB_HEIGHT,
    "articles_tab",
    550,
    350
);
geometry_settings!(
    RESULTS_TAB_MAXIMIZED,
    RESULTS_TAB_WIDTH,
    RESULTS_TAB_HEIGHT,
    "results_tab",
    750,
    450
);

setting!(
    TUI_ACTIVE_TAB,
    ["UI", "tui", "active_tab"],
    PublishedDefault::Integer(0),
    ["Remember the TUI's zero-based active tab ordinal."],
    true
);
setting!(
    TUI_RESULTS_PANEL_WIDTH,
    ["UI", "tui", "results_panel_width"],
    PublishedDefault::Integer(30),
    ["Remember the TUI Results list-panel width."],
    true
);
setting!(
    TUI_SORT_ASCENDING,
    ["UI", "tui", "sort_ascending"],
    PublishedDefault::Bool(false),
    ["Remember whether TUI Results are sorted in ascending order."],
    true
);

macro_rules! integer_default {
    ($setting:expr) => {
        match $setting.default {
            PublishedDefault::Integer(value) => value,
            _ => panic!("published default is not an integer"),
        }
    };
}

pub(crate) const MAIN_TAB_DEFAULT: (u32, u32) = (
    integer_default!(MAIN_TAB_WIDTH) as u32,
    integer_default!(MAIN_TAB_HEIGHT) as u32,
);
pub(crate) const BACKUPS_TAB_DEFAULT: (u32, u32) = (
    integer_default!(BACKUPS_TAB_WIDTH) as u32,
    integer_default!(BACKUPS_TAB_HEIGHT) as u32,
);
pub(crate) const ARTICLES_TAB_DEFAULT: (u32, u32) = (
    integer_default!(ARTICLES_TAB_WIDTH) as u32,
    integer_default!(ARTICLES_TAB_HEIGHT) as u32,
);
pub(crate) const RESULTS_TAB_DEFAULT: (u32, u32) = (
    integer_default!(RESULTS_TAB_WIDTH) as u32,
    integer_default!(RESULTS_TAB_HEIGHT) as u32,
);

/// Ordered registry used by both runtime defaults and compatibility generation.
pub(crate) const MIRROR_SETTINGS: &[SettingMetadata] = &[
    MANAGED_GAME,
    UPDATE_CHECK,
    GAME_VERSION,
    GAME_FOLDER_PATH,
    GAME_EXE_PATH,
    DOCUMENTS_FOLDER_PATH,
    INI_FOLDER_PATH,
    MODS_FOLDER_PATH,
    SCAN_CUSTOM_PATH,
    PAPYRUS_LOG_PATH,
    FCX_MODE,
    SIMPLIFY_LOGS,
    SHOW_STATISTICS,
    SHOW_FORMID_VALUES,
    FORMID_DATABASES,
    MOVE_UNSOLVED_LOGS,
    UNSOLVED_LOGS_DESTINATION,
    AUDIO_NOTIFICATIONS,
    UPDATE_SOURCE,
    DISABLE_CLI_PROGRESS,
    MAX_CONCURRENT_SCANS,
    AUTO_SWITCH_AFTER_SCAN,
    AUTO_REFRESH_INTERVAL_MS,
    MAIN_TAB_MAXIMIZED,
    MAIN_TAB_WIDTH,
    MAIN_TAB_HEIGHT,
    BACKUPS_TAB_MAXIMIZED,
    BACKUPS_TAB_WIDTH,
    BACKUPS_TAB_HEIGHT,
    ARTICLES_TAB_MAXIMIZED,
    ARTICLES_TAB_WIDTH,
    ARTICLES_TAB_HEIGHT,
    RESULTS_TAB_MAXIMIZED,
    RESULTS_TAB_WIDTH,
    RESULTS_TAB_HEIGHT,
    TUI_ACTIVE_TAB,
    TUI_RESULTS_PANEL_WIDTH,
    TUI_SORT_ASCENDING,
];

/// Verifies registry uniqueness and the derived dotted/JSON-pointer path representations.
pub(crate) fn registry_is_valid() -> bool {
    let mut paths = BTreeSet::new();
    let valid = MIRROR_SETTINGS.iter().all(|setting| {
        setting.path.len() >= 2
            && !setting.guidance.is_empty()
            && paths.insert(setting.path)
            && setting.dotted_path == setting.path.join(".")
            && setting.pointer_path == format!("/{}", setting.path.join("/"))
    });
    valid && MIRROR_SETTINGS.iter().any(|setting| setting.canonical)
}

// Keep the repository's required sibling-test declaration intact under rustfmt.
#[rustfmt::skip]
#[cfg(test)] #[path = "default_settings_tests.rs"] mod tests;
