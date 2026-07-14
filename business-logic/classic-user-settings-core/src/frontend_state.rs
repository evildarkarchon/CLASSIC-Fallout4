use crate::default_settings::{
    ARTICLES_TAB_DEFAULT, ARTICLES_TAB_HEIGHT, ARTICLES_TAB_MAXIMIZED, ARTICLES_TAB_WIDTH,
    AUTO_REFRESH_INTERVAL_MS, AUTO_SWITCH_AFTER_SCAN, BACKUPS_TAB_DEFAULT, BACKUPS_TAB_HEIGHT,
    BACKUPS_TAB_MAXIMIZED, BACKUPS_TAB_WIDTH, MAIN_TAB_DEFAULT, MAIN_TAB_HEIGHT,
    MAIN_TAB_MAXIMIZED, MAIN_TAB_WIDTH, MANAGED_GAME, RESULTS_TAB_DEFAULT, RESULTS_TAB_HEIGHT,
    RESULTS_TAB_MAXIMIZED, RESULTS_TAB_WIDTH, SettingMetadata, TUI_ACTIVE_TAB,
    TUI_RESULTS_PANEL_WIDTH, TUI_SORT_ASCENDING,
};
use crate::document::{Diagnostic, PreferenceOrigin};
use crate::preference::Preference;
use classic_settings_core::Yaml;

/// Cohesive, widget-independent User Settings state remembered by frontends.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FrontendState {
    preferences: FrontendPreferences,
    window_geometry: GuiWindowGeometry,
    tui: TuiRememberedState,
}

impl FrontendState {
    /// Projects frontend state from the canonical nested User Settings document.
    pub(crate) fn from_nested_document(document: &Yaml) -> (Self, Vec<Diagnostic>) {
        let mut diagnostics = Vec::new();
        let ui_root = AUTO_SWITCH_AFTER_SCAN.path[0];
        let ui = group(
            &document[ui_root],
            ui_root,
            "invalid_type_frontend_state",
            &mut diagnostics,
        );

        let preferences_path = dotted_prefix(AUTO_SWITCH_AFTER_SCAN, 2);
        let preferences_group = ui.child_group(
            AUTO_SWITCH_AFTER_SCAN.path[1],
            &preferences_path,
            "invalid_type_frontend_preferences",
            &mut diagnostics,
        );
        let legacy_auto_switch = match &document[MANAGED_GAME.path[0]] {
            settings @ Yaml::Hash(_) => child(settings, "Auto Switch After Scan"),
            Yaml::BadValue => None,
            _ => unreachable!("nested group shapes were validated before frontend projection"),
        };
        let preferences = FrontendPreferences::from_nested_group(
            preferences_group,
            legacy_auto_switch,
            &mut diagnostics,
        );

        let geometry_path = dotted_prefix(MAIN_TAB_WIDTH, 2);
        let geometry_group = ui.child_group(
            MAIN_TAB_WIDTH.path[1],
            &geometry_path,
            "invalid_type_gui_window_geometry",
            &mut diagnostics,
        );
        let window_geometry =
            GuiWindowGeometry::from_nested_group(geometry_group, &mut diagnostics);

        let tui_path = dotted_prefix(TUI_ACTIVE_TAB, 2);
        let tui_group = ui.child_group(
            TUI_ACTIVE_TAB.path[1],
            &tui_path,
            "invalid_type_tui_remembered_state",
            &mut diagnostics,
        );
        let tui = TuiRememberedState::from_nested_group(tui_group, &mut diagnostics);

        (
            Self {
                preferences,
                window_geometry,
                tui,
            },
            diagnostics,
        )
    }

    /// Projects frontend preferences available in the legacy flat ClassicConfig shape.
    pub(crate) fn from_legacy_flat_document(document: &Yaml) -> (Self, Vec<Diagnostic>) {
        let mut diagnostics = Vec::new();
        let preferences = FrontendPreferences {
            auto_switch_after_scan: bool_preference(
                child(document, "auto_switch_to_results"),
                AUTO_SWITCH_AFTER_SCAN.default().as_bool(),
                PreferenceOrigin::Default,
                "invalid_type_frontend_auto_switch_after_scan",
                "auto_switch_to_results must be a boolean",
                &mut diagnostics,
            ),
            auto_refresh_interval_ms: positive_u64_preference(
                child(document, "auto_refresh_interval_ms"),
                AUTO_REFRESH_INTERVAL_MS.default().as_integer() as u64,
                PreferenceOrigin::Default,
                "invalid_type_frontend_auto_refresh_interval_ms",
                "invalid_range_frontend_auto_refresh_interval_ms",
                "auto_refresh_interval_ms",
                &mut diagnostics,
            ),
        };
        (
            Self {
                preferences,
                window_geometry: GuiWindowGeometry::with_origin(PreferenceOrigin::Default),
                tui: TuiRememberedState::with_origin(PreferenceOrigin::Default),
            },
            diagnostics,
        )
    }

    /// Returns the published frontend defaults for a missing settings document.
    pub(crate) fn published_defaults() -> Self {
        Self::with_origin(PreferenceOrigin::Default)
    }

    /// Returns presentation-safe fallbacks for an untrusted settings document.
    pub(crate) fn degraded_fallbacks() -> Self {
        Self::with_origin(PreferenceOrigin::DegradedFallback)
    }

    /// Builds the complete frontend group with one provenance for every value.
    fn with_origin(origin: PreferenceOrigin) -> Self {
        Self {
            preferences: FrontendPreferences::with_origin(origin),
            window_geometry: GuiWindowGeometry::with_origin(origin),
            tui: TuiRememberedState::with_origin(origin),
        }
    }

    /// Returns remembered presentation preferences shared by frontends.
    pub fn preferences(&self) -> &FrontendPreferences {
        &self.preferences
    }

    /// Returns remembered geometry for each maintained GUI tab.
    pub fn window_geometry(&self) -> &GuiWindowGeometry {
        &self.window_geometry
    }

    /// Returns the canonical namespace reserved for remembered TUI state.
    pub fn tui(&self) -> &TuiRememberedState {
        &self.tui
    }
}

/// Remembered frontend presentation preferences.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FrontendPreferences {
    auto_switch_after_scan: Preference<bool>,
    auto_refresh_interval_ms: Preference<u64>,
}

impl FrontendPreferences {
    /// Projects canonical preferences, using the live GUI key as an auto-switch alias.
    fn from_nested_group(
        group: KnownGroup<'_>,
        legacy_auto_switch: Option<&Yaml>,
        diagnostics: &mut Vec<Diagnostic>,
    ) -> Self {
        let missing_origin = group.missing_origin();
        let canonical_auto_switch = group.child(AUTO_SWITCH_AFTER_SCAN.label());
        let auto_switch_after_scan = aliased_bool_preference(
            canonical_auto_switch,
            legacy_auto_switch,
            AUTO_SWITCH_AFTER_SCAN.default().as_bool(),
            missing_origin,
            diagnostics,
        );
        let auto_refresh_interval_ms = positive_u64_preference(
            group.child(AUTO_REFRESH_INTERVAL_MS.label()),
            AUTO_REFRESH_INTERVAL_MS.default().as_integer() as u64,
            missing_origin,
            "invalid_type_frontend_auto_refresh_interval_ms",
            "invalid_range_frontend_auto_refresh_interval_ms",
            AUTO_REFRESH_INTERVAL_MS.dotted_path,
            diagnostics,
        );
        Self {
            auto_switch_after_scan,
            auto_refresh_interval_ms,
        }
    }

    /// Builds the preference group with one provenance for every default.
    fn with_origin(origin: PreferenceOrigin) -> Self {
        Self {
            auto_switch_after_scan: Preference::new(
                AUTO_SWITCH_AFTER_SCAN.default().as_bool(),
                origin,
            ),
            auto_refresh_interval_ms: Preference::new(
                AUTO_REFRESH_INTERVAL_MS.default().as_integer() as u64,
                origin,
            ),
        }
    }

    /// Returns whether successful scans should select the Results presentation.
    pub fn auto_switch_after_scan(&self) -> bool {
        self.auto_switch_after_scan.value
    }

    /// Returns how automatic result switching was obtained.
    pub fn auto_switch_after_scan_origin(&self) -> PreferenceOrigin {
        self.auto_switch_after_scan.origin
    }

    /// Returns the remembered refresh interval in milliseconds.
    pub fn auto_refresh_interval_ms(&self) -> u64 {
        self.auto_refresh_interval_ms.value
    }

    /// Returns how the refresh interval was obtained.
    pub fn auto_refresh_interval_ms_origin(&self) -> PreferenceOrigin {
        self.auto_refresh_interval_ms.origin
    }
}

/// Remembered geometry for every maintained GUI tab.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GuiWindowGeometry {
    main_tab: WindowGeometry,
    backups_tab: WindowGeometry,
    articles_tab: WindowGeometry,
    results_tab: WindowGeometry,
}

impl GuiWindowGeometry {
    /// Projects every named geometry namespace independently.
    fn from_nested_group(group: KnownGroup<'_>, diagnostics: &mut Vec<Diagnostic>) -> Self {
        Self {
            main_tab: WindowGeometry::from_group(
                group.child_group(
                    MAIN_TAB_WIDTH.path[2],
                    &dotted_prefix(MAIN_TAB_WIDTH, 3),
                    "invalid_type_gui_geometry_tab",
                    diagnostics,
                ),
                MAIN_TAB_MAXIMIZED,
                MAIN_TAB_WIDTH,
                MAIN_TAB_HEIGHT,
                diagnostics,
            ),
            backups_tab: WindowGeometry::from_group(
                group.child_group(
                    BACKUPS_TAB_WIDTH.path[2],
                    &dotted_prefix(BACKUPS_TAB_WIDTH, 3),
                    "invalid_type_gui_geometry_tab",
                    diagnostics,
                ),
                BACKUPS_TAB_MAXIMIZED,
                BACKUPS_TAB_WIDTH,
                BACKUPS_TAB_HEIGHT,
                diagnostics,
            ),
            articles_tab: WindowGeometry::from_group(
                group.child_group(
                    ARTICLES_TAB_WIDTH.path[2],
                    &dotted_prefix(ARTICLES_TAB_WIDTH, 3),
                    "invalid_type_gui_geometry_tab",
                    diagnostics,
                ),
                ARTICLES_TAB_MAXIMIZED,
                ARTICLES_TAB_WIDTH,
                ARTICLES_TAB_HEIGHT,
                diagnostics,
            ),
            results_tab: WindowGeometry::from_group(
                group.child_group(
                    RESULTS_TAB_WIDTH.path[2],
                    &dotted_prefix(RESULTS_TAB_WIDTH, 3),
                    "invalid_type_gui_geometry_tab",
                    diagnostics,
                ),
                RESULTS_TAB_MAXIMIZED,
                RESULTS_TAB_WIDTH,
                RESULTS_TAB_HEIGHT,
                diagnostics,
            ),
        }
    }

    /// Builds every geometry entry with its tab-specific default dimensions.
    fn with_origin(origin: PreferenceOrigin) -> Self {
        Self {
            main_tab: WindowGeometry::with_origin(MAIN_TAB_MAXIMIZED, MAIN_TAB_DEFAULT, origin),
            backups_tab: WindowGeometry::with_origin(
                BACKUPS_TAB_MAXIMIZED,
                BACKUPS_TAB_DEFAULT,
                origin,
            ),
            articles_tab: WindowGeometry::with_origin(
                ARTICLES_TAB_MAXIMIZED,
                ARTICLES_TAB_DEFAULT,
                origin,
            ),
            results_tab: WindowGeometry::with_origin(
                RESULTS_TAB_MAXIMIZED,
                RESULTS_TAB_DEFAULT,
                origin,
            ),
        }
    }

    /// Returns geometry for the Main Options tab.
    pub fn main_tab(&self) -> &WindowGeometry {
        &self.main_tab
    }

    /// Returns geometry for the File Backup tab.
    pub fn backups_tab(&self) -> &WindowGeometry {
        &self.backups_tab
    }

    /// Returns geometry for the Articles tab.
    pub fn articles_tab(&self) -> &WindowGeometry {
        &self.articles_tab
    }

    /// Returns geometry for the Results tab.
    pub fn results_tab(&self) -> &WindowGeometry {
        &self.results_tab
    }
}

/// Widget-independent size and maximized state for one named GUI tab.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WindowGeometry {
    maximized: Preference<bool>,
    width: Preference<u32>,
    height: Preference<u32>,
}

impl WindowGeometry {
    /// Projects one named tab while retaining valid siblings when a leaf is invalid.
    fn from_group(
        group: KnownGroup<'_>,
        maximized_setting: SettingMetadata,
        width_setting: SettingMetadata,
        height_setting: SettingMetadata,
        diagnostics: &mut Vec<Diagnostic>,
    ) -> Self {
        let missing_origin = group.missing_origin();
        let width = positive_u32_preference(
            group.child(width_setting.label()),
            width_setting.default().as_integer() as u32,
            missing_origin,
            "invalid_type_gui_geometry_width",
            "invalid_range_gui_geometry_width",
            width_setting.dotted_path,
            diagnostics,
        );
        let height = positive_u32_preference(
            group.child(height_setting.label()),
            height_setting.default().as_integer() as u32,
            missing_origin,
            "invalid_type_gui_geometry_height",
            "invalid_range_gui_geometry_height",
            height_setting.dotted_path,
            diagnostics,
        );
        let maximized = bool_preference(
            group.child(maximized_setting.label()),
            maximized_setting.default().as_bool(),
            missing_origin,
            "invalid_type_gui_geometry_maximized",
            format!("{} must be a boolean", maximized_setting.dotted_path),
            diagnostics,
        );
        Self {
            maximized,
            width,
            height,
        }
    }

    /// Builds one tab geometry from its published maximized state and dimensions.
    fn with_origin(
        maximized_setting: SettingMetadata,
        default_size: (u32, u32),
        origin: PreferenceOrigin,
    ) -> Self {
        Self {
            maximized: Preference::new(maximized_setting.default().as_bool(), origin),
            width: Preference::new(default_size.0, origin),
            height: Preference::new(default_size.1, origin),
        }
    }

    /// Returns whether the tab's window was maximized.
    pub fn maximized(&self) -> bool {
        self.maximized.value
    }

    /// Returns how the maximized state was obtained.
    pub fn maximized_origin(&self) -> PreferenceOrigin {
        self.maximized.origin
    }

    /// Returns the remembered normal-state width in pixels.
    pub fn width(&self) -> u32 {
        self.width.value
    }

    /// Returns how the remembered width was obtained.
    pub fn width_origin(&self) -> PreferenceOrigin {
        self.width.origin
    }

    /// Returns the remembered normal-state height in pixels.
    pub fn height(&self) -> u32 {
        self.height.value
    }

    /// Returns how the remembered height was obtained.
    pub fn height_origin(&self) -> PreferenceOrigin {
        self.height.origin
    }
}

/// Remembered TUI state represented under the canonical `UI.tui` namespace.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TuiRememberedState {
    active_tab: Preference<u8>,
    results_panel_width: Preference<u16>,
    sort_ascending: Preference<bool>,
}

impl TuiRememberedState {
    /// Projects the canonical TUI namespace without reading the legacy state document.
    fn from_nested_group(group: KnownGroup<'_>, diagnostics: &mut Vec<Diagnostic>) -> Self {
        let missing_origin = group.missing_origin();
        Self {
            active_tab: bounded_u8_preference(
                group.child(TUI_ACTIVE_TAB.label()),
                TUI_ACTIVE_TAB.default().as_integer() as u8,
                3,
                missing_origin,
                "invalid_type_tui_active_tab",
                "invalid_range_tui_active_tab",
                TUI_ACTIVE_TAB.dotted_path,
                diagnostics,
            ),
            results_panel_width: u16_preference(
                group.child(TUI_RESULTS_PANEL_WIDTH.label()),
                TUI_RESULTS_PANEL_WIDTH.default().as_integer() as u16,
                missing_origin,
                "invalid_type_tui_results_panel_width",
                "invalid_range_tui_results_panel_width",
                TUI_RESULTS_PANEL_WIDTH.dotted_path,
                diagnostics,
            ),
            sort_ascending: bool_preference(
                group.child(TUI_SORT_ASCENDING.label()),
                TUI_SORT_ASCENDING.default().as_bool(),
                missing_origin,
                "invalid_type_tui_sort_ascending",
                format!("{} must be a boolean", TUI_SORT_ASCENDING.dotted_path),
                diagnostics,
            ),
        }
    }

    /// Builds the TUI namespace with its published defaults.
    fn with_origin(origin: PreferenceOrigin) -> Self {
        Self {
            active_tab: Preference::new(TUI_ACTIVE_TAB.default().as_integer() as u8, origin),
            results_panel_width: Preference::new(
                TUI_RESULTS_PANEL_WIDTH.default().as_integer() as u16,
                origin,
            ),
            sort_ascending: Preference::new(TUI_SORT_ASCENDING.default().as_bool(), origin),
        }
    }

    /// Returns the stable zero-based tab ordinal remembered by the TUI.
    pub fn active_tab(&self) -> u8 {
        self.active_tab.value
    }

    /// Returns how the active-tab ordinal was obtained.
    pub fn active_tab_origin(&self) -> PreferenceOrigin {
        self.active_tab.origin
    }

    /// Returns the remembered Results list-panel width.
    pub fn results_panel_width(&self) -> u16 {
        self.results_panel_width.value
    }

    /// Returns how the Results list-panel width was obtained.
    pub fn results_panel_width_origin(&self) -> PreferenceOrigin {
        self.results_panel_width.origin
    }

    /// Returns whether Results are remembered in ascending order.
    pub fn sort_ascending(&self) -> bool {
        self.sort_ascending.value
    }

    /// Returns how the sort direction was obtained.
    pub fn sort_ascending_origin(&self) -> PreferenceOrigin {
        self.sort_ascending.origin
    }
}

/// Mapping state for a known frontend namespace.
#[derive(Clone, Copy)]
enum KnownGroup<'a> {
    Missing,
    Mapping(&'a Yaml),
    Invalid,
}

impl<'a> KnownGroup<'a> {
    /// Returns one child leaf when this namespace is a mapping.
    fn child(self, key: &str) -> Option<&'a Yaml> {
        match self {
            Self::Mapping(mapping) => child(mapping, key),
            Self::Missing | Self::Invalid => None,
        }
    }

    /// Returns one child namespace and diagnoses a present non-mapping value.
    fn child_group(
        self,
        key: &str,
        path: &str,
        code: &'static str,
        diagnostics: &mut Vec<Diagnostic>,
    ) -> KnownGroup<'a> {
        match self {
            Self::Mapping(mapping) => group(&mapping[key], path, code, diagnostics),
            Self::Missing => KnownGroup::Missing,
            Self::Invalid => KnownGroup::Invalid,
        }
    }

    /// Distinguishes absent defaults from fallbacks caused by an invalid namespace.
    fn missing_origin(self) -> PreferenceOrigin {
        match self {
            Self::Missing | Self::Mapping(_) => PreferenceOrigin::Default,
            Self::Invalid => PreferenceOrigin::DegradedFallback,
        }
    }
}

/// Joins a registry path prefix for group diagnostics without duplicating its labels.
fn dotted_prefix(setting: SettingMetadata, component_count: usize) -> String {
    setting.path[..component_count].join(".")
}

/// Classifies one known namespace without interpreting unknown siblings.
fn group<'a>(
    node: &'a Yaml,
    path: &str,
    code: &'static str,
    diagnostics: &mut Vec<Diagnostic>,
) -> KnownGroup<'a> {
    match node {
        Yaml::Hash(_) => KnownGroup::Mapping(node),
        Yaml::BadValue => KnownGroup::Missing,
        _ => {
            if !code.is_empty() {
                diagnostics.push(Diagnostic::new(code, format!("{path} must be a mapping")));
            }
            KnownGroup::Invalid
        }
    }
}

/// Returns a present mapping child while treating YAML's bad-value sentinel as absent.
fn child<'a>(mapping: &'a Yaml, key: &str) -> Option<&'a Yaml> {
    match &mapping[key] {
        Yaml::BadValue => None,
        value => Some(value),
    }
}

/// Projects one boolean leaf with a caller-selected default and provenance.
fn bool_preference(
    node: Option<&Yaml>,
    default: bool,
    missing_origin: PreferenceOrigin,
    invalid_type_code: &'static str,
    invalid_message: impl Into<String>,
    diagnostics: &mut Vec<Diagnostic>,
) -> Preference<bool> {
    match node {
        Some(Yaml::Boolean(value)) => Preference::new(*value, PreferenceOrigin::Document),
        None => Preference::new(default, missing_origin),
        Some(_) => {
            diagnostics.push(Diagnostic::new(invalid_type_code, invalid_message));
            Preference::new(default, PreferenceOrigin::DegradedFallback)
        }
    }
}

/// Resolves canonical automatic switching ahead of the live GUI compatibility key.
fn aliased_bool_preference(
    canonical: Option<&Yaml>,
    alias: Option<&Yaml>,
    default: bool,
    missing_origin: PreferenceOrigin,
    diagnostics: &mut Vec<Diagnostic>,
) -> Preference<bool> {
    match (canonical, alias) {
        (Some(Yaml::Boolean(canonical)), Some(Yaml::Boolean(alias))) => {
            if canonical != alias {
                diagnostics.push(Diagnostic::new(
                    "canonical_alias_conflict_auto_switch_after_scan",
                    format!(
                        "{} conflicts with CLASSIC_Settings.Auto Switch After Scan; the canonical value wins",
                        AUTO_SWITCH_AFTER_SCAN.dotted_path
                    ),
                ));
            }
            Preference::new(*canonical, PreferenceOrigin::Document)
        }
        (Some(Yaml::Boolean(value)), Some(_)) => {
            diagnostics.push(Diagnostic::new(
                "invalid_type_frontend_auto_switch_after_scan",
                "CLASSIC_Settings.Auto Switch After Scan must be a boolean",
            ));
            Preference::new(*value, PreferenceOrigin::Document)
        }
        (Some(Yaml::Boolean(value)), None) => Preference::new(*value, PreferenceOrigin::Document),
        (None, Some(Yaml::Boolean(value))) => Preference::new(*value, PreferenceOrigin::Document),
        (Some(_), Some(Yaml::Boolean(value))) => {
            diagnostics.push(Diagnostic::new(
                "invalid_type_frontend_auto_switch_after_scan",
                format!("{} must be a boolean", AUTO_SWITCH_AFTER_SCAN.dotted_path),
            ));
            Preference::new(*value, PreferenceOrigin::Document)
        }
        (Some(_), _) => {
            diagnostics.push(Diagnostic::new(
                "invalid_type_frontend_auto_switch_after_scan",
                format!("{} must be a boolean", AUTO_SWITCH_AFTER_SCAN.dotted_path),
            ));
            Preference::new(default, PreferenceOrigin::DegradedFallback)
        }
        (None, Some(_)) => {
            diagnostics.push(Diagnostic::new(
                "invalid_type_frontend_auto_switch_after_scan",
                "CLASSIC_Settings.Auto Switch After Scan must be a boolean",
            ));
            Preference::new(default, PreferenceOrigin::DegradedFallback)
        }
        (None, None) => Preference::new(default, missing_origin),
    }
}

/// Projects one positive unsigned 64-bit integer leaf.
fn positive_u64_preference(
    node: Option<&Yaml>,
    default: u64,
    missing_origin: PreferenceOrigin,
    invalid_type_code: &'static str,
    invalid_range_code: &'static str,
    path: &str,
    diagnostics: &mut Vec<Diagnostic>,
) -> Preference<u64> {
    match node {
        Some(Yaml::Integer(value)) if *value > 0 => match u64::try_from(*value) {
            Ok(value) => Preference::new(value, PreferenceOrigin::Document),
            Err(_) => {
                diagnostics.push(Diagnostic::new(
                    invalid_range_code,
                    format!("{path} must fit in an unsigned 64-bit integer"),
                ));
                Preference::new(default, PreferenceOrigin::DegradedFallback)
            }
        },
        Some(Yaml::Integer(_)) => {
            diagnostics.push(Diagnostic::new(
                invalid_range_code,
                format!("{path} must be greater than zero"),
            ));
            Preference::new(default, PreferenceOrigin::DegradedFallback)
        }
        None => Preference::new(default, missing_origin),
        Some(_) => {
            diagnostics.push(Diagnostic::new(
                invalid_type_code,
                format!("{path} must be an integer"),
            ));
            Preference::new(default, PreferenceOrigin::DegradedFallback)
        }
    }
}

/// Projects one positive unsigned 32-bit integer leaf.
fn positive_u32_preference(
    node: Option<&Yaml>,
    default: u32,
    missing_origin: PreferenceOrigin,
    invalid_type_code: &'static str,
    invalid_range_code: &'static str,
    path: &str,
    diagnostics: &mut Vec<Diagnostic>,
) -> Preference<u32> {
    match node {
        Some(Yaml::Integer(value)) if *value > 0 => match u32::try_from(*value) {
            Ok(value) => Preference::new(value, PreferenceOrigin::Document),
            Err(_) => {
                diagnostics.push(Diagnostic::new(
                    invalid_range_code,
                    format!("{path} must fit in an unsigned 32-bit integer"),
                ));
                Preference::new(default, PreferenceOrigin::DegradedFallback)
            }
        },
        Some(Yaml::Integer(_)) => {
            diagnostics.push(Diagnostic::new(
                invalid_range_code,
                format!("{path} must be greater than zero"),
            ));
            Preference::new(default, PreferenceOrigin::DegradedFallback)
        }
        None => Preference::new(default, missing_origin),
        Some(_) => {
            diagnostics.push(Diagnostic::new(
                invalid_type_code,
                format!("{path} must be an integer"),
            ));
            Preference::new(default, PreferenceOrigin::DegradedFallback)
        }
    }
}

/// Projects one bounded unsigned 8-bit integer leaf.
#[allow(clippy::too_many_arguments)]
fn bounded_u8_preference(
    node: Option<&Yaml>,
    default: u8,
    maximum: u8,
    missing_origin: PreferenceOrigin,
    invalid_type_code: &'static str,
    invalid_range_code: &'static str,
    path: &str,
    diagnostics: &mut Vec<Diagnostic>,
) -> Preference<u8> {
    match node {
        Some(Yaml::Integer(value)) => match u8::try_from(*value) {
            Ok(value) if value <= maximum => Preference::new(value, PreferenceOrigin::Document),
            _ => {
                diagnostics.push(Diagnostic::new(
                    invalid_range_code,
                    format!("{path} must be between 0 and {maximum}"),
                ));
                Preference::new(default, PreferenceOrigin::DegradedFallback)
            }
        },
        None => Preference::new(default, missing_origin),
        Some(_) => {
            diagnostics.push(Diagnostic::new(
                invalid_type_code,
                format!("{path} must be an integer"),
            ));
            Preference::new(default, PreferenceOrigin::DegradedFallback)
        }
    }
}

/// Projects one unsigned 16-bit integer leaf, retaining zero for legacy import parity.
#[allow(clippy::too_many_arguments)]
fn u16_preference(
    node: Option<&Yaml>,
    default: u16,
    missing_origin: PreferenceOrigin,
    invalid_type_code: &'static str,
    invalid_range_code: &'static str,
    path: &str,
    diagnostics: &mut Vec<Diagnostic>,
) -> Preference<u16> {
    match node {
        Some(Yaml::Integer(value)) => match u16::try_from(*value) {
            Ok(value) => Preference::new(value, PreferenceOrigin::Document),
            Err(_) => {
                diagnostics.push(Diagnostic::new(
                    invalid_range_code,
                    format!("{path} must fit in an unsigned 16-bit integer"),
                ));
                Preference::new(default, PreferenceOrigin::DegradedFallback)
            }
        },
        None => Preference::new(default, missing_origin),
        Some(_) => {
            diagnostics.push(Diagnostic::new(
                invalid_type_code,
                format!("{path} must be an integer"),
            ));
            Preference::new(default, PreferenceOrigin::DegradedFallback)
        }
    }
}
