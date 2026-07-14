//! Conflict-safe publication of accepted User Settings Updates.

use crate::{AcceptedUserSettingsUpdate, Revision, UserSettings, UserSettingsUpdateField};
use classic_settings_core::{Yaml, YamlOperations, parse_yaml_content};
use sha2::{Digest, Sha256};
use std::fmt;
use std::fs::{File, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};

const CANONICAL_FILENAME: &str = "CLASSIC Settings.yaml";
const COMMIT_LOCK_SUFFIX: &str = ".commit.lock";

/// Result of attempting to publish a previously accepted User Settings Update.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum UserSettingsCommitOutcome {
    /// Every accepted field was published together at the returned content revision.
    Committed {
        /// SHA-256 revision of the newly published document.
        revision: Revision,
    },
    /// The document changed after preview, so the newer bytes were left untouched.
    Conflict {
        /// Revision against which the update was accepted.
        expected_revision: Revision,
        /// Revision found after acquiring cross-process coordination.
        actual_revision: Revision,
    },
}

/// Operational failure encountered before an accepted update could be published.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UserSettingsCommitError {
    code: &'static str,
    message: String,
}

impl UserSettingsCommitError {
    /// Returns the stable programmatic category for this failure.
    pub fn code(&self) -> &'static str {
        self.code
    }

    /// Returns human-readable context for the failed commit stage.
    pub fn message(&self) -> &str {
        &self.message
    }

    /// Builds one failure while retaining the stage-specific stable code.
    fn new(code: &'static str, message: impl Into<String>) -> Self {
        Self {
            code,
            message: message.into(),
        }
    }
}

impl fmt::Display for UserSettingsCommitError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}: {}", self.code, self.message)
    }
}

impl std::error::Error for UserSettingsCommitError {}

impl AcceptedUserSettingsUpdate {
    /// Commits this accepted update against the latest canonical document.
    ///
    /// The operation holds a cross-process sibling lock while reopening and comparing the exact
    /// content revision, patches only the accepted canonical fields, and publishes all fields in
    /// one durable atomic replacement. A revision mismatch is returned as data and performs no
    /// write; operational failures are returned as [`UserSettingsCommitError`].
    pub fn commit(
        &self,
        classic_root: impl AsRef<Path>,
    ) -> Result<UserSettingsCommitOutcome, UserSettingsCommitError> {
        self.commit_with_publisher(classic_root.as_ref(), &SystemPublisher { fail_at: None })
    }

    /// Runs the commit algorithm through an injectable publication boundary.
    fn commit_with_publisher(
        &self,
        classic_root: &Path,
        publisher: &impl Publisher,
    ) -> Result<UserSettingsCommitOutcome, UserSettingsCommitError> {
        let target = classic_root.join(CANONICAL_FILENAME);
        let _lock = acquire_commit_lock(&target)?;
        let latest = UserSettings::open(classic_root);

        if matches!(latest.revision(), Revision::Unavailable) {
            return Err(UserSettingsCommitError::new(
                "commit_source_unavailable",
                "User Settings could not be reopened while the commit lock was held",
            ));
        }
        if latest.revision() != self.base_revision() {
            return Ok(UserSettingsCommitOutcome::Conflict {
                expected_revision: self.base_revision().clone(),
                actual_revision: latest.revision().clone(),
            });
        }
        let document = latest_document(&latest)?;
        let patched = patch_accepted_fields(document, self.fields())?;
        let serialized = YamlOperations::new().dump_yaml(&patched).map_err(|error| {
            UserSettingsCommitError::new("commit_serialize_failed", error.to_string())
        })?;
        let bytes = serialized.as_bytes();

        publisher.publish(&target, bytes)?;

        Ok(UserSettingsCommitOutcome::Committed {
            revision: Revision::ContentSha256(Sha256::digest(bytes).into()),
        })
    }
}

/// Opens and exclusively locks the persistent sibling coordination file.
fn acquire_commit_lock(target: &Path) -> Result<File, UserSettingsCommitError> {
    let mut lock_name = target.as_os_str().to_os_string();
    lock_name.push(COMMIT_LOCK_SUFFIX);
    let lock_path = PathBuf::from(lock_name);
    let lock = OpenOptions::new()
        .create(true)
        .read(true)
        .write(true)
        .truncate(false)
        .open(&lock_path)
        .map_err(|error| {
            UserSettingsCommitError::new(
                "commit_lock_open_failed",
                format!("could not open {}: {error}", lock_path.display()),
            )
        })?;
    lock.lock().map_err(|error| {
        UserSettingsCommitError::new(
            "commit_lock_failed",
            format!("could not lock {}: {error}", lock_path.display()),
        )
    })?;
    Ok(lock)
}

/// Reconstructs the latest trusted YAML document, including first-run missing state.
fn latest_document(settings: &UserSettings) -> Result<Yaml, UserSettingsCommitError> {
    let Some(bytes) = settings.original_bytes() else {
        if matches!(settings.revision(), Revision::Missing) {
            let empty = Yaml::Hash(Default::default());
            return YamlOperations::new()
                .set_setting(&empty, "schema_version", Yaml::String("1.0".to_string()))
                .map_err(|error| {
                    UserSettingsCommitError::new("commit_patch_failed", error.to_string())
                });
        }
        return Err(UserSettingsCommitError::new(
            "commit_source_unavailable",
            "User Settings source bytes were unavailable after reopening",
        ));
    };
    let content = std::str::from_utf8(bytes)
        .map_err(|error| UserSettingsCommitError::new("commit_parse_failed", error.to_string()))?;
    let mut documents = parse_yaml_content("User Settings commit source", content)
        .map_err(|error| UserSettingsCommitError::new("commit_parse_failed", error.to_string()))?;
    if documents.len() != 1 {
        return Err(UserSettingsCommitError::new(
            "commit_parse_failed",
            format!("expected one YAML document, found {}", documents.len()),
        ));
    }
    Ok(documents.remove(0))
}

/// Applies exactly the accepted canonical fields to the preserved YAML tree.
fn patch_accepted_fields(
    document: Yaml,
    fields: &[UserSettingsUpdateField],
) -> Result<Yaml, UserSettingsCommitError> {
    let settings = fields
        .iter()
        .map(|field| (field.canonical_key_path(), field_yaml_value(field)))
        .collect::<Vec<_>>();
    YamlOperations::new()
        .set_settings_batch(&document, &settings)
        .map_err(|error| UserSettingsCommitError::new("commit_patch_failed", error.to_string()))
}

/// Converts one validated domain value into its canonical YAML representation.
fn field_yaml_value(field: &UserSettingsUpdateField) -> Yaml {
    match field {
        UserSettingsUpdateField::UpdateCheck(value)
        | UserSettingsUpdateField::FcxMode(value)
        | UserSettingsUpdateField::SimplifyLogs(value)
        | UserSettingsUpdateField::ShowStatistics(value)
        | UserSettingsUpdateField::FormIdValueLookup(value)
        | UserSettingsUpdateField::MoveUnsolvedLogs(value) => Yaml::Boolean(*value),
        UserSettingsUpdateField::ManagedGame(value) => Yaml::String(value.as_str().to_string()),
        UserSettingsUpdateField::GameVersionSelection(value) => {
            Yaml::String(value.as_str().to_string())
        }
        UserSettingsUpdateField::GameRoot(value)
        | UserSettingsUpdateField::GameExecutable(value)
        | UserSettingsUpdateField::DocumentsRoot(value)
        | UserSettingsUpdateField::IniFolder(value)
        | UserSettingsUpdateField::ModsFolder(value)
        | UserSettingsUpdateField::PapyrusLogPath(value)
        | UserSettingsUpdateField::UnsolvedLogsDestination(value)
        | UserSettingsUpdateField::CustomScanInput(value) => value
            .as_ref()
            .map_or(Yaml::Null, |value| Yaml::String(value.clone())),
        UserSettingsUpdateField::FormIdDatabases(databases) => Yaml::Hash(
            databases
                .iter()
                .map(|(game, paths)| {
                    (
                        Yaml::String(game.clone()),
                        Yaml::Array(paths.iter().cloned().map(Yaml::String).collect()),
                    )
                })
                .collect(),
        ),
        UserSettingsUpdateField::MaxConcurrentScans(value) => Yaml::Integer(i64::from(*value)),
    }
}

/// Injectable boundary for durable, atomic document publication.
trait Publisher {
    /// Publishes `bytes` at `target` or returns a stage-specific failure before replacement.
    fn publish(&self, target: &Path, bytes: &[u8]) -> Result<(), UserSettingsCommitError>;
}

/// Production publisher backed by a randomized same-directory temporary file.
struct SystemPublisher {
    fail_at: Option<PublicationStage>,
}

/// Fallible publication stages exposed only to the internal fault-injection seam.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum PublicationStage {
    Create,
    Write,
    Flush,
    Sync,
    Replace,
}

impl PublicationStage {
    /// Returns the public error code corresponding to this publication stage.
    fn error_code(self) -> &'static str {
        match self {
            Self::Create => "commit_temp_create_failed",
            Self::Write => "commit_temp_write_failed",
            Self::Flush => "commit_temp_flush_failed",
            Self::Sync => "commit_temp_sync_failed",
            Self::Replace => "commit_replace_failed",
        }
    }
}

impl SystemPublisher {
    /// Builds a publisher that deterministically fails before one requested stage.
    #[cfg(test)]
    fn failing_at(stage: PublicationStage) -> Self {
        Self {
            fail_at: Some(stage),
        }
    }

    /// Returns the injected failure before the stage mutates publication state.
    fn before(&self, stage: PublicationStage) -> Result<(), UserSettingsCommitError> {
        if self.fail_at == Some(stage) {
            return Err(UserSettingsCommitError::new(
                stage.error_code(),
                format!("injected {stage:?} failure"),
            ));
        }
        Ok(())
    }
}

impl Publisher for SystemPublisher {
    fn publish(&self, target: &Path, bytes: &[u8]) -> Result<(), UserSettingsCommitError> {
        let parent = target.parent().ok_or_else(|| {
            UserSettingsCommitError::new(
                "commit_temp_create_failed",
                format!("target has no parent: {}", target.display()),
            )
        })?;
        self.before(PublicationStage::Create)?;
        let mut temp = tempfile::Builder::new()
            .prefix(".classic-user-settings-")
            .suffix(".tmp")
            .tempfile_in(parent)
            .map_err(|error| {
                UserSettingsCommitError::new("commit_temp_create_failed", error.to_string())
            })?;
        let staged = (|| {
            self.before(PublicationStage::Write)?;
            temp.write_all(bytes).map_err(|error| {
                UserSettingsCommitError::new("commit_temp_write_failed", error.to_string())
            })?;
            self.before(PublicationStage::Flush)?;
            temp.flush().map_err(|error| {
                UserSettingsCommitError::new("commit_temp_flush_failed", error.to_string())
            })?;
            self.before(PublicationStage::Sync)?;
            temp.as_file().sync_all().map_err(|error| {
                UserSettingsCommitError::new("commit_temp_sync_failed", error.to_string())
            })?;
            self.before(PublicationStage::Replace)
        })();
        if let Err(error) = staged {
            return Err(cleanup_failed_publication(temp, error));
        }

        if let Err(error) = temp.persist(target) {
            let replacement =
                UserSettingsCommitError::new("commit_replace_failed", error.error.to_string());
            return Err(cleanup_failed_publication(error.file, replacement));
        }
        sync_parent_directory(parent);
        Ok(())
    }
}

/// Explicitly removes a failed publication artifact and retains both failures when cleanup fails.
fn cleanup_failed_publication(
    temp: tempfile::NamedTempFile,
    primary: UserSettingsCommitError,
) -> UserSettingsCommitError {
    match temp.close() {
        Ok(()) => primary,
        Err(cleanup) => UserSettingsCommitError::new(
            "commit_temp_cleanup_failed",
            format!("{primary}; temporary-file cleanup also failed: {cleanup}"),
        ),
    }
}

/// Best-effort directory synchronization after the atomic replacement is visible.
#[cfg(unix)]
fn sync_parent_directory(parent: &Path) {
    // A post-replacement sync failure cannot be reported without falsely implying the old
    // document survived, so directory durability is best-effort after the atomic boundary.
    if let Ok(directory) = File::open(parent) {
        let _ = directory.sync_all();
    }
}

/// Windows journals same-directory replacement metadata; std has no directory fsync handle.
#[cfg(not(unix))]
fn sync_parent_directory(_parent: &Path) {}

#[cfg(test)]
#[path = "commit_tests.rs"]
mod tests;
