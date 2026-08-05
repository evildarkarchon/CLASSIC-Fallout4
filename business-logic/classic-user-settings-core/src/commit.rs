//! Conflict-safe publication of accepted User Settings Updates.

use crate::default_settings::published_defaults_document;
use crate::{
    AcceptedUserSettingsUpdate, GuiWindow, Revision, UpdateDiagnostic, UserSettings,
    UserSettingsUpdate, UserSettingsUpdateField, UserSettingsUpdatePreview,
};
use classic_durable_publication as durable_publication;
use classic_settings_core::{Yaml, YamlOperations, parse_yaml_content};
use sha2::{Digest, Sha256};
use std::fmt;
use std::path::Path;

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

/// Result of publishing one replay-safe frontend geometry transition.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum UserSettingsFrontendTransitionOutcome {
    /// The transition was published, possibly after one conflict retry.
    Committed {
        /// SHA-256 revision of the newly published document.
        revision: Revision,
    },
    /// The transition was invalid against the snapshot used by the final attempt.
    Rejected {
        /// Structured validation diagnostics for the complete transition.
        diagnostics: Vec<UpdateDiagnostic>,
    },
    /// A second concurrent edit won after the one allowed replay attempt.
    Conflict {
        /// Revision against which the final retry was accepted.
        expected_revision: Revision,
        /// Newer revision found while publishing the retry.
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

impl UserSettings {
    /// Publishes one accepted GUI geometry transition with at most one conflict replay.
    ///
    /// Geometry is replay-safe because it contains only the completed widget transition, not
    /// other editable form values. The core reopens and revalidates the complete transition for
    /// each attempt; a second concurrent edit is returned as a conflict without being overwritten.
    /// Operational reopen, lock, parse, and publication failures return
    /// [`UserSettingsCommitError`] without partially persisting the transition.
    pub fn commit_frontend_geometry_transition(
        classic_root: impl AsRef<Path>,
        expected_revision: &Revision,
        window: GuiWindow,
        maximized: bool,
        width: i64,
        height: i64,
    ) -> Result<UserSettingsFrontendTransitionOutcome, UserSettingsCommitError> {
        let classic_root = classic_root.as_ref();
        let update =
            UserSettingsUpdate::new().with_window_geometry(window, maximized, width, height);
        let first =
            commit_frontend_transition_attempt(classic_root, expected_revision, update.clone())?;
        let UserSettingsFrontendTransitionOutcome::Conflict {
            actual_revision, ..
        } = first
        else {
            return Ok(first);
        };

        commit_frontend_transition_attempt(classic_root, &actual_revision, update)
    }
}

/// Reopens, validates, and publishes one geometry transition against one expected revision.
fn commit_frontend_transition_attempt(
    classic_root: &Path,
    expected_revision: &Revision,
    update: UserSettingsUpdate,
) -> Result<UserSettingsFrontendTransitionOutcome, UserSettingsCommitError> {
    let settings = UserSettings::open(classic_root);
    if matches!(settings.revision(), Revision::Unavailable) {
        return Err(UserSettingsCommitError::new(
            "commit_source_unavailable",
            "User Settings could not be reopened before the frontend transition commit",
        ));
    }
    if settings.revision() != expected_revision {
        return Ok(UserSettingsFrontendTransitionOutcome::Conflict {
            expected_revision: expected_revision.clone(),
            actual_revision: settings.revision().clone(),
        });
    }

    let accepted = match settings.preview_update(update) {
        UserSettingsUpdatePreview::Accepted(accepted) => accepted,
        UserSettingsUpdatePreview::Rejected(diagnostics) => {
            return Ok(UserSettingsFrontendTransitionOutcome::Rejected { diagnostics });
        }
    };
    match accepted.commit(classic_root)? {
        UserSettingsCommitOutcome::Committed { revision } => {
            Ok(UserSettingsFrontendTransitionOutcome::Committed { revision })
        }
        UserSettingsCommitOutcome::Conflict {
            expected_revision,
            actual_revision,
        } => Ok(UserSettingsFrontendTransitionOutcome::Conflict {
            expected_revision,
            actual_revision,
        }),
    }
}

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
        self.commit_with_publisher(classic_root.as_ref(), &SystemPublisher::system())
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
        let document = latest_document(&latest, self.is_bootstrap())?;
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

/// Returns the one cross-process lock policy every User Settings publication shares.
///
/// The suffix is appended to the whole target path, so the lock file is exactly the
/// `CLASSIC Settings.yaml.commit.lock` sibling this crate has always used. Nothing on disk moved
/// when the implementation behind it did.
fn commit_lock_policy() -> durable_publication::LockPolicy {
    durable_publication::LockPolicy::sibling(COMMIT_LOCK_SUFFIX)
}

/// Opens and exclusively locks the persistent sibling coordination file.
///
/// The lock itself is the workspace's single cross-process implementation, from
/// `classic-durable-publication`. Because this guard already spans every publication in a commit,
/// migration, or import sequence, the publications made underneath it pass
/// [`durable_publication::LockPolicy::none`]: a second lock scoped to one publication would
/// release before the sequence it exists to protect had finished.
pub(crate) fn acquire_commit_lock(
    target: &Path,
) -> Result<durable_publication::PublicationLock, UserSettingsCommitError> {
    let lock = commit_lock_policy()
        .acquire(target)
        .map_err(map_lock_error)?;
    // Only `LockPolicy::none` yields `None`, and this policy is always a sibling.
    Ok(lock.expect("a sibling lock policy always names a lock file"))
}

/// Preserves this crate's two published lock codes, and their messages, across the adoption.
fn map_lock_error(error: durable_publication::PublicationError) -> UserSettingsCommitError {
    match error {
        durable_publication::PublicationError::LockOpen { path, source } => {
            UserSettingsCommitError::new(
                "commit_lock_open_failed",
                format!("could not open {}: {source}", path.display()),
            )
        }
        durable_publication::PublicationError::LockAcquire { path, source } => {
            UserSettingsCommitError::new(
                "commit_lock_failed",
                format!("could not lock {}: {source}", path.display()),
            )
        }
        // Every remaining variant belongs to a publication, and this function only ever acquires
        // a lock, so none of them can arrive here. They are listed rather than caught by a
        // wildcard so that a new variant in the shared module fails this build instead of being
        // silently absorbed — and mapped rather than panicked on so that reaching one somehow
        // cannot turn into an abort.
        other @ (durable_publication::PublicationError::Stage { .. }
        | durable_publication::PublicationError::BackupUnreadable { .. }
        | durable_publication::PublicationError::StagedUnreadable { .. }
        | durable_publication::PublicationError::DigestMismatch { .. }
        | durable_publication::PublicationError::BackupMismatch { .. }) => {
            UserSettingsCommitError::new("commit_lock_failed", other.to_string())
        }
    }
}

/// Reconstructs the latest trusted YAML document, including first-run missing state.
fn latest_document(
    settings: &UserSettings,
    bootstrap: bool,
) -> Result<Yaml, UserSettingsCommitError> {
    let Some(bytes) = settings.original_bytes() else {
        if matches!(settings.revision(), Revision::Missing) {
            if bootstrap {
                return published_defaults_document().map_err(|error| {
                    UserSettingsCommitError::new("commit_bootstrap_defaults_failed", error)
                });
            }
            return Err(UserSettingsCommitError::new(
                "commit_missing_requires_bootstrap",
                "Missing User Settings cannot be created by an ordinary update",
            ));
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
        | UserSettingsUpdateField::AutoSwitchAfterScan(value)
        | UserSettingsUpdateField::WindowMaximized(_, value)
        | UserSettingsUpdateField::TuiSortAscending(value)
        | UserSettingsUpdateField::FcxMode(value)
        | UserSettingsUpdateField::SimplifyLogs(value)
        | UserSettingsUpdateField::ShowStatistics(value)
        | UserSettingsUpdateField::FormIdValueLookup(value)
        | UserSettingsUpdateField::MoveUnsolvedLogs(value) => Yaml::Boolean(*value),
        UserSettingsUpdateField::ManagedGame(value) => Yaml::String(value.as_str().to_string()),
        UserSettingsUpdateField::UpdateSource(value) => Yaml::String(value.as_str().to_string()),
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
        UserSettingsUpdateField::MaxConcurrentScans(value)
        | UserSettingsUpdateField::WindowWidth(_, value)
        | UserSettingsUpdateField::WindowHeight(_, value) => Yaml::Integer(i64::from(*value)),
        UserSettingsUpdateField::TuiActiveTab(value) => Yaml::Integer(i64::from(*value)),
        UserSettingsUpdateField::TuiResultsPanelWidth(value) => Yaml::Integer(i64::from(*value)),
    }
}

/// Injectable boundary for durable, atomic document publication.
pub(crate) trait Publisher {
    /// Publishes `bytes` at `target` or returns a stage-specific failure before replacement.
    fn publish(&self, target: &Path, bytes: &[u8]) -> Result<(), UserSettingsCommitError>;
}

/// Production publisher backed by the workspace's shared Durable Publication module.
pub(crate) struct SystemPublisher;

/// The workspace's single publication stage vocabulary, under this crate's local name.
///
/// This crate keeps no stage definition of its own. What it keeps is the projection below: the
/// shared module owns the five-state sequence, and this crate owns what each state is *called* on
/// the way out.
pub(crate) use durable_publication::PublicationStage;

/// Projects a publication stage onto the error code this crate publishes for it.
///
/// This is an extension rather than a rename because the two vocabularies genuinely disagree at
/// the end. The shared module's terminal stage is `Publish`; this crate has always published
/// `commit_replace_failed`, and every operation-specific code in `migration_persistence` and
/// `legacy_tui_state_import` is derived from that string. Collapsing onto the shared type must
/// not collapse that name with it.
pub(crate) trait CommitPublicationStage {
    /// Returns the public error code corresponding to this publication stage.
    fn error_code(self) -> &'static str;

    /// Builds the failure this crate reports when a publication fails at this stage.
    ///
    /// This is the only way to construct a stage failure outside this module, which is what lets
    /// [`UserSettingsCommitError::new`] stay private: the test fakes that stand in for the
    /// publisher need a stage failure specifically, not a general-purpose error constructor.
    fn failure(self, detail: impl fmt::Display) -> UserSettingsCommitError;
}

impl CommitPublicationStage for PublicationStage {
    fn error_code(self) -> &'static str {
        match self {
            Self::Create => "commit_temp_create_failed",
            Self::Write => "commit_temp_write_failed",
            Self::Flush => "commit_temp_flush_failed",
            Self::Sync => "commit_temp_sync_failed",
            // The shared vocabulary calls this stage `Publish`. Mapping it to anything but
            // `commit_replace_failed` would silently retire that published code and every
            // operation code derived from it, across three bindings at once.
            Self::Publish => "commit_replace_failed",
        }
    }

    fn failure(self, detail: impl fmt::Display) -> UserSettingsCommitError {
        UserSettingsCommitError::new(self.error_code(), detail.to_string())
    }
}

impl SystemPublisher {
    /// Builds the production durable publisher.
    pub(crate) const fn system() -> Self {
        Self
    }
}

impl Publisher for SystemPublisher {
    fn publish(&self, target: &Path, bytes: &[u8]) -> Result<(), UserSettingsCommitError> {
        // Every call site holds `acquire_commit_lock` across its complete sequence, so the
        // publication takes no lock of its own. Cross-process serialization is unchanged: it is
        // the same lock file, held over a strictly wider window than one publication.
        let publication =
            durable_publication::publish(target, bytes, &durable_publication::LockPolicy::none())
                .map_err(|error| map_publication_error(&error))?;

        // Durability uncertainty is deliberately discarded rather than reported. Surfacing it
        // would require new stable codes across the C++, Node, and Python bindings plus
        // refreshed parity baselines. Follow-up: GitHub issue #153 ("Deepen Durable
        // Publication"), under "Out of Scope" — "Surfacing durability uncertainty on User
        // Settings commit ... tracked separately".
        //
        // The previous implementation discarded the same signal by not checking the
        // parent-directory fsync at all, which was invisible. Naming it here does not change
        // behavior; it makes the decision reviewable.
        let _commit_durability = publication.into_durability();
        Ok(())
    }
}

/// Projects a neutral durable publication failure onto this crate's stable commit codes.
///
/// The message keeps the underlying filesystem failure, which the shared module carries as a
/// `#[source]` and therefore leaves out of its own `Display`.
fn map_publication_error(error: &durable_publication::PublicationError) -> UserSettingsCommitError {
    let message = match error.io_source() {
        Some(source) => format!("{error}: {source}"),
        None => error.to_string(),
    };
    match error {
        // Built through `CommitPublicationStage::failure` rather than by naming a code here, so
        // that a real stage failure and the one a test fake stands in for are constructed
        // identically.
        durable_publication::PublicationError::Stage { stage, .. } => stage.failure(message),
        // Unreachable while this seam passes `LockPolicy::none`, but mapped rather than panicked
        // on so that a future policy change cannot turn into an abort.
        durable_publication::PublicationError::LockOpen { .. } => {
            UserSettingsCommitError::new("commit_lock_open_failed", message)
        }
        durable_publication::PublicationError::LockAcquire { .. } => {
            UserSettingsCommitError::new("commit_lock_failed", message)
        }
        // The verified-backup and verified-install operations are not reachable through this
        // seam, which only ever calls `publish`, so none of these can arrive. They are listed
        // rather than caught by a wildcard so that a new variant in the shared module fails this
        // build and gets a deliberate code, instead of silently inheriting one. The terminal stage
        // is the honest fallback for the ones that exist today: no replacement took place.
        durable_publication::PublicationError::BackupUnreadable { .. }
        | durable_publication::PublicationError::StagedUnreadable { .. }
        | durable_publication::PublicationError::DigestMismatch { .. }
        | durable_publication::PublicationError::BackupMismatch { .. } => {
            PublicationStage::Publish.failure(message)
        }
    }
}

#[cfg(test)]
#[path = "commit_tests.rs"]
mod tests;
