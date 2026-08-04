use std::path::{Path, PathBuf};

use super::{PublicationError, PublicationStage};
use crate::identity::ContentIdentity;

#[test]
fn every_stage_renders_a_stable_lowercase_identifier() {
    let rendered: Vec<_> = [
        PublicationStage::Create,
        PublicationStage::Write,
        PublicationStage::Flush,
        PublicationStage::Sync,
        PublicationStage::Publish,
    ]
    .into_iter()
    .map(|stage| stage.to_string())
    .collect();

    assert_eq!(rendered, ["create", "write", "flush", "sync", "publish"]);
}

#[test]
fn stage_failure_exposes_its_stage_path_and_source() {
    let error = PublicationError::stage_failure(
        PublicationStage::Sync,
        Path::new("/data/CLASSIC Ignore.yaml"),
        std::io::Error::from(std::io::ErrorKind::PermissionDenied),
    );

    assert_eq!(error.stage(), Some(PublicationStage::Sync));
    assert_eq!(error.path(), Path::new("/data/CLASSIC Ignore.yaml"));
    assert_eq!(
        error.io_source().map(std::io::Error::kind),
        Some(std::io::ErrorKind::PermissionDenied)
    );
}

#[test]
fn lock_failures_carry_the_lock_path_and_no_stage() {
    let open = PublicationError::LockOpen {
        path: PathBuf::from("/data/settings.yaml.commit.lock"),
        source: std::io::Error::from(std::io::ErrorKind::NotFound),
    };
    let acquire = PublicationError::LockAcquire {
        path: PathBuf::from("/data/settings.yaml.commit.lock"),
        source: std::io::Error::from(std::io::ErrorKind::WouldBlock),
    };

    assert_eq!(open.stage(), None);
    assert_eq!(acquire.stage(), None);
    assert_eq!(
        open.path(),
        Path::new("/data/settings.yaml.commit.lock"),
        "callers detect a removed directory from the lock-open source kind"
    );
    assert_eq!(
        open.io_source().map(std::io::Error::kind),
        Some(std::io::ErrorKind::NotFound)
    );
}

#[test]
fn backup_mismatch_carries_both_identities_and_no_io_source() {
    let error = PublicationError::BackupMismatch {
        path: PathBuf::from("/backup/original.bak"),
        expected: ContentIdentity::from_bytes(b"original"),
        actual: ContentIdentity::from_bytes(b""),
    };

    assert_eq!(error.stage(), None);
    assert!(
        error.io_source().is_none(),
        "a byte comparison result is not an I/O failure"
    );
    let PublicationError::BackupMismatch {
        expected, actual, ..
    } = &error
    else {
        unreachable!("constructed as a mismatch")
    };
    assert_eq!(expected.byte_len(), 8);
    assert_eq!(actual.byte_len(), 0);
}

#[test]
fn stage_failure_message_names_the_stage_and_the_path() {
    let error = PublicationError::stage_failure(
        PublicationStage::Write,
        Path::new("/data/target.yaml"),
        std::io::Error::from(std::io::ErrorKind::WriteZero),
    );

    let message = error.to_string();
    assert!(message.contains("write"), "message was: {message}");
    assert!(message.contains("target.yaml"), "message was: {message}");
}
