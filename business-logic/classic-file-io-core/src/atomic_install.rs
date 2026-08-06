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
//! [`install_atomic`] validates what only this module can know, then hands the
//! durability sequence to `classic-durable-publication`:
//!
//! 1. Validate that `source_tmp` lives in the same directory as `target` so the
//!    final rename stays cross-platform-atomic (NTFS/ext4 guarantee same-volume
//!    same-directory rename atomicity). This precondition stays here because
//!    the shared module adopts the staged file where the caller put it and has
//!    no way to check it.
//! 2. Call `durable_publication::install_verified`, which takes the install
//!    lock, verifies the digest case-insensitively, deletes `source_tmp` and
//!    aborts on mismatch, synchronizes the staged bytes, rotates `<target>` to
//!    `<target>.prev`, and moves `source_tmp` onto `target`.
//! 3. Map the neutral publication failure back onto this crate's published
//!    error codes, which are unchanged by that move.
//!
//! The rollback generation is the shared module's, not this module's: `.prev`
//! is reachable only through `install_verified`, which is what keeps ADR-0006's
//! prohibition on creating that state for Local Ignore YAML Data structural.
//! [`prev_path_for`] therefore delegates rather than spelling the suffix again.
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
//! SHA-256 mismatch is surfaced via the [`FileIOError::ChecksumMismatch`]
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
//!
//! All three take that lock through the one shared implementation in
//! `classic-durable-publication`, on the same lock filename as before. Install
//! gets it from the [`LockPolicy`] it passes in; rollback and self-heal publish
//! nothing but move the same files, so they acquire the same policy directly.

use crate::error::FileIOError;
use classic_durable_publication::{self as durable_publication, LockPolicy, PublicationLock};
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

/// Suffix appended to the canonical target path to name the per-target
/// install/rollback lock file. Chosen to be unusual enough that it will
/// never collide with a legitimate cache file a manifest might publish.
const LOCK_SUFFIX: &str = ".install.lock";

/// The lock every operation in this module serializes on.
///
/// One policy value rather than three call sites spelling [`LOCK_SUFFIX`], so
/// an install and a concurrent rollback cannot drift onto different lock files.
fn install_lock_policy() -> LockPolicy {
    LockPolicy::sibling(LOCK_SUFFIX)
}

/// Acquire an exclusive cross-process advisory lock on the sibling
/// `<target>.install.lock` file. The returned handle MUST stay in scope
/// for the duration of the multi-step rename sequence; dropping it
/// releases the lock (including on panic / process termination).
///
/// This is for the operations that move the rollback generation without
/// publishing anything — [`rollback`] and [`self_heal`]. [`install_atomic`]
/// does not call it: it passes [`install_lock_policy`] into the shared module,
/// which takes the same lock on the same path for the whole install sequence.
///
/// The lock file is intentionally left on disk after release; removing it
/// would race with subsequent acquirers that could obtain a handle on the
/// about-to-be-deleted path.
///
/// A policy that yields no lock is refused rather than tolerated. Both callers
/// move the rollback generation, so running unlocked would silently reintroduce
/// the interleaving the lock exists to prevent — and a discarded `None` would
/// look exactly like a held lock at the call site.
fn acquire_install_lock(target: &Path) -> Result<PublicationLock, FileIOError> {
    install_lock_policy()
        .acquire(target)
        .map_err(map_publication_error)?
        .ok_or_else(|| FileIOError::WriteError {
            path: target.to_path_buf(),
            source: std::io::Error::other(
                "install lock policy yielded no lock; refusing to move the rollback generation unlocked",
            ),
        })
}

/// Map a neutral durable-publication failure onto this crate's published codes.
///
/// The published error surface of [`install_atomic`] is unchanged by moving
/// onto the shared module, so this is a translation of an existing contract
/// rather than a new one: every stage failure and every lock failure was
/// already a [`FileIOError::WriteError`] naming the same path, and a digest
/// mismatch was already a [`FileIOError::ChecksumMismatch`] carrying the
/// caller's expected digest verbatim.
///
/// The two backup variants are unreachable here — `install_verified` publishes
/// no backup — but they are mapped rather than panicked on, so that a change in
/// the shared enum cannot turn into an abort in an install path.
fn map_publication_error(error: durable_publication::PublicationError) -> FileIOError {
    use durable_publication::PublicationError as Failure;

    match error {
        Failure::Stage { path, source, .. }
        | Failure::LockOpen { path, source }
        | Failure::LockAcquire { path, source } => FileIOError::WriteError { path, source },
        Failure::DigestMismatch {
            path,
            expected,
            actual,
        } => FileIOError::ChecksumMismatch {
            path,
            expected,
            actual: actual.sha256_hex(),
        },
        // The prior implementation reached the staged bytes through the shared
        // file hasher, whose open and read failures surfaced as `IoError`.
        Failure::StagedUnreadable { source, .. } | Failure::BackupUnreadable { source, .. } => {
            FileIOError::IoError(source)
        }
        Failure::BackupMismatch { path, .. } => FileIOError::WriteError {
            path,
            source: std::io::Error::other(
                "published backup bytes differ from the retained original",
            ),
        },
    }
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
/// - [`FileIOError::WriteError`] — the install lock could not be taken, or any
///   of the underlying renames or synchronization calls failed.
/// - [`FileIOError::IoError`] — `source_tmp` could not be read for digest
///   verification.
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

    // A directory (or anything else that is not a regular file) at the staged
    // path is a caller mistake rather than an integrity failure, and it was
    // already reported this way when the shared file hasher validated its
    // target. Keep it here, where "what counts as an installable file" belongs.
    if !source_tmp.is_file() {
        return Err(FileIOError::InvalidPath(format!(
            "Path is not a file: {}",
            source_tmp.display()
        )));
    }

    // Everything from the install lock onward is the shared durability
    // sequence: verify the digest, delete the staged file and abort on
    // mismatch, synchronize it, rotate `<target>` to its rollback generation,
    // and move the staged file onto `target`.
    //
    // Integrity verification deliberately does not go through `FileHasher`.
    // That constraint predates this module's move onto the shared crate — a
    // one-shot install must not perturb the process-global hash cache that
    // dedicated cache tests assert on — and it now holds structurally rather
    // than by remembering to call the uncached entry point: the shared module
    // knows nothing about this crate's cache and streams the digest itself.
    let install = durable_publication::install_verified(
        target,
        source_tmp,
        expected_sha256,
        &install_lock_policy(),
    )
    .map_err(map_publication_error)?;

    let outcome = InstallOutcome {
        target: target.to_path_buf(),
        created_prev: install.created_rollback_generation(),
        sha256: install.identity().sha256_hex(),
    };

    // Post-rename durability uncertainty is deliberately discarded on this
    // path, and named here rather than dropped so the decision is reviewable.
    // Surfacing it would mean a new stable outcome across the C++, Node, and
    // Python bindings plus refreshed parity baselines, which is out of scope
    // for a behaviour-preserving change.
    //
    // Follow-up: GitHub issue #153 ("Deepen Durable Publication"), under
    // "Out of Scope" — "Surfacing durability uncertainty on User Settings
    // commit or YAML Data Update Channel install ... tracked separately".
    //
    // The previous implementation discarded the same signal by not checking
    // the parent-directory fsync at all, which was invisible.
    let _install_durability = install.into_durability();

    Ok(outcome)
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

/// Return the `<target>.prev` rollback generation path.
///
/// Delegates rather than reconstructing the suffix so that the operations
/// which *consume* a rollback generation cannot drift from the one operation
/// that creates it. `.prev` is owned by `install_verified` and appears nowhere
/// else in this crate.
fn prev_path_for(target: &Path) -> PathBuf {
    durable_publication::rollback_generation_path(target)
}

fn scratch_path_for(target: &Path) -> PathBuf {
    let mut os = target.as_os_str().to_os_string();
    os.push(".rollback.tmp");
    PathBuf::from(os)
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
