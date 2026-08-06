//! The workspace's one cross-process publication lock.
//!
//! # Library choice
//!
//! This module uses the standard library's [`std::fs::File::lock`] rather than
//! `fs4`'s `lock_exclusive`, which two of the three existing call sites use
//! today. Both wrap the same primitives — `flock` on Unix, `LockFileEx` on
//! Windows — so the choice is not about behavior. It is that `File::lock` is
//! stable well below this workspace's `rust-version`, so the one locking
//! implementation that replaces two needs nothing beyond the standard library
//! to do it.
//!
//! The lock is advisory on Unix and mandatory on Windows, exactly as it is
//! today in every caller. It is released when the handle drops, including on
//! process termination.
//!
//! # Lock file placement
//!
//! Lock *filenames* remain caller policy, supplied through [`LockPolicy`], so
//! migrating a caller onto this crate changes nothing on disk. The three
//! shapes below exist because the existing callers genuinely differ: two name
//! a sibling of the target, and one places a fixed name two directories above
//! it.
//!
//! Lock files are deliberately never removed: deleting one races with any
//! process that has already opened the path but not yet acquired it.

use std::fs::{File, OpenOptions};
use std::path::{Path, PathBuf};

use crate::error::PublicationError;

/// Where a durable publication's cross-process lock lives, if it takes one.
#[derive(Debug, Clone, PartialEq, Eq)]
enum LockLocation {
    /// No lock is taken.
    None,
    /// `<target><suffix>`.
    Sibling(String),
    /// A complete path the caller computed itself.
    Explicit(PathBuf),
}

/// Whether — and where — a durable publication takes a cross-process lock.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LockPolicy {
    location: LockLocation,
}

impl LockPolicy {
    /// Take no cross-process lock.
    ///
    /// Appropriate for callers that serialize by some other means, such as an
    /// exact-byte conflict check immediately adjacent to the publish step.
    /// This is also the only policy that places no new file on disk.
    #[must_use]
    pub const fn none() -> Self {
        Self {
            location: LockLocation::None,
        }
    }

    /// Lock the sibling file named by appending `suffix` to the target path.
    ///
    /// The suffix is appended to the whole target path, not to its file stem,
    /// so `CLASSIC Settings.yaml` with `.commit.lock` yields
    /// `CLASSIC Settings.yaml.commit.lock`.
    #[must_use]
    pub fn sibling(suffix: impl Into<String>) -> Self {
        Self {
            location: LockLocation::Sibling(suffix.into()),
        }
    }

    /// Lock exactly `path`, which the caller derives however it likes.
    ///
    /// [`Self::sibling`] covers callers whose lock sits beside the target.
    /// This covers the rest — notably a caller whose lock is a fixed name
    /// several directories above the target — so that adopting this crate
    /// never has to move an existing lock file.
    #[must_use]
    pub fn at(path: impl Into<PathBuf>) -> Self {
        Self {
            location: LockLocation::Explicit(path.into()),
        }
    }

    /// Return the lock file this policy would use for `target`, if any.
    #[must_use]
    pub fn lock_path(&self, target: &Path) -> Option<PathBuf> {
        match &self.location {
            LockLocation::None => None,
            LockLocation::Sibling(suffix) => {
                let mut name = target.as_os_str().to_os_string();
                name.push(suffix);
                Some(PathBuf::from(name))
            }
            LockLocation::Explicit(path) => Some(path.clone()),
        }
    }

    /// Acquire the lock this policy describes for `target`.
    ///
    /// Returns `Ok(None)` for [`LockPolicy::none`]. The returned guard must
    /// stay in scope for the whole sequence it protects.
    ///
    /// The publication operations call this for themselves, so a caller only
    /// reaches for it directly to put a *neighbouring* operation under the
    /// same lock — `classic-file-io-core`'s rollback and self-heal are that
    /// case: they perform no publication of their own, but they move the same
    /// files an install moves and must serialize against it. Using this rather
    /// than a second hand-rolled lock is what makes "one cross-process lock
    /// implementation" true rather than aspirational.
    ///
    /// # Errors
    ///
    /// Returns [`PublicationError::LockOpen`] when the lock file cannot be
    /// opened or created, and [`PublicationError::LockAcquire`] when it is
    /// opened but cannot be locked.
    pub fn acquire(&self, target: &Path) -> Result<Option<PublicationLock>, PublicationError> {
        let Some(lock_path) = self.lock_path(target) else {
            return Ok(None);
        };
        // `truncate(false)` so a concurrent acquirer cannot truncate a lock
        // file the current holder has open; no bytes are ever written to it.
        let file = OpenOptions::new()
            .create(true)
            .read(true)
            .write(true)
            .truncate(false)
            .open(&lock_path)
            .map_err(|source| PublicationError::LockOpen {
                path: lock_path.clone(),
                source,
            })?;
        file.lock()
            .map_err(|source| PublicationError::LockAcquire {
                path: lock_path,
                source,
            })?;
        Ok(Some(PublicationLock { _file: file }))
    }
}

/// Guard holding an exclusive cross-process publication lock.
///
/// Dropping the guard closes the handle, which releases the lock — including
/// on panic and on process termination. It carries no methods because holding
/// it is the entire contract.
#[must_use = "the lock is released as soon as this guard is dropped"]
#[derive(Debug)]
pub struct PublicationLock {
    _file: File,
}

#[rustfmt::skip]
#[cfg(test)] #[path = "lock_tests.rs"] mod tests;
