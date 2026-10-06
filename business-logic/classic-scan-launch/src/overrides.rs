//! Per-run overrides accepted by Crash Log Scan Launch.

use classic_shared_core::GameId;
use classic_user_settings_core::GameVersionSelection;
use std::num::NonZeroUsize;
use std::path::{Path, PathBuf};

/// Concurrency requested for one run, as an override of the saved Max Concurrent Scans.
///
/// Adaptive selection is its own value rather than an absent override, so explicitly asking
/// for adaptive concurrency overrides a saved limit.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MaxConcurrency {
    /// Let the run choose its concurrency from the available CPUs.
    Adaptive,
    /// Run at most this many Crash Log analyses at once.
    Limit(NonZeroUsize),
}

impl MaxConcurrency {
    /// Maps the frontend convention where zero means adaptive and any other count is a limit.
    ///
    /// This is the shape every CLI flag and binding uses (`--max-concurrent 0` asks for
    /// adaptive concurrency), so the conversion lives here once.
    #[must_use]
    pub fn from_count(count: usize) -> Self {
        NonZeroUsize::new(count).map_or(Self::Adaptive, Self::Limit)
    }

    /// Returns the request's explicit concurrency limit, where `None` selects adaptively.
    #[must_use]
    pub const fn limit(self) -> Option<usize> {
        match self {
            Self::Adaptive => None,
            Self::Limit(limit) => Some(limit.get()),
        }
    }
}

/// Optional per-run values that win over the saved User Settings for one launch.
///
/// Every override is optional. Two styles exist:
/// - **Explicit value wins** (game, game version, scan path, max concurrency): a supplied
///   value replaces the saved one.
/// - **Supplied as on** (FormID values, simplify logs, FCX Mode): supplying the override
///   turns the option on for this run; not supplying it keeps the saved value. There is no
///   way to turn a saved option off for one run, matching the CLI flags these model.
///
/// Built with the `with_*` methods so later overrides can be added without breaking callers.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct CrashLogScanLaunchOverrides {
    game: Option<GameId>,
    game_version: Option<GameVersionSelection>,
    scan_path: Option<PathBuf>,
    max_concurrency: Option<MaxConcurrency>,
    show_formid_values: bool,
    simplify_logs: bool,
    fcx_mode: bool,
}

impl CrashLogScanLaunchOverrides {
    /// Creates an override set that supplies nothing, so every saved value applies.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Scans `game` instead of the saved managed game.
    #[must_use]
    pub fn with_game(mut self, game: GameId) -> Self {
        self.game = Some(game);
        self
    }

    /// Uses `game_version` instead of the saved game-version selection.
    #[must_use]
    pub fn with_game_version(mut self, game_version: GameVersionSelection) -> Self {
        self.game_version = Some(game_version);
        self
    }

    /// Scans `scan_path` as the custom scan folder instead of the saved custom scan folder.
    ///
    /// Only a Standard scan has a custom scan folder; a Targeted scan reads only its inputs.
    #[must_use]
    pub fn with_scan_path(mut self, scan_path: impl Into<PathBuf>) -> Self {
        self.scan_path = Some(scan_path.into());
        self
    }

    /// Uses `max_concurrency` instead of the saved Max Concurrent Scans.
    #[must_use]
    pub fn with_max_concurrency(mut self, max_concurrency: MaxConcurrency) -> Self {
        self.max_concurrency = Some(max_concurrency);
        self
    }

    /// Turns FormID value lookup on for this run, whatever the saved value.
    #[must_use]
    pub fn with_show_formid_values(mut self) -> Self {
        self.show_formid_values = true;
        self
    }

    /// Turns simplify logs on for this run, whatever the saved value.
    #[must_use]
    pub fn with_simplify_logs(mut self) -> Self {
        self.simplify_logs = true;
        self
    }

    /// Turns FCX Mode on for this run, whatever the saved value.
    ///
    /// The launched request then carries its Crash Log Scan Setup Context, for a Standard
    /// or a Targeted intent alike.
    #[must_use]
    pub fn with_fcx_mode(mut self) -> Self {
        self.fcx_mode = true;
        self
    }

    /// Returns the supplied game, if any.
    #[must_use]
    pub const fn game(&self) -> Option<GameId> {
        self.game
    }

    /// Returns the supplied game-version selection, if any.
    #[must_use]
    pub const fn game_version(&self) -> Option<GameVersionSelection> {
        self.game_version
    }

    /// Returns the supplied custom scan folder, if any.
    #[must_use]
    pub fn scan_path(&self) -> Option<&Path> {
        self.scan_path.as_deref()
    }

    /// Returns the supplied concurrency, if any.
    #[must_use]
    pub const fn max_concurrency(&self) -> Option<MaxConcurrency> {
        self.max_concurrency
    }

    /// Returns whether FormID value lookup was supplied as on.
    #[must_use]
    pub const fn show_formid_values(&self) -> bool {
        self.show_formid_values
    }

    /// Returns whether simplify logs was supplied as on.
    #[must_use]
    pub const fn simplify_logs(&self) -> bool {
        self.simplify_logs
    }

    /// Returns whether FCX Mode was supplied as on.
    #[must_use]
    pub const fn fcx_mode(&self) -> bool {
        self.fcx_mode
    }
}
