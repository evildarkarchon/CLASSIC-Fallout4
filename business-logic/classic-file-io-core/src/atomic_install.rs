//! Atomic install and rollback helpers for the YAML update delivery flow.
//!
//! These helpers implement the D-06 install-flow contract from the YAML update
//! delivery change: a downloaded file lands in a temporary path inside the
//! target's own directory, has its SHA-256 digest verified against the
//! manifest-declared value, and — only on success — is promoted to the target
//! via an atomic rename while the previous copy is preserved as `<target>.prev`
//! for one-step rollback.
//!
//! # Flow
//!
//! [`install_atomic`] implements the full install path:
//!
//! 1. Validate that `source_tmp` lives in the same directory as `target` so the
//!    final rename stays cross-platform-atomic (NTFS/ext4 guarantee same-volume
//!    same-directory rename atomicity).
//! 2. Compute SHA-256 of `source_tmp`; compare to `expected_sha256`
//!    case-insensitively. On mismatch, delete `source_tmp` and leave the target
//!    and any existing `.prev` untouched.
//! 3. `sync_all()` the temp file so its bytes are on stable storage before the
//!    rename. Callers that wrote via async file APIs typically only drained
//!    user-space buffers; without this step a crash between the rename and the
//!    OS writeback can leave the canonical `target` path holding truncated or
//!    zero bytes while `self_heal` refuses to recover (it only acts when the
//!    target is missing, not when the target exists with garbage).
//! 4. If `target` already exists, rename it to `<target>.prev`, clobbering any
//!    older `.prev` (multiple rollback generations are explicitly out of scope).
//! 5. Rename `source_tmp` to `target`.
//! 6. Best-effort fsync the parent directory on Unix to force metadata commit
//!    (no-op on Windows; NTFS journal commits rename metadata atomically).
//!
//! [`rollback`] swaps `<target>` ↔ `<target>.prev` when a previous copy exists,
//! or returns [`RollbackOutcome::NoPreviousVersion`] when none does. If `target`
//! is missing but `<target>.prev` exists (interrupted install state), the
//! previous file is promoted back to the canonical name.
//!
//! [`self_heal`] is a strict subset of [`rollback`]: it ONLY promotes `.prev`
//! when the canonical target is missing. It never swaps. Callers that run on
//! every load (e.g. the shippable-YAML loader) must use [`self_heal`], not
//! [`rollback`], to avoid silently oscillating an updated file back to its
//! previous version on steady-state reads.
//!
//! # Error surface
//!
//! SHA-256 mismatch is surfaced via the new [`FileIOError::ChecksumMismatch`]
//! variant so callers can distinguish integrity failures from ordinary I/O
//! errors without pattern-matching on error strings.
//!
//! # Concurrency
//!
//! [`install_atomic`], [`rollback`], and the mutating branch of
//! [`self_heal`] acquire an exclusive OS-level lock on a `<target>.install.lock`
//! sibling file before any rename. The lock is held for the full sequence
//! `<target>` → `<target>.prev` → install/rollback and released when the
//! lock handle drops (including on process crash). Two processes or two
//! threads racing on the same target therefore serialize, so the one-step
//! rollback invariant — `<target>.prev` always holds the content that was
//! at `<target>` immediately before the most recent install — cannot be
//! corrupted by interleaved renames. The lock file itself is left on disk
//! after release; deleting it would race with concurrent acquirers.

use crate::error::FileIOError;
use crate::hash::FileHasher;
use fs4::fs_std::FileExt;
use std::fs::OpenOptions;
use std::path::{Path, PathBuf};

/// Outcome of a successful [`install_atomic`] call.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InstallOutcome {
    /// Absolute path to the installed file (same as the `target` argument).
    pub target: PathBuf,
    /// `true` when a pre-existing target was renamed to `<target>.prev` during
    /// install (i.e., a rollback copy is now available).
    pub created_prev: bool,
    /// The verified SHA-256 digest (lowercase hex) of the installed file.
    pub sha256: String,
}

/// Outcome of a [`rollback`] call.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RollbackOutcome {
    /// Rollback completed: the previous copy is now the canonical target.
    RolledBack {
        /// The path whose content was restored from `.prev`.
        target: PathBuf,
    },
    /// No `.prev` file existed for the target; nothing changed on disk.
    NoPreviousVersion {
        /// The path that was queried.
        target: PathBuf,
    },
}

/// Outcome of a [`self_heal`] call.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SelfHealOutcome {
    /// `<target>` was missing and `<target>.prev` was promoted to canonical.
    Promoted {
        /// The path that was restored from `.prev`.
        target: PathBuf,
    },
    /// Nothing to do — either both files exist (steady-state post-install) or
    /// neither does. No on-disk changes were made.
    NoAction {
        /// The path that was queried.
        target: PathBuf,
    },
}

/// Suffix appended to the canonical target path to store the previous copy.
const PREV_SUFFIX: &str = ".prev";

/// Suffix appended to the canonical target path to name the per-target
/// install/rollback lock file. Chosen to be unusual enough that it will
/// never collide with a legitimate cache file a manifest might publish.
const LOCK_SUFFIX: &str = ".install.lock";

/// Acquire an exclusive cross-process advisory lock on the sibling
/// `<target>.install.lock` file. The returned handle MUST stay in scope
/// for the duration of the multi-step rename sequence; dropping it
/// releases the lock (including on panic / process termination).
///
/// The lock file is created with `create(true)` so the first caller in a
/// fresh cache directory can still acquire, and `truncate(false)` so
/// concurrent acquirers do not truncate a lock file the holder has open
/// (a truncate would race with the current holder, though no bytes are
/// ever written). The file is intentionally left on disk after release;
/// removing it would race with subsequent acquirers that could obtain a
/// handle on the about-to-be-deleted path.
fn acquire_install_lock(target: &Path) -> Result<std::fs::File, FileIOError> {
    let mut os = target.as_os_str().to_os_string();
    os.push(LOCK_SUFFIX);
    let lock_path = PathBuf::from(os);

    let lock_file = OpenOptions::new()
        .create(true)
        .read(true)
        .write(true)
        .truncate(false)
        .open(&lock_path)
        .map_err(|source| FileIOError::WriteError {
            path: lock_path.clone(),
            source,
        })?;
    FileExt::lock_exclusive(&lock_file).map_err(|source| FileIOError::WriteError {
        path: lock_path,
        source,
    })?;
    Ok(lock_file)
}

/// Install `source_tmp` as `target` atomically, preserving the previous copy as
/// `<target>.prev` and verifying the SHA-256 digest before any rename.
///
/// `expected_sha256` is compared case-insensitively so callers can pass either
/// the lowercase `FileHasher` output or an uppercase manifest value.
///
/// # Errors
///
/// - [`FileIOError::InvalidPath`] — `source_tmp` does not live in the same
///   directory as `target` (same-directory rename invariant), or `target` has
///   no parent directory.
/// - [`FileIOError::NotFound`] — `source_tmp` does not exist.
/// - [`FileIOError::ChecksumMismatch`] — SHA-256 of `source_tmp` does not match
///   `expected_sha256`. The temporary file is deleted before this error is
///   returned.
/// - [`FileIOError::IoError`] — any of the underlying file renames or fsync
///   calls failed.
pub fn install_atomic(
    target: &Path,
    source_tmp: &Path,
    expected_sha256: &str,
) -> Result<InstallOutcome, FileIOError> {
    let parent = target.parent().ok_or_else(|| {
        FileIOError::InvalidPath(format!(
            "target has no parent directory: {}",
            target.display()
        ))
    })?;

    let tmp_parent = source_tmp.parent().ok_or_else(|| {
        FileIOError::InvalidPath(format!(
            "source_tmp has no parent directory: {}",
            source_tmp.display()
        ))
    })?;

    if !paths_refer_to_same_directory(parent, tmp_parent) {
        return Err(FileIOError::InvalidPath(format!(
            "source_tmp must live in the same directory as target (target parent: {}, tmp parent: {})",
            parent.display(),
            tmp_parent.display(),
        )));
    }

    if !source_tmp.exists() {
        return Err(FileIOError::NotFound(source_tmp.display().to_string()));
    }

    // Serialize concurrent install/rollback on this exact target so the
    // multi-step `target -> target.prev` + `tmp -> target` rename sequence
    // cannot interleave across processes or threads. Held for the entire
    // function scope; released automatically on the early-return checksum
    // path as well.
    let _lock = acquire_install_lock(target)?;

    // Clear any cached hash first so a stale entry from a previous install at
    // this path does not short-circuit the integrity check.
    FileHasher::clear_cache();
    let actual_sha = FileHasher::hash_file(source_tmp)?;

    if !sha256_eq(&actual_sha, expected_sha256) {
        // Integrity failure — delete the temp file and preserve all existing
        // target/.prev state.
        let _ = std::fs::remove_file(source_tmp);
        return Err(FileIOError::ChecksumMismatch {
            path: source_tmp.to_path_buf(),
            expected: expected_sha256.to_string(),
            actual: actual_sha,
        });
    }

    // Durably sync `source_tmp` bytes to stable storage BEFORE renaming it
    // into `target`. Without this, a crash or power loss between the rename
    // and the OS's background flush can leave the canonical `target` path
    // holding truncated or zero bytes while `self_heal` refuses to help —
    // `self_heal` only promotes `.prev` when `target` is missing, not when
    // `target` exists but contains garbage. The parent-directory fsync
    // below commits the rename metadata, not the file data. Both are
    // required for crash durability.
    //
    // `sync_all()` requires a handle with write access on Windows
    // (FlushFileBuffers enforces GENERIC_WRITE), so we re-open with write
    // mode. The handle is scoped to this block so it is closed before the
    // rename executes.
    {
        let f = OpenOptions::new().write(true).open(source_tmp).map_err(|source| {
            FileIOError::WriteError {
                path: source_tmp.to_path_buf(),
                source,
            }
        })?;
        f.sync_all().map_err(|source| FileIOError::WriteError {
            path: source_tmp.to_path_buf(),
            source,
        })?;
    }

    let prev_path = prev_path_for(target);
    let created_prev = if target.exists() {
        // Clobber any older .prev — we only keep one rollback generation.
        if prev_path.exists() {
            std::fs::remove_file(&prev_path).map_err(|source| FileIOError::WriteError {
                path: prev_path.clone(),
                source,
            })?;
        }
        std::fs::rename(target, &prev_path).map_err(|source| FileIOError::WriteError {
            path: prev_path.clone(),
            source,
        })?;
        true
    } else {
        false
    };

    std::fs::rename(source_tmp, target).map_err(|source| FileIOError::WriteError {
        path: target.to_path_buf(),
        source,
    })?;

    fsync_directory(parent);

    Ok(InstallOutcome {
        target: target.to_path_buf(),
        created_prev,
        sha256: actual_sha,
    })
}

/// Roll back `target` to its previous copy stored at `<target>.prev`.
///
/// Semantics:
///
/// - If `<target>.prev` does not exist: no filesystem changes;
///   [`RollbackOutcome::NoPreviousVersion`].
/// - If `<target>.prev` exists and `target` also exists: the two are swapped,
///   so the caller retains one rollback step in the other direction.
/// - If `<target>.prev` exists but `target` does not (interrupted-install
///   recovery / self-heal): the previous copy is promoted to the canonical
///   path without swapping.
pub fn rollback(target: &Path) -> Result<RollbackOutcome, FileIOError> {
    let parent = target.parent().ok_or_else(|| {
        FileIOError::InvalidPath(format!(
            "target has no parent directory: {}",
            target.display()
        ))
    })?;

    // Take the lock BEFORE checking `.prev` existence so a concurrent
    // install cannot rotate `.prev` out from under us between the check
    // and the rename sequence.
    let _lock = acquire_install_lock(target)?;

    let prev_path = prev_path_for(target);

    if !prev_path.exists() {
        return Ok(RollbackOutcome::NoPreviousVersion {
            target: target.to_path_buf(),
        });
    }

    if target.exists() {
        // Three-step swap: we can't atomically swap two files on Windows
        // without advanced Win32 APIs, so stage through a sibling temp path.
        // If interrupted mid-swap, the loader's self-heal will recover.
        let scratch = scratch_path_for(target);
        if scratch.exists() {
            std::fs::remove_file(&scratch).map_err(|source| FileIOError::WriteError {
                path: scratch.clone(),
                source,
            })?;
        }
        std::fs::rename(target, &scratch).map_err(|source| FileIOError::WriteError {
            path: scratch.clone(),
            source,
        })?;
        std::fs::rename(&prev_path, target).map_err(|source| FileIOError::WriteError {
            path: target.to_path_buf(),
            source,
        })?;
        std::fs::rename(&scratch, &prev_path).map_err(|source| FileIOError::WriteError {
            path: prev_path.clone(),
            source,
        })?;
    } else {
        // Self-heal: promote .prev to the canonical name.
        std::fs::rename(&prev_path, target).map_err(|source| FileIOError::WriteError {
            path: target.to_path_buf(),
            source,
        })?;
    }

    fsync_directory(parent);

    Ok(RollbackOutcome::RolledBack {
        target: target.to_path_buf(),
    })
}

/// Safe self-heal: promote `<target>.prev` to `target` ONLY when the canonical
/// target is missing. Never swaps.
///
/// Intended for callers that run on every read (e.g. the shippable-YAML
/// loader). Using [`rollback`] in that position is unsafe: when both `target`
/// and `<target>.prev` exist (the normal post-install state), `rollback` will
/// swap them and silently revert the just-installed file.
///
/// # Semantics
///
/// - `target` exists: [`SelfHealOutcome::NoAction`], regardless of whether
///   `<target>.prev` exists.
/// - `target` missing, `<target>.prev` missing: [`SelfHealOutcome::NoAction`].
/// - `target` missing, `<target>.prev` exists: rename `.prev` → `target` and
///   return [`SelfHealOutcome::Promoted`].
pub fn self_heal(target: &Path) -> Result<SelfHealOutcome, FileIOError> {
    // Fast-path unlocked: steady-state reads hit this branch and must not
    // pay the lock cost. A concurrent install always ends with `target`
    // existing, so this can only miss during the brief rename window —
    // the double-check under the lock below handles that race.
    if target.exists() {
        return Ok(SelfHealOutcome::NoAction {
            target: target.to_path_buf(),
        });
    }

    let parent = target.parent().ok_or_else(|| {
        FileIOError::InvalidPath(format!(
            "target has no parent directory: {}",
            target.display()
        ))
    })?;

    // Acquire the install lock BEFORE mutating. A concurrent install may
    // be partway through the `target -> target.prev -> target` rename
    // sequence right now; without the lock we could race that install's
    // mid-flight state and promote its in-progress `.prev` back.
    let _lock = acquire_install_lock(target)?;

    // Re-check under the lock: the concurrent install may have finished
    // while we were waiting, in which case there is nothing to heal.
    if target.exists() {
        return Ok(SelfHealOutcome::NoAction {
            target: target.to_path_buf(),
        });
    }

    let prev_path = prev_path_for(target);
    if !prev_path.exists() {
        return Ok(SelfHealOutcome::NoAction {
            target: target.to_path_buf(),
        });
    }

    std::fs::rename(&prev_path, target).map_err(|source| FileIOError::WriteError {
        path: target.to_path_buf(),
        source,
    })?;

    fsync_directory(parent);

    Ok(SelfHealOutcome::Promoted {
        target: target.to_path_buf(),
    })
}

fn prev_path_for(target: &Path) -> PathBuf {
    let mut os = target.as_os_str().to_os_string();
    os.push(PREV_SUFFIX);
    PathBuf::from(os)
}

fn scratch_path_for(target: &Path) -> PathBuf {
    let mut os = target.as_os_str().to_os_string();
    os.push(".rollback.tmp");
    PathBuf::from(os)
}

/// Compare two hex-encoded SHA-256 values case-insensitively.
fn sha256_eq(actual: &str, expected: &str) -> bool {
    actual.len() == expected.len()
        && actual
            .bytes()
            .zip(expected.bytes())
            .all(|(a, b)| a.eq_ignore_ascii_case(&b))
}

/// Canonicalize parent directories before comparing them so that
/// `./cache/CLASSIC Main.yaml.new` and `cache/CLASSIC Main.yaml` are recognized
/// as siblings under the same directory. Falls back to a plain equality check
/// when canonicalization fails (e.g., the temp dir isn't accessible in the
/// unusual way tests sometimes arrange).
fn paths_refer_to_same_directory(a: &Path, b: &Path) -> bool {
    match (std::fs::canonicalize(a), std::fs::canonicalize(b)) {
        (Ok(ca), Ok(cb)) => ca == cb,
        _ => a == b,
    }
}

#[cfg(unix)]
fn fsync_directory(dir: &Path) {
    use std::fs::File;
    // Best-effort; we do not fail the install if the fsync errors, since the
    // rename itself already committed to the filesystem journal.
    if let Ok(f) = File::open(dir) {
        let _ = f.sync_all();
    }
}

#[cfg(not(unix))]
fn fsync_directory(_dir: &Path) {
    // NTFS journals rename metadata atomically; there is no portable std::fs
    // equivalent to fsync-on-directory on Windows. Intentionally a no-op.
}

#[cfg(test)]
mod tests {
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
            prev_bytes == b"ORIGINAL"
                || prev_bytes == b"PAYLOAD-A"
                || prev_bytes == b"PAYLOAD-B",
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

        assert!(
            result_install.is_ok(),
            "install failed: {result_install:?}"
        );
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
}
