//! The pending recovery a frontend receives: one object to prompt from and settle.
//!
//! The scan-run contract owns the mechanics of a paused run — the single-use continuation,
//! whether cancellation was already requested, and the typed facts — in
//! [`PendingRecovery`]. It cannot carry the recovery prompt, because the prompt is Display
//! Content and the scanlog core crate must never depend on this one. So this module bundles the
//! two: [`take_pending_recovery`] takes the contract's pending recovery out of a paused
//! [`RunResult`] and renders its prompt once, and every binding projects that bundle as the
//! single pending-recovery object its frontends see (ADR-0009).
//!
//! # Settling
//!
//! [`PendingRecoveryWithPrompt::settle`] takes an optional
//! [`LocalIgnoreRecoveryDecision`]. No decision abandons the run, which is still not a third
//! decision. When [`PendingRecoveryWithPrompt::cancellation_requested`] is `true` a frontend
//! does not prompt at all: it settles with no decision.

use crate::recovery::{RecoveryPrompt, render_local_ignore_recovery};
use classic_scanlog_core::scan_run::contract::{
    LocalIgnoreRecoveryDecision, Observer, ObserverFailurePolicy, PendingRecovery, ResumeError,
    RunResult, SettledRunResult,
};

/// A paused Crash Log Scan Run's pending recovery together with its rendered prompt.
///
/// The prompt is rendered from the pending recovery's own facts when the bundle is built, so it
/// always agrees with what settling can honour, including whether Reset To Default is available.
#[derive(Debug)]
pub struct PendingRecoveryWithPrompt {
    recovery: PendingRecovery,
    prompt: RecoveryPrompt,
}

impl PendingRecoveryWithPrompt {
    /// Bundles a contract pending recovery with the prompt rendered from its facts.
    #[must_use]
    pub fn new(recovery: PendingRecovery) -> Self {
        let prompt = render_local_ignore_recovery(Some(recovery.installed_yaml_data()));
        Self { recovery, prompt }
    }

    /// Returns the recovery prompt, already rendered as Display Content.
    #[must_use]
    pub const fn prompt(&self) -> &RecoveryPrompt {
        &self.prompt
    }

    /// Returns whether cancellation of the paused run was already requested.
    ///
    /// Read live from the run's own control. When `true`, do not prompt; settle with no decision.
    #[must_use]
    pub fn cancellation_requested(&self) -> bool {
        self.recovery.cancellation_requested()
    }

    /// Returns the contract pending recovery this bundle renders.
    #[must_use]
    pub const fn recovery(&self) -> &PendingRecovery {
        &self.recovery
    }

    /// Settles the paused run once; see [`PendingRecovery::settle`].
    ///
    /// # Errors
    ///
    /// The same typed [`ResumeError`] as [`PendingRecovery::settle`], including
    /// [`ResumeError::ContinuationConsumed`] on replay.
    pub async fn settle(
        &self,
        decision: Option<LocalIgnoreRecoveryDecision>,
        observer: Option<&mut dyn Observer>,
        observer_failure_policy: ObserverFailurePolicy,
    ) -> Result<SettledRunResult, ResumeError> {
        self.recovery
            .settle(decision, observer, observer_failure_policy)
            .await
    }
}

/// Takes the pending recovery a paused run offers and renders its prompt.
///
/// Returns `None` for every run that did not pause, and on a second call. The rest of `result`
/// stays readable, so render the paused run with [`crate::render_run_result`] afterwards as
/// usual.
pub fn take_pending_recovery(result: &mut RunResult) -> Option<PendingRecoveryWithPrompt> {
    result
        .take_pending_recovery()
        .map(PendingRecoveryWithPrompt::new)
}
