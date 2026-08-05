//! The staging-and-publish sequence and the two operations built on it.

use std::fs::File;
use std::io::Write as _;
use std::path::Path;

use tempfile::NamedTempFile;

use crate::error::{PublicationError, PublicationStage};
use crate::identity::ContentIdentity;
use crate::lock::LockPolicy;

/// Whether the published namespace entry reached the durability barrier.
///
/// On Unix these are genuinely separate events: `rename` makes complete bytes
/// visible, and a later directory synchronization is what makes the *entry*
/// survive a crash. The second can fail on its own, after the first has
/// already succeeded, which is why uncertainty is a value rather than an
/// error. This module never decides whether that uncertainty matters.
#[derive(Debug)]
pub enum Durability {
    /// The bytes and their namespace entry reached the durability barrier.
    Durable,
    /// Complete bytes are visible, but namespace durability is unconfirmed.
    Unknown(std::io::Error),
}

impl Durability {
    /// Return whether the namespace entry is known to be durable.
    #[must_use]
    pub const fn is_durable(&self) -> bool {
        matches!(self, Self::Durable)
    }

    /// Return the failure that left namespace durability unconfirmed.
    #[must_use]
    pub const fn unknown_source(&self) -> Option<&std::io::Error> {
        match self {
            Self::Durable => None,
            Self::Unknown(source) => Some(source),
        }
    }
}

/// A completed durable publication.
///
/// Marked `#[must_use]` because the durability outcome it carries is the one
/// thing a caller can accidentally drop. Discarding it should be a written
/// decision, not an omission.
#[must_use]
#[derive(Debug)]
pub struct Publication {
    identity: ContentIdentity,
    durability: Durability,
}

impl Publication {
    /// Return the identity of the bytes now visible at the target path.
    #[must_use]
    pub const fn identity(&self) -> &ContentIdentity {
        &self.identity
    }

    /// Return whether the namespace entry reached the durability barrier.
    #[must_use]
    pub const fn durability(&self) -> &Durability {
        &self.durability
    }

    /// Consume the publication and return only its durability outcome.
    ///
    /// Callers that deliberately discard durability uncertainty should do so
    /// through this method, so the discard is a named expression rather than
    /// an omitted error check.
    #[must_use]
    pub fn into_durability(self) -> Durability {
        self.durability
    }
}

/// The byte-exact backup that must exist before a target is replaced.
///
/// The caller owns backup *location*; this crate only owns the ordering that
/// makes the backup trustworthy. `original` is the caller's retained copy of
/// the bytes currently at the target, which the reread backup must match.
#[derive(Debug, Clone, Copy)]
pub struct VerifiedBackup<'a> {
    path: &'a Path,
    original: &'a [u8],
}

impl<'a> VerifiedBackup<'a> {
    /// Describe a backup of `original` to be published at `path`.
    #[must_use]
    pub const fn new(path: &'a Path, original: &'a [u8]) -> Self {
        Self { path, original }
    }

    /// Return the path the backup is published to.
    #[must_use]
    pub const fn path(&self) -> &'a Path {
        self.path
    }

    /// Return the retained original bytes the backup must match.
    #[must_use]
    pub const fn original(&self) -> &'a [u8] {
        self.original
    }
}

/// A replacement that was preceded by a verified backup.
///
/// `#[must_use]` for the same reason as [`Publication`]: it carries the
/// replacement's durability outcome.
#[must_use]
#[derive(Debug)]
pub struct VerifiedBackupPublication {
    backup_identity: ContentIdentity,
    replacement: Publication,
}

impl VerifiedBackupPublication {
    /// Return the identity of the backup that was reread and byte-compared.
    #[must_use]
    pub const fn backup_identity(&self) -> &ContentIdentity {
        &self.backup_identity
    }

    /// Return the replacement publication at the target path.
    ///
    /// `Publication` is itself `#[must_use]`, so no attribute is needed here.
    pub const fn replacement(&self) -> &Publication {
        &self.replacement
    }

    /// Consume this result and return the replacement publication.
    pub fn into_replacement(self) -> Publication {
        self.replacement
    }
}

/// Whether a publication may replace an existing entry at its final path.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum PublicationMode {
    /// Replace whatever currently occupies the final path.
    Replace,
    /// Publish to a path that must not already exist.
    Unique,
}

/// Prefix for the same-directory staging file.
///
/// The leading dot keeps the staging artifact out of the way on Unix listings
/// during the brief window it exists.
const STAGING_PREFIX: &str = ".classic-durable-publication-";

/// Suffix for the same-directory staging file.
const STAGING_SUFFIX: &str = ".tmp";

/// Durably publish complete bytes at `target`, replacing whatever is there.
///
/// The bytes are staged in `target`'s own directory, written, flushed, and
/// synchronized before any part of them becomes visible at `target`, so a
/// crash cannot leave partial content behind.
///
/// # Concurrency
///
/// `lock` decides whether this call takes an exclusive cross-process lock. The
/// lock, when requested, is held for the entire staging-and-publish sequence
/// and released when this function returns. With [`LockPolicy::none`] this
/// call takes no lock and a concurrent writer may win the final publish; the
/// bytes visible at `target` are still complete either way.
///
/// # Errors
///
/// Returns [`PublicationError::LockOpen`] or [`PublicationError::LockAcquire`]
/// when a requested lock cannot be taken, and [`PublicationError::Stage`] when
/// any step of the sequence fails. In every error case `target` retains its
/// prior content.
///
/// Note that a failed *durability* barrier is not an error: it is reported as
/// [`Durability::Unknown`] on the returned [`Publication`].
pub fn publish(
    target: &Path,
    bytes: &[u8],
    lock: &LockPolicy,
) -> Result<Publication, PublicationError> {
    let _lock = lock.acquire(target)?;
    publish_locked(target, bytes, PublicationMode::Replace)
}

/// Complete bytes staged and synchronized beside a target, not yet visible.
///
/// Holding one of these means every fallible part of a publication except the
/// final move has already succeeded: the bytes are written and at the
/// platform's durability barrier, and [`Self::publish`] is the single remaining
/// step. Nothing is visible at the target until that call.
///
/// `#[must_use]` because dropping this discards work rather than performing it.
/// Dropping is safe — the staging file is removed — but it is never what a
/// caller means.
#[must_use = "a staged publication is only visible once it is published"]
#[derive(Debug)]
pub struct StagedPublication<'a> {
    staged: NamedTempFile,
    target: &'a Path,
    identity: ContentIdentity,
}

impl<'a> StagedPublication<'a> {
    /// Return the target these bytes will become visible at.
    #[must_use]
    pub const fn target(&self) -> &'a Path {
        self.target
    }

    /// Return the identity of the bytes waiting to be published.
    #[must_use]
    pub const fn identity(&self) -> &ContentIdentity {
        &self.identity
    }

    /// Move the synchronized staging file onto the target, replacing it.
    ///
    /// # Errors
    ///
    /// Returns [`PublicationError::Stage`] with a [`PublicationStage::Publish`]
    /// stage when the move fails; the target retains its prior content and the
    /// staging file is removed best-effort.
    pub fn publish(self) -> Result<Publication, PublicationError> {
        let durability = publish_staged(self.staged, self.target, PublicationMode::Replace)?;
        Ok(Publication {
            identity: self.identity,
            durability,
        })
    }
}

/// Stage complete bytes beside `target` without making them visible.
///
/// This is [`publish`] stopped one step short, for the caller that must run a
/// check of its own in the narrowest possible window before the final move.
/// `classic-config-core`'s Local Ignore reset is that caller: it rereads the
/// canonical bytes and byte-compares them against what the user approved, and
/// the value of that check is inversely proportional to how much work sits
/// between it and the move. Staging first collapses that gap to the move alone.
///
/// # Concurrency
///
/// Takes no lock, for the same reason [`publish_verified_backup`] does not: a
/// lock scoped to staging alone would release before the move it exists to
/// guard. A caller splitting the sequence holds its own lock across both.
///
/// # Errors
///
/// Returns [`PublicationError::Stage`] when any of the create, write, flush, or
/// sync steps fails. Nothing has been made visible at `target` in any case.
pub fn stage<'a>(
    target: &'a Path,
    bytes: &[u8],
) -> Result<StagedPublication<'a>, PublicationError> {
    Ok(StagedPublication {
        staged: stage_bytes(target, bytes)?,
        target,
        identity: ContentIdentity::from_bytes(bytes),
    })
}

/// Publish a verified backup, then replace `target` only if the backup holds.
///
/// The ordering is the point of this operation:
///
/// 1. Publish `backup.original()` to `backup.path()`, which must not exist.
/// 2. Reread those bytes *from disk* and byte-compare them against the
///    retained original.
/// 3. Abort without touching `target` if they differ.
/// 4. Only then publish `bytes` at `target`.
///
/// Step 2 is a reread rather than a trust of step 1 because a backup that
/// silently failed to write is indistinguishable from a good one until it is
/// read back. Aborting at step 3 is what prevents an accepted recovery from
/// destroying the only copy of a user's data.
///
/// # Concurrency
///
/// `lock` is acquired on `target` — not on the backup path — and is held
/// across all four steps, so the backup cannot be verified against one target
/// state and then applied to another. Backup paths are expected to be unique
/// per publication, which is why the backup publish refuses to clobber.
///
/// # Errors
///
/// Returns [`PublicationError::LockOpen`] or [`PublicationError::LockAcquire`]
/// when a requested lock cannot be taken; [`PublicationError::Stage`] when the
/// backup or the replacement fails to stage or publish (a backup path that
/// already exists surfaces here with an
/// [`std::io::ErrorKind::AlreadyExists`] source);
/// [`PublicationError::BackupUnreadable`] when the reread fails; and
/// [`PublicationError::BackupMismatch`] when the reread bytes differ. In every
/// error case `target` retains its prior content.
pub fn publish_with_verified_backup(
    target: &Path,
    bytes: &[u8],
    backup: VerifiedBackup<'_>,
    lock: &LockPolicy,
) -> Result<VerifiedBackupPublication, PublicationError> {
    let _lock = lock.acquire(target)?;

    let backup_identity = publish_verified_backup_locked(backup)?;
    let replacement = publish_locked(target, bytes, PublicationMode::Replace)?;
    Ok(VerifiedBackupPublication {
        backup_identity,
        replacement,
    })
}

/// Publish a backup and prove it byte-exact, without replacing anything.
///
/// This is the first half of [`publish_with_verified_backup`], exposed on its
/// own for the caller whose conflict policy has to run *between* the
/// verification and the replacement. Splitting it here keeps the ordering that
/// makes a backup trustworthy — unique publish, reread from disk, byte-compare,
/// abort on mismatch — inside this module, while leaving the caller free to
/// decide, after the backup exists, whether replacing is still the right thing
/// to do.
///
/// The returned [`ContentIdentity`] is calculated from the *reread* bytes
/// rather than from `backup.original()`, so it attests what is actually on
/// disk.
///
/// # Concurrency
///
/// This operation takes no lock of its own, because a lock scoped to it alone
/// would be worthless: it would release before the caller's replacement, which
/// is exactly the window the lock exists to close. A caller that splits the
/// sequence this way must hold its own lock across this call, its policy check,
/// and the subsequent [`publish`]. Callers with nothing to do in between should
/// use [`publish_with_verified_backup`], which locks all four steps together.
///
/// # Errors
///
/// Returns [`PublicationError::Stage`] when the backup fails to stage or
/// publish — a backup path that already exists surfaces here with an
/// [`std::io::ErrorKind::AlreadyExists`] source;
/// [`PublicationError::BackupUnreadable`] when the reread fails; and
/// [`PublicationError::BackupMismatch`] when the reread bytes differ. No
/// replacement is ever attempted by this operation.
pub fn publish_verified_backup(
    backup: VerifiedBackup<'_>,
) -> Result<ContentIdentity, PublicationError> {
    publish_verified_backup_locked(backup)
}

/// Publish and verify a backup with any caller lock already held.
fn publish_verified_backup_locked(
    backup: VerifiedBackup<'_>,
) -> Result<ContentIdentity, PublicationError> {
    // The backup's own durability outcome is deliberately not surfaced: the
    // reread below is a stronger statement about the backup than a directory
    // synchronization would be, and backup durability policy belongs to the
    // caller that chose the backup location. Named rather than dropped, which
    // is the same discipline this crate asks of its callers.
    let _backup_durability =
        publish_locked(backup.path(), backup.original(), PublicationMode::Unique)?
            .into_durability();

    #[cfg(test)]
    fault::tamper_published_backup(backup.path());

    let reread =
        std::fs::read(backup.path()).map_err(|source| PublicationError::BackupUnreadable {
            path: backup.path().to_path_buf(),
            source,
        })?;
    if reread != backup.original() {
        return Err(PublicationError::BackupMismatch {
            path: backup.path().to_path_buf(),
            expected: ContentIdentity::from_bytes(backup.original()),
            actual: ContentIdentity::from_bytes(&reread),
        });
    }
    Ok(ContentIdentity::from_bytes(&reread))
}

/// Run the staging-and-publish sequence with any lock already held.
fn publish_locked(
    target: &Path,
    bytes: &[u8],
    mode: PublicationMode,
) -> Result<Publication, PublicationError> {
    let staged = stage_bytes(target, bytes)?;
    let durability = publish_staged(staged, target, mode)?;
    Ok(Publication {
        identity: ContentIdentity::from_bytes(bytes),
        durability,
    })
}

/// Write, flush, and synchronize a same-directory staging file.
///
/// Staging in the target's *own* directory is what makes the final move a
/// same-volume operation, which is the precondition for it being atomic.
fn stage_bytes(target: &Path, bytes: &[u8]) -> Result<NamedTempFile, PublicationError> {
    let parent = target.parent().ok_or_else(|| {
        PublicationError::stage_failure(
            PublicationStage::Create,
            target,
            std::io::Error::new(
                std::io::ErrorKind::InvalidInput,
                "publication path has no parent directory",
            ),
        )
    })?;
    let mut staged = tempfile::Builder::new()
        .prefix(STAGING_PREFIX)
        .suffix(STAGING_SUFFIX)
        .tempfile_in(parent)
        .map_err(|source| {
            PublicationError::stage_failure(PublicationStage::Create, target, source)
        })?;
    staged.write_all(bytes).map_err(|source| {
        PublicationError::stage_failure(PublicationStage::Write, target, source)
    })?;
    staged.flush().map_err(|source| {
        PublicationError::stage_failure(PublicationStage::Flush, target, source)
    })?;
    staged.as_file().sync_all().map_err(|source| {
        PublicationError::stage_failure(PublicationStage::Sync, target, source)
    })?;
    Ok(staged)
}

/// Move a fully synchronized staging file onto its final path.
fn publish_staged(
    staged: NamedTempFile,
    target: &Path,
    mode: PublicationMode,
) -> Result<Durability, PublicationError> {
    // `keep` is load-bearing on Windows, not merely an ownership transfer: it
    // clears the staged file's FILE_ATTRIBUTE_TEMPORARY. A file that still
    // carries that attribute may never be written back by the cache manager,
    // which would defeat the write-through move performed below. Do not
    // replace this with a plain rename of `staged.path()`.
    let (staged_file, staged_path) = staged.keep().map_err(|failure| {
        PublicationError::stage_failure(PublicationStage::Publish, target, failure.error)
    })?;
    drop(staged_file);

    match publish_staged_path(&staged_path, target, mode) {
        Ok(durability) => Ok(durability),
        Err(error) => {
            // The staging path is caller-owned from `keep` onward, and a
            // failure here means the move never consumed it. `NamedTempFile`
            // can no longer clean it up, so remove it best-effort; a leftover
            // staging artifact must not mask the real failure.
            let _ = std::fs::remove_file(&staged_path);
            Err(error)
        }
    }
}

/// Rename onto the final path, then report Unix namespace durability.
#[cfg(unix)]
fn publish_staged_path(
    staged_path: &Path,
    target: &Path,
    mode: PublicationMode,
) -> Result<Durability, PublicationError> {
    let parent = target.parent().unwrap_or_else(|| Path::new("."));
    // Open the parent before the move so the post-publish synchronization uses
    // a handle that was valid at publish time.
    let directory = File::open(parent).map_err(|source| {
        PublicationError::stage_failure(PublicationStage::Publish, target, source)
    })?;
    match mode {
        PublicationMode::Replace => std::fs::rename(staged_path, target),
        // `move_atomic` refuses to clobber and reports AlreadyExists.
        PublicationMode::Unique => atomicwrites::move_atomic(staged_path, target),
    }
    .map_err(|source| PublicationError::stage_failure(PublicationStage::Publish, target, source))?;
    Ok(published_durability(Some(&directory)))
}

/// Use a write-through move on platforms without directory synchronization.
#[cfg(not(unix))]
fn publish_staged_path(
    staged_path: &Path,
    target: &Path,
    mode: PublicationMode,
) -> Result<Durability, PublicationError> {
    match mode {
        // MoveFileEx with MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH.
        PublicationMode::Replace => atomicwrites::replace_atomic(staged_path, target),
        // The same call without MOVEFILE_REPLACE_EXISTING.
        PublicationMode::Unique => atomicwrites::move_atomic(staged_path, target),
    }
    .map_err(|source| PublicationError::stage_failure(PublicationStage::Publish, target, source))?;
    Ok(published_durability(None))
}

/// Report namespace durability once complete bytes are already visible.
///
/// A failure here is returned as data, never as an error: reporting it as a
/// failure would falsely imply the previous content survived.
fn published_durability(directory: Option<&File>) -> Durability {
    #[cfg(test)]
    if fault::directory_sync_should_fail() {
        return Durability::Unknown(std::io::Error::new(
            std::io::ErrorKind::PermissionDenied,
            "injected publication directory synchronization failure",
        ));
    }
    match directory {
        Some(directory) => match directory.sync_all() {
            Ok(()) => Durability::Durable,
            Err(source) => Durability::Unknown(source),
        },
        // Windows journals same-directory replacement metadata and std exposes
        // no directory synchronization handle, so a completed write-through
        // move is already at the durability barrier.
        None => Durability::Durable,
    }
}

/// Deliberately unpublished fault injection, reachable only under `cfg(test)`.
///
/// Two of this module's outcomes have no portable filesystem condition that
/// provokes them on demand:
///
/// - A directory synchronization failure. `fsync` on a directory handle does
///   not fail to order, yet the uncertain outcome is the one thing about this
///   module every caller must handle.
/// - A published backup whose bytes on disk differ from what was written. That
///   is precisely a filesystem or device that lied about a completed write —
///   the condition the reread exists to catch, and one no cooperating
///   filesystem will reproduce.
///
/// These hooks are not exposed on the crate's interface. A caller that wants
/// to test its own stage mapping should use a fake at its own seam rather than
/// reach for anything here.
#[cfg(test)]
pub(crate) mod fault {
    use std::cell::{Cell, RefCell};
    use std::path::Path;

    thread_local! {
        static FAIL_DIRECTORY_SYNC: Cell<bool> = const { Cell::new(false) };
        static TAMPER_BACKUP_WITH: RefCell<Option<Vec<u8>>> = const { RefCell::new(None) };
    }

    /// Return whether the current thread should report an uncertain barrier.
    pub(crate) fn directory_sync_should_fail() -> bool {
        FAIL_DIRECTORY_SYNC.with(Cell::get)
    }

    /// Force durability uncertainty on this thread until the guard drops.
    pub(crate) fn fail_directory_sync() -> FaultGuard {
        FAIL_DIRECTORY_SYNC.with(|flag| flag.set(true));
        FaultGuard
    }

    /// Overwrite a just-published backup so its reread cannot match.
    pub(crate) fn tamper_published_backup(path: &Path) {
        TAMPER_BACKUP_WITH.with(|bytes| {
            if let Some(bytes) = bytes.borrow().as_deref() {
                std::fs::write(path, bytes).expect("tampering with a published backup");
            }
        });
    }

    /// Make every published backup on this thread reread as `bytes`.
    pub(crate) fn corrupt_published_backups(bytes: &[u8]) -> FaultGuard {
        TAMPER_BACKUP_WITH.with(|slot| *slot.borrow_mut() = Some(bytes.to_vec()));
        FaultGuard
    }

    /// Restores normal behavior for every fault on this thread when dropped.
    pub(crate) struct FaultGuard;

    impl Drop for FaultGuard {
        fn drop(&mut self) {
            FAIL_DIRECTORY_SYNC.with(|flag| flag.set(false));
            TAMPER_BACKUP_WITH.with(|slot| *slot.borrow_mut() = None);
        }
    }
}

#[cfg(test)]
#[path = "publication_tests.rs"]
mod tests;
