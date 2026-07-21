//! Installed YAML Data selection and side-effect-limited inspection.

use crate::client_schemas;
use crate::explicit_yaml_data::{
    ExplicitYamlDataLoadError, GameDataRole, YamlDataContentIdentity, game_data_key,
    registered_game_data_role, validate_game, validate_ignore, validate_main,
};
use crate::yamldata::{YamlDataCore, parse_and_merge_yaml_content};
use classic_path_core::yaml_cache_dir_with_env;
use classic_settings_core::{
    Compatibility, SchemaCompat, SchemaVersion, YamlOperations, extract_schema_version,
    schema_compat_check,
};
use classic_shared_core::GameId;
use fs4::fs_std::FileExt;
use std::fs::{File, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};
use tempfile::NamedTempFile;
use thiserror::Error;
use yaml_rust2::Yaml;

static LOCAL_IGNORE_BACKUP_SEQUENCE: AtomicU64 = AtomicU64::new(0);

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
    /// Candidate or Local Ignore bytes were not valid UTF-8.
    InvalidUtf8,
    /// Candidate or Local Ignore text was not valid YAML Data.
    Parse,
    /// A parsed candidate omitted or malformed its schema version.
    InvalidSchema,
    /// A candidate schema was outside the client-owned compatibility range.
    IncompatibleSchema,
    /// A candidate or Local Ignore document failed role-specific semantic validation.
    InvalidRoleData,
    /// Missing Local Ignore YAML Data was generated from selected Main defaults.
    LocalIgnoreGenerated,
    /// Malformed Local Ignore YAML Data was reset from retained selected-Main defaults.
    LocalIgnoreReset,
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
    /// Malformed Local Ignore bytes were retained but ignored for this operation only.
    ProceedWithoutIgnore,
    /// Malformed Local Ignore bytes were backed up and reset from retained defaults.
    ResetToDefault,
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

#[derive(Debug, Clone)]
struct OwnedInstalledYamlDataFile {
    bytes: Box<[u8]>,
    yaml: Yaml,
    inspected: InspectedYamlDataFile,
}

#[derive(Debug, Clone)]
struct SelectedInstalledYamlData {
    requested_game: GameId,
    game_data_role: GameDataRole,
    main: OwnedInstalledYamlDataFile,
    game_file: OwnedInstalledYamlDataFile,
    diagnostics: Vec<InstalledYamlDataDiagnostic>,
}

#[derive(Debug, Clone)]
struct OwnedLocalIgnoreYamlData {
    bytes: Box<[u8]>,
    identity: YamlDataContentIdentity,
}

enum PreparedLocalIgnoreReset {
    Ready(Box<InstalledYamlDataSnapshot>),
    Unavailable { reason: String },
}

/// Private filesystem seam for deterministic Local Ignore publication and reread tests.
///
/// Production uses [`SystemLocalIgnoreFileSystem`]. Keeping this seam private prevents callers
/// from replacing config-owned generation policy while allowing failure atomicity and races to
/// be driven at the complete loader boundary.
trait LocalIgnoreFileSystem {
    /// Read the canonical Local Ignore path.
    fn read(&self, path: &Path) -> std::io::Result<Vec<u8>>;

    /// Atomically move one fully synced staged file into an absent canonical path.
    fn publish_staged_noclobber(&self, staged_path: &Path, path: &Path) -> std::io::Result<bool>;
}

/// Production Local Ignore filesystem implementation backed by `std::fs`.
struct SystemLocalIgnoreFileSystem;

impl LocalIgnoreFileSystem for SystemLocalIgnoreFileSystem {
    fn read(&self, path: &Path) -> std::io::Result<Vec<u8>> {
        std::fs::read(path)
    }

    fn publish_staged_noclobber(&self, staged_path: &Path, path: &Path) -> std::io::Result<bool> {
        // Local Ignore may live on FAT or network volumes where hard links are unavailable;
        // atomicwrites maps this to a no-replace, write-through move on Windows.
        match atomicwrites::move_atomic(staged_path, path) {
            Ok(()) => Ok(true),
            Err(source) if source.kind() == std::io::ErrorKind::AlreadyExists => Ok(false),
            Err(source) => Err(source),
        }
    }
}

/// Private durable-publication seam for Local Ignore reset fault and race tests.
trait LocalIgnoreResetPublisher {
    /// Durably publish the byte-exact backup without replacing an existing backup identity.
    fn publish_backup(&self, path: &Path, bytes: &[u8]) -> Result<(), LocalIgnoreResetError>;

    /// Stage replacement bytes, recheck the canonical bytes, then atomically replace on match.
    fn replace_if_unchanged(
        &self,
        path: &Path,
        expected: &[u8],
        replacement: &[u8],
    ) -> Result<ConditionalReplacement, LocalIgnoreResetError>;
}

/// Result of the conflict check immediately adjacent to atomic replacement.
enum ConditionalReplacement {
    Replaced,
    Conflict(Option<YamlDataContentIdentity>),
}

/// Which durable publication in the reset transaction is being staged.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum LocalIgnoreResetPublicationKind {
    Backup,
    Replacement,
}

/// Production reset publisher using fully synchronized same-directory staging files.
struct SystemLocalIgnoreResetPublisher {
    fail_at: Option<(
        LocalIgnoreResetPublicationKind,
        LocalIgnoreResetPublicationStage,
    )>,
}

impl SystemLocalIgnoreResetPublisher {
    /// Build the production publisher without fault injection.
    const fn system() -> Self {
        Self { fail_at: None }
    }

    /// Build a publisher that fails immediately before one real publication boundary.
    #[cfg(test)]
    const fn failing_at(
        kind: LocalIgnoreResetPublicationKind,
        stage: LocalIgnoreResetPublicationStage,
    ) -> Self {
        Self {
            fail_at: Some((kind, stage)),
        }
    }

    /// Return an injected I/O failure before the requested boundary mutates state.
    fn before(
        &self,
        kind: LocalIgnoreResetPublicationKind,
        stage: LocalIgnoreResetPublicationStage,
    ) -> Result<(), ResetPublicationFailure> {
        if self.fail_at == Some((kind, stage)) {
            return Err(ResetPublicationFailure {
                stage,
                source: std::io::Error::new(
                    std::io::ErrorKind::PermissionDenied,
                    format!("injected {kind:?} {stage:?} failure"),
                ),
            });
        }
        Ok(())
    }
}

impl LocalIgnoreResetPublisher for SystemLocalIgnoreResetPublisher {
    fn publish_backup(&self, path: &Path, bytes: &[u8]) -> Result<(), LocalIgnoreResetError> {
        publish_local_ignore_reset_backup(self, path, bytes).map_err(|failure| {
            LocalIgnoreResetError::BackupPublication {
                path: path.to_path_buf(),
                stage: failure.stage,
                source: failure.source,
            }
        })
    }

    fn replace_if_unchanged(
        &self,
        path: &Path,
        expected: &[u8],
        replacement: &[u8],
    ) -> Result<ConditionalReplacement, LocalIgnoreResetError> {
        let staged = stage_local_ignore_reset_bytes(
            self,
            LocalIgnoreResetPublicationKind::Replacement,
            path,
            replacement,
        )
        .map_err(|failure| LocalIgnoreResetError::ReplacementPublication {
            path: path.to_path_buf(),
            stage: failure.stage,
            source: failure.source,
        })?;
        let current = match std::fs::read(path) {
            Ok(bytes) => bytes,
            Err(source) if source.kind() == std::io::ErrorKind::NotFound => {
                return Ok(ConditionalReplacement::Conflict(None));
            }
            Err(source) => {
                return Err(LocalIgnoreResetError::Read {
                    path: path.to_path_buf(),
                    source,
                });
            }
        };
        if current != expected {
            return Ok(ConditionalReplacement::Conflict(Some(
                YamlDataContentIdentity::from_bytes(&current),
            )));
        }

        self.before(
            LocalIgnoreResetPublicationKind::Replacement,
            LocalIgnoreResetPublicationStage::Publish,
        )
        .map_err(|failure| LocalIgnoreResetError::ReplacementPublication {
            path: path.to_path_buf(),
            stage: failure.stage,
            source: failure.source,
        })?;
        staged
            .persist(path)
            .map_err(|failure| LocalIgnoreResetError::ReplacementPublication {
                path: path.to_path_buf(),
                stage: LocalIgnoreResetPublicationStage::Publish,
                source: failure.error,
            })?;
        if let Some(parent) = path.parent() {
            sync_replacement_parent_best_effort(parent);
        }
        Ok(ConditionalReplacement::Replaced)
    }
}

/// Stage-specific internal filesystem failure used by both reset publications.
struct ResetPublicationFailure {
    stage: LocalIgnoreResetPublicationStage,
    source: std::io::Error,
}

/// Write, flush, and synchronize a same-directory staging file without publishing it.
fn stage_local_ignore_reset_bytes(
    publisher: &SystemLocalIgnoreResetPublisher,
    kind: LocalIgnoreResetPublicationKind,
    path: &Path,
    bytes: &[u8],
) -> Result<NamedTempFile, ResetPublicationFailure> {
    let parent = path.parent().ok_or_else(|| ResetPublicationFailure {
        stage: LocalIgnoreResetPublicationStage::Create,
        source: std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            "Local Ignore publication path has no parent directory",
        ),
    })?;
    publisher.before(kind, LocalIgnoreResetPublicationStage::Create)?;
    let mut staged = tempfile::Builder::new()
        .prefix(".classic-local-ignore-reset-")
        .suffix(".tmp")
        .tempfile_in(parent)
        .map_err(|source| ResetPublicationFailure {
            stage: LocalIgnoreResetPublicationStage::Create,
            source,
        })?;
    publisher.before(kind, LocalIgnoreResetPublicationStage::Write)?;
    staged
        .write_all(bytes)
        .map_err(|source| ResetPublicationFailure {
            stage: LocalIgnoreResetPublicationStage::Write,
            source,
        })?;
    publisher.before(kind, LocalIgnoreResetPublicationStage::Flush)?;
    staged.flush().map_err(|source| ResetPublicationFailure {
        stage: LocalIgnoreResetPublicationStage::Flush,
        source,
    })?;
    publisher.before(kind, LocalIgnoreResetPublicationStage::Sync)?;
    staged
        .as_file()
        .sync_all()
        .map_err(|source| ResetPublicationFailure {
            stage: LocalIgnoreResetPublicationStage::Sync,
            source,
        })?;
    Ok(staged)
}

/// Durably publish complete backup bytes to one uniquely owned final path.
fn publish_local_ignore_reset_backup(
    publisher: &SystemLocalIgnoreResetPublisher,
    path: &Path,
    bytes: &[u8],
) -> Result<(), ResetPublicationFailure> {
    let staged = stage_local_ignore_reset_bytes(
        publisher,
        LocalIgnoreResetPublicationKind::Backup,
        path,
        bytes,
    )?;
    publisher.before(
        LocalIgnoreResetPublicationKind::Backup,
        LocalIgnoreResetPublicationStage::Publish,
    )?;
    let (staged_file, staged_path) = staged.keep().map_err(|failure| ResetPublicationFailure {
        stage: LocalIgnoreResetPublicationStage::Publish,
        source: failure.error,
    })?;
    drop(staged_file);
    if let Err(source) = atomicwrites::move_atomic(&staged_path, path) {
        // `keep` must clear Windows' temporary attribute before a write-through move; remove the
        // now caller-owned staging path best-effort when that final move fails.
        let _ = std::fs::remove_file(&staged_path);
        return Err(ResetPublicationFailure {
            stage: LocalIgnoreResetPublicationStage::Publish,
            source,
        });
    }
    Ok(())
}

/// Best-effort directory synchronization after canonical replacement is already authoritative.
#[cfg(unix)]
fn sync_replacement_parent_best_effort(parent: &Path) {
    // A post-replacement sync failure cannot be reported without falsely claiming the prior
    // canonical file remains authoritative, so replacement metadata durability is best-effort.
    if let Ok(directory) = std::fs::File::open(parent) {
        let _ = directory.sync_all();
    }
}

/// Windows journals same-directory replacement metadata; std has no directory fsync handle.
#[cfg(not(unix))]
fn sync_replacement_parent_best_effort(_parent: &Path) {}

/// Immutable parsed Installed YAML Data backed by the exact selected file bytes.
pub struct InstalledYamlDataSnapshot {
    yaml_data: YamlDataCore,
    simplify_remove_list: Vec<String>,
    requested_game: GameId,
    game_data_role: GameDataRole,
    main: OwnedInstalledYamlDataFile,
    game_file: OwnedInstalledYamlDataFile,
    local_ignore: OwnedLocalIgnoreYamlData,
    local_ignore_state: LocalIgnoreYamlDataState,
    diagnostics: Vec<InstalledYamlDataDiagnostic>,
}

/// Immutable recovery proposal for malformed existing Local Ignore YAML Data.
///
/// The plan owns the already selected Main and game snapshot, the exact malformed bytes,
/// and the selected-Main default state. Accepting a decision never reselects files.
pub struct LocalIgnoreRecoveryPlan {
    proceed_without_ignore_snapshot: InstalledYamlDataSnapshot,
    local_ignore_path: PathBuf,
    backup_directory: PathBuf,
    reset: PreparedLocalIgnoreReset,
    selected_game_version: String,
}

/// Typed result of attempting to reset malformed Local Ignore YAML Data.
#[derive(Debug)]
pub enum LocalIgnoreResetOutcome {
    /// The malformed bytes were durably backed up and retained defaults became authoritative.
    Reset(LocalIgnoreResetResult),
    /// The canonical file no longer matched the identity retained by the recovery plan.
    Conflict(LocalIgnoreResetConflict),
}

/// Identity mismatch that prevented a Local Ignore reset from overwriting newer state.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LocalIgnoreResetConflict {
    expected_identity: YamlDataContentIdentity,
    actual_identity: Option<YamlDataContentIdentity>,
    backup_path: Option<PathBuf>,
}

impl LocalIgnoreResetConflict {
    /// Return the malformed-file identity against which the caller approved reset.
    #[must_use]
    pub const fn expected_identity(&self) -> &YamlDataContentIdentity {
        &self.expected_identity
    }

    /// Return the current canonical identity, or `None` when the file was removed.
    #[must_use]
    pub const fn actual_identity(&self) -> Option<&YamlDataContentIdentity> {
        self.actual_identity.as_ref()
    }

    /// Return the verified backup retained before a late conflict, when one was published.
    #[must_use]
    pub fn backup_path(&self) -> Option<&Path> {
        self.backup_path.as_deref()
    }
}

/// Successful durable Local Ignore reset and the retained operation snapshot it completed.
#[derive(Debug)]
pub struct LocalIgnoreResetResult {
    snapshot: Box<InstalledYamlDataSnapshot>,
    local_ignore_path: PathBuf,
    backup_path: PathBuf,
    malformed_local_ignore_identity: YamlDataContentIdentity,
    backup_identity: YamlDataContentIdentity,
    replacement_identity: YamlDataContentIdentity,
}

impl LocalIgnoreResetResult {
    /// Return the reset-ready snapshot built from the already selected Main and game bytes.
    #[must_use]
    pub const fn snapshot(&self) -> &InstalledYamlDataSnapshot {
        &self.snapshot
    }

    /// Consume the reset result and return its retained Installed YAML Data snapshot.
    #[must_use]
    pub fn into_snapshot(self) -> InstalledYamlDataSnapshot {
        *self.snapshot
    }

    /// Return the canonical Local Ignore path that was reset.
    #[must_use]
    pub fn local_ignore_path(&self) -> &Path {
        &self.local_ignore_path
    }

    /// Return the durable byte-exact backup path verified before replacement.
    #[must_use]
    pub fn backup_path(&self) -> &Path {
        &self.backup_path
    }

    /// Return the malformed identity observed when the recovery plan was created.
    #[must_use]
    pub const fn malformed_local_ignore_identity(&self) -> &YamlDataContentIdentity {
        &self.malformed_local_ignore_identity
    }

    /// Return the identity independently verified from the durable backup bytes.
    #[must_use]
    pub const fn backup_identity(&self) -> &YamlDataContentIdentity {
        &self.backup_identity
    }

    /// Return the identity of the retained defaults published as the replacement.
    #[must_use]
    pub const fn replacement_identity(&self) -> &YamlDataContentIdentity {
        &self.replacement_identity
    }

    /// Return selection, malformed-file, and successful-reset diagnostics.
    #[must_use]
    pub fn diagnostics(&self) -> &[InstalledYamlDataDiagnostic] {
        self.snapshot.diagnostics()
    }
}

/// Durable publication stage attributed by a Local Ignore reset failure.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LocalIgnoreResetPublicationStage {
    /// A same-directory staging file could not be created.
    Create,
    /// Complete bytes could not be written to the staging file.
    Write,
    /// Buffered staging bytes could not be flushed.
    Flush,
    /// Staging bytes could not be synchronized to durable storage.
    Sync,
    /// The fully synchronized staging file could not be atomically or durably published.
    Publish,
}

/// Operational failure encountered before a Local Ignore reset became authoritative.
#[derive(Debug, Error)]
pub enum LocalIgnoreResetError {
    /// The selected Main defaults retained by the plan were unusable.
    #[error("retained selected Main defaults cannot reset Local Ignore YAML Data `{}`: {reason}", path.display())]
    DefaultsUnavailable {
        /// Canonical Local Ignore path that would have been reset.
        path: PathBuf,
        /// Stable validation detail captured when the recovery plan was created.
        reason: String,
    },
    /// The canonical Local Ignore file could not be opened and locked for the critical section.
    #[error("failed to lock Local Ignore YAML Data `{}` for reset: {source}", path.display())]
    Lock {
        /// Canonical Local Ignore path.
        path: PathBuf,
        /// Underlying filesystem failure.
        #[source]
        source: std::io::Error,
    },
    /// The authoritative Local Ignore bytes could not be read during conflict protection.
    #[error("failed to read Local Ignore YAML Data `{}` during reset: {source}", path.display())]
    Read {
        /// Canonical Local Ignore path.
        path: PathBuf,
        /// Underlying filesystem failure.
        #[source]
        source: std::io::Error,
    },
    /// The config-owned Local Ignore backup directory could not be created.
    #[error("failed to create Local Ignore backup directory `{}`: {source}", path.display())]
    BackupDirectory {
        /// Backup directory that could not be prepared.
        path: PathBuf,
        /// Underlying filesystem failure.
        #[source]
        source: std::io::Error,
    },
    /// The byte-exact backup could not be durably published.
    #[error("failed to publish Local Ignore backup `{}` at {stage:?}: {source}", path.display())]
    BackupPublication {
        /// Intended durable backup path.
        path: PathBuf,
        /// Publication boundary that failed.
        stage: LocalIgnoreResetPublicationStage,
        /// Underlying filesystem failure.
        #[source]
        source: std::io::Error,
    },
    /// The published backup could not be reread or did not match the retained malformed bytes.
    #[error("failed to verify Local Ignore backup `{}`: {reason}", path.display())]
    BackupVerification {
        /// Published backup path.
        path: PathBuf,
        /// Stable verification detail.
        reason: String,
    },
    /// Retained defaults could not be atomically published at the canonical path.
    #[error("failed to publish Local Ignore replacement `{}` at {stage:?}: {source}", path.display())]
    ReplacementPublication {
        /// Canonical Local Ignore path.
        path: PathBuf,
        /// Publication boundary that failed.
        stage: LocalIgnoreResetPublicationStage,
        /// Underlying filesystem failure.
        #[source]
        source: std::io::Error,
    },
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

    /// Return simplify-log removal entries parsed from the retained selected Main bytes.
    ///
    /// Keeping this data on the snapshot lets operation consumers preserve simplify behavior
    /// without reopening a mutable installed Main path after selection.
    #[must_use]
    pub fn simplify_remove_list(&self) -> &[String] {
        &self.simplify_remove_list
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
    ///
    /// For [`LocalIgnoreYamlDataState::ProceedWithoutIgnore`], this identifies the malformed
    /// installed bytes retained for recovery attribution; the current operation uses no entries.
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

// A custom formatter keeps retained malformed/default bytes and parsed YAML documents private.
impl std::fmt::Debug for LocalIgnoreRecoveryPlan {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter
            .debug_struct("LocalIgnoreRecoveryPlan")
            .field("game", &self.proceed_without_ignore_snapshot.game())
            .field("main", &self.proceed_without_ignore_snapshot.main())
            .field(
                "game_file",
                &self.proceed_without_ignore_snapshot.game_file(),
            )
            .field("local_ignore_path", &self.local_ignore_path)
            .field(
                "malformed_local_ignore_identity",
                &self.proceed_without_ignore_snapshot.local_ignore_identity(),
            )
            .field(
                "default_local_ignore_identity",
                &self.default_local_ignore_identity(),
            )
            .field(
                "default_local_ignore_unavailable_reason",
                &match &self.reset {
                    PreparedLocalIgnoreReset::Ready(_) => None,
                    PreparedLocalIgnoreReset::Unavailable { reason } => Some(reason),
                },
            )
            .field("selected_game_version", &self.selected_game_version)
            .field(
                "diagnostics",
                &self.proceed_without_ignore_snapshot.diagnostics(),
            )
            .finish_non_exhaustive()
    }
}

impl LocalIgnoreRecoveryPlan {
    /// Borrows the retained Proceed Without Ignore snapshot for workspace-owned preparation.
    ///
    /// This hidden seam lets the Crash Log Scan coordinator prepare intake before presenting
    /// recovery without transferring, cloning, or serializing the retained snapshot. Callers
    /// still must consume this plan through [`Self::proceed_without_ignore`] before analysis.
    #[doc(hidden)]
    #[must_use]
    pub fn snapshot_for_scan_preparation(&self) -> &InstalledYamlDataSnapshot {
        &self.proceed_without_ignore_snapshot
    }

    /// Return the typed game retained by the already selected snapshot.
    #[must_use]
    pub const fn game(&self) -> GameId {
        self.proceed_without_ignore_snapshot.game()
    }

    /// Return the registered game-data role retained by the already selected snapshot.
    #[must_use]
    pub const fn game_data_role(&self) -> GameDataRole {
        self.proceed_without_ignore_snapshot.game_data_role()
    }

    /// Return the retained independently selected Main file facts.
    #[must_use]
    pub const fn main(&self) -> &InspectedYamlDataFile {
        self.proceed_without_ignore_snapshot.main()
    }

    /// Return the retained independently selected game file facts.
    #[must_use]
    pub const fn game_file(&self) -> &InspectedYamlDataFile {
        self.proceed_without_ignore_snapshot.game_file()
    }

    /// Return the canonical malformed Local Ignore path observed by this plan.
    #[must_use]
    pub fn local_ignore_path(&self) -> &Path {
        &self.local_ignore_path
    }

    /// Return the identity of the exact malformed Local Ignore bytes observed by this plan.
    #[must_use]
    pub const fn malformed_local_ignore_identity(&self) -> &YamlDataContentIdentity {
        self.proceed_without_ignore_snapshot.local_ignore_identity()
    }

    /// Return the identity of validated selected-Main defaults retained for recovery, if usable.
    ///
    /// Invalid or unavailable defaults do not prevent Proceed Without Ignore because that
    /// decision does not read or publish them.
    #[must_use]
    pub fn default_local_ignore_identity(&self) -> Option<&YamlDataContentIdentity> {
        match &self.reset {
            PreparedLocalIgnoreReset::Ready(snapshot) => Some(snapshot.local_ignore_identity()),
            PreparedLocalIgnoreReset::Unavailable { .. } => None,
        }
    }

    /// Return the retained Version Registry selection mode for the interrupted operation.
    #[must_use]
    pub fn selected_game_version(&self) -> &str {
        &self.selected_game_version
    }

    /// Return retained selection and malformed Local Ignore diagnostics.
    #[must_use]
    pub fn diagnostics(&self) -> &[InstalledYamlDataDiagnostic] {
        self.proceed_without_ignore_snapshot.diagnostics()
    }

    /// Complete the retained operation with no Local Ignore entries and no filesystem writes.
    ///
    /// The returned snapshot owns the same selected Main/game bytes and malformed-file identity
    /// captured when recovery became necessary. The empty ignore list applies only to this
    /// snapshot; a later installed load will encounter the malformed file again.
    #[must_use]
    pub fn proceed_without_ignore(self) -> InstalledYamlDataSnapshot {
        self.proceed_without_ignore_snapshot
    }

    /// Durably back up malformed bytes and atomically publish retained selected-Main defaults.
    ///
    /// This synchronous call is the reset's explicit non-interruptible critical section. A scan
    /// coordinator checks cancellation immediately before entering; once called, reset never
    /// polls cancellation or yields until it has either preserved the original as authoritative
    /// or completed the verified backup and atomic replacement. The selected Main, game, and
    /// replacement bytes all come from this plan and are never reselected.
    ///
    /// # Errors
    ///
    /// Returns a stage-specific [`LocalIgnoreResetError`] before replacement becomes
    /// authoritative. A typed [`LocalIgnoreResetOutcome::Conflict`] means the malformed file was
    /// changed or removed after this plan was created and was not overwritten.
    pub fn reset_to_default(self) -> Result<LocalIgnoreResetOutcome, LocalIgnoreResetError> {
        self.reset_to_default_with_publisher(&SystemLocalIgnoreResetPublisher::system())
    }

    /// Runs reset through an injected durable-publication boundary for fault and race tests.
    fn reset_to_default_with_publisher(
        self,
        publisher: &impl LocalIgnoreResetPublisher,
    ) -> Result<LocalIgnoreResetOutcome, LocalIgnoreResetError> {
        let Self {
            proceed_without_ignore_snapshot,
            local_ignore_path,
            backup_directory,
            reset,
            selected_game_version: _,
        } = self;
        let expected_bytes = proceed_without_ignore_snapshot.local_ignore.bytes;
        let expected_identity = proceed_without_ignore_snapshot.local_ignore.identity;
        let _reset_lock = match acquire_local_ignore_reset_lock(&local_ignore_path) {
            Ok(lock) => lock,
            Err(LocalIgnoreResetError::Lock { source, .. })
                if source.kind() == std::io::ErrorKind::NotFound =>
            {
                let current = read_reset_canonical(&local_ignore_path)?;
                return Ok(LocalIgnoreResetOutcome::Conflict(
                    LocalIgnoreResetConflict {
                        expected_identity,
                        actual_identity: current
                            .as_deref()
                            .map(YamlDataContentIdentity::from_bytes),
                        backup_path: None,
                    },
                ));
            }
            Err(error) => return Err(error),
        };
        let current = read_reset_canonical(&local_ignore_path)?;
        if current.as_deref() != Some(expected_bytes.as_ref()) {
            return Ok(LocalIgnoreResetOutcome::Conflict(
                LocalIgnoreResetConflict {
                    expected_identity,
                    actual_identity: current.as_deref().map(YamlDataContentIdentity::from_bytes),
                    backup_path: None,
                },
            ));
        }
        let PreparedLocalIgnoreReset::Ready(mut reset_snapshot) = reset else {
            let PreparedLocalIgnoreReset::Unavailable { reason } = reset else {
                unreachable!("Local Ignore reset preparation has only two states")
            };
            return Err(LocalIgnoreResetError::DefaultsUnavailable {
                path: local_ignore_path,
                reason,
            });
        };

        create_local_ignore_backup_directory(&backup_directory)?;
        let backup_path = unique_local_ignore_backup_path(&backup_directory, &expected_identity);
        publisher.publish_backup(&backup_path, &expected_bytes)?;
        let backup_bytes = std::fs::read(&backup_path).map_err(|source| {
            LocalIgnoreResetError::BackupVerification {
                path: backup_path.clone(),
                reason: source.to_string(),
            }
        })?;
        if backup_bytes != expected_bytes.as_ref() {
            return Err(LocalIgnoreResetError::BackupVerification {
                path: backup_path,
                reason: "published backup bytes differ from the retained malformed bytes"
                    .to_string(),
            });
        }
        let backup_identity = YamlDataContentIdentity::from_bytes(&backup_bytes);

        let replacement_bytes = reset_snapshot.local_ignore.bytes.clone();
        let replacement_identity = reset_snapshot.local_ignore.identity.clone();
        match publisher.replace_if_unchanged(
            &local_ignore_path,
            &expected_bytes,
            &replacement_bytes,
        )? {
            ConditionalReplacement::Replaced => {}
            ConditionalReplacement::Conflict(actual_identity) => {
                return Ok(LocalIgnoreResetOutcome::Conflict(
                    LocalIgnoreResetConflict {
                        expected_identity,
                        actual_identity,
                        backup_path: Some(backup_path),
                    },
                ));
            }
        }

        reset_snapshot.diagnostics.push(InstalledYamlDataDiagnostic {
            role: None,
            candidate: None,
            path: Some(local_ignore_path.clone()),
            kind: InstalledYamlDataDiagnosticKind::LocalIgnoreReset,
            message: format!(
                "reset malformed Local Ignore YAML Data from retained selected Main defaults; byte-exact backup verified at {}",
                backup_path.display()
            ),
        });
        Ok(LocalIgnoreResetOutcome::Reset(LocalIgnoreResetResult {
            snapshot: reset_snapshot,
            local_ignore_path,
            backup_path,
            malformed_local_ignore_identity: expected_identity,
            backup_identity,
            replacement_identity,
        }))
    }
}

/// Build a process-unique backup name while retaining the malformed content identity in its stem.
fn unique_local_ignore_backup_path(
    directory: &Path,
    identity: &YamlDataContentIdentity,
) -> PathBuf {
    let unix_nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    let sequence = LOCAL_IGNORE_BACKUP_SEQUENCE.fetch_add(1, Ordering::Relaxed);
    directory.join(format!(
        "CLASSIC Ignore.yaml.{}.{}-{}-{}.bak",
        identity.sha256_hex(),
        unix_nanos,
        std::process::id(),
        sequence
    ))
}

/// Acquire the config-owned installation lock held across conflict check, backup, and replacement.
fn acquire_local_ignore_reset_lock(path: &Path) -> Result<File, LocalIgnoreResetError> {
    let lock_parent = path
        .parent()
        .and_then(Path::parent)
        .or_else(|| path.parent())
        .unwrap_or_else(|| Path::new("."));
    let lock_path = lock_parent.join(".classic-local-ignore-reset.lock");
    let lock = OpenOptions::new()
        .create(true)
        .read(true)
        .write(true)
        .truncate(false)
        .open(&lock_path)
        .map_err(|source| LocalIgnoreResetError::Lock {
            path: path.to_path_buf(),
            source,
        })?;
    FileExt::lock_exclusive(&lock).map_err(|source| LocalIgnoreResetError::Lock {
        path: path.to_path_buf(),
        source,
    })?;
    Ok(lock)
}

/// Create and durably record the config-owned backup directory hierarchy before publication.
fn create_local_ignore_backup_directory(path: &Path) -> Result<(), LocalIgnoreResetError> {
    std::fs::create_dir_all(path).map_err(|source| LocalIgnoreResetError::BackupDirectory {
        path: path.to_path_buf(),
        source,
    })?;
    sync_local_ignore_backup_directory_chain(path)
}

/// Synchronize each installation-owned directory entry used by the backup path on Unix.
#[cfg(unix)]
fn sync_local_ignore_backup_directory_chain(path: &Path) -> Result<(), LocalIgnoreResetError> {
    // The backup path is `<installation>/CLASSIC Backup/YAML Data/Local Ignore`; syncing from
    // the installation root downward makes every newly created directory entry durable before
    // the byte-exact backup itself is published.
    let mut directories = path.ancestors().take(4).collect::<Vec<_>>();
    directories.reverse();
    for directory in directories {
        let handle =
            File::open(directory).map_err(|source| LocalIgnoreResetError::BackupDirectory {
                path: directory.to_path_buf(),
                source,
            })?;
        handle
            .sync_all()
            .map_err(|source| LocalIgnoreResetError::BackupDirectory {
                path: directory.to_path_buf(),
                source,
            })?;
    }
    Ok(())
}

/// Windows journals directory creation metadata; std exposes no directory fsync handle.
#[cfg(not(unix))]
fn sync_local_ignore_backup_directory_chain(_path: &Path) -> Result<(), LocalIgnoreResetError> {
    Ok(())
}

/// Read the canonical reset path while preserving removal as conflict data.
fn read_reset_canonical(path: &Path) -> Result<Option<Vec<u8>>, LocalIgnoreResetError> {
    match std::fs::read(path) {
        Ok(bytes) => Ok(Some(bytes)),
        Err(source) if source.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(source) => Err(LocalIgnoreResetError::Read {
            path: path.to_path_buf(),
            source,
        }),
    }
}

/// Expected outcomes from loading Installed YAML Data.
#[derive(Debug)]
pub enum InstalledYamlDataLoadOutcome {
    /// Main, game, and valid Local Ignore data were loaded into one immutable snapshot.
    Ready(InstalledYamlDataSnapshot),
    /// Existing Local Ignore data is malformed and requires an explicit caller decision.
    LocalIgnoreRecoveryRequired(LocalIgnoreRecoveryPlan),
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
            let generated = publish_local_ignore_if_absent(
                local_ignore_io,
                &ignore_path,
                defaults.content.as_bytes(),
            )?;
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
    let ignore_content = match std::str::from_utf8(&local_ignore.bytes) {
        Ok(content) => content,
        Err(source) => {
            return local_ignore_recovery_required(
                selected,
                local_ignore,
                ignore_path,
                request.selected_game_version,
                InstalledYamlDataDiagnosticKind::InvalidUtf8,
                format!("existing Local Ignore YAML Data is not UTF-8: {source}"),
            );
        }
    };
    let ignore_yaml = match parse_and_merge_yaml_content(
        "Local Ignore YAML",
        "Local Ignore YAML",
        ignore_content,
    ) {
        Ok(yaml) => yaml,
        Err(source) => {
            return local_ignore_recovery_required(
                selected,
                local_ignore,
                ignore_path,
                request.selected_game_version,
                InstalledYamlDataDiagnosticKind::Parse,
                format!("existing Local Ignore YAML Data could not be parsed: {source}"),
            );
        }
    };
    if let Err(source) = validate_ignore(&ignore_yaml, selected.game_data_role, &ignore_path) {
        return local_ignore_recovery_required(
            selected,
            local_ignore,
            ignore_path,
            request.selected_game_version,
            InstalledYamlDataDiagnosticKind::InvalidRoleData,
            format!(
                "existing Local Ignore YAML Data is invalid: {}",
                explicit_validation_reason(source)
            ),
        );
    }
    let snapshot = build_installed_yaml_data_snapshot(
        selected,
        local_ignore,
        local_ignore_state,
        &ignore_yaml,
        &request.selected_game_version,
    )?;

    Ok(InstalledYamlDataLoadOutcome::Ready(snapshot))
}

/// Build the immutable operation snapshot from already retained selected data.
///
/// Callers supply the operation's Local Ignore document explicitly, which lets recovery use an
/// in-memory empty document without reopening or changing any installation path.
fn build_installed_yaml_data_snapshot(
    selected: SelectedInstalledYamlData,
    local_ignore: OwnedLocalIgnoreYamlData,
    local_ignore_state: LocalIgnoreYamlDataState,
    ignore_yaml: &Yaml,
    selected_game_version: &str,
) -> Result<InstalledYamlDataSnapshot, InstalledYamlDataLoadError> {
    // Keep the retained byte buffers tied to the public identities even after parsing.
    debug_assert_eq!(
        selected.main.bytes.len() as u64,
        selected.main.inspected.identity().byte_len()
    );
    debug_assert_eq!(
        selected.game_file.bytes.len() as u64,
        selected.game_file.inspected.identity().byte_len()
    );
    debug_assert_eq!(
        local_ignore.bytes.len() as u64,
        local_ignore.identity.byte_len()
    );
    let simplify_remove_list =
        YamlOperations::new().get_vec_value(&selected.main.yaml, "exclude_log_records");
    let yaml_data = YamlDataCore::build_from_yaml_documents(
        &selected.main.yaml,
        &selected.game_file.yaml,
        ignore_yaml,
        game_data_key(selected.game_data_role),
        selected_game_version,
    )
    .map_err(|source| InstalledYamlDataLoadError::InvalidSelectedData {
        message: source.to_string(),
    })?;

    Ok(InstalledYamlDataSnapshot {
        yaml_data,
        simplify_remove_list,
        requested_game: selected.requested_game,
        game_data_role: selected.game_data_role,
        main: selected.main,
        game_file: selected.game_file,
        local_ignore,
        local_ignore_state,
        diagnostics: selected.diagnostics,
    })
}

/// Return an immutable recovery plan without re-reading or rewriting malformed Local Ignore data.
fn local_ignore_recovery_required(
    mut selected: SelectedInstalledYamlData,
    malformed_local_ignore: OwnedLocalIgnoreYamlData,
    local_ignore_path: PathBuf,
    selected_game_version: String,
    kind: InstalledYamlDataDiagnosticKind,
    message: String,
) -> Result<InstalledYamlDataLoadOutcome, InstalledYamlDataLoadError> {
    // Proceed Without Ignore never reads or publishes defaults. Preserve their validity state for
    // a later reset decision without turning this non-mutating recovery choice into a fatal load.
    let validated_defaults =
        validate_local_ignore_defaults(&selected, &local_ignore_path).map(|defaults| {
            (
                defaults.content.as_bytes().to_vec().into_boxed_slice(),
                defaults.yaml,
            )
        });
    selected.diagnostics.push(InstalledYamlDataDiagnostic {
        role: None,
        candidate: None,
        path: Some(local_ignore_path.clone()),
        kind,
        message,
    });
    let reset = match validated_defaults {
        Ok((bytes, yaml)) => {
            let local_ignore = OwnedLocalIgnoreYamlData {
                identity: YamlDataContentIdentity::from_bytes(&bytes),
                bytes,
            };
            PreparedLocalIgnoreReset::Ready(Box::new(build_installed_yaml_data_snapshot(
                selected.clone(),
                local_ignore,
                LocalIgnoreYamlDataState::ResetToDefault,
                &yaml,
                &selected_game_version,
            )?))
        }
        Err(reason) => PreparedLocalIgnoreReset::Unavailable { reason },
    };
    let mut empty_ignore_mapping = yaml_rust2::yaml::Hash::new();
    empty_ignore_mapping.insert(
        Yaml::String(format!(
            "CLASSIC_Ignore_{}",
            game_data_key(selected.game_data_role)
        )),
        Yaml::Array(Vec::new()),
    );
    let proceed_without_ignore_snapshot = build_installed_yaml_data_snapshot(
        selected,
        malformed_local_ignore,
        LocalIgnoreYamlDataState::ProceedWithoutIgnore,
        &Yaml::Hash(empty_ignore_mapping),
        &selected_game_version,
    )?;
    let backup_directory = local_ignore_path
        .ancestors()
        .nth(2)
        .unwrap_or_else(|| local_ignore_path.parent().unwrap_or_else(|| Path::new(".")))
        .join("CLASSIC Backup")
        .join("YAML Data")
        .join("Local Ignore");

    Ok(InstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired(
        LocalIgnoreRecoveryPlan {
            proceed_without_ignore_snapshot,
            local_ignore_path,
            backup_directory,
            reset,
            selected_game_version,
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
) -> Result<ValidatedLocalIgnoreDefaults<'a>, InstalledYamlDataLoadError> {
    validate_local_ignore_defaults(selected, ignore_path).map_err(|reason| {
        InstalledYamlDataLoadError::LocalIgnoreDefaultInvalid {
            path: ignore_path.to_path_buf(),
            reason,
        }
    })
}

/// Validate selected-Main Local Ignore defaults without deciding how a caller classifies failure.
struct ValidatedLocalIgnoreDefaults<'a> {
    content: &'a str,
    yaml: Yaml,
}

/// Validate selected-Main defaults and retain both their exact text and parsed document.
fn validate_local_ignore_defaults<'a>(
    selected: &'a SelectedInstalledYamlData,
    ignore_path: &Path,
) -> Result<ValidatedLocalIgnoreDefaults<'a>, String> {
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
        .ok_or_else(|| {
            "required `CLASSIC_Info.default_ignorefile` non-empty string is missing or malformed"
                .to_string()
        })?;
    let yaml = parse_and_merge_yaml_content(
        "selected Main Local Ignore default",
        "Selected Main Local Ignore Default",
        defaults,
    )
    .map_err(|source| source.to_string())?;
    validate_ignore(&yaml, selected.game_data_role, ignore_path)
        .map_err(explicit_validation_reason)?;
    Ok(ValidatedLocalIgnoreDefaults {
        content: defaults,
        yaml,
    })
}

/// Stage complete bytes beside `path`, then atomically publish them only if `path` is absent.
///
/// A no-clobber move makes the fully synced staged file visible at the canonical path; on Windows,
/// this is a write-through rename that does not require hard-link support. `Ok(false)` means a
/// concurrent creator won; callers must reread the canonical path and treat that winner as
/// authoritative.
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
    let (staged_file, staged_path) =
        staged
            .keep()
            .map_err(|failure| InstalledYamlDataLoadError::LocalIgnoreCreate {
                path: path.to_path_buf(),
                source: failure.error,
            })?;
    drop(staged_file);
    let publication = local_ignore_io.publish_staged_noclobber(&staged_path, path);
    if let Err(source) = std::fs::remove_file(&staged_path)
        && source.kind() != std::io::ErrorKind::NotFound
    {
        // Match NamedTempFile's best-effort drop cleanup: a private staging artifact must not
        // override either a complete canonical winner or the primary publication error.
        log::warn!(
            "failed to clean Local Ignore staging file `{}`: {source}",
            staged_path.display()
        );
    }
    publication.map_err(|source| InstalledYamlDataLoadError::LocalIgnoreCreate {
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
