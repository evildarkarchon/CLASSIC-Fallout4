use super::*;
use crate::MigrationPlanningOutcome;
use crate::commit::{PublicationStage, Publisher, SystemPublisher};
use std::cell::Cell;

/// Publisher that corrupts only the first canonical publication after it becomes visible.
struct CorruptFirstCanonicalPublication {
    inner: SystemPublisher,
    corrupted: Cell<bool>,
}

/// Publisher that corrupts only its first successfully persisted target.
struct CorruptFirstPublication {
    inner: SystemPublisher,
    corrupted: Cell<bool>,
}

impl CorruptFirstPublication {
    /// Builds a deterministic backup-reread verification fault.
    fn new() -> Self {
        Self {
            inner: SystemPublisher::system(),
            corrupted: Cell::new(false),
        }
    }
}

impl Publisher for CorruptFirstPublication {
    /// Publishes normally, then corrupts the first visible artifact before verification.
    fn publish(&self, target: &Path, bytes: &[u8]) -> Result<(), crate::UserSettingsCommitError> {
        self.inner.publish(target, bytes)?;
        if !self.corrupted.replace(true) {
            std::fs::write(target, b"corrupted after persistence").unwrap();
        }
        Ok(())
    }
}

impl CorruptFirstCanonicalPublication {
    /// Builds a deterministic post-replacement verification fault.
    fn new() -> Self {
        Self {
            inner: SystemPublisher::system(),
            corrupted: Cell::new(false),
        }
    }
}

impl Publisher for CorruptFirstCanonicalPublication {
    /// Publishes normally, then simulates external corruption before the operation reopens.
    fn publish(&self, target: &Path, bytes: &[u8]) -> Result<(), crate::UserSettingsCommitError> {
        self.inner.publish(target, bytes)?;
        if target.ends_with(CANONICAL_RELATIVE_PATH) && !self.corrupted.replace(true) {
            std::fs::write(target, b"not: [valid YAML").unwrap();
        }
        Ok(())
    }
}

#[test]
fn reconstructed_review_plans_reverse_in_core_but_cannot_authorize_persistence() {
    let root = tempfile::tempdir().unwrap();
    let settings_path = root.path().join(CANONICAL_RELATIVE_PATH);
    std::fs::write(&settings_path, b"update_check: true\nfcx_mode: false\n").unwrap();
    let MigrationPlanningOutcome::Planned(plan) = UserSettings::open(root.path()).plan_migration()
    else {
        panic!("the supported flat shape must produce a migration plan");
    };
    let reconstructed = UserSettingsMigrationPlan::from((
        plan.required(),
        (plan.source().location(), plan.source().schema_version()),
        (plan.target().location(), plan.target().schema_version()),
        plan.changes()
            .iter()
            .map(|change| {
                (
                    change.kind(),
                    change.source_path().map(str::to_string),
                    change.target_path().map(str::to_string),
                    change.before().map(str::to_string),
                    change.after().map(str::to_string),
                )
            })
            .collect::<Vec<_>>(),
        plan.original_bytes().to_vec(),
        plan.proposed_bytes().to_vec(),
    ));

    let reconstructed_reverse = reconstructed.reverse_in_memory();
    let planned_reverse = plan.reverse_in_memory();
    assert_eq!(reconstructed_reverse.required(), planned_reverse.required());
    assert_eq!(
        reconstructed_reverse.base_revision(),
        planned_reverse.base_revision()
    );
    assert_eq!(reconstructed_reverse.source(), planned_reverse.source());
    assert_eq!(reconstructed_reverse.target(), planned_reverse.target());
    assert_eq!(reconstructed_reverse.changes(), planned_reverse.changes());
    assert_eq!(
        reconstructed_reverse.original_bytes(),
        planned_reverse.original_bytes()
    );
    assert_eq!(
        reconstructed_reverse.proposed_bytes(),
        planned_reverse.proposed_bytes(),
        "binding review reconstruction must delegate exact reversal semantics to core"
    );
    let error = reconstructed.apply(root.path()).unwrap_err();
    assert_eq!(error.code(), "migration_plan_unattested");
    assert_eq!(std::fs::read(settings_path).unwrap(), plan.original_bytes());
}

#[test]
fn failed_post_publication_verification_rolls_back_the_last_accepted_document() {
    let root = tempfile::tempdir().unwrap();
    let settings_path = root.path().join(CANONICAL_RELATIVE_PATH);
    let original = b"update_check: true\nfcx_mode: false\n";
    std::fs::write(&settings_path, original).unwrap();
    let MigrationPlanningOutcome::Planned(plan) = UserSettings::open(root.path()).plan_migration()
    else {
        panic!("the supported flat shape must produce a migration plan");
    };

    let error = plan
        .apply_with_publisher(root.path(), &CorruptFirstCanonicalPublication::new())
        .unwrap_err();

    assert_eq!(error.code(), "migration_reopen_verify_failed");
    assert_eq!(std::fs::read(settings_path).unwrap(), original);
    assert_eq!(
        UserSettings::open(root.path()).revision(),
        plan.base_revision()
    );
}

#[test]
fn every_interrupted_backup_or_publish_stage_preserves_the_last_accepted_document() {
    for publication in [1, 2] {
        for stage in [
            PublicationStage::Create,
            PublicationStage::Write,
            PublicationStage::Flush,
            PublicationStage::Sync,
            PublicationStage::Replace,
        ] {
            let root = tempfile::tempdir().unwrap();
            let settings_path = root.path().join(CANONICAL_RELATIVE_PATH);
            let original = b"update_check: true\nfcx_mode: false\n";
            std::fs::write(&settings_path, original).unwrap();
            let MigrationPlanningOutcome::Planned(plan) =
                UserSettings::open(root.path()).plan_migration()
            else {
                panic!("the supported flat shape must produce a migration plan");
            };
            let publisher = SystemPublisher::failing_at_publication(stage, publication);

            let error = plan
                .apply_with_publisher(root.path(), &publisher)
                .expect_err("an injected persistence interruption must be returned");

            let operation = if publication == 1 {
                "migration_backup"
            } else {
                "migration_publish"
            };
            assert!(
                error.code().starts_with(operation),
                "unexpected {stage:?} error for publication {publication}: {error}"
            );
            assert_eq!(std::fs::read(&settings_path).unwrap(), original);
            assert_eq!(
                UserSettings::open(root.path()).revision(),
                plan.base_revision()
            );
        }
    }
}

#[test]
fn failed_backup_reread_verification_never_publishes_the_migration() {
    let root = tempfile::tempdir().unwrap();
    let settings_path = root.path().join(CANONICAL_RELATIVE_PATH);
    let original = b"update_check: true\nfcx_mode: false\n";
    std::fs::write(&settings_path, original).unwrap();
    let MigrationPlanningOutcome::Planned(plan) = UserSettings::open(root.path()).plan_migration()
    else {
        panic!("the supported flat shape must produce a migration plan");
    };

    let error = plan
        .apply_with_publisher(root.path(), &CorruptFirstPublication::new())
        .unwrap_err();

    assert_eq!(error.code(), "migration_backup_verify_failed");
    assert_eq!(std::fs::read(settings_path).unwrap(), original);
}

#[test]
fn every_interrupted_restore_stage_preserves_the_migrated_document() {
    for stage in [
        PublicationStage::Create,
        PublicationStage::Write,
        PublicationStage::Flush,
        PublicationStage::Sync,
        PublicationStage::Replace,
    ] {
        let root = tempfile::tempdir().unwrap();
        let settings_path = root.path().join(CANONICAL_RELATIVE_PATH);
        std::fs::write(&settings_path, b"update_check: true\nfcx_mode: false\n").unwrap();
        let MigrationPlanningOutcome::Planned(plan) =
            UserSettings::open(root.path()).plan_migration()
        else {
            panic!("the supported flat shape must produce a migration plan");
        };
        let UserSettingsMigrationApplyOutcome::Applied(receipt) = plan.apply(root.path()).unwrap()
        else {
            panic!("the unchanged migration must apply");
        };
        let migrated = std::fs::read(&settings_path).unwrap();

        let error = receipt
            .restore_with_publisher(root.path(), &SystemPublisher::failing_at(stage))
            .unwrap_err();

        assert!(error.code().starts_with("migration_restore"));
        assert_eq!(std::fs::read(&settings_path).unwrap(), migrated);
        assert_eq!(
            UserSettings::open(root.path()).revision(),
            receipt.published_revision()
        );
    }
}

#[test]
fn failed_restore_reopen_verification_rolls_back_the_migrated_document() {
    let root = tempfile::tempdir().unwrap();
    let settings_path = root.path().join(CANONICAL_RELATIVE_PATH);
    std::fs::write(&settings_path, b"update_check: true\nfcx_mode: false\n").unwrap();
    let MigrationPlanningOutcome::Planned(plan) = UserSettings::open(root.path()).plan_migration()
    else {
        panic!("the supported flat shape must produce a migration plan");
    };
    let UserSettingsMigrationApplyOutcome::Applied(receipt) = plan.apply(root.path()).unwrap()
    else {
        panic!("the unchanged migration must apply");
    };
    let migrated = std::fs::read(&settings_path).unwrap();

    let error = receipt
        .restore_with_publisher(root.path(), &CorruptFirstCanonicalPublication::new())
        .unwrap_err();

    assert_eq!(error.code(), "migration_restore_reopen_verify_failed");
    assert_eq!(std::fs::read(&settings_path).unwrap(), migrated);
    assert_eq!(
        UserSettings::open(root.path()).revision(),
        receipt.published_revision()
    );
}
