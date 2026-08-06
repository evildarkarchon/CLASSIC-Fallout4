//! Deliberately unpublished fault injection, reachable only under `cfg(test)`.
//!
//! Two of `publication`'s outcomes have no portable filesystem condition that
//! provokes them on demand:
//!
//! - A directory synchronization failure. `fsync` on a directory handle does
//!   not fail to order, yet the uncertain outcome is the one thing about that
//!   module every caller must handle.
//! - A published backup whose bytes on disk differ from what was written. That
//!   is precisely a filesystem or device that lied about a completed write —
//!   the condition the reread exists to catch, and one no cooperating
//!   filesystem will reproduce.
//!
//! These hooks are not exposed on the crate's interface. A caller that wants
//! to test its own stage mapping should use a fake at its own seam rather than
//! reach for anything here.
//!
//! This lives in a sibling file rather than inline in `publication.rs` because
//! the repository's Rust test layout keeps test-only bodies, fixtures, and
//! helpers out of the production module. It mirrors
//! `classic-config-core`'s `installed_yaml_data_reset_fault.rs`.

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
