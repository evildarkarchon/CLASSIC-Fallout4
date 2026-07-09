//! Game Setup Intake.
//!
//! This module resolves saved or detected setup inputs into a typed, read-only
//! view of a supported game installation. It owns setup-time path, version,
//! registry, executable, documents, and XSE validation while leaving persistence
//! and broader game-file scans to callers.

use std::path::{Path, PathBuf};

use classic_file_io_core::FileHasher;
use classic_path_core::{DocsPathFinder, GamePathFinder};
use classic_shared_core::GameId;
use classic_version_core::extract_pe_version;
use classic_version_registry_core::{
    GameVersion as RegistryGameVersion, MatchConfidence, VersionInfo, VersionRegistry,
    get_version_registry,
};
use classic_xse_core::{XseType, get_xse_info, parse_version};

/// Top-level state for a Game Setup Intake run.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GameSetupIntakeStatus {
    /// Enough setup facts were resolved to return diagnostics.
    Ready,
    /// A caller must ask the user for missing setup input before all checks can run.
    ActionRequired,
    /// A fatal internal error prevented even a diagnostic result from being formed.
    FatalError,
}

impl GameSetupIntakeStatus {
    /// Return the stable adapter-facing status identifier.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Ready => "ready",
            Self::ActionRequired => "action_required",
            Self::FatalError => "fatal_error",
        }
    }
}

/// State for one typed Game Setup Check.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GameSetupCheckState {
    /// The expectation was checked and passed.
    Passed,
    /// The expectation was checked and failed.
    Failed,
    /// The expectation produced a non-blocking warning.
    Warning,
    /// The expectation could not be checked because prerequisite facts were absent.
    Skipped,
    /// CLASSIC does not currently have enough curated data for this expectation.
    Unsupported,
    /// The caller must collect user input before this expectation can be checked.
    ActionRequired,
}

impl GameSetupCheckState {
    /// Return the stable adapter-facing state identifier.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Passed => "passed",
            Self::Failed => "failed",
            Self::Warning => "warning",
            Self::Skipped => "skipped",
            Self::Unsupported => "unsupported",
            Self::ActionRequired => "action_required",
        }
    }
}

/// Kind of setup expectation checked during intake.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GameSetupCheckKind {
    /// Game installation path resolution.
    GamePath,
    /// Documents folder path resolution.
    DocumentsPath,
    /// Version Registry metadata lookup.
    RegistryMetadata,
    /// Executable PE version detection.
    ExecutableVersion,
    /// Executable SHA-256 comparison.
    ExecutableHash,
    /// Installation location check.
    InstallationLocation,
    /// Documents folder readiness.
    DocumentsFolder,
    /// XSE loader installation state.
    XseLoader,
    /// XSE loader version compatibility.
    XseVersion,
    /// Address Library file state.
    AddressLibrary,
    /// XSE script file hashes.
    XseScriptHashes,
}

impl GameSetupCheckKind {
    /// Return the stable adapter-facing check identifier.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::GamePath => "game_path",
            Self::DocumentsPath => "documents_path",
            Self::RegistryMetadata => "registry_metadata",
            Self::ExecutableVersion => "executable_version",
            Self::ExecutableHash => "executable_hash",
            Self::InstallationLocation => "installation_location",
            Self::DocumentsFolder => "documents_folder",
            Self::XseLoader => "xse_loader",
            Self::XseVersion => "xse_version",
            Self::AddressLibrary => "address_library",
            Self::XseScriptHashes => "xse_script_hashes",
        }
    }
}

/// User action requested by a Game Setup Intake result.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GameSetupRequiredAction {
    /// Ask the user for the game installation path.
    ChooseGamePath,
    /// Ask the user for the documents folder path.
    ChooseDocumentsPath,
    /// Ask the user to choose a concrete supported game version.
    ChooseGameVersion,
}

impl GameSetupRequiredAction {
    /// Return the stable adapter-facing action identifier.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::ChooseGamePath => "choose_game_path",
            Self::ChooseDocumentsPath => "choose_documents_path",
            Self::ChooseGameVersion => "choose_game_version",
        }
    }
}

/// Path value discovered by Game Setup Intake that a caller may persist.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameSetupPathUpdate {
    /// Stable path kind, currently `game_root` or `docs_root`.
    pub kind: String,
    /// The resolved path value.
    pub path: PathBuf,
}

impl GameSetupPathUpdate {
    /// Create a new proposed path update.
    #[must_use]
    pub fn new(kind: impl Into<String>, path: PathBuf) -> Self {
        Self {
            kind: kind.into(),
            path,
        }
    }
}

/// Resolved path facts produced by Game Setup Intake.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct GameSetupResolvedPaths {
    /// Resolved game installation root.
    pub game_root: Option<PathBuf>,
    /// Resolved documents root.
    pub docs_root: Option<PathBuf>,
    /// Resolved game executable path.
    pub game_exe_path: Option<PathBuf>,
    /// Resolved XSE plugins directory.
    pub plugins_path: Option<PathBuf>,
}

/// Version facts produced by Game Setup Intake.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct GameSetupVersionFacts {
    /// Raw selected version from settings or caller input.
    pub requested: String,
    /// Canonical selected version after alias normalization.
    pub selected: String,
    /// Detected executable version, when PE metadata could be read.
    pub detected_exe_version: Option<String>,
    /// Version Registry ID used for expectation lookup.
    pub registry_id: Option<String>,
    /// Version Registry display name used for expectation lookup.
    pub registry_display_name: Option<String>,
    /// Confidence reported by the Version Registry matcher.
    pub match_confidence: Option<String>,
}

/// One typed Game Setup Check result.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameSetupCheck {
    /// Check kind.
    pub kind: GameSetupCheckKind,
    /// Check state.
    pub state: GameSetupCheckState,
    /// Short human-readable summary.
    pub message: String,
    /// Optional detail lines for adapters that want more context.
    pub details: Vec<String>,
}

impl GameSetupCheck {
    /// Create a check result without detail lines.
    #[must_use]
    pub fn new(
        kind: GameSetupCheckKind,
        state: GameSetupCheckState,
        message: impl Into<String>,
    ) -> Self {
        Self {
            kind,
            state,
            message: message.into(),
            details: Vec::new(),
        }
    }

    /// Create a check result with detail lines.
    #[must_use]
    pub fn with_details(
        kind: GameSetupCheckKind,
        state: GameSetupCheckState,
        message: impl Into<String>,
        details: Vec<String>,
    ) -> Self {
        Self {
            kind,
            state,
            message: message.into(),
            details,
        }
    }
}

/// Input for preparing and validating a game setup.
#[derive(Debug, Clone)]
pub struct GameSetupIntake {
    /// Supported game identifier.
    pub game_id: GameId,
    /// Selected game version, usually `auto` or a canonical Fallout 4 mode.
    pub selected_game_version: String,
    /// Saved or caller-provided game root.
    pub game_root: Option<PathBuf>,
    /// Saved or caller-provided documents root.
    pub docs_root: Option<PathBuf>,
    /// Optional XSE log path used as a game-root detection hint.
    pub xse_log_path: Option<PathBuf>,
}

impl GameSetupIntake {
    /// Create a new Game Setup Intake request.
    ///
    /// The request is read-only: running it may discover replacement paths, but
    /// those are returned as proposed updates rather than persisted directly.
    #[must_use]
    pub fn new(game_id: GameId, selected_game_version: impl Into<String>) -> Self {
        Self {
            game_id,
            selected_game_version: selected_game_version.into(),
            game_root: None,
            docs_root: None,
            xse_log_path: None,
        }
    }

    /// Set a saved or caller-provided game root.
    #[must_use]
    pub fn with_game_root(mut self, path: impl Into<PathBuf>) -> Self {
        self.game_root = non_empty_pathbuf(path.into());
        self
    }

    /// Set a saved or caller-provided documents root.
    #[must_use]
    pub fn with_docs_root(mut self, path: impl Into<PathBuf>) -> Self {
        self.docs_root = non_empty_pathbuf(path.into());
        self
    }

    /// Set an XSE log path to use as a game-root detection hint.
    #[must_use]
    pub fn with_xse_log_path(mut self, path: impl Into<PathBuf>) -> Self {
        self.xse_log_path = non_empty_pathbuf(path.into());
        self
    }

    /// Run Game Setup Intake and return typed diagnostics plus rendered text.
    ///
    /// Validation failures are represented as [`GameSetupCheck`] values. The
    /// top-level status becomes `ActionRequired` only when the caller needs to
    /// collect missing setup input before all relevant checks can run.
    #[must_use]
    pub fn run(&self) -> GameSetupIntakeResult {
        let mut checks = Vec::new();
        let mut actions = Vec::new();
        let mut path_updates = Vec::new();

        let game_root = resolve_game_root(self, &mut checks, &mut actions);
        let game_exe_path = game_root
            .as_ref()
            .map(|root| root.join(self.game_id.exe_name()));
        let version_context = resolve_version_context(self, game_exe_path.as_deref());
        let mut version_facts = version_context.facts;
        checks.extend(version_context.checks);

        let paths = resolve_version_dependent_paths(
            self,
            version_context.info.as_ref(),
            game_root,
            game_exe_path,
            &mut checks,
            &mut actions,
        );
        if let Some(game_root) = &paths.game_root
            && self.game_root.as_ref() != Some(game_root)
        {
            path_updates.push(GameSetupPathUpdate::new("game_root", game_root.clone()));
        }
        if let Some(docs_root) = &paths.docs_root
            && self.docs_root.as_ref() != Some(docs_root)
        {
            path_updates.push(GameSetupPathUpdate::new("docs_root", docs_root.clone()));
        }

        run_executable_checks(&paths, version_context.info.as_ref(), &mut checks);
        run_documents_checks(self.game_id, &paths, &mut checks);
        run_xse_checks(
            self.game_id,
            &paths,
            version_context.info.as_ref(),
            &mut checks,
        );

        if version_facts.selected == "auto"
            && version_context.info.is_none()
            && paths.game_exe_path.is_some()
        {
            actions.push(GameSetupRequiredAction::ChooseGameVersion);
            checks.push(GameSetupCheck::new(
                GameSetupCheckKind::RegistryMetadata,
                GameSetupCheckState::ActionRequired,
                "Choose a concrete game version because auto detection did not match registry data.",
            ));
        }

        let status = if actions.is_empty() {
            GameSetupIntakeStatus::Ready
        } else {
            GameSetupIntakeStatus::ActionRequired
        };
        version_facts.registry_id = version_context.info.as_ref().map(|info| info.id.clone());
        version_facts.registry_display_name = version_context
            .info
            .as_ref()
            .map(|info| info.display_name.clone());

        let mut result = GameSetupIntakeResult {
            status,
            game_id: self.game_id,
            paths,
            path_updates,
            version: version_facts,
            checks,
            actions,
            fatal_errors: Vec::new(),
            rendered_report: String::new(),
        };
        result.rendered_report = result.render_report();
        result
    }
}

/// Result of a Game Setup Intake run.
#[derive(Debug, Clone)]
pub struct GameSetupIntakeResult {
    /// Top-level intake status.
    pub status: GameSetupIntakeStatus,
    /// Game identifier used by the run.
    pub game_id: GameId,
    /// Resolved setup paths.
    pub paths: GameSetupResolvedPaths,
    /// Proposed path updates that callers may persist.
    pub path_updates: Vec<GameSetupPathUpdate>,
    /// Version facts used by the run.
    pub version: GameSetupVersionFacts,
    /// Typed setup checks.
    pub checks: Vec<GameSetupCheck>,
    /// User actions required before all checks can run.
    pub actions: Vec<GameSetupRequiredAction>,
    /// Fatal errors that prevented normal diagnostics.
    pub fatal_errors: Vec<String>,
    /// Canonical Rust-rendered report text.
    pub rendered_report: String,
}

impl GameSetupIntakeResult {
    /// Return `true` when at least one check failed or a fatal error occurred.
    #[must_use]
    pub fn has_errors(&self) -> bool {
        !self.fatal_errors.is_empty()
            || self
                .checks
                .iter()
                .any(|check| check.state == GameSetupCheckState::Failed)
    }

    /// Return the number of typed checks produced by the run.
    #[must_use]
    pub fn total_checks(&self) -> usize {
        self.checks.len()
    }

    /// Return the number of failed typed checks.
    #[must_use]
    pub fn failed_checks(&self) -> usize {
        self.checks
            .iter()
            .filter(|check| check.state == GameSetupCheckState::Failed)
            .count()
    }

    /// Render the result into CLASSIC's canonical setup report text.
    #[must_use]
    pub fn render_report(&self) -> String {
        let mut lines = Vec::new();
        lines.push(format!(
            "Game Setup Intake: {} ({})",
            self.game_id,
            self.status.as_str()
        ));

        if let Some(game_root) = &self.paths.game_root {
            lines.push(format!("Game Root: {}", game_root.display()));
        }
        if let Some(docs_root) = &self.paths.docs_root {
            lines.push(format!("Documents Root: {}", docs_root.display()));
        }
        if let Some(registry) = &self.version.registry_display_name {
            lines.push(format!("Version: {registry}"));
        } else {
            lines.push(format!("Version: {}", self.version.selected));
        }
        lines.push("-----".to_string());

        for check in &self.checks {
            lines.push(format!(
                "[{}] {}: {}",
                check.state.as_str(),
                check.kind.as_str(),
                check.message
            ));
            for detail in &check.details {
                lines.push(format!("  - {detail}"));
            }
            lines.push("-----".to_string());
        }

        if !self.actions.is_empty() {
            lines.push("Required Actions:".to_string());
            for action in &self.actions {
                lines.push(format!("  - {}", action.as_str()));
            }
            lines.push("-----".to_string());
        }

        lines.join("\n") + "\n"
    }
}

struct VersionContext {
    info: Option<VersionInfo>,
    facts: GameSetupVersionFacts,
    checks: Vec<GameSetupCheck>,
}

/// Resolve version registry metadata using any game executable path already discovered.
fn resolve_version_context(intake: &GameSetupIntake, exe_path: Option<&Path>) -> VersionContext {
    resolve_version_context_with_registry(intake, exe_path, get_version_registry())
}

fn resolve_version_context_with_registry(
    intake: &GameSetupIntake,
    exe_path: Option<&Path>,
    registry: &VersionRegistry,
) -> VersionContext {
    let selected = normalize_game_setup_version_selection(&intake.selected_game_version);
    let mut facts = GameSetupVersionFacts {
        requested: intake.selected_game_version.clone(),
        selected: selected.clone(),
        ..GameSetupVersionFacts::default()
    };

    let candidates = registry_auto_candidates(registry, intake.game_id);
    if candidates.is_empty() {
        return VersionContext {
            info: None,
            facts,
            checks: vec![GameSetupCheck::new(
                GameSetupCheckKind::RegistryMetadata,
                GameSetupCheckState::Unsupported,
                format!(
                    "Version Registry setup metadata is not available for {}.",
                    intake.game_id
                ),
            )],
        };
    };

    let info = if selected == "auto" {
        match exe_path {
            Some(path) if path.exists() => {
                detect_registry_info_from_exe(path, &candidates, &mut facts)
            }
            _ => None,
        }
    } else {
        registry_id_for_selection(intake.game_id, &selected)
            .and_then(|id| registry.get_by_id(id).cloned())
    };

    let checks = match &info {
        Some(info) => vec![GameSetupCheck::new(
            GameSetupCheckKind::RegistryMetadata,
            GameSetupCheckState::Passed,
            format!("Using Version Registry metadata for {}.", info.display_name),
        )],
        None => vec![GameSetupCheck::new(
            GameSetupCheckKind::RegistryMetadata,
            if selected == "auto" {
                GameSetupCheckState::Skipped
            } else {
                GameSetupCheckState::Unsupported
            },
            format!("No Version Registry setup metadata matched {selected}."),
        )],
    };

    VersionContext {
        info,
        facts,
        checks,
    }
}

fn detect_registry_info_from_exe(
    exe_path: &Path,
    candidates: &[VersionInfo],
    facts: &mut GameSetupVersionFacts,
) -> Option<VersionInfo> {
    if let Ok((major, minor, patch, build)) = extract_pe_version(exe_path) {
        let detected = RegistryGameVersion::new(
            u32::from(major),
            u32::from(minor),
            u32::from(patch),
            u32::from(build),
        );
        facts.detected_exe_version = Some(detected.to_string());
        if let Some(info) = candidates.iter().find(|info| info.version == detected) {
            facts.match_confidence =
                Some(match_confidence_name(MatchConfidence::Exact).to_string());
            return Some(info.clone());
        }
        if let Some(info) = candidates
            .iter()
            .find(|info| info.is_compatible_with(&detected))
        {
            facts.match_confidence =
                Some(match_confidence_name(MatchConfidence::Range).to_string());
            return Some(info.clone());
        }
        facts.match_confidence = Some(match_confidence_name(MatchConfidence::Unknown).to_string());
    }

    let hash = FileHasher::hash_file(exe_path).ok()?;
    candidates
        .iter()
        .find(|info| {
            info.exe_hash
                .as_deref()
                .is_some_and(|expected| expected.eq_ignore_ascii_case(&hash))
        })
        .map(|info| {
            facts.match_confidence =
                Some(match_confidence_name(MatchConfidence::Exact).to_string());
            info.clone()
        })
}

/// Resolve paths whose exact shape depends on selected Version Registry metadata.
fn resolve_version_dependent_paths(
    intake: &GameSetupIntake,
    info: Option<&VersionInfo>,
    game_root: Option<PathBuf>,
    game_exe_path: Option<PathBuf>,
    checks: &mut Vec<GameSetupCheck>,
    actions: &mut Vec<GameSetupRequiredAction>,
) -> GameSetupResolvedPaths {
    let docs_root = resolve_docs_root(intake, info, checks, actions);
    let plugins_path = game_root
        .as_ref()
        .zip(info.and_then(|info| info.xse.as_ref()))
        .map(|(root, xse)| {
            root.join("Data")
                .join(xse_runtime_folder_name(&xse.acronym))
                .join("Plugins")
        });

    GameSetupResolvedPaths {
        game_root,
        docs_root,
        game_exe_path,
        plugins_path,
    }
}

fn resolve_game_root(
    intake: &GameSetupIntake,
    checks: &mut Vec<GameSetupCheck>,
    actions: &mut Vec<GameSetupRequiredAction>,
) -> Option<PathBuf> {
    let finder = GamePathFinder::new(
        intake.game_id.exe_name(),
        None::<&str>,
        intake.game_id.as_str(),
        // GamePathFinder still needs a product hint for Windows registry lookup;
        // VersionInfo drives the version-specific expectations after this point.
        intake.game_id.is_vr(),
    );
    match finder.find_game_path(intake.game_root.as_deref(), intake.xse_log_path.as_deref()) {
        Ok(path) => {
            checks.push(GameSetupCheck::new(
                GameSetupCheckKind::GamePath,
                GameSetupCheckState::Passed,
                format!("Resolved game root at {}.", path.display()),
            ));
            Some(path)
        }
        Err(error) => {
            actions.push(GameSetupRequiredAction::ChooseGamePath);
            checks.push(GameSetupCheck::new(
                GameSetupCheckKind::GamePath,
                GameSetupCheckState::ActionRequired,
                format!("Game root could not be resolved: {error}."),
            ));
            None
        }
    }
}

fn resolve_docs_root(
    intake: &GameSetupIntake,
    info: Option<&VersionInfo>,
    checks: &mut Vec<GameSetupCheck>,
    actions: &mut Vec<GameSetupRequiredAction>,
) -> Option<PathBuf> {
    let docs_name = info
        .map(|info| info.docs_name.as_str())
        .filter(|name| !name.trim().is_empty())
        .unwrap_or_else(|| intake.game_id.as_str());
    let mut finder = DocsPathFinder::new(format!(r"My Games\{docs_name}"));
    if let Some(info) = info
        && info.steam_id != 0
    {
        finder = finder.with_steam_app_id(info.steam_id);
    }

    let cached = intake
        .docs_root
        .as_ref()
        .map(|path| path.to_string_lossy().to_string());
    match finder.find_docs_path(cached.as_deref()) {
        Ok(path) => {
            checks.push(GameSetupCheck::new(
                GameSetupCheckKind::DocumentsPath,
                GameSetupCheckState::Passed,
                format!("Resolved documents root at {}.", path.display()),
            ));
            Some(path)
        }
        Err(error) => {
            actions.push(GameSetupRequiredAction::ChooseDocumentsPath);
            checks.push(GameSetupCheck::new(
                GameSetupCheckKind::DocumentsPath,
                GameSetupCheckState::ActionRequired,
                format!("Documents root could not be resolved: {error}."),
            ));
            None
        }
    }
}

fn run_executable_checks(
    paths: &GameSetupResolvedPaths,
    info: Option<&VersionInfo>,
    checks: &mut Vec<GameSetupCheck>,
) {
    let Some(exe_path) = &paths.game_exe_path else {
        checks.push(GameSetupCheck::new(
            GameSetupCheckKind::ExecutableVersion,
            GameSetupCheckState::Skipped,
            "Executable checks need a resolved game root.",
        ));
        return;
    };

    if !exe_path.exists() {
        checks.push(GameSetupCheck::new(
            GameSetupCheckKind::ExecutableVersion,
            GameSetupCheckState::Failed,
            format!("Game executable not found at {}.", exe_path.display()),
        ));
        return;
    }

    match (extract_pe_version(exe_path), info) {
        (Ok((major, minor, patch, build)), Some(info)) => {
            let detected = RegistryGameVersion::new(
                u32::from(major),
                u32::from(minor),
                u32::from(patch),
                u32::from(build),
            );
            let state = if info.is_compatible_with(&detected) {
                GameSetupCheckState::Passed
            } else {
                GameSetupCheckState::Failed
            };
            checks.push(GameSetupCheck::new(
                GameSetupCheckKind::ExecutableVersion,
                state,
                format!("Detected executable version {detected}."),
            ));
        }
        (Ok((major, minor, patch, build)), None) => {
            let detected = RegistryGameVersion::new(
                u32::from(major),
                u32::from(minor),
                u32::from(patch),
                u32::from(build),
            );
            checks.push(GameSetupCheck::new(
                GameSetupCheckKind::ExecutableVersion,
                GameSetupCheckState::Unsupported,
                format!(
                    "Detected executable version {detected}, but no registry expectation matched."
                ),
            ));
        }
        (Err(error), _) => checks.push(GameSetupCheck::new(
            GameSetupCheckKind::ExecutableVersion,
            GameSetupCheckState::Warning,
            format!("Executable PE version could not be read: {error}."),
        )),
    }

    match (
        FileHasher::hash_file(exe_path),
        info.and_then(|info| info.exe_hash.as_deref()),
    ) {
        (Ok(actual), Some(expected)) => {
            let state = if actual.eq_ignore_ascii_case(expected) {
                GameSetupCheckState::Passed
            } else {
                GameSetupCheckState::Failed
            };
            checks.push(GameSetupCheck::with_details(
                GameSetupCheckKind::ExecutableHash,
                state,
                "Compared executable hash against Version Registry expectation.",
                vec![format!("actual={actual}"), format!("expected={expected}")],
            ));
        }
        (Ok(_), None) => checks.push(GameSetupCheck::new(
            GameSetupCheckKind::ExecutableHash,
            GameSetupCheckState::Unsupported,
            "No executable hash expectation is available for this game version.",
        )),
        (Err(error), _) => checks.push(GameSetupCheck::new(
            GameSetupCheckKind::ExecutableHash,
            GameSetupCheckState::Failed,
            format!("Executable hash could not be calculated: {error}."),
        )),
    }

    let path_text = exe_path.to_string_lossy();
    let in_program_files = path_text.contains("Program Files");
    checks.push(GameSetupCheck::new(
        GameSetupCheckKind::InstallationLocation,
        if in_program_files {
            GameSetupCheckState::Warning
        } else {
            GameSetupCheckState::Passed
        },
        if in_program_files {
            "Game executable is under Program Files; permissions can interfere with modded setups."
                .to_string()
        } else {
            "Game executable is outside Program Files.".to_string()
        },
    ));
}

fn run_documents_checks(
    game_id: GameId,
    paths: &GameSetupResolvedPaths,
    checks: &mut Vec<GameSetupCheck>,
) {
    let Some(docs_root) = &paths.docs_root else {
        checks.push(GameSetupCheck::new(
            GameSetupCheckKind::DocumentsFolder,
            GameSetupCheckState::Skipped,
            "Documents checks need a resolved documents root.",
        ));
        return;
    };

    let docs_checker = classic_path_core::DocumentsChecker::new(game_id.as_str());
    match docs_checker.run_all_checks(docs_root) {
        Ok(messages) => {
            let state = if messages.iter().any(|message| message.contains("❌")) {
                GameSetupCheckState::Failed
            } else if messages.iter().any(|message| message.contains("⚠")) {
                GameSetupCheckState::Warning
            } else {
                GameSetupCheckState::Passed
            };
            checks.push(GameSetupCheck::with_details(
                GameSetupCheckKind::DocumentsFolder,
                state,
                "Ran documents folder checks.",
                messages,
            ));
        }
        Err(error) => checks.push(GameSetupCheck::new(
            GameSetupCheckKind::DocumentsFolder,
            GameSetupCheckState::Failed,
            format!("Documents folder checks failed: {error}."),
        )),
    }
}

fn run_xse_checks(
    game_id: GameId,
    paths: &GameSetupResolvedPaths,
    info: Option<&VersionInfo>,
    checks: &mut Vec<GameSetupCheck>,
) {
    let Some(game_root) = &paths.game_root else {
        checks.push(GameSetupCheck::new(
            GameSetupCheckKind::XseLoader,
            GameSetupCheckState::Skipped,
            "XSE checks need a resolved game root.",
        ));
        return;
    };

    let xse_type = XseType::from_game_id(game_id);
    let xse_info = get_xse_info(game_root, xse_type);
    checks.push(GameSetupCheck::new(
        GameSetupCheckKind::XseLoader,
        if xse_info.installed {
            GameSetupCheckState::Passed
        } else {
            GameSetupCheckState::Failed
        },
        if xse_info.installed {
            format!("{} loader is installed.", xse_type.as_str())
        } else {
            format!(
                "{} loader was not found at {}.",
                xse_type.as_str(),
                xse_info.loader_path().display()
            )
        },
    ));

    match (
        xse_info.version.as_ref(),
        info.and_then(|info| info.xse.as_ref()),
    ) {
        (Some(actual), Some(expected)) => {
            let state = parse_version(&expected.compatible_version)
                .ok()
                .map(|expected_version| {
                    if &expected_version == actual {
                        GameSetupCheckState::Passed
                    } else {
                        GameSetupCheckState::Failed
                    }
                })
                .unwrap_or(GameSetupCheckState::Unsupported);
            checks.push(GameSetupCheck::new(
                GameSetupCheckKind::XseVersion,
                state,
                format!(
                    "Detected {} version {}; expected {}.",
                    expected.acronym, actual, expected.compatible_version
                ),
            ));
        }
        (None, Some(expected)) if xse_info.installed => checks.push(GameSetupCheck::new(
            GameSetupCheckKind::XseVersion,
            GameSetupCheckState::Failed,
            format!(
                "{} is installed, but its version could not be detected.",
                expected.acronym
            ),
        )),
        (_, None) => checks.push(GameSetupCheck::new(
            GameSetupCheckKind::XseVersion,
            GameSetupCheckState::Unsupported,
            "No Version Registry XSE expectation is available for this game version.",
        )),
        (None, Some(_)) => checks.push(GameSetupCheck::new(
            GameSetupCheckKind::XseVersion,
            GameSetupCheckState::Skipped,
            "XSE version check skipped because the loader is missing.",
        )),
    }

    run_address_library_check(paths, info, checks);
    run_xse_script_hash_checks(paths, info, checks);
}

fn run_address_library_check(
    paths: &GameSetupResolvedPaths,
    info: Option<&VersionInfo>,
    checks: &mut Vec<GameSetupCheck>,
) {
    let Some(expected) = info.and_then(|info| info.address_library.as_ref()) else {
        checks.push(GameSetupCheck::new(
            GameSetupCheckKind::AddressLibrary,
            GameSetupCheckState::Unsupported,
            "No Address Library expectation is available for this game version.",
        ));
        return;
    };
    let Some(plugins_path) = &paths.plugins_path else {
        checks.push(GameSetupCheck::new(
            GameSetupCheckKind::AddressLibrary,
            GameSetupCheckState::Skipped,
            "Address Library check needs a resolved plugins folder.",
        ));
        return;
    };

    if !plugins_path.exists() {
        checks.push(GameSetupCheck::new(
            GameSetupCheckKind::AddressLibrary,
            GameSetupCheckState::Failed,
            format!("Plugins folder not found at {}.", plugins_path.display()),
        ));
        return;
    }

    let expected_path = plugins_path.join(&expected.filename);
    if expected_path.exists() {
        checks.push(GameSetupCheck::new(
            GameSetupCheckKind::AddressLibrary,
            GameSetupCheckState::Passed,
            format!("Address Library file {} is installed.", expected.filename),
        ));
        return;
    }

    let known_wrong = known_address_library_files(info.map(|info| info.game.as_str()))
        .into_iter()
        .filter(|filename| filename != &expected.filename && plugins_path.join(filename).exists())
        .collect::<Vec<_>>();
    let details = if known_wrong.is_empty() {
        vec![format!("expected={}", expected.filename)]
    } else {
        known_wrong
            .into_iter()
            .map(|filename| format!("found known different file: {filename}"))
            .collect()
    };
    checks.push(GameSetupCheck::with_details(
        GameSetupCheckKind::AddressLibrary,
        GameSetupCheckState::Failed,
        "Expected Address Library file is not installed.",
        details,
    ));
}

fn run_xse_script_hash_checks(
    paths: &GameSetupResolvedPaths,
    info: Option<&VersionInfo>,
    checks: &mut Vec<GameSetupCheck>,
) {
    let Some(xse) = info.and_then(|info| info.xse.as_ref()) else {
        checks.push(GameSetupCheck::new(
            GameSetupCheckKind::XseScriptHashes,
            GameSetupCheckState::Unsupported,
            "No XSE script hash expectations are available for this game version.",
        ));
        return;
    };
    if xse.script_hashes.is_empty() {
        checks.push(GameSetupCheck::new(
            GameSetupCheckKind::XseScriptHashes,
            GameSetupCheckState::Unsupported,
            format!("{} has no curated script hash expectations.", xse.acronym),
        ));
        return;
    }
    let Some(game_root) = &paths.game_root else {
        checks.push(GameSetupCheck::new(
            GameSetupCheckKind::XseScriptHashes,
            GameSetupCheckState::Skipped,
            "XSE script hash checks need a resolved game root.",
        ));
        return;
    };

    let scripts_root = game_root.join("Data").join("Scripts");
    let mut missing = 0usize;
    let mut mismatched = 0usize;
    let mut details = Vec::new();
    for (script, expected_hash) in &xse.script_hashes {
        let script_path = scripts_root.join(script);
        if !script_path.exists() {
            missing += 1;
            if details.len() < 10 {
                details.push(format!("missing {script}"));
            }
            continue;
        }
        match FileHasher::hash_file(&script_path) {
            Ok(actual) if actual.eq_ignore_ascii_case(expected_hash) => {}
            Ok(actual) => {
                mismatched += 1;
                if details.len() < 10 {
                    details.push(format!("{script} hash mismatch: actual={actual}"));
                }
            }
            Err(error) => {
                mismatched += 1;
                if details.len() < 10 {
                    details.push(format!("{script} hash failed: {error}"));
                }
            }
        }
    }

    let state = if missing == 0 && mismatched == 0 {
        GameSetupCheckState::Passed
    } else {
        GameSetupCheckState::Failed
    };
    checks.push(GameSetupCheck::with_details(
        GameSetupCheckKind::XseScriptHashes,
        state,
        format!(
            "Checked {} {} script file hashes; missing={}, mismatched={}.",
            xse.script_hashes.len(),
            xse.acronym,
            missing,
            mismatched
        ),
        details,
    ));
}

/// Normalize a raw game-version setup selection.
#[must_use]
pub fn normalize_game_setup_version_selection(value: &str) -> String {
    let normalized: String = value
        .chars()
        .filter(|ch| ch.is_ascii_alphanumeric())
        .map(|ch| ch.to_ascii_lowercase())
        .collect();
    match normalized.as_str() {
        "" | "auto" => "auto",
        "original" | "og" => "Original",
        "nextgen" | "ng" => "NextGen",
        "anniversaryedition" | "anniversary" | "ae" => "AnniversaryEdition",
        "vr" => "VR",
        _ => "auto",
    }
    .to_string()
}

/// Return whether saved paths are missing and Game Setup Intake should resolve them.
#[must_use]
pub fn game_setup_needs_path_detection(
    game_path: Option<&str>,
    docs_path: Option<&str>,
) -> (bool, bool) {
    let needs_game = game_path.is_none_or(|path| path.trim().is_empty());
    let needs_docs = docs_path.is_none_or(|path| path.trim().is_empty());
    (needs_game, needs_docs)
}

fn non_empty_pathbuf(path: PathBuf) -> Option<PathBuf> {
    if path.as_os_str().is_empty() {
        None
    } else {
        Some(path)
    }
}

fn registry_auto_candidates(registry: &VersionRegistry, game_id: GameId) -> Vec<VersionInfo> {
    let default_id = registry
        .unknown_version_handling()
        .get_default(game_id.as_str());
    let mut candidates = Vec::new();
    for game_name in registry_game_names(game_id) {
        for info in registry.get_all_for_game(game_name, None) {
            if registry_info_matches_game_id(info, game_id, default_id)
                && !candidates
                    .iter()
                    .any(|candidate: &VersionInfo| candidate.id == info.id)
            {
                candidates.push(info.clone());
            }
        }
    }
    candidates
}

fn registry_game_names(game_id: GameId) -> &'static [&'static str] {
    match game_id {
        GameId::Fallout4 => &["Fallout4"],
        GameId::Fallout4VR => &["Fallout4VR", "Fallout4"],
        GameId::Skyrim | GameId::Starfield => &[],
    }
}

fn registry_info_matches_game_id(
    info: &VersionInfo,
    game_id: GameId,
    default_id: Option<&str>,
) -> bool {
    if default_id == Some(info.id.as_str()) {
        return true;
    }

    match game_id {
        GameId::Fallout4 => info.game == "Fallout4" && info.docs_name == "Fallout4",
        GameId::Fallout4VR => info.game == "Fallout4VR" || info.docs_name == "Fallout4VR",
        GameId::Skyrim | GameId::Starfield => info.game == game_id.as_str(),
    }
}

fn registry_id_for_selection(game_id: GameId, selected: &str) -> Option<&'static str> {
    match (game_id, selected) {
        (GameId::Fallout4 | GameId::Fallout4VR, "Original") => Some("FO4_OG"),
        (GameId::Fallout4 | GameId::Fallout4VR, "NextGen") => Some("FO4_NG"),
        (GameId::Fallout4 | GameId::Fallout4VR, "AnniversaryEdition") => Some("FO4_AE"),
        (GameId::Fallout4 | GameId::Fallout4VR, "VR") => Some("FO4_VR"),
        _ => None,
    }
}

fn match_confidence_name(confidence: MatchConfidence) -> &'static str {
    match confidence {
        MatchConfidence::Exact => "exact",
        MatchConfidence::Range => "range",
        MatchConfidence::Nearest => "nearest",
        MatchConfidence::Default => "default",
        MatchConfidence::Unknown => "unknown",
    }
}

fn xse_runtime_folder_name(acronym: &str) -> &str {
    match acronym.trim() {
        // F4SEVR keeps its loader identity, but runtime plugins are conventionally
        // installed under Data/F4SE/Plugins.
        "F4SEVR" => "F4SE",
        other => other,
    }
}

fn known_address_library_files(game: Option<&str>) -> Vec<String> {
    let Some(game) = game else {
        return Vec::new();
    };
    get_version_registry()
        .get_all_for_game(game, None)
        .into_iter()
        .filter_map(|info| info.address_library.as_ref())
        .map(|address_library| address_library.filename.clone())
        .collect()
}

#[cfg(test)]
#[path = "game_setup_intake_tests.rs"]
mod tests;
