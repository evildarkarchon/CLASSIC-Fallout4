//! Public-seam probe for config's ownership of YAML Data install, rollback,
//! self-heal, and Ignore/Local YAML generation (#248).
//!
//! The per-module unit tests (`src/atomic_install_tests.rs`,
//! `src/generation_tests.rs`) pin each operation's edge cases. This file only
//! asserts that a caller outside the crate reaches the whole lifecycle through
//! `classic_config_core`'s root exports, and that the durable effects compose:
//! an install leaves a one-step rollback generation, rollback swaps it back,
//! and self-heal recovers a missing canonical file without ever swapping.

use classic_config_core::{
    FileGenerator, FileGeneratorConfig, RollbackOutcome, SelfHealOutcome, install_atomic, rollback,
    self_heal,
};
use classic_file_io_core::FileIOError;
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};

/// Lowercase hex SHA-256 of `bytes`, the digest form manifests publish.
fn sha256_hex(bytes: &[u8]) -> String {
    Sha256::digest(bytes)
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect()
}

/// The `<target>.prev` rollback generation path, spelled from the documented
/// contract rather than through the implementation's helper.
fn prev_of(target: &Path) -> PathBuf {
    let mut os = target.as_os_str().to_os_string();
    os.push(".prev");
    PathBuf::from(os)
}

#[test]
fn install_rollback_and_self_heal_compose_through_config() {
    let dir = tempfile::tempdir().unwrap();
    let target = dir.path().join("CLASSIC Main.yaml");
    let staged = dir.path().join("CLASSIC Main.yaml.new");
    std::fs::write(&target, b"bundled").unwrap();
    std::fs::write(&staged, b"updated").unwrap();

    let installed = install_atomic(&target, &staged, &sha256_hex(b"updated")).unwrap();
    assert!(installed.created_prev);
    assert_eq!(installed.sha256, sha256_hex(b"updated"));
    assert_eq!(std::fs::read(&target).unwrap(), b"updated");
    assert_eq!(std::fs::read(prev_of(&target)).unwrap(), b"bundled");

    // Steady state: both files exist, so self-heal must not swap them back.
    assert!(matches!(
        self_heal(&target).unwrap(),
        SelfHealOutcome::NoAction { .. }
    ));
    assert_eq!(std::fs::read(&target).unwrap(), b"updated");

    // Rollback swaps, keeping one step available in the other direction.
    assert_eq!(
        rollback(&target).unwrap(),
        RollbackOutcome::RolledBack {
            target: target.clone()
        }
    );
    assert_eq!(std::fs::read(&target).unwrap(), b"bundled");
    assert_eq!(std::fs::read(prev_of(&target)).unwrap(), b"updated");

    // Interrupted-install state: canonical file missing, `.prev` present.
    std::fs::remove_file(&target).unwrap();
    assert_eq!(
        self_heal(&target).unwrap(),
        SelfHealOutcome::Promoted {
            target: target.clone()
        }
    );
    assert_eq!(std::fs::read(&target).unwrap(), b"updated");
    assert!(!prev_of(&target).exists());
}

#[test]
fn digest_mismatch_keeps_typed_error_and_leaves_target_untouched() {
    let dir = tempfile::tempdir().unwrap();
    let target = dir.path().join("CLASSIC Main.yaml");
    let staged = dir.path().join("CLASSIC Main.yaml.new");
    std::fs::write(&target, b"bundled").unwrap();
    std::fs::write(&staged, b"tampered").unwrap();

    let error = install_atomic(&target, &staged, &sha256_hex(b"expected")).unwrap_err();
    assert!(matches!(error, FileIOError::ChecksumMismatch { .. }));
    assert!(!staged.exists(), "a rejected staged file is deleted");
    assert_eq!(std::fs::read(&target).unwrap(), b"bundled");
    assert!(!prev_of(&target).exists());
}

#[test]
fn generator_paths_are_reachable_through_config() {
    let generator = FileGenerator::new(FileGeneratorConfig::new(
        "ignore".to_string(),
        "local".to_string(),
        "Fallout4".to_string(),
    ));
    assert_eq!(
        generator.ignore_file_path(),
        PathBuf::from("CLASSIC Ignore.yaml")
    );
    assert_eq!(
        generator.local_yaml_path(),
        PathBuf::from("CLASSIC Data/CLASSIC Fallout4 Local.yaml")
    );
}
