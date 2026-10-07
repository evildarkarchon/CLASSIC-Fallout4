//! Launch diagnostics: non-fatal facts a frontend should show beside the scan it starts.

use classic_shared_core::GameId;
use classic_user_settings_core::Diagnostic;
use classic_vocabulary::Vocabulary;

/// One non-fatal fact reported by a Crash Log Scan Launch.
///
/// A launch with diagnostics still produced a scannable request; diagnostics never stop a
/// scan. New kinds are added as launch rules gain reportable outcomes. The enum is
/// deliberately exhaustive: a new kind fails to compile in every binding that projects it,
/// which is how CXX, Node and Python stay in parity with it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CrashLogScanLaunchDiagnostic {
    /// A diagnostic User Settings reported when the launch opened them read-only.
    ///
    /// Degraded documents (malformed, newer, needing migration) surface here: the launch
    /// still builds its request, from the values User Settings projected for that document.
    UserSettings(Diagnostic),
    /// A saved game-specific value was not applied because the scan targets a game other
    /// than the managed game (the game-differs rule).
    ///
    /// Reported only for a value that is saved and would have shaped this launch had it
    /// targeted the managed game; a value an override replaced is not reported, because the
    /// game difference is not what kept it out.
    SavedValueNotApplied {
        /// Which saved value was not applied.
        value: SavedGameSpecificValue,
        /// The managed game the saved value belongs to.
        managed_game: GameId,
        /// The game this launch scans.
        target_game: GameId,
    },
}

impl CrashLogScanLaunchDiagnostic {
    /// Returns which launch rule produced this diagnostic.
    #[must_use]
    pub const fn kind(&self) -> CrashLogScanLaunchDiagnosticKind {
        match self {
            Self::UserSettings(_) => CrashLogScanLaunchDiagnosticKind::UserSettings,
            Self::SavedValueNotApplied { value, .. } => value.not_applied_kind(),
        }
    }

    /// Returns the stable machine-readable code for programmatic handling.
    ///
    /// For [`Self::UserSettings`] this is the User Settings diagnostic code unchanged; for
    /// every other variant it is the frozen token of [`Self::kind`].
    #[must_use]
    pub fn code(&self) -> &str {
        match self {
            Self::UserSettings(diagnostic) => diagnostic.code(),
            Self::SavedValueNotApplied { .. } => self.kind().as_str(),
        }
    }

    /// Returns human-readable context. Prose, freely rewordable; branch on
    /// [`Self::kind`] and [`Self::code`] instead.
    ///
    /// Frontends show the Display Content the scan presentation module renders for a
    /// diagnostic rather than this text; it exists for logs and programmatic consumers.
    #[must_use]
    pub fn message(&self) -> &str {
        match self {
            Self::UserSettings(diagnostic) => diagnostic.message(),
            Self::SavedValueNotApplied { value, .. } => value.not_applied_message(),
        }
    }
}

/// A saved game-specific value the game-differs rule withholds from a non-managed game.
///
/// Every one of these is saved for the managed game alone, so applying it to another game's
/// scan would leak one game's settings into another's.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum SavedGameSpecificValue {
    /// The saved game version; the scan uses `auto` instead.
    GameVersion,
    /// Saved FCX Mode; the scan runs without FCX Mode unless an override turns it on.
    FcxMode,
    /// The saved custom scan folder a Standard scan would also read.
    CustomScanFolder,
    /// The saved game folder, documents folder and game executable.
    SetupFolders,
}

impl SavedGameSpecificValue {
    /// Returns the diagnostic kind reporting this value as not applied.
    #[must_use]
    pub const fn not_applied_kind(self) -> CrashLogScanLaunchDiagnosticKind {
        match self {
            Self::GameVersion => CrashLogScanLaunchDiagnosticKind::GameVersionNotApplied,
            Self::FcxMode => CrashLogScanLaunchDiagnosticKind::FcxModeNotApplied,
            Self::CustomScanFolder => CrashLogScanLaunchDiagnosticKind::CustomScanFolderNotApplied,
            Self::SetupFolders => CrashLogScanLaunchDiagnosticKind::SetupFoldersNotApplied,
        }
    }

    /// Prose for [`CrashLogScanLaunchDiagnostic::message`]; freely rewordable.
    const fn not_applied_message(self) -> &'static str {
        match self {
            Self::GameVersion => {
                "the saved game version belongs to the managed game, so this scan uses auto"
            }
            Self::FcxMode => {
                "saved FCX Mode belongs to the managed game, so this scan runs without it"
            }
            Self::CustomScanFolder => {
                "the saved custom scan folder belongs to the managed game, so this scan does not read it"
            }
            Self::SetupFolders => {
                "the saved setup folders belong to the managed game, so this scan does not use them"
            }
        }
    }
}

/// Which launch rule produced a [`CrashLogScanLaunchDiagnostic`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum CrashLogScanLaunchDiagnosticKind {
    /// Reported by User Settings while the launch opened them.
    UserSettings,
    /// The game-differs rule withheld the saved game version.
    GameVersionNotApplied,
    /// The game-differs rule withheld saved FCX Mode.
    FcxModeNotApplied,
    /// The game-differs rule withheld the saved custom scan folder.
    CustomScanFolderNotApplied,
    /// The game-differs rule withheld the saved setup folders.
    SetupFoldersNotApplied,
}

impl Vocabulary for CrashLogScanLaunchDiagnosticKind {
    const VARIANTS: &'static [Self] = &[
        Self::UserSettings,
        Self::GameVersionNotApplied,
        Self::FcxModeNotApplied,
        Self::CustomScanFolderNotApplied,
        Self::SetupFoldersNotApplied,
    ];

    /// These tokens are frozen; every binding publishes them unchanged.
    fn as_str(self) -> &'static str {
        match self {
            Self::UserSettings => "user_settings",
            Self::GameVersionNotApplied => "game_version_not_applied",
            Self::FcxModeNotApplied => "fcx_mode_not_applied",
            Self::CustomScanFolderNotApplied => "custom_scan_folder_not_applied",
            Self::SetupFoldersNotApplied => "setup_folders_not_applied",
        }
    }

    /// Prose, freely rewordable.
    fn label(self) -> &'static str {
        match self {
            Self::UserSettings => "User Settings",
            Self::GameVersionNotApplied => "saved game version not applied",
            Self::FcxModeNotApplied => "saved FCX Mode not applied",
            Self::CustomScanFolderNotApplied => "saved custom scan folder not applied",
            Self::SetupFoldersNotApplied => "saved setup folders not applied",
        }
    }
}
