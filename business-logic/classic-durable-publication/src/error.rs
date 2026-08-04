//! Neutral, caller-agnostic durable publication failures.
//!
//! Every failure here carries a path and, where one exists, the named stage
//! that failed plus the underlying [`std::io::Error`]. The types deliberately
//! know nothing about any caller's error enum or stable error codes: each
//! caller maps these onto its own published contract.

use std::fmt;
use std::path::{Path, PathBuf};

use thiserror::Error;

use crate::identity::ContentIdentity;

/// The named step of the staging-and-publish sequence that failed.
///
/// This is the single stage vocabulary for the whole workspace. It describes
/// the *staging file's* lifecycle, not the caller's transaction.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum PublicationStage {
    /// Creating the staging file in the final path's own directory.
    Create,
    /// Writing complete bytes into the staging file.
    Write,
    /// Flushing buffered staging bytes out of user space.
    Flush,
    /// Synchronizing the staging file to the platform's durability barrier.
    Sync,
    /// Moving the synchronized staging file onto its final path.
    Publish,
}

impl PublicationStage {
    /// Return the stable lowercase identifier used in rendered messages.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Create => "create",
            Self::Write => "write",
            Self::Flush => "flush",
            Self::Sync => "sync",
            Self::Publish => "publish",
        }
    }
}

impl fmt::Display for PublicationStage {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.as_str())
    }
}

/// A durable publication that did not complete.
///
/// Lock and backup-verification failures are separate variants rather than
/// extra stages because the existing callers publish distinct error codes for
/// them; folding them into [`PublicationStage`] would make those codes
/// unreachable from this type.
#[derive(Debug, Error)]
pub enum PublicationError {
    /// One step of the staging-and-publish sequence failed.
    ///
    /// Nothing was published: the final path still holds whatever it held
    /// before the call, and the staging file has been removed best-effort.
    #[error("durable publication failed during {stage} for {}", path.display())]
    Stage {
        /// The sequence step that failed.
        stage: PublicationStage,
        /// The final path the publication was targeting.
        path: PathBuf,
        /// The underlying filesystem failure.
        #[source]
        source: std::io::Error,
    },

    /// The cross-process lock file could not be opened.
    ///
    /// A [`std::io::ErrorKind::NotFound`] source means the directory that
    /// would hold the lock is gone, which callers may treat as a conflict
    /// rather than a failure.
    #[error("could not open the publication lock file {}", path.display())]
    LockOpen {
        /// The lock file path derived from the caller's [`crate::LockPolicy`].
        path: PathBuf,
        /// The underlying filesystem failure.
        #[source]
        source: std::io::Error,
    },

    /// The cross-process lock file was opened but could not be locked.
    #[error("could not acquire the publication lock {}", path.display())]
    LockAcquire {
        /// The lock file path derived from the caller's [`crate::LockPolicy`].
        path: PathBuf,
        /// The underlying filesystem failure.
        #[source]
        source: std::io::Error,
    },

    /// The published backup could not be reread for verification.
    ///
    /// The target has not been replaced.
    #[error("published backup {} could not be reread for verification", path.display())]
    BackupUnreadable {
        /// The backup path that was published and then reread.
        path: PathBuf,
        /// The underlying filesystem failure.
        #[source]
        source: std::io::Error,
    },

    /// The reread backup bytes differ from the retained original.
    ///
    /// Replacement was aborted, so the original is still the only copy at the
    /// target path. This is the condition the verified-backup ordering exists
    /// to catch: a backup that appeared to write but did not.
    #[error(
        "published backup {} does not match the retained original bytes",
        path.display()
    )]
    BackupMismatch {
        /// The backup path whose reread bytes were rejected.
        path: PathBuf,
        /// Identity of the retained original the backup should have matched.
        expected: ContentIdentity,
        /// Identity of the bytes actually found at the backup path.
        actual: ContentIdentity,
    },
}

impl PublicationError {
    /// Return the path the failure concerns.
    ///
    /// For [`Self::LockOpen`] and [`Self::LockAcquire`] this is the lock file,
    /// not the publication target.
    #[must_use]
    pub fn path(&self) -> &Path {
        match self {
            Self::Stage { path, .. }
            | Self::LockOpen { path, .. }
            | Self::LockAcquire { path, .. }
            | Self::BackupUnreadable { path, .. }
            | Self::BackupMismatch { path, .. } => path,
        }
    }

    /// Return the failed sequence step, if this failure has one.
    ///
    /// Lock and backup-verification failures happen outside the
    /// staging-and-publish sequence and therefore return `None`.
    #[must_use]
    pub const fn stage(&self) -> Option<PublicationStage> {
        match self {
            Self::Stage { stage, .. } => Some(*stage),
            _ => None,
        }
    }

    /// Return the underlying filesystem failure, if this failure has one.
    ///
    /// [`Self::BackupMismatch`] is a verification result rather than an I/O
    /// failure and therefore returns `None`.
    #[must_use]
    pub const fn io_source(&self) -> Option<&std::io::Error> {
        match self {
            Self::Stage { source, .. }
            | Self::LockOpen { source, .. }
            | Self::LockAcquire { source, .. }
            | Self::BackupUnreadable { source, .. } => Some(source),
            Self::BackupMismatch { .. } => None,
        }
    }

    /// Build a stage failure for one path.
    pub(crate) fn stage_failure(
        stage: PublicationStage,
        path: &Path,
        source: std::io::Error,
    ) -> Self {
        Self::Stage {
            stage,
            path: path.to_path_buf(),
            source,
        }
    }
}

#[cfg(test)]
#[path = "error_tests.rs"]
mod tests;
