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
#[path = "atomic_install_tests.rs"]
mod tests;
