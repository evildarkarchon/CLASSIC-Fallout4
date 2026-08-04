use std::path::{Path, PathBuf};

use super::LockPolicy;
use crate::error::PublicationError;

#[test]
fn no_lock_policy_derives_no_lock_path() {
    assert_eq!(
        LockPolicy::none().lock_path(Path::new("/data/target.yaml")),
        None
    );
}

#[test]
fn sibling_policy_appends_the_suffix_to_the_whole_target_path() {
    // Matching the existing on-disk names exactly is the point: adopting this
    // crate must not rename any caller's lock file.
    assert_eq!(
        LockPolicy::sibling(".commit.lock").lock_path(Path::new("/root/CLASSIC Settings.yaml")),
        Some(PathBuf::from("/root/CLASSIC Settings.yaml.commit.lock"))
    );
    assert_eq!(
        LockPolicy::sibling(".install.lock").lock_path(Path::new("/cache/CLASSIC Main.yaml")),
        Some(PathBuf::from("/cache/CLASSIC Main.yaml.install.lock"))
    );
}

#[test]
fn an_explicit_policy_locks_a_path_the_caller_derived_itself() {
    // The Local Ignore reset lock is a fixed name two directories above the
    // target, which `sibling` cannot express. Pinning it here so migrating
    // that caller cannot silently move a lock file on disk.
    let target = Path::new("/install/CLASSIC Data/CLASSIC Ignore.yaml");
    let caller_derived = Path::new("/install/.classic-local-ignore-reset.lock");

    assert_eq!(
        LockPolicy::at(caller_derived).lock_path(target),
        Some(caller_derived.to_path_buf())
    );
}

#[test]
fn an_explicit_policy_ignores_the_target_when_deriving_its_path() {
    let policy = LockPolicy::at("/elsewhere/shared.lock");

    assert_eq!(
        policy.lock_path(Path::new("/one/a.yaml")),
        policy.lock_path(Path::new("/two/b.yaml")),
        "an explicit lock is exactly the path the caller supplied"
    );
}

#[test]
fn acquiring_no_lock_policy_creates_nothing_on_disk() {
    let directory = tempfile::tempdir().expect("temporary directory");
    let target = directory.path().join("target.yaml");

    let guard = LockPolicy::none()
        .acquire(&target)
        .expect("the no-lock policy cannot fail");

    assert!(guard.is_none());
    assert_eq!(
        std::fs::read_dir(directory.path())
            .expect("readable directory")
            .count(),
        0,
        "the no-lock policy must not place a file beside user-editable data"
    );
}

#[test]
fn acquiring_a_sibling_lock_creates_the_lock_file_and_holds_it() {
    let directory = tempfile::tempdir().expect("temporary directory");
    let target = directory.path().join("target.yaml");
    let policy = LockPolicy::sibling(".commit.lock");

    let guard = policy.acquire(&target).expect("lock acquired");

    assert!(guard.is_some());
    assert!(
        policy
            .lock_path(&target)
            .expect("sibling policy has a lock path")
            .exists()
    );
}

#[test]
fn the_lock_file_survives_release_so_later_acquirers_do_not_race_a_deletion() {
    let directory = tempfile::tempdir().expect("temporary directory");
    let target = directory.path().join("target.yaml");
    let policy = LockPolicy::sibling(".install.lock");
    let lock_path = policy.lock_path(&target).expect("sibling lock path");

    drop(policy.acquire(&target).expect("lock acquired"));

    assert!(lock_path.exists());
    // Re-acquiring after release must succeed rather than block.
    drop(policy.acquire(&target).expect("lock reacquired"));
}

#[test]
fn a_missing_directory_surfaces_as_a_lock_open_failure_not_a_panic() {
    let directory = tempfile::tempdir().expect("temporary directory");
    let target = directory.path().join("gone").join("target.yaml");

    let error = LockPolicy::sibling(".commit.lock")
        .acquire(&target)
        .expect_err("a lock file cannot be created inside a missing directory");

    assert!(matches!(error, PublicationError::LockOpen { .. }));
    assert_eq!(
        error.io_source().map(std::io::Error::kind),
        Some(std::io::ErrorKind::NotFound),
        "callers map a NotFound lock open onto their own conflict outcome"
    );
    assert_eq!(error.stage(), None);
}
