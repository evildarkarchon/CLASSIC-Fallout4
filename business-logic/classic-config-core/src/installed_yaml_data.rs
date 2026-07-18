//! Installed YAML Data selection and side-effect-limited inspection.

use crate::client_schemas;
use crate::explicit_yaml_data::{
    ExplicitYamlDataLoadError, GameDataRole, YamlDataContentIdentity, game_data_key,
    registered_game_data_role, validate_game, validate_ignore, validate_main,
};
use crate::yamldata::{YamlDataCore, parse_and_merge_yaml_content};
use classic_path_core::yaml_cache_dir_with_env;
use classic_settings_core::{
    Compatibility, SchemaCompat, SchemaVersion, extract_schema_version, schema_compat_check,
};
use classic_shared_core::GameId;
use std::io::Write;
use std::path::{Path, PathBuf};
use tempfile::NamedTempFile;
use thiserror::Error;
use yaml_rust2::Yaml;

/// The update-eligible role being inspected.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InstalledYamlDataRole {
    /// Global Main YAML Data.
    Main,
    /// Selected-game YAML Data.
    Game,
}

impl std::fmt::Display for InstalledYamlDataRole {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Main => formatter.write_str("Main"),
            Self::Game => formatter.write_str("game"),
        }
    }
}

/// The installed candidate that supplied a selected YAML Data file.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InstalledYamlDataProvenance {
    /// Canonical per-user updated candidate.
    Updated,
    /// Previous updated sibling used read-only because the canonical file was absent.
    Previous,
    /// Install-tree bundled candidate.
    Bundled,
}

/// Stable category for an inspection diagnostic.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InstalledYamlDataDiagnosticKind {
    /// The per-user update cache could not be resolved.
    CacheUnavailable,
    /// A candidate was absent when it was required as the final fallback.
    Missing,
    /// A present candidate could not be read.
    Read,
    /// Candidate bytes were not valid UTF-8.
    InvalidUtf8,
    /// Candidate text was not valid YAML Data.
    Parse,
    /// A parsed candidate omitted or malformed its schema version.
    InvalidSchema,
    /// A candidate schema was outside the client-owned compatibility range.
    IncompatibleSchema,
    /// A candidate failed role-specific semantic validation.
    InvalidRoleData,
    /// Missing Local Ignore YAML Data was generated from selected Main defaults.
    LocalIgnoreGenerated,
}

/// Structured attribution for Installed YAML Data selection or local generation events.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InstalledYamlDataDiagnostic {
    role: Option<InstalledYamlDataRole>,
    candidate: Option<InstalledYamlDataProvenance>,
    path: Option<PathBuf>,
    kind: InstalledYamlDataDiagnosticKind,
    message: String,
}

impl InstalledYamlDataDiagnostic {
    /// Return the affected update-eligible role, or `None` for installation-wide and Local Ignore diagnostics.
    #[must_use]
    pub const fn role(&self) -> Option<InstalledYamlDataRole> {
        self.role
    }

    /// Return the rejected candidate kind, or `None` when the event is not candidate-specific.
    #[must_use]
    pub const fn candidate(&self) -> Option<InstalledYamlDataProvenance> {
        self.candidate
    }

    /// Return the affected path when the diagnostic is path-attributable.
    #[must_use]
    pub fn path(&self) -> Option<&Path> {
        self.path.as_deref()
    }

    /// Return the stable diagnostic category.
    #[must_use]
    pub const fn kind(&self) -> InstalledYamlDataDiagnosticKind {
        self.kind
    }

    /// Return an actionable human-readable explanation.
    #[must_use]
    pub fn message(&self) -> &str {
        &self.message
    }
}

/// One selected update-eligible YAML Data file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InspectedYamlDataFile {
    role: InstalledYamlDataRole,
    provenance: InstalledYamlDataProvenance,
    schema_version: SchemaVersion,
    identity: YamlDataContentIdentity,
}

impl InspectedYamlDataFile {
    /// Return whether this is the Main or selected-game file.
    #[must_use]
    pub const fn role(&self) -> InstalledYamlDataRole {
        self.role
    }

    /// Return which installed candidate supplied the selected bytes.
    #[must_use]
    pub const fn provenance(&self) -> InstalledYamlDataProvenance {
        self.provenance
    }

    /// Return the compatible schema version parsed from the selected bytes.
    #[must_use]
    pub const fn schema_version(&self) -> SchemaVersion {
        self.schema_version
    }

    /// Return the SHA-256 and byte length derived from the selected bytes.
    #[must_use]
    pub const fn identity(&self) -> &YamlDataContentIdentity {
        &self.identity
    }
}

/// One installation root and typed game identity to inspect.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InstalledYamlDataInspectionRequest {
    /// CLASSIC installation root containing `CLASSIC Data/databases`.
    pub installation_root: PathBuf,
    /// Typed game identity used to select registered game YAML Data.
    pub game: GameId,
}

/// One installation root, typed game, and game-version mode to load.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InstalledYamlDataLoadRequest {
    /// CLASSIC installation root containing `CLASSIC Data`.
    pub installation_root: PathBuf,
    /// Typed game identity used to select registered game YAML Data.
    pub game: GameId,
    /// Existing game-version mode used only for Version Registry metadata selection.
    pub selected_game_version: String,
}

/// How Local Ignore YAML Data entered an installed snapshot.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LocalIgnoreYamlDataState {
    /// A valid user-owned Local Ignore file already existed in the installation.
    Existing,
    /// Missing Local Ignore YAML Data was generated from selected Main defaults.
    Generated,
}

/// Selected update-eligible YAML Data facts from one inspection.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InstalledYamlDataInspection {
    requested_game: GameId,
    game_data_role: GameDataRole,
    main: InspectedYamlDataFile,
    game_file: InspectedYamlDataFile,
    diagnostics: Vec<InstalledYamlDataDiagnostic>,
}

#[derive(Debug)]
struct OwnedInstalledYamlDataFile {
    bytes: Box<[u8]>,
    yaml: Yaml,
    inspected: InspectedYamlDataFile,
}

#[derive(Debug)]
struct SelectedInstalledYamlData {
    requested_game: GameId,
    game_data_role: GameDataRole,
    main: OwnedInstalledYamlDataFile,
    game_file: OwnedInstalledYamlDataFile,
    diagnostics: Vec<InstalledYamlDataDiagnostic>,
}

#[derive(Debug)]
struct OwnedLocalIgnoreYamlData {
    bytes: Box<[u8]>,
    identity: YamlDataContentIdentity,
}

/// Private filesystem seam for deterministic Local Ignore publication and reread tests.
///
/// Production uses [`SystemLocalIgnoreFileSystem`]. Keeping this seam private prevents callers
/// from replacing config-owned generation policy while allowing failure atomicity and races to
/// be driven at the complete loader boundary.
trait LocalIgnoreFileSystem {
    /// Read the canonical Local Ignore path.
    fn read(&self, path: &Path) -> std::io::Result<Vec<u8>>;

    /// Atomically link one fully synced staged file into an absent canonical path.
    fn publish_staged_noclobber(&self, staged_path: &Path, path: &Path) -> std::io::Result<bool>;
}

/// Production Local Ignore filesystem implementation backed by `std::fs`.
struct SystemLocalIgnoreFileSystem;

impl LocalIgnoreFileSystem for SystemLocalIgnoreFileSystem {
    fn read(&self, path: &Path) -> std::io::Result<Vec<u8>> {
        std::fs::read(path)
    }

    fn publish_staged_noclobber(&self, staged_path: &Path, path: &Path) -> std::io::Result<bool> {
        match std::fs::hard_link(staged_path, path) {
            Ok(()) => Ok(true),
            Err(source) if source.kind() == std::io::ErrorKind::AlreadyExists => Ok(false),
            Err(source) => Err(source),
        }
    }
}

/// Immutable parsed Installed YAML Data backed by the exact selected file bytes.
pub struct InstalledYamlDataSnapshot {
    yaml_data: YamlDataCore,
    requested_game: GameId,
    game_data_role: GameDataRole,
    main: OwnedInstalledYamlDataFile,
    game_file: OwnedInstalledYamlDataFile,
    local_ignore: OwnedLocalIgnoreYamlData,
    local_ignore_state: LocalIgnoreYamlDataState,
    diagnostics: Vec<InstalledYamlDataDiagnostic>,
}

// A custom formatter prevents private retained bytes and parsed YAML documents from becoming
// observable through a derived `Debug` implementation.
impl std::fmt::Debug for InstalledYamlDataSnapshot {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter
            .debug_struct("InstalledYamlDataSnapshot")
            .field("requested_game", &self.requested_game)
            .field("game_data_role", &self.game_data_role)
            .field("main", &self.main.inspected)
            .field("game_file", &self.game_file.inspected)
            .field("local_ignore_identity", &self.local_ignore.identity)
            .field("local_ignore_state", &self.local_ignore_state)
            .field("diagnostics", &self.diagnostics)
            .finish_non_exhaustive()
    }
}

impl InstalledYamlDataSnapshot {
    /// Return parsed YAML Data derived only from the retained selected bytes.
    #[must_use]
    pub const fn yaml_data(&self) -> &YamlDataCore {
        &self.yaml_data
    }

    /// Return the typed game requested by the caller.
    #[must_use]
    pub const fn game(&self) -> GameId {
        self.requested_game
    }

    /// Return the registered data role used for the selected game file.
    #[must_use]
    pub const fn game_data_role(&self) -> GameDataRole {
        self.game_data_role
    }

    /// Return the independently selected Main file facts.
    #[must_use]
    pub const fn main(&self) -> &InspectedYamlDataFile {
        &self.main.inspected
    }

    /// Return the independently selected game file facts.
    #[must_use]
    pub const fn game_file(&self) -> &InspectedYamlDataFile {
        &self.game_file.inspected
    }

    /// Return how Local Ignore YAML Data entered this snapshot.
    #[must_use]
    pub const fn local_ignore_state(&self) -> LocalIgnoreYamlDataState {
        self.local_ignore_state
    }

    /// Return the identity derived from the exact retained Local Ignore bytes.
    #[must_use]
    pub const fn local_ignore_identity(&self) -> &YamlDataContentIdentity {
        &self.local_ignore.identity
    }

    /// Return structured fallback, cache-resolution, and generation diagnostics.
    #[must_use]
    pub fn diagnostics(&self) -> &[InstalledYamlDataDiagnostic] {
        &self.diagnostics
    }
}

/// Expected outcomes from loading Installed YAML Data.
#[derive(Debug)]
pub enum InstalledYamlDataLoadOutcome {
    /// Main, game, and valid Local Ignore data were loaded into one immutable snapshot.
    Ready(InstalledYamlDataSnapshot),
}

impl InstalledYamlDataInspection {
    /// Return the typed game requested by the caller.
    #[must_use]
    pub const fn game(&self) -> GameId {
        self.requested_game
    }

    /// Return the registered data role used for the selected game file.
    #[must_use]
    pub const fn game_data_role(&self) -> GameDataRole {
        self.game_data_role
    }

    /// Return the independently selected Main file facts.
    #[must_use]
    pub const fn main(&self) -> &InspectedYamlDataFile {
        &self.main
    }

    /// Return the independently selected game file facts.
    #[must_use]
    pub const fn game_file(&self) -> &InspectedYamlDataFile {
        &self.game_file
    }

    /// Return structured fallback and cache-resolution diagnostics.
    #[must_use]
    pub fn diagnostics(&self) -> &[InstalledYamlDataDiagnostic] {
        &self.diagnostics
    }
}

/// Failures that prevent inspection from selecting both required files.
#[derive(Debug, Error)]
pub enum InstalledYamlDataInspectionError {
    /// The typed game has no registered YAML Data role in this client.
    #[error("unsupported game for Installed YAML Data inspection: {game}")]
    UnsupportedGame {
        /// Unsupported typed game identity.
        game: GameId,
    },
    /// Neither updated nor bundled data was usable for one required role.
    #[error("no usable Installed YAML Data source for {role}")]
    NoUsableSource {
        /// Required role that could not be selected.
        role: InstalledYamlDataRole,
        /// Every actionable diagnostic observed before selection failed.
        diagnostics: Vec<InstalledYamlDataDiagnostic>,
    },
}

/// Fatal failures that prevent Installed YAML Data from becoming ready.
#[derive(Debug, Error)]
pub enum InstalledYamlDataLoadError {
    /// The typed game has no registered YAML Data role in this client.
    #[error("unsupported game for Installed YAML Data loading: {game}")]
    UnsupportedGame {
        /// Unsupported typed game identity.
        game: GameId,
    },
    /// Neither updated nor bundled data was usable for one required role.
    #[error("no usable Installed YAML Data source for {role}")]
    NoUsableSource {
        /// Required role that could not be selected.
        role: InstalledYamlDataRole,
        /// Every actionable diagnostic observed before selection failed.
        diagnostics: Vec<InstalledYamlDataDiagnostic>,
    },
    /// Existing Local Ignore YAML Data could not be read.
    #[error("failed to read Local Ignore YAML Data `{}`: {source}", path.display())]
    LocalIgnoreRead {
        /// Expected Local Ignore path.
        path: PathBuf,
        /// Underlying filesystem failure.
        #[source]
        source: std::io::Error,
    },
    /// Existing Local Ignore bytes were not valid UTF-8.
    #[error("Local Ignore YAML Data `{}` is not UTF-8: {source}", path.display())]
    LocalIgnoreInvalidUtf8 {
        /// Existing Local Ignore path.
        path: PathBuf,
        /// Underlying UTF-8 failure.
        #[source]
        source: std::str::Utf8Error,
    },
    /// Existing Local Ignore content could not be parsed as YAML.
    #[error("failed to parse Local Ignore YAML Data `{}`: {message}", path.display())]
    LocalIgnoreParse {
        /// Existing Local Ignore path.
        path: PathBuf,
        /// Parser failure details.
        message: String,
    },
    /// Existing Local Ignore content did not satisfy its role contract.
    #[error("Local Ignore YAML Data `{}` is invalid: {reason}", path.display())]
    LocalIgnoreInvalidRoleData {
        /// Existing Local Ignore path.
        path: PathBuf,
        /// Stable validation details.
        reason: String,
    },
    /// Selected Main defaults could not safely initialize missing Local Ignore YAML Data.
    #[error("selected Main default for Local Ignore YAML Data `{}` is invalid: {reason}", path.display())]
    LocalIgnoreDefaultInvalid {
        /// Expected Local Ignore path.
        path: PathBuf,
        /// Stable validation details.
        reason: String,
    },
    /// Missing Local Ignore YAML Data could not be atomically created.
    #[error("failed to create Local Ignore YAML Data `{}`: {source}", path.display())]
    LocalIgnoreCreate {
        /// Expected Local Ignore path.
        path: PathBuf,
        /// Underlying staging or publication failure.
        #[source]
        source: std::io::Error,
    },
    /// Selected documents could not be projected into parsed YAML Data.
    #[error("selected Installed YAML Data is invalid: {message}")]
    InvalidSelectedData {
        /// Projection failure details.
        message: String,
    },
}

/// Inspect installed Main and game YAML Data without reading or modifying Local Ignore.
///
/// Candidate files are read at most once. Parsing, semantic validation, schema extraction,
/// and content identity all borrow the exact owned bytes from that read. Inspection never
/// creates the cache or promotes, deletes, rewrites, or repairs any candidate.
pub fn inspect_installed_yaml_data(
    request: InstalledYamlDataInspectionRequest,
) -> Result<InstalledYamlDataInspection, InstalledYamlDataInspectionError> {
    inspect_installed_yaml_data_with_env(request, |name| match std::env::var(name) {
        Ok(value) if !value.is_empty() => Some(value),
        _ => None,
    })
}

/// Testable form of [`inspect_installed_yaml_data`] with injected cache environment lookup.
///
/// The environment callback controls only per-user cache resolution. Bundled candidates are
/// always resolved from the request's explicit installation root.
pub fn inspect_installed_yaml_data_with_env<F>(
    request: InstalledYamlDataInspectionRequest,
    env: F,
) -> Result<InstalledYamlDataInspection, InstalledYamlDataInspectionError>
where
    F: Fn(&str) -> Option<String>,
{
    let selected = select_installed_yaml_data(&request.installation_root, request.game, env)?;
    Ok(InstalledYamlDataInspection {
        requested_game: selected.requested_game,
        game_data_role: selected.game_data_role,
        main: selected.main.inspected,
        game_file: selected.game_file.inspected,
        diagnostics: selected.diagnostics,
    })
}

/// Load one immutable Installed YAML Data snapshot, generating missing Local Ignore when needed.
///
/// Main and game candidates use the same config-owned selector as inspection. Every selected
/// file is read once, and parsing, validation, identity, and the returned `YamlDataCore` all
/// derive from the exact retained bytes. Existing Local Ignore is never rewritten.
pub fn load_installed_yaml_data(
    request: InstalledYamlDataLoadRequest,
) -> Result<InstalledYamlDataLoadOutcome, InstalledYamlDataLoadError> {
    load_installed_yaml_data_with_env(request, |name| match std::env::var(name) {
        Ok(value) if !value.is_empty() => Some(value),
        _ => None,
    })
}

/// Testable form of [`load_installed_yaml_data`] with injected cache environment lookup.
///
/// The environment callback controls only per-user cache resolution. The installation root
/// remains the sole authority for bundled and Local Ignore paths.
pub fn load_installed_yaml_data_with_env<F>(
    request: InstalledYamlDataLoadRequest,
    env: F,
) -> Result<InstalledYamlDataLoadOutcome, InstalledYamlDataLoadError>
where
    F: Fn(&str) -> Option<String>,
{
    load_installed_yaml_data_with_env_and_io(request, env, &SystemLocalIgnoreFileSystem)
}

/// Shared installed loader implementation with private Local Ignore filesystem injection.
///
/// Main and game selection always uses the production filesystem policy. Only Local Ignore
/// canonical reads and the final no-clobber publication operation are injected for deterministic
/// concurrency and failure-atomicity tests.
fn load_installed_yaml_data_with_env_and_io<F, I>(
    request: InstalledYamlDataLoadRequest,
    env: F,
    local_ignore_io: &I,
) -> Result<InstalledYamlDataLoadOutcome, InstalledYamlDataLoadError>
where
    F: Fn(&str) -> Option<String>,
    I: LocalIgnoreFileSystem,
{
    let mut selected = select_installed_yaml_data(&request.installation_root, request.game, env)
        .map_err(InstalledYamlDataLoadError::from)?;
    let ignore_path = request
        .installation_root
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");
    let (ignore_bytes, local_ignore_state) = match local_ignore_io.read(&ignore_path) {
        Ok(bytes) => (bytes, LocalIgnoreYamlDataState::Existing),
        Err(source) if source.kind() == std::io::ErrorKind::NotFound => {
            let defaults = validated_local_ignore_defaults(&selected, &ignore_path)?;
            let generated =
                publish_local_ignore_if_absent(local_ignore_io, &ignore_path, defaults.as_bytes())?;
            let bytes = local_ignore_io.read(&ignore_path).map_err(|source| {
                InstalledYamlDataLoadError::LocalIgnoreRead {
                    path: ignore_path.clone(),
                    source,
                }
            })?;
            if generated {
                selected.diagnostics.push(InstalledYamlDataDiagnostic {
                    role: None,
                    candidate: None,
                    path: Some(ignore_path.clone()),
                    kind: InstalledYamlDataDiagnosticKind::LocalIgnoreGenerated,
                    message: format!(
                        "generated missing Local Ignore YAML Data from selected Main defaults at {}",
                        ignore_path.display()
                    ),
                });
                (bytes, LocalIgnoreYamlDataState::Generated)
            } else {
                (bytes, LocalIgnoreYamlDataState::Existing)
            }
        }
        Err(source) => {
            return Err(InstalledYamlDataLoadError::LocalIgnoreRead {
                path: ignore_path,
                source,
            });
        }
    };
    let local_ignore = OwnedLocalIgnoreYamlData {
        identity: YamlDataContentIdentity::from_bytes(&ignore_bytes),
        bytes: ignore_bytes.into_boxed_slice(),
    };
    let ignore_content = std::str::from_utf8(&local_ignore.bytes).map_err(|source| {
        InstalledYamlDataLoadError::LocalIgnoreInvalidUtf8 {
            path: ignore_path.clone(),
            source,
        }
    })?;
    let ignore_yaml =
        parse_and_merge_yaml_content("Local Ignore YAML", "Local Ignore YAML", ignore_content)
            .map_err(|source| InstalledYamlDataLoadError::LocalIgnoreParse {
                path: ignore_path.clone(),
                message: source.to_string(),
            })?;
    validate_ignore(&ignore_yaml, selected.game_data_role, &ignore_path).map_err(|source| {
        InstalledYamlDataLoadError::LocalIgnoreInvalidRoleData {
            path: ignore_path,
            reason: explicit_validation_reason(source),
        }
    })?;
    // Keep the retained byte buffers tied to the public identities even after parsing.
    debug_assert_eq!(
        selected.main.bytes.len() as u64,
        selected.main.inspected.identity().byte_len()
    );
    debug_assert_eq!(
        selected.game_file.bytes.len() as u64,
        selected.game_file.inspected.identity().byte_len()
    );
    let yaml_data = YamlDataCore::build_from_yaml_documents(
        &selected.main.yaml,
        &selected.game_file.yaml,
        &ignore_yaml,
        game_data_key(selected.game_data_role),
        &request.selected_game_version,
    )
    .map_err(|source| InstalledYamlDataLoadError::InvalidSelectedData {
        message: source.to_string(),
    })?;

    Ok(InstalledYamlDataLoadOutcome::Ready(
        InstalledYamlDataSnapshot {
            yaml_data,
            requested_game: selected.requested_game,
            game_data_role: selected.game_data_role,
            main: selected.main,
            game_file: selected.game_file,
            local_ignore,
            local_ignore_state,
            diagnostics: selected.diagnostics,
        },
    ))
}

/// Extract and strictly validate the Local Ignore template retained in selected Main YAML Data.
///
/// Validation completes before any staging file is created, so malformed defaults cannot leave
/// filesystem artifacts or become visible to a concurrent loader.
fn validated_local_ignore_defaults<'a>(
    selected: &'a SelectedInstalledYamlData,
    ignore_path: &Path,
) -> Result<&'a str, InstalledYamlDataLoadError> {
    let defaults = selected
        .main
        .yaml
        .as_hash()
        .and_then(|main| {
            main.iter().find_map(|(key, value)| {
                (key.as_str() == Some("CLASSIC_Info"))
                    .then_some(value)
                    .and_then(Yaml::as_hash)
            })
        })
        .and_then(|info| {
            info.iter().find_map(|(key, value)| {
                (key.as_str() == Some("default_ignorefile"))
                    .then_some(value)
                    .and_then(Yaml::as_str)
            })
        })
        .filter(|defaults| !defaults.trim().is_empty())
        .ok_or_else(|| InstalledYamlDataLoadError::LocalIgnoreDefaultInvalid {
            path: ignore_path.to_path_buf(),
            reason: "required `CLASSIC_Info.default_ignorefile` non-empty string is missing or malformed"
                .to_string(),
        })?;
    let yaml = parse_and_merge_yaml_content(
        "selected Main Local Ignore default",
        "Selected Main Local Ignore Default",
        defaults,
    )
    .map_err(
        |source| InstalledYamlDataLoadError::LocalIgnoreDefaultInvalid {
            path: ignore_path.to_path_buf(),
            reason: source.to_string(),
        },
    )?;
    validate_ignore(&yaml, selected.game_data_role, ignore_path).map_err(|source| {
        InstalledYamlDataLoadError::LocalIgnoreDefaultInvalid {
            path: ignore_path.to_path_buf(),
            reason: explicit_validation_reason(source),
        }
    })?;
    Ok(defaults)
}

/// Stage complete bytes beside `path`, then atomically publish them only if `path` is absent.
///
/// A hard link makes the fully synced staged inode visible at the canonical path in one
/// no-clobber filesystem operation. `Ok(false)` means a concurrent creator won; callers must
/// reread the canonical path and treat that winner as authoritative.
fn publish_local_ignore_if_absent<I>(
    local_ignore_io: &I,
    path: &Path,
    content: &[u8],
) -> Result<bool, InstalledYamlDataLoadError>
where
    I: LocalIgnoreFileSystem,
{
    let parent = path
        .parent()
        .ok_or_else(|| InstalledYamlDataLoadError::LocalIgnoreCreate {
            path: path.to_path_buf(),
            source: std::io::Error::new(
                std::io::ErrorKind::InvalidInput,
                "Local Ignore path has no parent directory",
            ),
        })?;
    let mut staged = NamedTempFile::new_in(parent).map_err(|source| {
        InstalledYamlDataLoadError::LocalIgnoreCreate {
            path: path.to_path_buf(),
            source,
        }
    })?;
    staged
        .write_all(content)
        .map_err(|source| InstalledYamlDataLoadError::LocalIgnoreCreate {
            path: path.to_path_buf(),
            source,
        })?;
    staged.as_file().sync_all().map_err(|source| {
        InstalledYamlDataLoadError::LocalIgnoreCreate {
            path: path.to_path_buf(),
            source,
        }
    })?;
    local_ignore_io
        .publish_staged_noclobber(staged.path(), path)
        .map_err(|source| InstalledYamlDataLoadError::LocalIgnoreCreate {
            path: path.to_path_buf(),
            source,
        })
}

impl From<InstalledYamlDataInspectionError> for InstalledYamlDataLoadError {
    fn from(source: InstalledYamlDataInspectionError) -> Self {
        match source {
            InstalledYamlDataInspectionError::UnsupportedGame { game } => {
                Self::UnsupportedGame { game }
            }
            InstalledYamlDataInspectionError::NoUsableSource { role, diagnostics } => {
                Self::NoUsableSource { role, diagnostics }
            }
        }
    }
}

/// Selects Main and game YAML Data independently from updated and bundled candidates.
///
/// The environment callback is used only to resolve the shared cache directory. Cache
/// failures and rejected candidates become diagnostics while bundled candidates remain
/// eligible; this selector does not read or validate the installation's Local Ignore file.
fn select_installed_yaml_data<F>(
    installation_root: &Path,
    game: GameId,
    env: F,
) -> Result<SelectedInstalledYamlData, InstalledYamlDataInspectionError>
where
    F: Fn(&str) -> Option<String>,
{
    let game_data_role = registered_game_data_role(game)
        .ok_or(InstalledYamlDataInspectionError::UnsupportedGame { game })?;
    let bundled_dir = installation_root.join("CLASSIC Data").join("databases");
    let mut diagnostics = Vec::new();
    let cache_dir = match yaml_cache_dir_with_env(env) {
        Ok(path) => Some(path),
        Err(source) => {
            diagnostics.push(InstalledYamlDataDiagnostic {
                role: None,
                candidate: None,
                path: None,
                kind: InstalledYamlDataDiagnosticKind::CacheUnavailable,
                message: format!(
                    "updated YAML Data cache is unavailable: {source}; bundled candidates remain eligible"
                ),
            });
            None
        }
    };

    let main = select_file(
        InstalledYamlDataRole::Main,
        "CLASSIC Main.yaml",
        client_schemas::MAIN_YAML,
        cache_dir.as_deref(),
        &bundled_dir,
        &mut diagnostics,
    )?;
    let game_file = select_file(
        InstalledYamlDataRole::Game,
        game_file_name(game_data_role),
        client_schemas::GAME_FALLOUT4_YAML,
        cache_dir.as_deref(),
        &bundled_dir,
        &mut diagnostics,
    )?;

    Ok(SelectedInstalledYamlData {
        requested_game: game,
        game_data_role,
        main,
        game_file,
        diagnostics,
    })
}

const fn game_file_name(role: GameDataRole) -> &'static str {
    match role {
        GameDataRole::Fallout4 => "CLASSIC Fallout4.yaml",
    }
}

/// Select one installed role using canonical, absent-only previous, then bundled precedence.
///
/// Rejected candidates are appended to `diagnostics`; the function never mutates a candidate.
fn select_file(
    role: InstalledYamlDataRole,
    file_name: &str,
    accepted: SchemaCompat,
    cache_dir: Option<&Path>,
    bundled_dir: &Path,
    diagnostics: &mut Vec<InstalledYamlDataDiagnostic>,
) -> Result<OwnedInstalledYamlDataFile, InstalledYamlDataInspectionError> {
    if let Some(cache_dir) = cache_dir {
        let canonical = cache_dir.join(file_name);
        match inspect_candidate(
            role,
            InstalledYamlDataProvenance::Updated,
            &canonical,
            accepted,
        ) {
            CandidateAttempt::Selected(selected) => return Ok(selected),
            CandidateAttempt::Missing => {
                let previous = cache_dir.join(format!("{file_name}.prev"));
                match inspect_candidate(
                    role,
                    InstalledYamlDataProvenance::Previous,
                    &previous,
                    accepted,
                ) {
                    CandidateAttempt::Selected(selected) => return Ok(selected),
                    CandidateAttempt::Rejected(diagnostic) => diagnostics.push(diagnostic),
                    CandidateAttempt::Missing => {}
                }
            }
            CandidateAttempt::Rejected(diagnostic) => diagnostics.push(diagnostic),
        }
    }

    let bundled = bundled_dir.join(file_name);
    match inspect_candidate(
        role,
        InstalledYamlDataProvenance::Bundled,
        &bundled,
        accepted,
    ) {
        CandidateAttempt::Selected(selected) => Ok(selected),
        CandidateAttempt::Rejected(diagnostic) => {
            diagnostics.push(diagnostic);
            Err(InstalledYamlDataInspectionError::NoUsableSource {
                role,
                diagnostics: diagnostics.clone(),
            })
        }
        CandidateAttempt::Missing => {
            diagnostics.push(candidate_diagnostic(
                role,
                InstalledYamlDataProvenance::Bundled,
                &bundled,
                InstalledYamlDataDiagnosticKind::Missing,
                "bundled YAML Data candidate is missing",
            ));
            Err(InstalledYamlDataInspectionError::NoUsableSource {
                role,
                diagnostics: diagnostics.clone(),
            })
        }
    }
}

enum CandidateAttempt {
    Selected(OwnedInstalledYamlDataFile),
    Missing,
    Rejected(InstalledYamlDataDiagnostic),
}

/// Read, parse, schema-gate, semantically validate, and identify one exact candidate.
///
/// `Missing` is reserved for `NotFound`; every other failure retains structured attribution.
fn inspect_candidate(
    role: InstalledYamlDataRole,
    provenance: InstalledYamlDataProvenance,
    path: &Path,
    accepted: SchemaCompat,
) -> CandidateAttempt {
    let bytes = match std::fs::read(path) {
        Ok(bytes) => bytes,
        Err(source) if source.kind() == std::io::ErrorKind::NotFound => {
            return CandidateAttempt::Missing;
        }
        Err(source) => {
            return CandidateAttempt::Rejected(candidate_diagnostic(
                role,
                provenance,
                path,
                InstalledYamlDataDiagnosticKind::Read,
                format!("failed to read candidate: {source}"),
            ));
        }
    };
    let content = match std::str::from_utf8(&bytes) {
        Ok(content) => content,
        Err(source) => {
            return CandidateAttempt::Rejected(candidate_diagnostic(
                role,
                provenance,
                path,
                InstalledYamlDataDiagnosticKind::InvalidUtf8,
                format!("candidate is not UTF-8: {source}"),
            ));
        }
    };
    let yaml = match parse_candidate(role, provenance, path, content) {
        Ok(yaml) => yaml,
        Err(diagnostic) => return CandidateAttempt::Rejected(diagnostic),
    };
    let schema_version = match extract_schema_version(&yaml) {
        Ok(version) => version,
        Err(source) => {
            return CandidateAttempt::Rejected(candidate_diagnostic(
                role,
                provenance,
                path,
                InstalledYamlDataDiagnosticKind::InvalidSchema,
                format!("candidate schema version is invalid: {source}"),
            ));
        }
    };
    if let incompatible @ (Compatibility::IncompatibleMajor { .. }
    | Compatibility::IncompatibleMinor { .. }) = schema_compat_check(&schema_version, &accepted)
    {
        return CandidateAttempt::Rejected(candidate_diagnostic(
            role,
            provenance,
            path,
            InstalledYamlDataDiagnosticKind::IncompatibleSchema,
            format!("candidate schema version {schema_version} is incompatible: {incompatible:?}"),
        ));
    }
    if let Err(source) = validate_candidate_role(role, &yaml, path) {
        return CandidateAttempt::Rejected(candidate_diagnostic(
            role,
            provenance,
            path,
            InstalledYamlDataDiagnosticKind::InvalidRoleData,
            source,
        ));
    }

    CandidateAttempt::Selected(OwnedInstalledYamlDataFile {
        inspected: InspectedYamlDataFile {
            role,
            provenance,
            schema_version,
            identity: YamlDataContentIdentity::from_bytes(&bytes),
        },
        bytes: bytes.into_boxed_slice(),
        yaml,
    })
}

/// Parse one candidate as the mergeable YAML stream required by its installed role.
fn parse_candidate(
    role: InstalledYamlDataRole,
    provenance: InstalledYamlDataProvenance,
    path: &Path,
    content: &str,
) -> Result<Yaml, InstalledYamlDataDiagnostic> {
    let (parse_label, empty_label) = match role {
        InstalledYamlDataRole::Main => ("installed Main YAML", "Installed Main YAML"),
        InstalledYamlDataRole::Game => ("installed game YAML", "Installed game YAML"),
    };
    parse_and_merge_yaml_content(parse_label, empty_label, content).map_err(|source| {
        candidate_diagnostic(
            role,
            provenance,
            path,
            InstalledYamlDataDiagnosticKind::Parse,
            format!("failed to parse candidate: {source}"),
        )
    })
}

/// Apply the strict explicit-loader semantic validator for an installed role.
fn validate_candidate_role(
    role: InstalledYamlDataRole,
    yaml: &Yaml,
    path: &Path,
) -> Result<(), String> {
    let result = match role {
        InstalledYamlDataRole::Main => validate_main(yaml, path),
        InstalledYamlDataRole::Game => validate_game(yaml, path),
    };
    result.map_err(explicit_validation_reason)
}

fn explicit_validation_reason(source: ExplicitYamlDataLoadError) -> String {
    match source {
        ExplicitYamlDataLoadError::InvalidRoleData { reason, .. } => reason,
        other => other.to_string(),
    }
}

/// Build one path-attributed rejection diagnostic without changing the rejected file.
fn candidate_diagnostic(
    role: InstalledYamlDataRole,
    candidate: InstalledYamlDataProvenance,
    path: &Path,
    kind: InstalledYamlDataDiagnosticKind,
    message: impl Into<String>,
) -> InstalledYamlDataDiagnostic {
    InstalledYamlDataDiagnostic {
        role: Some(role),
        candidate: Some(candidate),
        path: Some(path.to_path_buf()),
        kind,
        message: message.into(),
    }
}

#[cfg(test)]
#[path = "installed_yaml_data_tests.rs"]
mod tests;
