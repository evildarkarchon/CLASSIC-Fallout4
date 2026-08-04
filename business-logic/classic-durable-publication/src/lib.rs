//! Workspace-internal **Durable Publication** for CLASSIC.
//!
//! This unpublished crate owns one thing: making complete bytes visible at a
//! canonical path such that a crash cannot leave partial content behind. Every
//! file replacement CLASSIC performs on data a user cannot afford to lose is
//! meant to go through here, so that a durability defect has exactly one place
//! to be found and fixed.
//!
//! # The sequence
//!
//! 1. **Create** a staging file in the target's *own* directory, so the final
//!    move is same-volume and therefore atomic.
//! 2. **Write** the complete bytes into it.
//! 3. **Flush** them out of user space.
//! 4. **Sync** the staging file to the platform's durability barrier.
//! 5. **Publish** it onto the final path.
//!
//! Nothing is visible at the target until step 5, and step 5 only ever moves a
//! file whose bytes are already complete and synchronized.
//!
//! # Platform behavior
//!
//! On Unix, step 5 is `rename` followed by an explicit synchronization of the
//! parent directory. Those are separable events, which is the only reason
//! durability uncertainty can be modelled at all: the bytes are visible as
//! soon as the rename returns, but the directory entry is not guaranteed to
//! survive a crash until the synchronization succeeds.
//!
//! On other platforms, step 5 is a write-through replacement performed after
//! the staged file's temporary attribute has been cleared. That clearing is
//! not incidental — see the comment on the publish step in `publication.rs`.
//!
//! # Operations
//!
//! - [`publish`] replaces whatever is at the target.
//! - [`publish_with_verified_backup`] publishes a backup, rereads it from
//!   disk, byte-compares it against the caller's retained original, and only
//!   then replaces the target — aborting entirely if the comparison fails.
//!
//! These are separate named operations over one shared implementation rather
//! than one operation with a policy struct, because a policy matrix would make
//! the interface nearly as complex as the mechanism underneath it.
//!
//! # Concurrency contract
//!
//! Both operations take a [`LockPolicy`] and honour it identically:
//!
//! - [`LockPolicy::sibling`] acquires an exclusive cross-process lock on a
//!   sibling lock file *before* any staging, holds it for the whole sequence,
//!   and releases it when the call returns. For
//!   [`publish_with_verified_backup`], the single lock spans the backup
//!   publish, the reread, the comparison, and the replacement, so a backup
//!   cannot be verified against one target state and applied to another.
//! - [`LockPolicy::none`] takes no lock at all. Concurrent writers may race
//!   for the final publish; the loser's bytes are simply discarded and
//!   whichever bytes win are complete.
//!
//! The lock is always taken on the *target* path, never on the backup path.
//! Lock filenames stay caller policy so that adopting this crate changes
//! nothing on disk. Lock files are never removed — deleting one races with any
//! process that has opened but not yet acquired it.
//!
//! # What this crate does not own
//!
//! Backup location, conflict or revision policy, and rollback generations all
//! stay with the callers. This crate never decides whether a
//! [`Durability::Unknown`] outcome matters; it only guarantees that the
//! outcome is reported rather than discarded.
//!
//! # Error contract
//!
//! Failures are neutral: a [`PublicationStage`], a path, and a source error,
//! with no knowledge of any caller's error type. Each caller maps them onto
//! its own stable, published error codes.

mod error;
mod identity;
mod lock;
mod publication;

pub use error::{PublicationError, PublicationStage};
pub use identity::ContentIdentity;
pub use lock::LockPolicy;
pub use publication::{
    Durability, Publication, VerifiedBackup, VerifiedBackupPublication, publish,
    publish_with_verified_backup,
};
