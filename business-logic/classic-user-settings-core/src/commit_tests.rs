use super::{PublicationStage, SystemPublisher};
use crate::{UserSettings, UserSettingsUpdate, UserSettingsUpdatePreview};

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
        let publisher = SystemPublisher::failing_at(stage);

        let error = accepted
            .commit_with_publisher(root.path(), &publisher)
            .expect_err("injected publication failure must be returned");

        assert_eq!(error.code(), stage.error_code());
        assert_eq!(std::fs::read(&path).unwrap(), original);
        assert!(matches!(
            UserSettings::open(root.path()).revision(),
            crate::Revision::ContentSha256(_)
        ));
        let temp_files = std::fs::read_dir(root.path())
            .unwrap()
            .filter_map(Result::ok)
            .filter(|entry| {
                entry
                    .file_name()
                    .to_string_lossy()
                    .starts_with(".classic-user-settings-")
            })
            .collect::<Vec<_>>();
        assert!(
            temp_files.is_empty(),
            "{stage:?} left temporary files behind"
        );
    }
}
