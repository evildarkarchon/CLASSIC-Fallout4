use std::path::{Path, PathBuf};

use super::{
    Durability, STAGING_PREFIX, VerifiedBackup, fault, install_verified, publish,
    publish_verified_backup, publish_with_verified_backup, rollback_generation_path, stage,
};
use crate::error::{PublicationError, PublicationStage};
use crate::identity::ContentIdentity;
use crate::lock::LockPolicy;

/// Render the lowercase digest of `bytes`, as an expected-digest argument.
fn digest_of(bytes: &[u8]) -> String {
    ContentIdentity::from_bytes(bytes).sha256_hex()
}

/// List leftover staging artifacts in one directory.
///
/// A failed publication must remove the staging file it took ownership of, and
/// a successful one must have had it consumed by the move.
fn staging_artifacts(directory: &Path) -> Vec<PathBuf> {
    let Ok(entries) = std::fs::read_dir(directory) else {
        return Vec::new();
    };
    entries
        .flatten()
        .map(|entry| entry.path())
        .filter(|path| {
            path.file_name()
                .and_then(|name| name.to_str())
                .is_some_and(|name| name.starts_with(STAGING_PREFIX))
        })
        .collect()
}

/// An owned temporary directory that files under test are published into.
struct Fixture {
    directory: tempfile::TempDir,
}

impl Fixture {
    fn new() -> Self {
        Self {
            directory: tempfile::tempdir().expect("temporary directory"),
        }
    }

    fn root(&self) -> &Path {
        self.directory.path()
    }

    fn path(&self, name: &str) -> PathBuf {
        self.directory.path().join(name)
    }

    /// Write `bytes` at `name` without going through the module under test.
    fn seed(&self, name: &str, bytes: &[u8]) -> PathBuf {
        let path = self.path(name);
        std::fs::write(&path, bytes).expect("seeding a fixture file");
        path
    }

    fn read(&self, name: &str) -> Vec<u8> {
        std::fs::read(self.path(name)).expect("reading a fixture file")
    }
}

// ---------------------------------------------------------------------------
// publish
// ---------------------------------------------------------------------------

#[test]
fn publish_makes_complete_bytes_visible_at_an_absent_target() {
    let fixture = Fixture::new();
    let target = fixture.path("CLASSIC Ignore.yaml");

    let publication = publish(&target, b"complete bytes", &LockPolicy::none())
        .expect("publication to an absent target");

    assert_eq!(fixture.read("CLASSIC Ignore.yaml"), b"complete bytes");
    assert_eq!(publication.identity().byte_len(), 14);
    assert_eq!(
        publication.identity().sha256_hex(),
        crate::ContentIdentity::from_bytes(b"complete bytes").sha256_hex()
    );
}

#[test]
fn publish_replaces_existing_content_wholesale() {
    let fixture = Fixture::new();
    let target = fixture.seed("target.yaml", b"the much longer previous content");

    let _publication = publish(&target, b"short", &LockPolicy::none()).expect("replacement");

    assert_eq!(
        fixture.read("target.yaml"),
        b"short",
        "a replacement must not leave a tail of the previous content"
    );
}

#[test]
fn publish_always_reports_a_durability_outcome() {
    let fixture = Fixture::new();
    let target = fixture.path("target.yaml");

    let publication = publish(&target, b"bytes", &LockPolicy::none()).expect("publication");

    assert!(
        publication.durability().is_durable(),
        "an ordinary publication on a healthy filesystem is durable"
    );
    assert!(publication.into_durability().is_durable());
}

#[test]
fn publish_leaves_no_staging_artifact_behind_on_success() {
    let fixture = Fixture::new();
    let target = fixture.path("target.yaml");

    let _publication = publish(&target, b"bytes", &LockPolicy::none()).expect("publication");

    assert!(
        staging_artifacts(fixture.root()).is_empty(),
        "the staging file must be consumed by the publish step"
    );
}

#[test]
fn publish_takes_and_releases_the_requested_sibling_lock() {
    let fixture = Fixture::new();
    let target = fixture.path("target.yaml");
    let policy = LockPolicy::sibling(".commit.lock");

    let _first = publish(&target, b"first", &policy).expect("first publication");
    let _second = publish(&target, b"second", &policy).expect("second publication must not block");

    assert_eq!(fixture.read("target.yaml"), b"second");
    assert!(
        policy
            .lock_path(&target)
            .expect("sibling lock path")
            .exists()
    );
}

// ---------------------------------------------------------------------------
// Real filesystem failures
// ---------------------------------------------------------------------------

#[test]
fn a_missing_parent_directory_fails_at_the_create_stage() {
    let fixture = Fixture::new();
    let target = fixture.path("absent-directory").join("target.yaml");

    let error =
        publish(&target, b"bytes", &LockPolicy::none()).expect_err("staging has nowhere to land");

    assert_eq!(error.stage(), Some(PublicationStage::Create));
    assert_eq!(error.path(), target);
    assert_eq!(
        error.io_source().map(std::io::Error::kind),
        Some(std::io::ErrorKind::NotFound)
    );
}

#[test]
fn a_parent_path_that_is_a_file_fails_at_the_create_stage() {
    let fixture = Fixture::new();
    let blocking_file = fixture.seed("not-a-directory", b"occupied");
    let target = blocking_file.join("target.yaml");

    let error = publish(&target, b"bytes", &LockPolicy::none())
        .expect_err("a regular file cannot hold a staging file");

    assert_eq!(error.stage(), Some(PublicationStage::Create));
}

#[cfg(unix)]
#[test]
fn a_read_only_parent_directory_fails_at_the_create_stage() {
    use std::os::unix::fs::PermissionsExt as _;

    let fixture = Fixture::new();
    let parent = fixture.path("read-only");
    std::fs::create_dir(&parent).expect("creating the parent");
    let target = parent.join("target.yaml");
    std::fs::set_permissions(&parent, std::fs::Permissions::from_mode(0o555))
        .expect("making the parent read-only");

    let error = publish(&target, b"bytes", &LockPolicy::none())
        .expect_err("staging cannot be created in a read-only directory");

    // Restore write permission so the fixture's own cleanup can succeed.
    std::fs::set_permissions(&parent, std::fs::Permissions::from_mode(0o755))
        .expect("restoring the parent");

    assert_eq!(error.stage(), Some(PublicationStage::Create));
    assert_eq!(
        error.io_source().map(std::io::Error::kind),
        Some(std::io::ErrorKind::PermissionDenied)
    );
}

#[cfg(windows)]
#[test]
fn a_read_only_target_fails_at_the_publish_stage_and_keeps_its_content() {
    let fixture = Fixture::new();
    let target = fixture.seed("target.yaml", b"protected");
    let mut permissions = std::fs::metadata(&target)
        .expect("target metadata")
        .permissions();
    permissions.set_readonly(true);
    std::fs::set_permissions(&target, permissions).expect("marking the target read-only");

    let error = publish(&target, b"replacement", &LockPolicy::none())
        .expect_err("a write-through move cannot replace a read-only destination");

    let mut permissions = std::fs::metadata(&target)
        .expect("target metadata")
        .permissions();
    // The lint warns that clearing the read-only flag makes a file world
    // writable on Unix; this test is `cfg(windows)`, where the flag is a
    // single file attribute with no group or other bits behind it.
    #[allow(clippy::permissions_set_readonly_false)]
    permissions.set_readonly(false);
    std::fs::set_permissions(&target, permissions).expect("restoring the target");

    assert_eq!(error.stage(), Some(PublicationStage::Publish));
    assert_eq!(
        fixture.read("target.yaml"),
        b"protected",
        "a failed publication must leave the previous content in place"
    );
    assert!(
        staging_artifacts(fixture.root()).is_empty(),
        "a failed publish must remove the staging file it took ownership of"
    );
}

#[test]
fn a_directory_synchronization_failure_is_reported_as_uncertain_not_as_an_error() {
    let fixture = Fixture::new();
    let target = fixture.path("target.yaml");

    let _fault = fault::fail_directory_sync();
    let publication =
        publish(&target, b"bytes", &LockPolicy::none()).expect("the bytes are still published");

    assert_eq!(
        fixture.read("target.yaml"),
        b"bytes",
        "complete bytes are visible even when the barrier is unconfirmed"
    );
    assert!(!publication.durability().is_durable());
    assert!(matches!(publication.durability(), Durability::Unknown(_)));
    assert_eq!(
        publication
            .durability()
            .unknown_source()
            .map(std::io::Error::kind),
        Some(std::io::ErrorKind::PermissionDenied)
    );
}

// ---------------------------------------------------------------------------
// publish_with_verified_backup
// ---------------------------------------------------------------------------

#[test]
fn a_verified_backup_precedes_the_replacement_and_reports_both_identities() {
    let fixture = Fixture::new();
    let target = fixture.seed("target.yaml", b"the original");
    let backup_path = fixture.path("target.yaml.bak");

    let result = publish_with_verified_backup(
        &target,
        b"the replacement",
        VerifiedBackup::new(&backup_path, b"the original"),
        &LockPolicy::sibling(".reset.lock"),
    )
    .expect("verified backup publication");

    assert_eq!(fixture.read("target.yaml.bak"), b"the original");
    assert_eq!(fixture.read("target.yaml"), b"the replacement");
    assert_eq!(
        result.backup_identity(),
        &crate::ContentIdentity::from_bytes(b"the original")
    );
    assert_eq!(
        result.replacement().identity(),
        &crate::ContentIdentity::from_bytes(b"the replacement")
    );
    assert!(result.into_replacement().durability().is_durable());
}

#[test]
fn a_backup_whose_reread_bytes_do_not_match_aborts_the_replacement() {
    let fixture = Fixture::new();
    let target = fixture.seed("target.yaml", b"the only copy");
    let backup_path = fixture.path("target.yaml.bak");

    // Model a backup that appeared to write but landed empty.
    let _fault = fault::corrupt_published_backups(b"");
    let error = publish_with_verified_backup(
        &target,
        b"the replacement",
        VerifiedBackup::new(&backup_path, b"the only copy"),
        &LockPolicy::none(),
    )
    .expect_err("replacement must abort when the backup cannot be trusted");

    assert_eq!(
        fixture.read("target.yaml"),
        b"the only copy",
        "aborting is what stops an accepted recovery destroying the only copy"
    );
    let PublicationError::BackupMismatch {
        path,
        expected,
        actual,
    } = &error
    else {
        panic!("expected a backup mismatch, got: {error}")
    };
    assert_eq!(path, &backup_path);
    assert_eq!(
        expected,
        &crate::ContentIdentity::from_bytes(b"the only copy")
    );
    assert_eq!(actual.byte_len(), 0);
}

#[test]
fn a_backup_path_that_already_exists_is_refused_rather_than_clobbered() {
    let fixture = Fixture::new();
    let target = fixture.seed("target.yaml", b"the original");
    let backup_path = fixture.seed("target.yaml.bak", b"an earlier backup");

    let error = publish_with_verified_backup(
        &target,
        b"the replacement",
        VerifiedBackup::new(&backup_path, b"the original"),
        &LockPolicy::none(),
    )
    .expect_err("a unique-path publication must not overwrite");

    assert_eq!(error.stage(), Some(PublicationStage::Publish));
    assert_eq!(
        error.io_source().map(std::io::Error::kind),
        Some(std::io::ErrorKind::AlreadyExists)
    );
    assert_eq!(fixture.read("target.yaml.bak"), b"an earlier backup");
    assert_eq!(fixture.read("target.yaml"), b"the original");
}

#[test]
fn a_backup_that_cannot_be_staged_leaves_the_target_untouched() {
    let fixture = Fixture::new();
    let target = fixture.seed("target.yaml", b"the original");
    let backup_path = fixture.path("absent-directory").join("target.yaml.bak");

    let error = publish_with_verified_backup(
        &target,
        b"the replacement",
        VerifiedBackup::new(&backup_path, b"the original"),
        &LockPolicy::none(),
    )
    .expect_err("the backup cannot be staged");

    assert_eq!(error.stage(), Some(PublicationStage::Create));
    assert_eq!(error.path(), backup_path);
    assert_eq!(fixture.read("target.yaml"), b"the original");
}

#[test]
fn the_replacement_still_reports_durability_after_a_verified_backup() {
    let fixture = Fixture::new();
    let target = fixture.seed("target.yaml", b"the original");
    let backup_path = fixture.path("target.yaml.bak");

    let _fault = fault::fail_directory_sync();
    let result = publish_with_verified_backup(
        &target,
        b"the replacement",
        VerifiedBackup::new(&backup_path, b"the original"),
        &LockPolicy::none(),
    )
    .expect("the replacement is still published");

    assert_eq!(fixture.read("target.yaml"), b"the replacement");
    assert!(
        !result.replacement().durability().is_durable(),
        "uncertainty on the replacement is a value the caller must decide about"
    );
}

#[test]
fn the_lock_is_taken_on_the_target_and_not_on_the_backup_path() {
    let fixture = Fixture::new();
    let target = fixture.seed("target.yaml", b"the original");
    let backup_path = fixture.path("target.yaml.bak");
    let policy = LockPolicy::sibling(".reset.lock");

    let _result = publish_with_verified_backup(
        &target,
        b"the replacement",
        VerifiedBackup::new(&backup_path, b"the original"),
        &policy,
    )
    .expect("verified backup publication");

    assert!(fixture.path("target.yaml.reset.lock").exists());
    assert!(
        !fixture.path("target.yaml.bak.reset.lock").exists(),
        "one lock spans the whole operation, so the backup path is not locked separately"
    );
}

// ---------------------------------------------------------------------------
// stage
// ---------------------------------------------------------------------------

#[test]
fn staging_makes_nothing_visible_at_the_target() {
    let fixture = Fixture::new();
    let target = fixture.seed("target.yaml", b"the original");

    let staged = stage(&target, b"the replacement").expect("staging");

    assert_eq!(
        fixture.read("target.yaml"),
        b"the original",
        "nothing is visible at the target until the staged publication is published"
    );
    assert_eq!(staged.target(), target);
    assert_eq!(
        staged.identity(),
        &crate::ContentIdentity::from_bytes(b"the replacement")
    );
    assert_eq!(
        staging_artifacts(fixture.root()).len(),
        1,
        "the staging file exists while the handle is held"
    );
}

#[test]
fn publishing_a_staged_publication_replaces_the_target() {
    let fixture = Fixture::new();
    let target = fixture.seed("target.yaml", b"the original");

    let publication = stage(&target, b"the replacement")
        .expect("staging")
        .publish()
        .expect("publishing the staged bytes");

    assert_eq!(fixture.read("target.yaml"), b"the replacement");
    assert!(publication.durability().is_durable());
    assert!(staging_artifacts(fixture.root()).is_empty());
}

#[test]
fn dropping_a_staged_publication_leaves_the_target_and_the_directory_clean() {
    let fixture = Fixture::new();
    let target = fixture.seed("target.yaml", b"the original");

    drop(stage(&target, b"the replacement").expect("staging"));

    assert_eq!(fixture.read("target.yaml"), b"the original");
    assert!(
        staging_artifacts(fixture.root()).is_empty(),
        "an abandoned staging file must not accumulate beside a user's data"
    );
}

#[test]
fn staging_reports_its_own_failures_before_anything_is_committed_to() {
    let fixture = Fixture::new();
    let target = fixture.path("absent-directory").join("target.yaml");

    let error = stage(&target, b"bytes").expect_err("staging has nowhere to land");

    assert_eq!(error.stage(), Some(PublicationStage::Create));
    assert_eq!(error.path(), target);
}

#[test]
fn a_staged_publication_only_leaves_the_final_move_between_a_check_and_the_target() {
    let fixture = Fixture::new();
    let target = fixture.seed("target.yaml", b"the original");

    // The shape the Local Ignore reset relies on: stage everything fallible, run the caller's own
    // check, then publish. The check sees the pre-replacement bytes, and only the move follows it.
    let staged = stage(&target, b"the replacement").expect("staging");
    let observed = std::fs::read(&target).expect("the caller's own check");
    assert_eq!(observed, b"the original");
    let publication = staged.publish().expect("publishing after the check");

    assert_eq!(fixture.read("target.yaml"), b"the replacement");
    assert_eq!(
        publication.identity(),
        &crate::ContentIdentity::from_bytes(b"the replacement")
    );
}

// ---------------------------------------------------------------------------
// publish_verified_backup
// ---------------------------------------------------------------------------

#[test]
fn a_standalone_verified_backup_publishes_and_attests_the_bytes_on_disk() {
    let fixture = Fixture::new();
    let backup_path = fixture.path("target.yaml.bak");

    let published = publish_verified_backup(VerifiedBackup::new(&backup_path, b"the original"))
        .expect("standalone verified backup");

    assert_eq!(fixture.read("target.yaml.bak"), b"the original");
    assert_eq!(
        published.identity(),
        &crate::ContentIdentity::from_bytes(b"the original")
    );
    assert!(
        published.durability().is_durable(),
        "a cooperating filesystem reaches the barrier, and the caller must be able to see that"
    );
    assert!(staging_artifacts(fixture.root()).is_empty());
}

#[test]
fn a_standalone_verified_backup_replaces_nothing() {
    let fixture = Fixture::new();
    let target = fixture.seed("target.yaml", b"the original");
    let backup_path = fixture.path("target.yaml.bak");

    let _published = publish_verified_backup(VerifiedBackup::new(&backup_path, b"the original"))
        .expect("standalone verified backup");

    assert_eq!(
        std::fs::read(&target).expect("target"),
        b"the original",
        "this half of the sequence never touches a target; the caller decides"
    );
}

#[test]
fn a_standalone_backup_whose_reread_bytes_do_not_match_is_rejected() {
    let fixture = Fixture::new();
    let backup_path = fixture.path("target.yaml.bak");

    // Model a backup that appeared to write but landed empty.
    let _fault = fault::corrupt_published_backups(b"");
    let error = publish_verified_backup(VerifiedBackup::new(&backup_path, b"the only copy"))
        .expect_err("a backup that cannot be trusted must be reported, not returned");

    let PublicationError::BackupMismatch {
        path,
        expected,
        actual,
    } = &error
    else {
        panic!("expected a backup mismatch, got: {error}")
    };
    assert_eq!(path, &backup_path);
    assert_eq!(
        expected,
        &crate::ContentIdentity::from_bytes(b"the only copy")
    );
    assert_eq!(actual.byte_len(), 0);
}

#[test]
fn a_standalone_backup_path_that_already_exists_is_refused_rather_than_clobbered() {
    let fixture = Fixture::new();
    let backup_path = fixture.seed("target.yaml.bak", b"an earlier backup");

    let error = publish_verified_backup(VerifiedBackup::new(&backup_path, b"the original"))
        .expect_err("a unique-path publication must not overwrite");

    assert_eq!(error.stage(), Some(PublicationStage::Publish));
    assert_eq!(
        error.io_source().map(std::io::Error::kind),
        Some(std::io::ErrorKind::AlreadyExists)
    );
    assert_eq!(fixture.read("target.yaml.bak"), b"an earlier backup");
}

#[test]
fn a_standalone_backup_that_cannot_be_staged_reports_the_create_stage() {
    let fixture = Fixture::new();
    let backup_path = fixture.path("absent-directory").join("target.yaml.bak");

    let error = publish_verified_backup(VerifiedBackup::new(&backup_path, b"the original"))
        .expect_err("the backup cannot be staged");

    assert_eq!(error.stage(), Some(PublicationStage::Create));
    assert_eq!(error.path(), backup_path);
}

#[test]
fn splitting_the_sequence_yields_the_same_bytes_as_the_combined_operation() {
    let fixture = Fixture::new();
    let target = fixture.seed("target.yaml", b"the original");
    let backup_path = fixture.path("target.yaml.bak");

    // What a caller with a policy check in the middle does: verify the backup,
    // decide, then replace. The observable result must match the welded form.
    let published_backup =
        publish_verified_backup(VerifiedBackup::new(&backup_path, b"the original"))
            .expect("standalone verified backup");
    let replacement = publish(&target, b"the replacement", &LockPolicy::none())
        .expect("replacement after the caller's own policy check");

    assert_eq!(fixture.read("target.yaml.bak"), b"the original");
    assert_eq!(fixture.read("target.yaml"), b"the replacement");
    assert_eq!(
        published_backup.identity(),
        &crate::ContentIdentity::from_bytes(b"the original")
    );
    assert_eq!(
        replacement.identity(),
        &crate::ContentIdentity::from_bytes(b"the replacement")
    );
    assert!(staging_artifacts(fixture.root()).is_empty());
}

// ---------------------------------------------------------------------------
// install_verified
// ---------------------------------------------------------------------------

#[test]
fn a_verified_install_over_an_absent_target_creates_no_rollback_generation() {
    let fixture = Fixture::new();
    let target = fixture.path("CLASSIC Main.yaml");
    let staged = fixture.seed("CLASSIC Main.yaml.new", b"the delivered payload");

    let install = install_verified(
        &target,
        &staged,
        &digest_of(b"the delivered payload"),
        &LockPolicy::none(),
    )
    .expect("install over an absent target");

    assert_eq!(fixture.read("CLASSIC Main.yaml"), b"the delivered payload");
    assert!(
        !install.created_rollback_generation(),
        "there was no target to preserve"
    );
    assert!(!rollback_generation_path(&target).exists());
    assert!(!staged.exists(), "the staged file is moved, not copied");
}

#[test]
fn a_verified_install_preserves_the_replaced_target_as_a_rollback_generation() {
    let fixture = Fixture::new();
    let target = fixture.seed("CLASSIC Main.yaml", b"the installed generation");
    let staged = fixture.seed("CLASSIC Main.yaml.new", b"the delivered payload");

    let install = install_verified(
        &target,
        &staged,
        &digest_of(b"the delivered payload"),
        &LockPolicy::none(),
    )
    .expect("install over an existing target");

    assert!(install.created_rollback_generation());
    assert_eq!(fixture.read("CLASSIC Main.yaml"), b"the delivered payload");
    assert_eq!(
        std::fs::read(rollback_generation_path(&target)).expect("the rollback generation"),
        b"the installed generation"
    );
}

#[test]
fn a_verified_install_keeps_exactly_one_rollback_generation() {
    let fixture = Fixture::new();
    let target = fixture.seed("CLASSIC Main.yaml", b"generation two");
    fixture.seed("CLASSIC Main.yaml.prev", b"generation zero");
    let staged = fixture.seed("CLASSIC Main.yaml.new", b"generation three");

    let _install = install_verified(
        &target,
        &staged,
        &digest_of(b"generation three"),
        &LockPolicy::none(),
    )
    .expect("install over an existing rollback generation");

    assert_eq!(
        fixture.read("CLASSIC Main.yaml.prev"),
        b"generation two",
        "the rollback generation holds the version installed immediately before"
    );
    assert_eq!(fixture.read("CLASSIC Main.yaml"), b"generation three");
}

#[test]
fn a_verified_install_attests_the_bytes_it_installed() {
    let fixture = Fixture::new();
    let target = fixture.path("CLASSIC Main.yaml");
    let staged = fixture.seed("CLASSIC Main.yaml.new", b"the delivered payload");

    let install = install_verified(
        &target,
        &staged,
        &digest_of(b"the delivered payload"),
        &LockPolicy::none(),
    )
    .expect("install");

    assert_eq!(
        install.identity(),
        &ContentIdentity::from_bytes(b"the delivered payload")
    );
    assert_eq!(install.identity().byte_len(), 21);
}

#[test]
fn a_verified_install_accepts_an_expected_digest_in_any_letter_case() {
    let fixture = Fixture::new();
    let target = fixture.path("CLASSIC Main.yaml");
    let staged = fixture.seed("CLASSIC Main.yaml.new", b"the delivered payload");

    let _install = install_verified(
        &target,
        &staged,
        &digest_of(b"the delivered payload").to_uppercase(),
        &LockPolicy::none(),
    )
    .expect("an uppercase manifest digest is the same digest");

    assert_eq!(fixture.read("CLASSIC Main.yaml"), b"the delivered payload");
}

#[test]
fn a_digest_mismatch_deletes_the_staged_file_and_preserves_every_existing_file() {
    let fixture = Fixture::new();
    let target = fixture.seed("CLASSIC Main.yaml", b"keep the installed bytes");
    fixture.seed("CLASSIC Main.yaml.prev", b"keep the rollback generation");
    let staged = fixture.seed("CLASSIC Main.yaml.new", b"the tampered payload");

    let error = install_verified(
        &target,
        &staged,
        &digest_of(b"the payload the manifest promised"),
        &LockPolicy::none(),
    )
    .expect_err("a digest mismatch must abort the install");

    match error {
        PublicationError::DigestMismatch {
            path,
            expected,
            actual,
        } => {
            assert_eq!(path, staged);
            assert_eq!(expected, digest_of(b"the payload the manifest promised"));
            assert_eq!(actual, ContentIdentity::from_bytes(b"the tampered payload"));
        }
        other => panic!("expected a digest mismatch, got {other:?}"),
    }

    assert!(
        !staged.exists(),
        "bytes that failed verification must not survive beside the target"
    );
    assert_eq!(
        fixture.read("CLASSIC Main.yaml"),
        b"keep the installed bytes"
    );
    assert_eq!(
        fixture.read("CLASSIC Main.yaml.prev"),
        b"keep the rollback generation"
    );
}

#[test]
fn a_staged_file_that_cannot_be_read_is_reported_without_touching_the_target() {
    let fixture = Fixture::new();
    let target = fixture.seed("CLASSIC Main.yaml", b"the installed bytes");
    let staged = fixture.path("CLASSIC Main.yaml.new");

    let error = install_verified(
        &target,
        &staged,
        &digest_of(b"anything"),
        &LockPolicy::none(),
    )
    .expect_err("an absent staged file cannot be verified");

    assert!(matches!(error, PublicationError::StagedUnreadable { .. }));
    assert_eq!(error.path(), staged);
    assert_eq!(fixture.read("CLASSIC Main.yaml"), b"the installed bytes");
    assert!(!rollback_generation_path(&target).exists());
}

#[test]
fn a_verified_install_of_a_caller_written_file_needs_no_synchronization_from_the_caller() {
    use std::io::Write as _;

    let fixture = Fixture::new();
    let target = fixture.path("CLASSIC Main.yaml");
    let staged = fixture.path("CLASSIC Main.yaml.new");

    // The shape an async downloader produces: open, write, drop — user-space
    // buffers drained, nothing pushed to the durability barrier. Owning that
    // synchronization is why the staged file is adopted rather than trusted.
    {
        let mut file = std::fs::File::create(&staged).expect("creating the staged file");
        file.write_all(b"the downloaded payload")
            .expect("writing the staged file");
    }

    let _install = install_verified(
        &target,
        &staged,
        &digest_of(b"the downloaded payload"),
        &LockPolicy::none(),
    )
    .expect("install of an unsynchronized staged file");

    assert_eq!(fixture.read("CLASSIC Main.yaml"), b"the downloaded payload");
}

#[test]
fn a_verified_install_always_reports_a_durability_outcome() {
    let fixture = Fixture::new();
    let target = fixture.path("CLASSIC Main.yaml");
    let staged = fixture.seed("CLASSIC Main.yaml.new", b"payload");

    let install = install_verified(
        &target,
        &staged,
        &digest_of(b"payload"),
        &LockPolicy::none(),
    )
    .expect("install");

    assert!(install.durability().is_durable());
    assert!(install.into_durability().is_durable());
}

#[test]
fn a_verified_install_reports_an_uncertain_barrier_rather_than_failing() {
    let fixture = Fixture::new();
    let target = fixture.path("CLASSIC Main.yaml");
    let staged = fixture.seed("CLASSIC Main.yaml.new", b"payload");

    let install = {
        let _fault = fault::fail_directory_sync();
        install_verified(
            &target,
            &staged,
            &digest_of(b"payload"),
            &LockPolicy::none(),
        )
        .expect("an uncertain barrier is a value, not a failure")
    };

    assert_eq!(
        fixture.read("CLASSIC Main.yaml"),
        b"payload",
        "the bytes are visible even when the namespace entry is unconfirmed"
    );
    assert!(matches!(install.durability(), Durability::Unknown(_)));
    assert_eq!(
        install
            .durability()
            .unknown_source()
            .map(std::io::Error::kind),
        Some(std::io::ErrorKind::PermissionDenied)
    );
}

#[test]
fn a_verified_install_takes_and_releases_the_requested_sibling_lock() {
    let fixture = Fixture::new();
    let target = fixture.path("CLASSIC Main.yaml");
    let policy = LockPolicy::sibling(".install.lock");

    let first = fixture.seed("CLASSIC Main.yaml.a", b"first payload");
    let _first = install_verified(&target, &first, &digest_of(b"first payload"), &policy)
        .expect("first install");
    let second = fixture.seed("CLASSIC Main.yaml.b", b"second payload");
    let _second = install_verified(&target, &second, &digest_of(b"second payload"), &policy)
        .expect("the second install must not block on a released lock");

    assert_eq!(fixture.read("CLASSIC Main.yaml"), b"second payload");
    assert!(
        policy
            .lock_path(&target)
            .expect("sibling lock path")
            .exists()
    );
}

#[test]
fn the_rollback_generation_path_is_a_sibling_of_the_whole_target_name() {
    let target = Path::new("cache").join("CLASSIC Main.yaml");

    assert_eq!(
        rollback_generation_path(&target),
        Path::new("cache").join("CLASSIC Main.yaml.prev"),
        "the suffix appends to the full name, never replacing the extension"
    );
}

#[test]
fn no_publication_operation_can_produce_a_rollback_generation() {
    let fixture = Fixture::new();
    let target = fixture.seed("CLASSIC Ignore.yaml", b"the malformed original");
    let backup_path = fixture.path("CLASSIC Ignore.yaml.bak");

    let _replacement =
        publish(&target, b"the defaults", &LockPolicy::none()).expect("plain publication");
    let _backed = publish_with_verified_backup(
        &target,
        b"the defaults again",
        VerifiedBackup::new(&backup_path, b"the defaults"),
        &LockPolicy::none(),
    )
    .expect("verified-backup publication");

    // ADR-0006 prohibits creating a rollback generation for Local Ignore YAML
    // Data. That holds because the operations that path uses cannot express
    // one, not because the caller remembers not to ask.
    assert!(
        !rollback_generation_path(&target).exists(),
        "only install_verified may create a rollback generation"
    );
}
