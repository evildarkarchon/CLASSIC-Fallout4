//! Explicit import of the retired TUI remembered-state document.

use crate::commit::{Publisher, SystemPublisher, acquire_commit_lock};
use crate::{
    CommitEligibility, DocumentClassification, Revision, UserSettings, UserSettingsCommitOutcome,
    UserSettingsUpdate, UserSettingsUpdatePreview,
};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::fmt;
use std::path::{Path, PathBuf};

const BACKUP_RELATIVE_DIRECTORY: &str = "CLASSIC Backup/User Settings/TUI State Imports";
const CANONICAL_FILENAME: &str = "CLASSIC Settings.yaml";

/// Result of explicitly importing one retired TUI `state.json` document.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LegacyTuiStateImportOutcome {
    /// The concrete legacy path did not contain a file, so no settings or backup were written.
    NoLegacySource,
    /// User Settings must be migrated before the remembered state can be imported.
    RequiresSettingsMigration {
        /// Format and schema classification of the unchanged settings base.
        classification: DocumentClassification,
        /// Content revision of the unchanged settings base.
        revision: Revision,
    },
    /// User Settings could not be trusted as a base, so no import artifacts were written.
    UntrustedSettingsBase {
        /// Format and schema classification of the unchanged settings base.
        classification: DocumentClassification,
        /// Content revision, or unavailability marker, for the unchanged settings base.
        revision: Revision,
    },
    /// Exact legacy bytes were backed up and all three remembered fields were committed together.
    Applied(LegacyTuiStateImportReceipt),
    /// User Settings changed after the import operation selected its base.
    SettingsConflict {
        /// Revision selected before backup publication.
        expected_revision: Revision,
        /// Revision found immediately before preview or during commit.
        actual_revision: Revision,
    },
    /// The concrete legacy source changed after it was read and validated.
    LegacySourceConflict {
        /// Exact-byte revision that was parsed and approved for import.
        expected_revision: Revision,
        /// Revision found when the concrete source path was reread.
        actual_revision: Revision,
    },
}

/// Result of explicitly restoring the User Settings base replaced by a legacy TUI state import.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LegacyTuiStateImportRestoreOutcome {
    /// The verified pre-import base was restored, including the missing-document state.
    Restored {
        /// Revision reopened after restoration; [`Revision::Missing`] represents file removal.
        revision: Revision,
    },
    /// User Settings changed after import, so restore did not overwrite the newer document.
    Conflict {
        /// Revision published by the successful import.
        expected_revision: Revision,
        /// Revision found while the User Settings commit lock was held.
        actual_revision: Revision,
    },
}

/// Verified record of one successfully imported legacy TUI state document.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LegacyTuiStateImportReceipt {
    source_path: PathBuf,
    backup_path: PathBuf,
    settings_path: PathBuf,
    settings_backup_path: Option<PathBuf>,
    source_revision: Revision,
    backup_revision: Revision,
    base_settings_revision: Revision,
    published_settings_revision: Revision,
}

impl LegacyTuiStateImportReceipt {
    /// Returns the concrete legacy `state.json` path left dormant by the import.
    pub fn source_path(&self) -> &Path {
        &self.source_path
    }

    /// Returns the retained content-addressed backup verified before settings publication.
    pub fn backup_path(&self) -> &Path {
        &self.backup_path
    }

    /// Returns the canonical User Settings path published by the import.
    pub fn settings_path(&self) -> &Path {
        &self.settings_path
    }

    /// Returns the retained exact pre-import settings backup, or `None` for a missing base.
    pub fn settings_backup_path(&self) -> Option<&Path> {
        self.settings_backup_path.as_deref()
    }

    /// Returns the revision of the exact legacy bytes parsed for import.
    pub const fn source_revision(&self) -> &Revision {
        &self.source_revision
    }

    /// Returns the revision independently recomputed from the reread backup bytes.
    pub const fn backup_revision(&self) -> &Revision {
        &self.backup_revision
    }

    /// Returns the User Settings revision against which the import was previewed.
    pub const fn base_settings_revision(&self) -> &Revision {
        &self.base_settings_revision
    }

    /// Returns the revision produced by the all-or-nothing User Settings commit.
    pub const fn published_settings_revision(&self) -> &Revision {
        &self.published_settings_revision
    }

    /// Explicitly restores the verified User Settings base replaced by this import.
    ///
    /// Restore conflict-checks the imported revision under User Settings coordination, rereads
    /// and verifies the retained pre-import settings backup when one exists, and atomically
    /// republishes it. A missing pre-import base removes the imported canonical document while
    /// retaining both import backups and the dormant legacy `state.json`.
    pub fn restore(
        &self,
        classic_root: impl AsRef<Path>,
    ) -> Result<LegacyTuiStateImportRestoreOutcome, LegacyTuiStateImportError> {
        self.restore_with_publisher(classic_root.as_ref(), &SystemPublisher::system())
    }

    /// Runs restoration through the durable publication seam used by fault tests.
    fn restore_with_publisher(
        &self,
        classic_root: &Path,
        publisher: &impl Publisher,
    ) -> Result<LegacyTuiStateImportRestoreOutcome, LegacyTuiStateImportError> {
        let expected_settings_path = classic_root.join(CANONICAL_FILENAME);
        if self.settings_path != expected_settings_path {
            return Err(LegacyTuiStateImportError::new(
                "legacy_tui_state_restore_root_mismatch",
                "the restore root does not match the root recorded by this import receipt",
            ));
        }
        let _lock = acquire_commit_lock(&self.settings_path).map_err(map_restore_commit_error)?;
        let latest = UserSettings::open(classic_root);
        if latest.revision() != &self.published_settings_revision {
            return Ok(LegacyTuiStateImportRestoreOutcome::Conflict {
                expected_revision: self.published_settings_revision.clone(),
                actual_revision: latest.revision().clone(),
            });
        }
        let imported_bytes = latest.original_bytes().ok_or_else(|| {
            LegacyTuiStateImportError::new(
                "legacy_tui_state_restore_source_unavailable",
                "the imported User Settings bytes were unavailable while the restore lock was held",
            )
        })?;

        match &self.settings_backup_path {
            Some(backup_path) => {
                let restored_bytes = std::fs::read(backup_path).map_err(|error| {
                    LegacyTuiStateImportError::new(
                        "legacy_tui_state_restore_backup_read_failed",
                        format!("could not read {}: {error}", backup_path.display()),
                    )
                })?;
                if content_revision(&restored_bytes) != self.base_settings_revision {
                    return Err(LegacyTuiStateImportError::new(
                        "legacy_tui_state_restore_backup_verify_failed",
                        format!(
                            "retained settings backup {} no longer matches its verified revision",
                            backup_path.display()
                        ),
                    ));
                }
                publisher
                    .publish(&self.settings_path, &restored_bytes)
                    .map_err(map_restore_publication_error)?;
                let reopened = UserSettings::open(classic_root);
                if reopened.revision() != &self.base_settings_revision
                    || reopened.original_bytes() != Some(restored_bytes.as_slice())
                {
                    return Err(rollback_failed_restore(
                        publisher,
                        classic_root,
                        &self.settings_path,
                        imported_bytes,
                        &self.published_settings_revision,
                        "restored User Settings did not reopen as the verified pre-import backup",
                    ));
                }
            }
            None => {
                if self.base_settings_revision != Revision::Missing {
                    return Err(LegacyTuiStateImportError::new(
                        "legacy_tui_state_restore_backup_missing",
                        "the import receipt has no settings backup for a non-missing base",
                    ));
                }
                std::fs::remove_file(&self.settings_path).map_err(|error| {
                    LegacyTuiStateImportError::new(
                        "legacy_tui_state_restore_remove_failed",
                        format!("could not remove {}: {error}", self.settings_path.display()),
                    )
                })?;
                if UserSettings::open(classic_root).revision() != &Revision::Missing {
                    return Err(rollback_failed_restore(
                        publisher,
                        classic_root,
                        &self.settings_path,
                        imported_bytes,
                        &self.published_settings_revision,
                        "restored missing User Settings base did not reopen as missing",
                    ));
                }
            }
        }

        Ok(LegacyTuiStateImportRestoreOutcome::Restored {
            revision: self.base_settings_revision.clone(),
        })
    }
}

/// Operational or validation failure encountered during a legacy TUI state import.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LegacyTuiStateImportError {
    code: &'static str,
    message: String,
}

impl LegacyTuiStateImportError {
    /// Builds one stage-specific import failure.
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

    /// Returns human-readable context for the failed import stage.
    pub fn message(&self) -> &str {
        &self.message
    }
}

impl fmt::Display for LegacyTuiStateImportError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}: {}", self.code, self.message)
    }
}

impl std::error::Error for LegacyTuiStateImportError {}

/// Explicitly imports one retired TUI `state.json` document into canonical User Settings.
///
/// The caller supplies both the CLASSIC root and concrete legacy source path. The operation only
/// accepts a trusted current-compatible or missing settings base, retains and rereads an exact
/// content-addressed backup, then previews and commits all three remembered fields together. The
/// legacy source remains in place and is never renamed, truncated, or deleted.
pub fn import_legacy_tui_state(
    classic_root: impl AsRef<Path>,
    legacy_state_path: impl AsRef<Path>,
) -> Result<LegacyTuiStateImportOutcome, LegacyTuiStateImportError> {
    import_with_publisher(
        classic_root.as_ref(),
        legacy_state_path.as_ref(),
        &SystemPublisher::system(),
    )
}

/// Runs the import algorithm through the durable publication seam used by fault tests.
fn import_with_publisher(
    classic_root: &Path,
    legacy_state_path: &Path,
    publisher: &impl Publisher,
) -> Result<LegacyTuiStateImportOutcome, LegacyTuiStateImportError> {
    let source_bytes = match std::fs::read(legacy_state_path) {
        Ok(bytes) => bytes,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            return Ok(LegacyTuiStateImportOutcome::NoLegacySource);
        }
        Err(error) => {
            return Err(LegacyTuiStateImportError::new(
                "legacy_tui_state_read_failed",
                format!("could not read {}: {error}", legacy_state_path.display()),
            ));
        }
    };
    let state = parse_legacy_state(&source_bytes)?;
    let source_revision = content_revision(&source_bytes);

    let settings = UserSettings::open(classic_root);
    match settings.commit_eligibility() {
        CommitEligibility::RequiresMigration => {
            return Ok(LegacyTuiStateImportOutcome::RequiresSettingsMigration {
                classification: settings.classification(),
                revision: settings.revision().clone(),
            });
        }
        CommitEligibility::BlockedUntrusted => {
            return Ok(LegacyTuiStateImportOutcome::UntrustedSettingsBase {
                classification: settings.classification(),
                revision: settings.revision().clone(),
            });
        }
        CommitEligibility::Eligible => {}
    }
    let base_settings_revision = settings.revision().clone();
    let pre_import_settings_bytes = settings.original_bytes().map(<[u8]>::to_vec);
    let settings_path = classic_root.join(CANONICAL_FILENAME);

    if let Some(conflict) =
        legacy_source_conflict(legacy_state_path, &source_bytes, &source_revision)?
    {
        return Ok(conflict);
    }

    let backup_path = backup_path(classic_root, &source_bytes);
    let backup_parent = backup_path.parent().ok_or_else(|| {
        LegacyTuiStateImportError::new(
            "legacy_tui_state_backup_directory_failed",
            format!("backup path has no parent: {}", backup_path.display()),
        )
    })?;
    std::fs::create_dir_all(backup_parent).map_err(|error| {
        LegacyTuiStateImportError::new(
            "legacy_tui_state_backup_directory_failed",
            format!("could not create {}: {error}", backup_parent.display()),
        )
    })?;
    publisher
        .publish(&backup_path, &source_bytes)
        .map_err(map_backup_publication_error)?;
    let verified_backup = std::fs::read(&backup_path).map_err(|error| {
        LegacyTuiStateImportError::new(
            "legacy_tui_state_backup_verify_failed",
            format!("could not reread {}: {error}", backup_path.display()),
        )
    })?;
    if verified_backup != source_bytes {
        return Err(LegacyTuiStateImportError::new(
            "legacy_tui_state_backup_verify_failed",
            format!(
                "retained backup {} did not match the exact legacy source bytes",
                backup_path.display()
            ),
        ));
    }
    let backup_revision = content_revision(&verified_backup);

    let settings_backup_path = if let Some(settings_bytes) = &pre_import_settings_bytes {
        let path = settings_backup_path(classic_root, settings_bytes);
        publisher
            .publish(&path, settings_bytes)
            .map_err(map_settings_backup_publication_error)?;
        let verified_settings_backup = std::fs::read(&path).map_err(|error| {
            LegacyTuiStateImportError::new(
                "legacy_tui_state_settings_backup_verify_failed",
                format!("could not reread {}: {error}", path.display()),
            )
        })?;
        if verified_settings_backup != *settings_bytes {
            return Err(LegacyTuiStateImportError::new(
                "legacy_tui_state_settings_backup_verify_failed",
                format!(
                    "retained settings backup {} did not match the exact pre-import bytes",
                    path.display()
                ),
            ));
        }
        Some(path)
    } else {
        None
    };

    // A second source check closes the potentially slow durable-backup window. The content-
    // addressed backup is retained even on conflict because it still exactly attests the bytes
    // that were parsed, while the live legacy source remains untouched.
    if let Some(conflict) =
        legacy_source_conflict(legacy_state_path, &source_bytes, &source_revision)?
    {
        return Ok(conflict);
    }

    let latest = UserSettings::open(classic_root);
    if latest.revision() != &base_settings_revision {
        return Ok(LegacyTuiStateImportOutcome::SettingsConflict {
            expected_revision: base_settings_revision,
            actual_revision: latest.revision().clone(),
        });
    }
    let update = UserSettingsUpdate::new().with_tui_remembered_state(
        i64::from(state.active_tab),
        i64::from(state.results_panel_width),
        state.sort_ascending,
    );
    let preview = if matches!(latest.revision(), Revision::Missing) {
        latest.preview_bootstrap(update)
    } else {
        latest.preview_update(update)
    };
    let accepted = match preview {
        UserSettingsUpdatePreview::Accepted(accepted) => accepted,
        UserSettingsUpdatePreview::Rejected(diagnostics) => {
            return Err(LegacyTuiStateImportError::new(
                "legacy_tui_state_preview_failed",
                format!("validated legacy state was rejected during preview: {diagnostics:?}"),
            ));
        }
    };
    let outcome = accepted
        .commit(classic_root)
        .map_err(map_settings_commit_error)?;
    let published_settings_revision = match outcome {
        UserSettingsCommitOutcome::Committed { revision } => revision,
        UserSettingsCommitOutcome::Conflict {
            expected_revision,
            actual_revision,
        } => {
            return Ok(LegacyTuiStateImportOutcome::SettingsConflict {
                expected_revision,
                actual_revision,
            });
        }
    };

    Ok(LegacyTuiStateImportOutcome::Applied(
        LegacyTuiStateImportReceipt {
            source_path: legacy_state_path.to_path_buf(),
            backup_path,
            settings_path,
            settings_backup_path,
            source_revision,
            backup_revision,
            base_settings_revision,
            published_settings_revision,
        },
    ))
}

/// Valid remembered state decoded from the exact legacy JSON object.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct LegacyTuiState {
    active_tab: u8,
    results_panel_width: u16,
    sort_ascending: bool,
}

/// Parses the three maintained fields while intentionally ignoring future JSON members.
fn parse_legacy_state(bytes: &[u8]) -> Result<LegacyTuiState, LegacyTuiStateImportError> {
    let value: Value = serde_json::from_slice(bytes).map_err(|error| {
        LegacyTuiStateImportError::new(
            "legacy_tui_state_parse_failed",
            format!("legacy TUI state is not valid JSON: {error}"),
        )
    })?;
    let object = value.as_object().ok_or_else(|| {
        LegacyTuiStateImportError::new(
            "legacy_tui_state_root_not_object",
            "legacy TUI state must be a JSON object",
        )
    })?;
    let active_tab = object
        .get("active_tab")
        .and_then(Value::as_u64)
        .and_then(|value| u8::try_from(value).ok())
        .filter(|value| *value <= 3)
        .ok_or_else(|| {
            LegacyTuiStateImportError::new(
                "legacy_tui_state_active_tab_invalid",
                "legacy TUI active_tab must be an integer from 0 through 3",
            )
        })?;
    let results_panel_width = object
        .get("results_panel_width")
        .and_then(Value::as_u64)
        .and_then(|value| u16::try_from(value).ok())
        .ok_or_else(|| {
            LegacyTuiStateImportError::new(
                "legacy_tui_state_results_panel_width_invalid",
                "legacy TUI results_panel_width must be an unsigned 16-bit integer",
            )
        })?;
    let sort_ascending = object
        .get("sort_ascending")
        .and_then(Value::as_bool)
        .ok_or_else(|| {
            LegacyTuiStateImportError::new(
                "legacy_tui_state_sort_ascending_invalid",
                "legacy TUI sort_ascending must be a boolean",
            )
        })?;

    Ok(LegacyTuiState {
        active_tab,
        results_panel_width,
        sort_ascending,
    })
}

/// Rereads one concrete legacy path and returns a typed conflict when its identity changed.
fn legacy_source_conflict(
    path: &Path,
    expected_bytes: &[u8],
    expected_revision: &Revision,
) -> Result<Option<LegacyTuiStateImportOutcome>, LegacyTuiStateImportError> {
    let (actual_bytes, actual_revision) = match std::fs::read(path) {
        Ok(bytes) => {
            let revision = content_revision(&bytes);
            (Some(bytes), revision)
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => (None, Revision::Missing),
        Err(error) => {
            return Err(LegacyTuiStateImportError::new(
                "legacy_tui_state_reread_failed",
                format!("could not reread {}: {error}", path.display()),
            ));
        }
    };
    Ok((actual_bytes.as_deref() != Some(expected_bytes)).then(|| {
        LegacyTuiStateImportOutcome::LegacySourceConflict {
            expected_revision: expected_revision.clone(),
            actual_revision,
        }
    }))
}

/// Returns the content-addressed retained backup path for exact legacy JSON bytes.
fn backup_path(classic_root: &Path, bytes: &[u8]) -> PathBuf {
    let digest = Sha256::digest(bytes);
    let name = format!("{}.json", hex_digest(&digest));
    classic_root.join(BACKUP_RELATIVE_DIRECTORY).join(name)
}

/// Returns the content-addressed retained backup path for pre-import User Settings bytes.
fn settings_backup_path(classic_root: &Path, bytes: &[u8]) -> PathBuf {
    let digest = Sha256::digest(bytes);
    let name = format!("{}.yaml", hex_digest(&digest));
    classic_root.join(BACKUP_RELATIVE_DIRECTORY).join(name)
}

/// Converts exact bytes into the crate's content-derived revision.
fn content_revision(bytes: &[u8]) -> Revision {
    Revision::ContentSha256(Sha256::digest(bytes).into())
}

/// Retains the exact durable-publication stage in the import error vocabulary.
fn map_backup_publication_error(
    error: crate::UserSettingsCommitError,
) -> LegacyTuiStateImportError {
    let code = match error.code() {
        "commit_temp_create_failed" => "legacy_tui_state_backup_temp_create_failed",
        "commit_temp_write_failed" => "legacy_tui_state_backup_temp_write_failed",
        "commit_temp_flush_failed" => "legacy_tui_state_backup_temp_flush_failed",
        "commit_temp_sync_failed" => "legacy_tui_state_backup_temp_sync_failed",
        "commit_replace_failed" => "legacy_tui_state_backup_replace_failed",
        "commit_temp_cleanup_failed" => "legacy_tui_state_backup_temp_cleanup_failed",
        _ => "legacy_tui_state_backup_publish_failed",
    };
    LegacyTuiStateImportError::new(code, error.to_string())
}

/// Retains the durable stage used to back up the pre-import User Settings bytes.
fn map_settings_backup_publication_error(
    error: crate::UserSettingsCommitError,
) -> LegacyTuiStateImportError {
    let code = match error.code() {
        "commit_temp_create_failed" => "legacy_tui_state_settings_backup_temp_create_failed",
        "commit_temp_write_failed" => "legacy_tui_state_settings_backup_temp_write_failed",
        "commit_temp_flush_failed" => "legacy_tui_state_settings_backup_temp_flush_failed",
        "commit_temp_sync_failed" => "legacy_tui_state_settings_backup_temp_sync_failed",
        "commit_replace_failed" => "legacy_tui_state_settings_backup_replace_failed",
        "commit_temp_cleanup_failed" => "legacy_tui_state_settings_backup_temp_cleanup_failed",
        _ => "legacy_tui_state_settings_backup_publish_failed",
    };
    LegacyTuiStateImportError::new(code, error.to_string())
}

/// Retains the exact lock, reconstruction, patch, or publication stage of settings commit errors.
fn map_settings_commit_error(error: crate::UserSettingsCommitError) -> LegacyTuiStateImportError {
    let code = match error.code() {
        "commit_lock_open_failed" => "legacy_tui_state_commit_lock_open_failed",
        "commit_lock_failed" => "legacy_tui_state_commit_lock_failed",
        "commit_source_unavailable" => "legacy_tui_state_commit_source_unavailable",
        "commit_missing_requires_bootstrap" => "legacy_tui_state_commit_missing_requires_bootstrap",
        "commit_bootstrap_defaults_failed" => "legacy_tui_state_commit_bootstrap_defaults_failed",
        "commit_parse_failed" => "legacy_tui_state_commit_parse_failed",
        "commit_serialize_failed" => "legacy_tui_state_commit_serialize_failed",
        "commit_patch_failed" => "legacy_tui_state_commit_patch_failed",
        "commit_temp_create_failed" => "legacy_tui_state_commit_temp_create_failed",
        "commit_temp_write_failed" => "legacy_tui_state_commit_temp_write_failed",
        "commit_temp_flush_failed" => "legacy_tui_state_commit_temp_flush_failed",
        "commit_temp_sync_failed" => "legacy_tui_state_commit_temp_sync_failed",
        "commit_replace_failed" => "legacy_tui_state_commit_replace_failed",
        "commit_temp_cleanup_failed" => "legacy_tui_state_commit_temp_cleanup_failed",
        _ => "legacy_tui_state_commit_failed",
    };
    LegacyTuiStateImportError::new(code, error.to_string())
}

/// Maps restore lock failures without erasing whether open or acquisition failed.
fn map_restore_commit_error(error: crate::UserSettingsCommitError) -> LegacyTuiStateImportError {
    let code = match error.code() {
        "commit_lock_open_failed" => "legacy_tui_state_restore_lock_open_failed",
        "commit_lock_failed" => "legacy_tui_state_restore_lock_failed",
        _ => "legacy_tui_state_restore_lock_failed",
    };
    LegacyTuiStateImportError::new(code, error.to_string())
}

/// Maps durable restore publication failures into stable restore-stage categories.
fn map_restore_publication_error(
    error: crate::UserSettingsCommitError,
) -> LegacyTuiStateImportError {
    let code = match error.code() {
        "commit_temp_create_failed" => "legacy_tui_state_restore_temp_create_failed",
        "commit_temp_write_failed" => "legacy_tui_state_restore_temp_write_failed",
        "commit_temp_flush_failed" => "legacy_tui_state_restore_temp_flush_failed",
        "commit_temp_sync_failed" => "legacy_tui_state_restore_temp_sync_failed",
        "commit_replace_failed" => "legacy_tui_state_restore_replace_failed",
        "commit_temp_cleanup_failed" => "legacy_tui_state_restore_temp_cleanup_failed",
        _ => "legacy_tui_state_restore_publish_failed",
    };
    LegacyTuiStateImportError::new(code, error.to_string())
}

/// Republishes the imported bytes when post-restore verification unexpectedly fails.
fn rollback_failed_restore(
    publisher: &impl Publisher,
    classic_root: &Path,
    settings_path: &Path,
    imported_bytes: &[u8],
    imported_revision: &Revision,
    message: &str,
) -> LegacyTuiStateImportError {
    let verification =
        LegacyTuiStateImportError::new("legacy_tui_state_restore_reopen_verify_failed", message);
    if let Err(rollback) = publisher.publish(settings_path, imported_bytes) {
        return LegacyTuiStateImportError::new(
            "legacy_tui_state_restore_rollback_failed",
            format!("{verification}; rollback also failed: {rollback}"),
        );
    }
    let reopened = UserSettings::open(classic_root);
    if reopened.revision() != imported_revision || reopened.original_bytes() != Some(imported_bytes)
    {
        return LegacyTuiStateImportError::new(
            "legacy_tui_state_restore_rollback_verify_failed",
            format!("{verification}; rollback did not reopen the imported document"),
        );
    }
    verification
}

/// Formats a binary digest without adding another dependency to the public crate surface.
fn hex_digest(bytes: &[u8]) -> String {
    use fmt::Write as _;

    let mut encoded = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        write!(&mut encoded, "{byte:02x}").expect("writing to a String cannot fail");
    }
    encoded
}

#[cfg(test)]
#[path = "legacy_tui_state_import_tests.rs"]
mod tests;
