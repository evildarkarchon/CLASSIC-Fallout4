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
//! - [`publish_verified_backup`] is the first half of that on its own, for the
//!   caller whose conflict policy must run between the verification and the
//!   replacement.
//! - [`stage`] stops one step short of [`publish`], handing back a
//!   [`StagedPublication`] the caller publishes itself. This exists so that a
//!   caller's own last-moment check can sit in the narrowest possible window:
//!   everything fallible is already done, and only the move remains.
//! - [`install_verified`] adopts a file the caller already staged on disk,
//!   verifies its SHA-256 against an expected digest, and installs it while
//!   preserving one rollback generation. It is the only operation here that
//!   creates a rollback generation, and the only one that starts from bytes
//!   this crate did not write.
//!
//! These are separate named operations over one shared implementation rather
//! than one operation with a policy struct, because a policy matrix would make
//! the interface nearly as complex as the mechanism underneath it.
//!
//! # Concurrency contract
//!
//! The three locking operations take a [`LockPolicy`] and honour it
//! identically:
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
//! [`publish_verified_backup`] and [`stage`] take no [`LockPolicy`] at all. A
//! lock scoped to either alone would release before the move it exists to
//! guard, which is precisely the window a lock closes, so a caller that splits
//! the sequence must hold its own lock across every part.
//!
//! [`LockPolicy::acquire`] is public for one narrow reason: a caller may have
//! a *neighbouring* operation that publishes nothing but moves the same files
//! an install moves, and it must serialize against that install. Taking the
//! same lock from here is what keeps the workspace at one cross-process lock
//! implementation instead of drifting back to two.
//!
//! # What this crate does not own
//!
//! Backup location and conflict or revision policy stay with the callers. This
//! crate never decides whether a [`Durability::Unknown`] outcome matters; it
//! only guarantees that the outcome is reported rather than discarded.
//!
//! Rollback generations are a narrower case. The `.prev` convention is YAML
//! Data Update Channel policy, and it lives here only inside
//! [`install_verified`] — never in [`publish`] or
//! [`publish_with_verified_backup`]. That placement is load-bearing: it is how
//! ADR-0006's prohibition on creating that state for Local Ignore YAML Data
//! holds structurally, because the operation that caller uses cannot produce
//! a rollback generation at all.
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
pub use lock::{LockPolicy, PublicationLock};
pub use publication::{
    Durability, Install, Publication, StagedPublication, VerifiedBackup, VerifiedBackupPublication,
    install_verified, publish, publish_verified_backup, publish_with_verified_backup,
    rollback_generation_path, stage,
};
