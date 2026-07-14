//! Explicit, conflict-safe publication and restoration of approved User Settings migrations.

use crate::commit::{Publisher, SystemPublisher, acquire_commit_lock};
use crate::{MigrationEndpoint, Revision, SourceLocation, UserSettings, UserSettingsMigrationPlan};
use sha2::{Digest, Sha256};
use std::fmt;
use std::path::{Path, PathBuf};

const CANONICAL_RELATIVE_PATH: &str = "CLASSIC Settings.yaml";
const LEGACY_RELATIVE_PATH: &str = "CLASSIC Data/CLASSIC Settings.yaml";
const BACKUP_RELATIVE_DIRECTORY: &str = "CLASSIC Backup/User Settings/Migrations";

/// Result of explicitly applying an approved User Settings migration plan.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum UserSettingsMigrationApplyOutcome {
    /// The backup was verified and the migrated document was published and reopened.
    Applied(UserSettingsMigrationReceipt),
    /// The opened source changed after planning, so migration did not begin.
    Conflict {
        /// Revision against which the caller approved the plan.
        expected_revision: Revision,
        /// Revision found after acquiring cross-process coordination.
        actual_revision: Revision,
    },
}

/// Result of explicitly restoring a successfully applied User Settings migration.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum UserSettingsMigrationRestoreOutcome {
    /// The verified backup was atomically republished and reopened at this revision.
    Restored {
        /// SHA-256 revision of the byte-exact restored document.
        revision: Revision,
    },
    /// The migrated document changed after apply, so restore did not overwrite it.
    Conflict {
        /// Revision produced and verified by the successful migration.
        expected_revision: Revision,
        /// Revision found after acquiring cross-process coordination.
        actual_revision: Revision,
    },
}

/// Verified record of one successfully applied User Settings migration.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UserSettingsMigrationReceipt {
    source_path: PathBuf,
    destination_path: PathBuf,
    backup_path: PathBuf,
    source: MigrationEndpoint,
    target: MigrationEndpoint,
    backup_revision: Revision,
    published_revision: Revision,
}

impl UserSettingsMigrationReceipt {
    /// Returns the document path selected when the migration was planned and applied.
    pub fn source_path(&self) -> &Path {
        &self.source_path
    }

    /// Returns the canonical path at which the migrated document was published.
    pub fn destination_path(&self) -> &Path {
        &self.destination_path
    }

    /// Returns the retained, byte-exact backup path verified before publication.
    pub fn backup_path(&self) -> &Path {
        &self.backup_path
    }

    /// Returns the source version/location endpoint recorded by the approved plan.
    pub const fn source(&self) -> &MigrationEndpoint {
        &self.source
    }

    /// Returns the destination version/location endpoint recorded by the approved plan.
    pub const fn target(&self) -> &MigrationEndpoint {
        &self.target
    }

    /// Returns the exact-byte revision attested by the retained backup.
    pub const fn backup_revision(&self) -> &Revision {
        &self.backup_revision
    }

    /// Returns the exact-byte revision verified by reopening after publication.
    pub const fn published_revision(&self) -> &Revision {
        &self.published_revision
    }

    /// Explicitly restores this migration's retained, verified backup.
    ///
    /// Restore reacquires the same User Settings lock, refuses a stale migrated revision, rereads
    /// and verifies the retained backup, atomically republishes it, and reopens the restored
    /// document before reporting success.
    pub fn restore(
        &self,
        classic_root: impl AsRef<Path>,
    ) -> Result<UserSettingsMigrationRestoreOutcome, UserSettingsMigrationError> {
        self.restore_with_publisher(classic_root.as_ref(), &SystemPublisher::system())
    }

    /// Runs restoration through an injectable durable publication boundary.
    fn restore_with_publisher(
        &self,
        classic_root: &Path,
        publisher: &impl Publisher,
    ) -> Result<UserSettingsMigrationRestoreOutcome, UserSettingsMigrationError> {
        let expected_source = path_for_location(classic_root, self.source.location())?;
        let expected_destination = classic_root.join(CANONICAL_RELATIVE_PATH);
        if self.source_path != expected_source || self.destination_path != expected_destination {
            return Err(UserSettingsMigrationError::new(
                "migration_restore_root_mismatch",
                "the restore root does not match the root recorded by this migration receipt",
            ));
        }
        let _lock = acquire_commit_lock(&self.destination_path).map_err(map_lock_error)?;
        let latest = UserSettings::open(classic_root);
        if latest.revision() != &self.published_revision
            || latest.source().location() != self.target.location()
        {
            return Ok(UserSettingsMigrationRestoreOutcome::Conflict {
                expected_revision: self.published_revision.clone(),
                actual_revision: latest.revision().clone(),
            });
        }

        let backup_bytes = std::fs::read(&self.backup_path).map_err(|error| {
            UserSettingsMigrationError::new(
                "migration_restore_backup_read_failed",
                format!("could not read {}: {error}", self.backup_path.display()),
            )
        })?;
        let restored_revision = content_revision(&backup_bytes);
        if restored_revision != self.backup_revision {
            return Err(UserSettingsMigrationError::new(
                "migration_restore_backup_verify_failed",
                format!(
                    "retained backup {} no longer matches its verified revision",
                    self.backup_path.display()
                ),
            ));
        }

        let migrated_bytes = latest.original_bytes().ok_or_else(|| {
            UserSettingsMigrationError::new(
                "migration_restore_source_unavailable",
                "the migrated document had no retained bytes while the restore lock was held",
            )
        })?;
        if self.source.location() == SourceLocation::Legacy {
            let legacy_revision = revision_at_path(&self.source_path)?;
            if legacy_revision != self.backup_revision {
                return Ok(UserSettingsMigrationRestoreOutcome::Conflict {
                    expected_revision: self.backup_revision.clone(),
                    actual_revision: legacy_revision,
                });
            }
        }

        publisher
            .publish(&self.source_path, &backup_bytes)
            .map_err(|error| map_publication_error("migration_restore", &error))?;
        if self.source.location() == SourceLocation::Legacy {
            std::fs::remove_file(&self.destination_path).map_err(|error| {
                UserSettingsMigrationError::new(
                    "migration_restore_remove_destination_failed",
                    format!(
                        "could not retire migrated document {}: {error}",
                        self.destination_path.display()
                    ),
                )
            })?;
        }
        let reopened = UserSettings::open(classic_root);
        if reopened.revision() != &restored_revision
            || reopened.source().location() != self.source.location()
            || reopened.original_bytes() != Some(backup_bytes.as_slice())
        {
            let verification = UserSettingsMigrationError::new(
                "migration_restore_reopen_verify_failed",
                format!(
                    "restored User Settings at {} did not reopen as the verified backup",
                    self.source_path.display()
                ),
            );
            return Err(rollback_after_failed_verification(
                publisher,
                classic_root,
                &self.destination_path,
                migrated_bytes,
                &self.published_revision,
                self.target.location(),
                verification,
            ));
        }

        Ok(UserSettingsMigrationRestoreOutcome::Restored {
            revision: restored_revision,
        })
    }
}

/// Operational failure encountered while applying or restoring a User Settings migration.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UserSettingsMigrationError {
    code: &'static str,
    message: String,
}

impl UserSettingsMigrationError {
    /// Builds one stage-specific migration persistence failure.
    fn new(code: &'static str, message: impl Into<String>) -> Self {
        Self {
            code,
            message: message.into(),
        }
    }

    /// Returns the stable programmatic category for this failure.
    pub const fn code(&self) -> &'static str {
        self.code
    }

    /// Returns human-readable context for the failed persistence stage.
    pub fn message(&self) -> &str {
        &self.message
    }
}

impl fmt::Display for UserSettingsMigrationError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}: {}", self.code, self.message)
    }
}

impl std::error::Error for UserSettingsMigrationError {}

impl UserSettingsMigrationPlan {
    /// Explicitly applies this caller-approved plan under User Settings coordination.
    ///
    /// The operation reopens and compares the planned revision before creating any backup,
    /// retains and rereads a byte-exact backup, atomically publishes the proposed bytes, and
    /// reopens the document before returning an [`UserSettingsMigrationReceipt`].
    pub fn apply(
        &self,
        classic_root: impl AsRef<Path>,
    ) -> Result<UserSettingsMigrationApplyOutcome, UserSettingsMigrationError> {
        self.apply_with_publisher(classic_root.as_ref(), &SystemPublisher::system())
    }

    /// Runs migration application through an injectable durable publication boundary.
    fn apply_with_publisher(
        &self,
        classic_root: &Path,
        publisher: &impl Publisher,
    ) -> Result<UserSettingsMigrationApplyOutcome, UserSettingsMigrationError> {
        if !self.persistence_attested {
            return Err(UserSettingsMigrationError::new(
                "migration_plan_unattested",
                "review-only reconstructed plans cannot authorize migration persistence",
            ));
        }
        if self.target().location() != SourceLocation::Canonical {
            return Err(UserSettingsMigrationError::new(
                "migration_plan_direction_unsupported",
                "inverse review plans cannot be applied; restore requires a verified receipt",
            ));
        }
        let destination_path = classic_root.join(CANONICAL_RELATIVE_PATH);
        let _lock = acquire_commit_lock(&destination_path).map_err(map_lock_error)?;
        let latest = UserSettings::open(classic_root);
        if latest.revision() != self.base_revision()
            || latest.source().location() != self.source().location()
        {
            return Ok(UserSettingsMigrationApplyOutcome::Conflict {
                expected_revision: self.base_revision().clone(),
                actual_revision: latest.revision().clone(),
            });
        }

        let source_path = path_for_location(classic_root, self.source().location())?;
        let backup_path = backup_path(classic_root, self.original_bytes());
        let backup_parent = backup_path.parent().ok_or_else(|| {
            UserSettingsMigrationError::new(
                "migration_backup_directory_failed",
                format!("backup path has no parent: {}", backup_path.display()),
            )
        })?;
        std::fs::create_dir_all(backup_parent).map_err(|error| {
            UserSettingsMigrationError::new(
                "migration_backup_directory_failed",
                format!("could not create {}: {error}", backup_parent.display()),
            )
        })?;
        publisher
            .publish(&backup_path, self.original_bytes())
            .map_err(|error| map_publication_error("migration_backup", &error))?;
        let verified_backup = std::fs::read(&backup_path).map_err(|error| {
            UserSettingsMigrationError::new(
                "migration_backup_verify_failed",
                format!("could not reread {}: {error}", backup_path.display()),
            )
        })?;
        if verified_backup != self.original_bytes() {
            return Err(UserSettingsMigrationError::new(
                "migration_backup_verify_failed",
                format!("backup bytes did not match {}", source_path.display()),
            ));
        }

        publisher
            .publish(&destination_path, self.proposed_bytes())
            .map_err(|error| map_publication_error("migration_publish", &error))?;
        let published_revision = content_revision(self.proposed_bytes());
        let reopened = UserSettings::open(classic_root);
        if reopened.revision() != &published_revision
            || reopened.source().location() != self.target().location()
            || reopened.original_bytes() != Some(self.proposed_bytes())
        {
            let verification = UserSettingsMigrationError::new(
                "migration_reopen_verify_failed",
                format!(
                    "published User Settings at {} did not reopen as the approved plan",
                    destination_path.display()
                ),
            );
            return Err(rollback_after_failed_apply_verification(
                publisher,
                classic_root,
                &destination_path,
                self.source().location(),
                self.original_bytes(),
                self.base_revision(),
                verification,
            ));
        }

        Ok(UserSettingsMigrationApplyOutcome::Applied(
            UserSettingsMigrationReceipt {
                source_path,
                destination_path,
                backup_path,
                source: *self.source(),
                target: *self.target(),
                backup_revision: self.base_revision().clone(),
                published_revision,
            },
        ))
    }
}

/// Resolves one supported migration endpoint to its concrete root-relative path.
fn path_for_location(
    classic_root: &Path,
    location: SourceLocation,
) -> Result<PathBuf, UserSettingsMigrationError> {
    match location {
        SourceLocation::Canonical => Ok(classic_root.join(CANONICAL_RELATIVE_PATH)),
        SourceLocation::Legacy => Ok(classic_root.join(LEGACY_RELATIVE_PATH)),
        SourceLocation::Missing => Err(UserSettingsMigrationError::new(
            "migration_source_unavailable",
            "a migration plan cannot originate from a missing document",
        )),
    }
}

/// Returns the content-addressed retained backup path for exact source bytes.
fn backup_path(classic_root: &Path, bytes: &[u8]) -> PathBuf {
    let digest = Sha256::digest(bytes);
    let name = format!("{}.yaml", hex_digest(&digest));
    classic_root.join(BACKUP_RELATIVE_DIRECTORY).join(name)
}

/// Converts exact bytes into the crate's content-derived revision.
fn content_revision(bytes: &[u8]) -> Revision {
    Revision::ContentSha256(Sha256::digest(bytes).into())
}

/// Reads the exact-byte revision at one path without changing User Settings discovery precedence.
fn revision_at_path(path: &Path) -> Result<Revision, UserSettingsMigrationError> {
    match std::fs::read(path) {
        Ok(bytes) => Ok(content_revision(&bytes)),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(Revision::Missing),
        Err(error) => Err(UserSettingsMigrationError::new(
            "migration_restore_source_read_failed",
            format!("could not read {}: {error}", path.display()),
        )),
    }
}

/// Restores the last accepted migrated bytes after post-publication verification fails.
fn rollback_after_failed_verification(
    publisher: &impl Publisher,
    classic_root: &Path,
    destination_path: &Path,
    migrated_bytes: &[u8],
    migrated_revision: &Revision,
    migrated_location: SourceLocation,
    verification: UserSettingsMigrationError,
) -> UserSettingsMigrationError {
    if let Err(rollback) = publisher.publish(destination_path, migrated_bytes) {
        return UserSettingsMigrationError::new(
            "migration_restore_rollback_failed",
            format!("{verification}; rollback also failed: {rollback}"),
        );
    }
    let reopened = UserSettings::open(classic_root);
    if reopened.revision() != migrated_revision
        || reopened.source().location() != migrated_location
        || reopened.original_bytes() != Some(migrated_bytes)
    {
        return UserSettingsMigrationError::new(
            "migration_restore_rollback_verify_failed",
            format!("{verification}; rollback did not reopen the migrated document"),
        );
    }
    verification
}

/// Restores the planned source after a migrated publication cannot be verified.
fn rollback_after_failed_apply_verification(
    publisher: &impl Publisher,
    classic_root: &Path,
    destination_path: &Path,
    source_location: SourceLocation,
    original_bytes: &[u8],
    original_revision: &Revision,
    verification: UserSettingsMigrationError,
) -> UserSettingsMigrationError {
    let rollback = match source_location {
        SourceLocation::Canonical => publisher
            .publish(destination_path, original_bytes)
            .map_err(|error| error.to_string()),
        SourceLocation::Legacy => {
            std::fs::remove_file(destination_path).map_err(|error| error.to_string())
        }
        SourceLocation::Missing => {
            Err("migration plan originated from a missing source".to_string())
        }
    };
    if let Err(rollback) = rollback {
        return UserSettingsMigrationError::new(
            "migration_rollback_failed",
            format!("{verification}; rollback also failed: {rollback}"),
        );
    }
    let restored = UserSettings::open(classic_root);
    if restored.revision() != original_revision
        || restored.source().location() != source_location
        || restored.original_bytes() != Some(original_bytes)
    {
        return UserSettingsMigrationError::new(
            "migration_rollback_verify_failed",
            format!("{verification}; rollback did not reopen the last accepted document"),
        );
    }
    verification
}

/// Formats a digest without adding a dependency to the public persistence path.
fn hex_digest(bytes: &[u8]) -> String {
    use fmt::Write as _;

    let mut encoded = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        write!(&mut encoded, "{byte:02x}").expect("writing to a String cannot fail");
    }
    encoded
}

/// Maps the shared publisher's stable commit-stage code into one migration operation stage.
fn map_publication_error(
    operation: &'static str,
    error: &crate::UserSettingsCommitError,
) -> UserSettingsMigrationError {
    UserSettingsMigrationError::new(
        match error.code() {
            "commit_temp_create_failed" => concat_code(operation, "_create_failed"),
            "commit_temp_write_failed" => concat_code(operation, "_write_failed"),
            "commit_temp_flush_failed" => concat_code(operation, "_flush_failed"),
            "commit_temp_sync_failed" => concat_code(operation, "_sync_failed"),
            "commit_replace_failed" => concat_code(operation, "_replace_failed"),
            "commit_temp_cleanup_failed" => concat_code(operation, "_cleanup_failed"),
            _ => "migration_persistence_failed",
        },
        error.message().to_string(),
    )
}

/// Maps the shared coordination failure into the migration error namespace.
fn map_lock_error(error: crate::UserSettingsCommitError) -> UserSettingsMigrationError {
    UserSettingsMigrationError::new(
        match error.code() {
            "commit_lock_open_failed" => "migration_lock_open_failed",
            "commit_lock_failed" => "migration_lock_failed",
            _ => "migration_lock_failed",
        },
        error.message().to_string(),
    )
}

/// Returns a static operation/stage code for the two supported publication operations.
fn concat_code(operation: &'static str, suffix: &'static str) -> &'static str {
    match (operation, suffix) {
        ("migration_backup", "_create_failed") => "migration_backup_create_failed",
        ("migration_backup", "_write_failed") => "migration_backup_write_failed",
        ("migration_backup", "_flush_failed") => "migration_backup_flush_failed",
        ("migration_backup", "_sync_failed") => "migration_backup_sync_failed",
        ("migration_backup", "_replace_failed") => "migration_backup_replace_failed",
        ("migration_backup", "_cleanup_failed") => "migration_backup_cleanup_failed",
        ("migration_publish", "_create_failed") => "migration_publish_create_failed",
        ("migration_publish", "_write_failed") => "migration_publish_write_failed",
        ("migration_publish", "_flush_failed") => "migration_publish_flush_failed",
        ("migration_publish", "_sync_failed") => "migration_publish_sync_failed",
        ("migration_publish", "_replace_failed") => "migration_publish_replace_failed",
        ("migration_publish", "_cleanup_failed") => "migration_publish_cleanup_failed",
        ("migration_restore", "_create_failed") => "migration_restore_create_failed",
        ("migration_restore", "_write_failed") => "migration_restore_write_failed",
        ("migration_restore", "_flush_failed") => "migration_restore_flush_failed",
        ("migration_restore", "_sync_failed") => "migration_restore_sync_failed",
        ("migration_restore", "_replace_failed") => "migration_restore_replace_failed",
        ("migration_restore", "_cleanup_failed") => "migration_restore_cleanup_failed",
        _ => "migration_persistence_failed",
    }
}

#[cfg(test)]
#[path = "migration_persistence_tests.rs"]
mod tests;
