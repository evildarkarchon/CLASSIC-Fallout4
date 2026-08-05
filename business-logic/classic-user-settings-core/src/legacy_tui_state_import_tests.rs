use super::*;
use crate::UserSettingsCommitError;
use crate::commit::PublicationStage;
use std::cell::Cell;

/// Pure fake that returns one publication stage failure and touches no files.
///
/// Import's first publication is its backup, so failing on the first call is what exercises the
/// backup-stage projection. The staging sequence this used to interleave with now lives in
/// `classic-durable-publication`, leaving nothing in this crate to inject into.
struct StageFailurePublisher {
    stage: PublicationStage,
}

impl StageFailurePublisher {
    /// Builds a publisher that always fails at `stage`.
    const fn new(stage: PublicationStage) -> Self {
        Self { stage }
    }
}

impl Publisher for StageFailurePublisher {
    /// Returns the stage's stable failure and performs no filesystem work at all.
    fn publish(&self, _target: &Path, _bytes: &[u8]) -> Result<(), UserSettingsCommitError> {
        Err(self
            .stage
            .failure(format!("injected {:?} failure", self.stage)))
    }
}

/// Durable publisher that performs one external edit immediately after backup publication.
struct EditAfterBackup {
    inner: SystemPublisher,
    edit_path: PathBuf,
    edit_bytes: Vec<u8>,
    edited: Cell<bool>,
}

impl EditAfterBackup {
    /// Builds one deterministic concurrency edit at the public backup boundary.
    fn new(edit_path: PathBuf, edit_bytes: impl Into<Vec<u8>>) -> Self {
        Self {
            inner: SystemPublisher::system(),
            edit_path,
            edit_bytes: edit_bytes.into(),
            edited: Cell::new(false),
        }
    }
}

impl Publisher for EditAfterBackup {
    /// Publishes exact bytes, then simulates an external writer during the backup window.
    fn publish(&self, target: &Path, bytes: &[u8]) -> Result<(), UserSettingsCommitError> {
        self.inner.publish(target, bytes)?;
        if !self.edited.replace(true) {
            std::fs::write(&self.edit_path, &self.edit_bytes).unwrap();
        }
        Ok(())
    }
}

/// Publisher that corrupts the retained artifact before the import can verify it.
struct CorruptBackup {
    inner: SystemPublisher,
}

impl CorruptBackup {
    /// Builds a deterministic backup-reread verification fault.
    fn new() -> Self {
        Self {
            inner: SystemPublisher::system(),
        }
    }
}

impl Publisher for CorruptBackup {
    /// Publishes normally and then changes the visible artifact before its reread.
    fn publish(&self, target: &Path, bytes: &[u8]) -> Result<(), UserSettingsCommitError> {
        self.inner.publish(target, bytes)?;
        std::fs::write(target, b"corrupted after publication").unwrap();
        Ok(())
    }
}

/// Writes a trusted settings base and valid legacy TUI source for conflict tests.
fn install_sources(root: &Path) -> (PathBuf, PathBuf, Vec<u8>) {
    let settings_path = root.join("CLASSIC Settings.yaml");
    let settings_bytes = br#"schema_version: "1.0"
CLASSIC_Settings:
  Update Check: true
"#
    .to_vec();
    std::fs::write(&settings_path, &settings_bytes).unwrap();
    let legacy_path = root.join("state.json");
    std::fs::write(
        &legacy_path,
        br#"{"active_tab":2,"results_panel_width":44,"sort_ascending":true}"#,
    )
    .unwrap();
    (settings_path, legacy_path, settings_bytes)
}

#[test]
fn settings_edit_during_backup_returns_a_settings_conflict_without_overwrite() {
    let root = tempfile::tempdir().unwrap();
    let (settings_path, legacy_path, _) = install_sources(root.path());
    let newer = br#"schema_version: "1.0"
CLASSIC_Settings:
  Update Check: false
External:
  edit: concurrent
"#;

    let outcome = import_with_publisher(
        root.path(),
        &legacy_path,
        &EditAfterBackup::new(settings_path.clone(), newer.as_slice()),
    )
    .unwrap();

    assert!(matches!(
        outcome,
        LegacyTuiStateImportOutcome::SettingsConflict { .. }
    ));
    assert_eq!(std::fs::read(settings_path).unwrap(), newer);
}

#[test]
fn legacy_edit_during_backup_returns_a_source_conflict_and_leaves_it_dormant() {
    let root = tempfile::tempdir().unwrap();
    let (settings_path, legacy_path, settings_bytes) = install_sources(root.path());
    let newer = br#"{"active_tab":1,"results_panel_width":12,"sort_ascending":false}"#;

    let outcome = import_with_publisher(
        root.path(),
        &legacy_path,
        &EditAfterBackup::new(legacy_path.clone(), newer.as_slice()),
    )
    .unwrap();

    assert!(matches!(
        outcome,
        LegacyTuiStateImportOutcome::LegacySourceConflict { .. }
    ));
    assert_eq!(std::fs::read(&legacy_path).unwrap(), newer);
    assert_eq!(std::fs::read(settings_path).unwrap(), settings_bytes);
}

#[test]
fn corrupted_backup_fails_verification_before_settings_publication() {
    let root = tempfile::tempdir().unwrap();
    let (settings_path, legacy_path, settings_bytes) = install_sources(root.path());

    let error =
        import_with_publisher(root.path(), &legacy_path, &CorruptBackup::new()).unwrap_err();

    assert_eq!(error.code(), "legacy_tui_state_backup_verify_failed");
    assert_eq!(std::fs::read(settings_path).unwrap(), settings_bytes);
}

#[test]
fn backup_publication_errors_retain_the_failed_durability_stage() {
    let root = tempfile::tempdir().unwrap();
    let (settings_path, legacy_path, settings_bytes) = install_sources(root.path());

    let error = import_with_publisher(
        root.path(),
        &legacy_path,
        &StageFailurePublisher::new(PublicationStage::Create),
    )
    .unwrap_err();

    assert_eq!(error.code(), "legacy_tui_state_backup_temp_create_failed");
    assert_eq!(std::fs::read(settings_path).unwrap(), settings_bytes);
}
