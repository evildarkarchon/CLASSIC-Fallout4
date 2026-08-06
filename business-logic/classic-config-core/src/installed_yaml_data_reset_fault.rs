//! Test-only hooks for the two Local Ignore reset behaviors real files cannot provoke.
//!
//! Reset no longer owns a staging-and-publish sequence, so the private publisher trait that used
//! to exist purely as a fault seam is gone. What is left here is deliberately small, and the bar
//! for adding to it is high: a hook belongs here only when the behavior it exercises is real and
//! there is no portable way to provoke it.
//!
//! - [`ResetFaults::after_verified_backup`] runs arbitrary caller code at a real point in the
//!   sequence. Everything around it is real — a real backup was published, a real conflict recheck
//!   and a real replacement follow. It exists because the two things it proves, that an edit
//!   landing during backup publication is preserved and that the critical section does not yield
//!   once entered, are facts about ordering that can only be observed from inside.
//! - [`ResetFaults::replacement_durability_unknown`] forces the post-publish durability outcome.
//!   The replacement is genuinely published first, so the test still observes real bytes at the
//!   canonical path; only the barrier result is substituted. A directory synchronization does not
//!   fail on demand, and `classic-durable-publication`'s own injection hooks are private to that
//!   crate, so this is the only seam from which config-core can prove that
//!   `Durability::Unknown` becomes `ReplacementDurabilityUnknown` with a complete receipt.
//!
//! What deliberately does **not** live here is stage-failure and backup-mismatch injection. Those
//! fakes returned before any filesystem work happened, which made every assertion around them
//! either vacuous or an echo of a literal written a few lines away in the production path. The
//! conditions themselves are provoked against real files in `classic-durable-publication`'s suite,
//! and the only part config-core still owns — projecting a neutral failure onto a published error
//! code — is tested directly against [`super::project_publication_error`] instead.
//!
//! Hooks are thread-local and installed for the lifetime of a [`ResetFaultGuard`]. A test that
//! runs reset on another thread must install them *on that thread*.

use std::cell::RefCell;

/// Hooks applied to one reset call.
#[derive(Default)]
pub(super) struct ResetFaults {
    /// Report the replacement's namespace durability as unconfirmed after it is visible.
    pub(super) replacement_durability_unknown: bool,
    /// Run arbitrary code once the verified backup exists, before the replacement is staged.
    pub(super) after_verified_backup: Option<Box<dyn Fn()>>,
}

thread_local! {
    static FAULTS: RefCell<Option<ResetFaults>> = const { RefCell::new(None) };
}

/// Install `faults` on the current thread until the returned guard drops.
pub(super) fn install(faults: ResetFaults) -> ResetFaultGuard {
    FAULTS.with(|slot| *slot.borrow_mut() = Some(faults));
    ResetFaultGuard
}

/// Return whether replacement durability should be reported as unconfirmed.
pub(super) fn replacement_durability_unknown() -> bool {
    FAULTS.with(|slot| {
        slot.borrow()
            .as_ref()
            .is_some_and(|faults| faults.replacement_durability_unknown)
    })
}

/// Run the interleaving hook installed for the point just after the verified backup.
///
/// The hook is taken out of the `RefCell` and invoked outside the borrow, then put back, so that
/// it may itself touch fault state without panicking on a re-entrant borrow.
pub(super) fn after_verified_backup() {
    let hook = FAULTS.with(|slot| {
        slot.borrow_mut()
            .as_mut()
            .and_then(|faults| faults.after_verified_backup.take())
    });
    if let Some(hook) = hook {
        hook();
        FAULTS.with(|slot| {
            if let Some(faults) = slot.borrow_mut().as_mut() {
                faults.after_verified_backup = Some(hook);
            }
        });
    }
}

/// Clears every hook installed on this thread when dropped.
pub(super) struct ResetFaultGuard;

impl Drop for ResetFaultGuard {
    fn drop(&mut self) {
        FAULTS.with(|slot| *slot.borrow_mut() = None);
    }
}
