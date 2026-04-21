use super::*;
use std::io::Write;
use tempfile::tempdir;

fn sha256_hex(bytes: &[u8]) -> String {
    use sha2::{Digest, Sha256};
    let mut h = Sha256::new();
    h.update(bytes);
    let out = h.finalize();
    let mut s = String::with_capacity(out.len() * 2);
    for b in out.as_ref() as &[u8] {
        use std::fmt::Write as _;
        write!(&mut s, "{b:02x}").unwrap();
    }
    s
}

fn write_file(path: &Path, bytes: &[u8]) {
    let mut f = std::fs::File::create(path).unwrap();
    f.write_all(bytes).unwrap();
    f.sync_all().unwrap();
}

fn read_file(path: &Path) -> Vec<u8> {
    std::fs::read(path).unwrap()
}

#[test]
fn clean_install_no_existing_target() {
    let dir = tempdir().unwrap();
    let target = dir.path().join("file.yaml");
    let tmp = dir.path().join("file.yaml.new");
    let content = b"alpha";
    write_file(&tmp, content);

    let outcome = install_atomic(&target, &tmp, &sha256_hex(content)).unwrap();
    assert!(target.exists());
    assert!(!outcome.created_prev);
    assert!(!prev_path_for(&target).exists());
    assert_eq!(read_file(&target), content);
}

#[test]
fn install_over_existing_file_creates_prev() {
    let dir = tempdir().unwrap();
    let target = dir.path().join("file.yaml");
    let tmp = dir.path().join("file.yaml.new");

    write_file(&target, b"old-content");
    write_file(&tmp, b"new-content");

    let outcome = install_atomic(&target, &tmp, &sha256_hex(b"new-content")).unwrap();

    assert!(outcome.created_prev);
    assert_eq!(read_file(&target), b"new-content");
    assert_eq!(read_file(&prev_path_for(&target)), b"old-content");
}

#[test]
fn install_over_existing_prev_clobbers_old_prev() {
    let dir = tempdir().unwrap();
    let target = dir.path().join("file.yaml");
    let tmp = dir.path().join("file.yaml.new");
    let prev = prev_path_for(&target);

    write_file(&target, b"v2");
    write_file(&prev, b"ancient-v0");
    write_file(&tmp, b"v3");

    install_atomic(&target, &tmp, &sha256_hex(b"v3")).unwrap();

    // .prev should now hold v2 (not ancient-v0).
    assert_eq!(read_file(&prev), b"v2");
    assert_eq!(read_file(&target), b"v3");
}

#[test]
fn sha256_mismatch_deletes_tmp_and_preserves_state() {
    let dir = tempdir().unwrap();
    let target = dir.path().join("file.yaml");
    let tmp = dir.path().join("file.yaml.new");
    let prev = prev_path_for(&target);

    write_file(&target, b"keep-me");
    write_file(&prev, b"keep-prev");
    write_file(&tmp, b"tampered-content");

    // Lie about the hash.
    let err = install_atomic(&target, &tmp, &sha256_hex(b"different-payload")).unwrap_err();
    assert!(matches!(err, FileIOError::ChecksumMismatch { .. }));

    assert!(!tmp.exists(), "tmp must be deleted on mismatch");
    assert_eq!(read_file(&target), b"keep-me");
    assert_eq!(read_file(&prev), b"keep-prev");
}

#[test]
fn rejects_source_in_different_directory() {
    let dir_a = tempdir().unwrap();
    let dir_b = tempdir().unwrap();
    let target = dir_a.path().join("file.yaml");
    let tmp = dir_b.path().join("file.yaml.new");
    write_file(&tmp, b"payload");

    let err = install_atomic(&target, &tmp, &sha256_hex(b"payload")).unwrap_err();
    assert!(matches!(err, FileIOError::InvalidPath(_)));
}

#[test]
fn sha256_case_insensitive() {
    let dir = tempdir().unwrap();
    let target = dir.path().join("file.yaml");
    let tmp = dir.path().join("file.yaml.new");
    let content = b"beta";
    write_file(&tmp, content);

    // Pass the expected hash uppercased.
    let upper = sha256_hex(content).to_uppercase();
    install_atomic(&target, &tmp, &upper).unwrap();
    assert_eq!(read_file(&target), content);
}

#[test]
fn rollback_with_prev_swaps_files() {
    let dir = tempdir().unwrap();
    let target = dir.path().join("file.yaml");
    let prev = prev_path_for(&target);

    write_file(&target, b"current");
    write_file(&prev, b"previous");

    let outcome = rollback(&target).unwrap();
    assert!(matches!(outcome, RollbackOutcome::RolledBack { .. }));

    assert_eq!(read_file(&target), b"previous");
    assert_eq!(read_file(&prev), b"current");
}

#[test]
fn rollback_without_prev_returns_no_previous_version() {
    let dir = tempdir().unwrap();
    let target = dir.path().join("file.yaml");
    write_file(&target, b"only");

    let outcome = rollback(&target).unwrap();
    assert!(matches!(outcome, RollbackOutcome::NoPreviousVersion { .. }));

    // Target should be untouched.
    assert_eq!(read_file(&target), b"only");
    assert!(!prev_path_for(&target).exists());
}

#[test]
fn rollback_self_heal_when_target_missing_prev_present() {
    let dir = tempdir().unwrap();
    let target = dir.path().join("file.yaml");
    let prev = prev_path_for(&target);
    write_file(&prev, b"recovered");

    let outcome = rollback(&target).unwrap();
    assert!(matches!(outcome, RollbackOutcome::RolledBack { .. }));

    assert_eq!(read_file(&target), b"recovered");
    assert!(!prev.exists());
}

#[test]
fn self_heal_noop_when_both_exist_does_not_swap() {
    let dir = tempdir().unwrap();
    let target = dir.path().join("file.yaml");
    let prev = prev_path_for(&target);

    write_file(&target, b"current");
    write_file(&prev, b"previous");

    let outcome = self_heal(&target).unwrap();
    assert!(matches!(outcome, SelfHealOutcome::NoAction { .. }));

    // Critical: files must remain exactly as they were.
    assert_eq!(read_file(&target), b"current");
    assert_eq!(read_file(&prev), b"previous");
}

#[test]
fn self_heal_noop_when_neither_exists() {
    let dir = tempdir().unwrap();
    let target = dir.path().join("file.yaml");

    let outcome = self_heal(&target).unwrap();
    assert!(matches!(outcome, SelfHealOutcome::NoAction { .. }));
    assert!(!target.exists());
    assert!(!prev_path_for(&target).exists());
}

#[test]
fn self_heal_promotes_prev_when_target_missing() {
    let dir = tempdir().unwrap();
    let target = dir.path().join("file.yaml");
    let prev = prev_path_for(&target);
    write_file(&prev, b"recovered");

    let outcome = self_heal(&target).unwrap();
    assert!(matches!(outcome, SelfHealOutcome::Promoted { .. }));

    assert_eq!(read_file(&target), b"recovered");
    assert!(!prev.exists());
}

#[test]
fn self_heal_noop_when_only_target_exists() {
    let dir = tempdir().unwrap();
    let target = dir.path().join("file.yaml");
    write_file(&target, b"only");

    let outcome = self_heal(&target).unwrap();
    assert!(matches!(outcome, SelfHealOutcome::NoAction { .. }));
    assert_eq!(read_file(&target), b"only");
}

// Crash-durability regression (Codex adversarial review, finding #1):
// callers that wrote `source_tmp` via tokio's async writer pattern
// (`create`, `write_all`, `flush`) only drained user-space buffers; the
// OS page cache still held the bytes when `install_atomic` renamed the
// file into place. A power loss between the rename and the OS's
// writeback would leave `target` existing with truncated bytes, and
// `self_heal` would refuse to restore from `.prev` because the
// canonical target still exists. The install step now opens the temp
// file for write and calls `sync_all()` before renaming, so its bytes
// are on stable storage before the rename is visible.
//
// A pure unit test cannot simulate power loss, so the behavioural guard
// here is: install_atomic must accept a `source_tmp` written by a
// handle that was dropped WITHOUT an explicit sync, complete
// successfully, and leave the target with the correct bytes. This
// proves that the sync step does not regress the tokio-style writer
// pattern the yaml_update downloader uses.
#[test]
fn install_atomic_syncs_temp_file_before_rename() {
    let dir = tempdir().unwrap();
    let target = dir.path().join("file.yaml");
    let tmp = dir.path().join("file.yaml.new");
    let content = b"payload-for-durability";

    // Write via the no-sync path the async downloader uses: open,
    // write_all, drop without sync_all. The OS may or may not have
    // flushed by the time install_atomic runs — that's exactly the
    // window this fix guards.
    {
        let mut f = std::fs::File::create(&tmp).unwrap();
        f.write_all(content).unwrap();
        // Intentionally no sync_all / sync_data — install_atomic owns
        // the durability contract now.
    }

    install_atomic(&target, &tmp, &sha256_hex(content)).unwrap();
    assert!(target.exists());
    assert_eq!(read_file(&target), content);
    // Temp file was renamed, not copied.
    assert!(!tmp.exists());
}

// Concurrency regression (Codex adversarial review, rollback-history
// finding). Without per-target serialization, two concurrent
// `install_atomic` calls over the same existing target could interleave
// their `target -> target.prev` renames and leave `.prev` pointing at
// garbage (or at an in-progress write). The install lock must force the
// second install to wait until the first completes, so `.prev` always
// ends up pointing at a known-good version from some prior install.
#[test]
fn concurrent_installs_preserve_known_good_prev() {
    use std::sync::{Arc, Barrier};
    use std::thread;

    let dir = tempdir().unwrap();
    let dir_path: PathBuf = dir.path().to_path_buf();
    let target = dir_path.join("file.yaml");

    // Initial state: target exists with "ORIGINAL" content, no .prev.
    write_file(&target, b"ORIGINAL");

    // Barrier ensures both threads arrive at the install call at
    // roughly the same time, maximizing the rename-race window without
    // the lock.
    let barrier = Arc::new(Barrier::new(2));

    let barrier_a = Arc::clone(&barrier);
    let dir_a = dir_path.clone();
    let target_a = target.clone();
    let handle_a = thread::spawn(move || {
        let tmp = dir_a.join("file.yaml.tmp.A");
        write_file(&tmp, b"PAYLOAD-A");
        let expected = sha256_hex(b"PAYLOAD-A");
        barrier_a.wait();
        install_atomic(&target_a, &tmp, &expected)
    });

    let barrier_b = Arc::clone(&barrier);
    let dir_b = dir_path.clone();
    let target_b = target.clone();
    let handle_b = thread::spawn(move || {
        let tmp = dir_b.join("file.yaml.tmp.B");
        write_file(&tmp, b"PAYLOAD-B");
        let expected = sha256_hex(b"PAYLOAD-B");
        barrier_b.wait();
        install_atomic(&target_b, &tmp, &expected)
    });

    let result_a = handle_a.join().unwrap();
    let result_b = handle_b.join().unwrap();

    // Both installs must succeed — the lock serializes them, it doesn't
    // fail either one.
    assert!(result_a.is_ok(), "install A failed: {result_a:?}");
    assert!(result_b.is_ok(), "install B failed: {result_b:?}");

    // Invariant: final target holds one of the two payloads.
    let final_bytes = read_file(&target);
    assert!(
        final_bytes == b"PAYLOAD-A" || final_bytes == b"PAYLOAD-B",
        "target must contain one of the installed payloads, got: {:?}",
        String::from_utf8_lossy(&final_bytes)
    );

    // Invariant: `.prev` must exist (we installed over an existing target
    // twice; the first install promotes ORIGINAL, the second promotes
    // the first install's payload).
    let prev = prev_path_for(&target);
    assert!(
        prev.exists(),
        "installing over an existing target twice must leave `.prev` populated"
    );

    // Key rollback-invariant: `.prev` bytes must be one of the known
    // pre-update states — ORIGINAL (if second install's pre-image was
    // the first install's target) OR one of the payloads (if ordering
    // interleaved differently). Without locking, `.prev` can end up
    // holding bytes from an in-progress rename, which would fail here.
    let prev_bytes = read_file(&prev);
    assert!(
        prev_bytes == b"ORIGINAL" || prev_bytes == b"PAYLOAD-A" || prev_bytes == b"PAYLOAD-B",
        "`.prev` must contain a known installed version, not interleaved garbage. Got: {:?}",
        String::from_utf8_lossy(&prev_bytes)
    );

    // And the two must disagree — `.prev` is definitionally NOT the
    // currently-installed version.
    assert_ne!(
        final_bytes, prev_bytes,
        "`.prev` must differ from the currently-installed target"
    );
}

// Concurrency regression complement: one install + one rollback racing
// on the same target. Without the lock, rollback's three-step swap
// (target -> scratch, prev -> target, scratch -> prev) could interleave
// with install's two-step promotion. With the lock, one of the two
// completes fully before the other starts, and both succeed.
#[test]
fn concurrent_install_and_rollback_serialize_cleanly() {
    use std::sync::{Arc, Barrier};
    use std::thread;

    let dir = tempdir().unwrap();
    let dir_path: PathBuf = dir.path().to_path_buf();
    let target = dir_path.join("file.yaml");
    let prev = prev_path_for(&target);

    // Initial state: target holds V2, .prev holds V1 (steady-state
    // after a prior successful install).
    write_file(&target, b"V2");
    write_file(&prev, b"V1");

    let barrier = Arc::new(Barrier::new(2));

    let barrier_a = Arc::clone(&barrier);
    let dir_a = dir_path.clone();
    let target_a = target.clone();
    let handle_install = thread::spawn(move || {
        let tmp = dir_a.join("file.yaml.tmp.V3");
        write_file(&tmp, b"V3");
        let expected = sha256_hex(b"V3");
        barrier_a.wait();
        install_atomic(&target_a, &tmp, &expected)
    });

    let barrier_b = Arc::clone(&barrier);
    let target_b = target.clone();
    let handle_rollback = thread::spawn(move || {
        barrier_b.wait();
        rollback(&target_b)
    });

    let result_install = handle_install.join().unwrap();
    let result_rollback = handle_rollback.join().unwrap();

    assert!(result_install.is_ok(), "install failed: {result_install:?}");
    assert!(
        result_rollback.is_ok(),
        "rollback failed: {result_rollback:?}"
    );

    // Whichever ordering won, target + .prev must be a known pair:
    //   Install-then-rollback: target=V2, .prev=V3
    //   Rollback-then-install: target=V3, .prev=V1
    // Anything else indicates an interleaved rename corrupted state.
    let final_bytes = read_file(&target);
    let prev_bytes = read_file(&prev);
    let pair = (final_bytes.as_slice(), prev_bytes.as_slice());
    assert!(
        pair == (b"V2".as_slice(), b"V3".as_slice())
            || pair == (b"V3".as_slice(), b"V1".as_slice()),
        "target/.prev must be one of the two ordered outcomes. Got target={:?} prev={:?}",
        String::from_utf8_lossy(&final_bytes),
        String::from_utf8_lossy(&prev_bytes),
    );
}
