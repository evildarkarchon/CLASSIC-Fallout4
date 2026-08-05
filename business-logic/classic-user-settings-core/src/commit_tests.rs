use super::{
    PublicationStage, Publisher, SystemPublisher, UserSettingsCommitError, durable_publication,
};
use crate::{UserSettings, UserSettingsUpdate, UserSettingsUpdatePreview};
use std::path::Path;

/// Pure fake that returns one publication stage failure and touches no files.
///
/// The staging-and-publish sequence now lives in `classic-durable-publication`, so there is no
/// longer a real write sequence in this crate to interleave failure points into. What the commit
/// algorithm actually needs to be tested against is the *value* the publisher seam returns, which
/// is exactly what this produces.
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

/// Returns one accepted update against the current fixture revision.
fn accepted_update(root: &std::path::Path) -> crate::AcceptedUserSettingsUpdate {
    let settings = UserSettings::open(root);
    let UserSettingsUpdatePreview::Accepted(accepted) = settings.preview_update(
        UserSettingsUpdate::new().with_unsolved_logs_destination(Some("D:/Unsolved".to_string())),
    ) else {
        panic!("valid destination should be accepted");
    };
    accepted
}

#[test]
fn every_injected_publication_failure_preserves_a_parseable_original_and_cleans_temp_files() {
    for stage in [
        PublicationStage::Create,
        PublicationStage::Write,
        PublicationStage::Flush,
        PublicationStage::Sync,
        PublicationStage::Replace,
    ] {
        let root = tempfile::tempdir().unwrap();
        let path = root.path().join("CLASSIC Settings.yaml");
        let original = b"schema_version: \"1.0\"\nCLASSIC_Settings:\n  Update Check: true\n";
        std::fs::write(&path, original).unwrap();
        let accepted = accepted_update(root.path());
        let publisher = StageFailurePublisher::new(stage);

        let error = accepted
            .commit_with_publisher(root.path(), &publisher)
            .expect_err("injected publication failure must be returned");

        assert_eq!(error.code(), stage.error_code());
        assert_eq!(std::fs::read(&path).unwrap(), original);
        assert!(matches!(
            UserSettings::open(root.path()).revision(),
            crate::Revision::ContentSha256(_)
        ));
        // The fake is pure, so this now also asserts that the commit algorithm itself stages
        // nothing: every staging artifact belongs to the publisher seam. Both the retired
        // in-crate prefix and the shared module's are checked, so a leak from either is caught.
        let temp_files = std::fs::read_dir(root.path())
            .unwrap()
            .filter_map(Result::ok)
            .filter(|entry| {
                let name = entry.file_name().to_string_lossy().into_owned();
                name.starts_with(".classic-user-settings-")
                    || name.starts_with(".classic-durable-publication-")
            })
            .collect::<Vec<_>>();
        assert!(
            temp_files.is_empty(),
            "{stage:?} left temporary files behind"
        );
    }
}

#[test]
fn the_shared_terminal_publish_stage_keeps_this_crates_replace_error_code() {
    // The shared module's stage vocabulary ends in `Publish`; this crate's ends in `Replace` and
    // publishes `commit_replace_failed`. Every operation-specific code in this crate is derived
    // from these five, so a drift here silently retires a published contract in three places at
    // once. Pinned directly rather than only through a filesystem failure, because no portable
    // condition provokes each stage on demand.
    for (shared, local, code) in [
        (
            durable_publication::PublicationStage::Create,
            PublicationStage::Create,
            "commit_temp_create_failed",
        ),
        (
            durable_publication::PublicationStage::Write,
            PublicationStage::Write,
            "commit_temp_write_failed",
        ),
        (
            durable_publication::PublicationStage::Flush,
            PublicationStage::Flush,
            "commit_temp_flush_failed",
        ),
        (
            durable_publication::PublicationStage::Sync,
            PublicationStage::Sync,
            "commit_temp_sync_failed",
        ),
        (
            durable_publication::PublicationStage::Publish,
            PublicationStage::Replace,
            "commit_replace_failed",
        ),
    ] {
        assert_eq!(PublicationStage::from_publication(shared), local);
        assert_eq!(local.error_code(), code);
    }
}

#[test]
fn the_shared_publisher_projects_a_real_create_failure_without_leaving_artifacts() {
    // A missing parent directory is the one publication stage a portable filesystem condition can
    // provoke, so it is what proves the adapter is genuinely wired to the shared module rather
    // than only that the projection table is self-consistent.
    let root = tempfile::tempdir().unwrap();
    let unreachable_target = root
        .path()
        .join("absent directory")
        .join("CLASSIC Settings.yaml");

    let error = SystemPublisher::system()
        .publish(&unreachable_target, b"bytes")
        .expect_err("a missing parent directory cannot be staged into");

    assert_eq!(error.code(), "commit_temp_create_failed");
    assert!(!unreachable_target.exists());
    assert_eq!(std::fs::read_dir(root.path()).unwrap().count(), 0);
}

#[test]
fn the_commit_lock_keeps_its_established_sibling_filename() {
    // The lock implementation moved to the shared module; the lock *file* must not. Two CLASSIC
    // processes only serialize if they agree on this name, and one of them may be an older build.
    let root = tempfile::tempdir().unwrap();
    let target = root.path().join(super::CANONICAL_FILENAME);

    let lock_path = super::commit_lock_policy().lock_path(&target);

    // The suffix is appended to the whole path, not to the file stem.
    assert_eq!(
        lock_path,
        Some(root.path().join("CLASSIC Settings.yaml.commit.lock"))
    );
}
