//! The core-owned content of a Local Ignore recovery prompt.
//!
//! A malformed Local Ignore pauses a Crash Log Scan Run and asks the user to choose. This
//! module decides what that question says: the display lines explaining the situation, and
//! one description per recovery decision stating what choosing it will actually do.
//!
//! # Availability travels with the decision
//!
//! [`RecoveryDecisionDescription::available`] sits on the decision it describes rather than
//! arriving as a separate flag beside the prompt. That is deliberate, and it is what closes a
//! confirmed gap by construction: a frontend cannot offer an unavailable decision without
//! ignoring data placed directly in its hands. Before this, `local_ignore_reset_available`
//! was a fact each frontend had to remember to consult, and two of them did not — they
//! offered Reset To Default unconditionally, and choosing it spent the one-shot Crash Log
//! Scan Run Continuation on a guaranteed failure, leaving the user with no scan, no repair,
//! and no second attempt. A binding consumer building its own frontend gets the same
//! protection.
//!
//! # What this does not say
//!
//! The prompt states the question, not the facts behind it. It does not name the malformed
//! file's identity, because [`render_run_result`](crate::render_run_result) already renders
//! that in the Installed YAML Data block — and every surface that receives a prompt receives
//! the rendered run on the same envelope, so the identity is never missing, only stated once.
//! Rendering it here as well put the same line on screen twice in all three interactive
//! frontends, which is the drift this crate exists to remove, merely relocated into core.
//!
//! # What is Display Layout here
//!
//! The affordance beside a description is not core's. A native CLI's bracketed letters, a
//! TUI's key hints, and a Qt GUI's buttons are each that frontend's own choice, as is the
//! order the decisions are presented in and whether the prompt is a dialog, an overlay, or a
//! line of stdin. The descriptions themselves are locked Display Content and read identically
//! everywhere.
//!
//! # Abandonment is not a decision
//!
//! Every frontend also offers some way to back out, and none of them appears here.
//! [`LocalIgnoreRecoveryDecision`] has exactly two variants by design; backing out is spelled
//! as the *absence* of a decision and reaches the contract through
//! `CrashLogScanRunContinuation::abandon`. A third variant would reshape a type crossing five
//! binding surfaces and reopen the run contract's cancellation semantics, so the cancel
//! affordance and its wording stay each frontend's own.

#[cfg(test)]
#[path = "recovery_tests.rs"]
mod tests;

use crate::display::{DisplayLine, DisplaySegment, DisplaySeverity};
use classic_scanlog_core::scan_run::contract::{
    InstalledYamlDataRunData, LocalIgnoreRecoveryDecision,
};
use classic_vocabulary::Vocabulary;

use DisplaySegment::Text;
use DisplaySeverity::{Notice, Warning};

/// The core-owned content of a Local Ignore recovery prompt.
///
/// `decisions` lists every decision this continuation contract accepts, each already marked
/// available or not for this particular run. An adapter chooses the affordance; it may not
/// offer a decision core marked unavailable.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RecoveryPrompt {
    /// Why the run paused and what the user is deciding about, in reading order.
    pub lines: Vec<DisplayLine>,
    /// One description per recovery decision, in the contract's declared variant order.
    pub decisions: Vec<RecoveryDecisionDescription>,
}

/// One recovery decision, named and explained, with its availability attached.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RecoveryDecisionDescription {
    /// The decision this describes, ready to hand back to the continuation contract.
    pub decision: LocalIgnoreRecoveryDecision,
    /// The decision's Display Label, obtained from `Vocabulary::label()`.
    pub label: &'static str,
    /// What choosing it will actually do, as segments an adapter concatenates in order.
    pub description: Vec<DisplaySegment>,
    /// Whether this run can honor the decision.
    ///
    /// An adapter must not offer a decision for which this is `false`. Core still fails
    /// safely if one does — nothing on disk is touched — but the attempt spends the one-shot
    /// continuation, so the user is left with no scan and no second attempt.
    pub available: bool,
}

/// Renders the prompt shown when a malformed Local Ignore pauses a Crash Log Scan Run.
///
/// # Why the argument is optional
///
/// A recovery-required run always carries Installed YAML Data in practice, but a caller
/// holding `RunResult::installed_yaml_data` holds an `Option` and must do *something* when it
/// is absent. All three native frontends independently decided the same thing — a run that
/// reported nothing has not reported a denial, so withdrawing an option on silence would
/// regress the behaviour that shipped before the availability fact existed — and each wrote
/// that rule for itself. Taking the `Option` here is what makes it one rule rather than
/// three, which is the same move the rest of this crate makes for prose.
///
/// # Ordering
///
/// This borrows, like every other entry point in this crate, so take the continuation out of
/// the [`RunResult`](classic_scanlog_core::scan_run::contract::RunResult) before rendering.
///
/// # Scope
///
/// `data.local_ignore_reset_available` is meaningful only while the run's Local Ignore state
/// is `LocalIgnoreRunState::RecoveryRequired`, and is `false` in every other state. Calling
/// this for a run that is not paused on a recovery decision therefore reports Reset To
/// Default as unavailable, which fails closed rather than open.
#[must_use]
pub fn render_local_ignore_recovery(data: Option<&InstalledYamlDataRunData>) -> RecoveryPrompt {
    // Absent Installed YAML Data resolves to available here, once, rather than in each of the
    // three frontends that used to resolve it for themselves.
    render_recovery_prompt(data.is_none_or(|data| data.local_ignore_reset_available))
}

/// Renders a recovery prompt from the one fact it reads.
///
/// `pub(crate)` and fact-taking for the reason [`crate::render::render_yaml_data_file`] is:
/// [`InstalledYamlDataRunData`] embeds accessor-only types with no public constructor, so no
/// test can assemble one to feed through [`render_local_ignore_recovery`]. Pinning this
/// wording means calling the renderer with the same fact that function reads out.
pub(crate) fn render_recovery_prompt(reset_available: bool) -> RecoveryPrompt {
    let mut lines = vec![DisplayLine::new(
        Warning,
        vec![Text(
            "Your Local Ignore file is malformed, so this Crash Log Scan is paused until you choose how to continue.",
        )],
    )];
    if !reset_available {
        // Stated as a line rather than folded into the decision's own description, because
        // the description says what the decision *does* and stays true whether or not this
        // run can honor it. A frontend that withholds the decision, as it must, still shows
        // this line — which is what keeps a missing option from reading as a missing feature.
        //
        // This exact sentence was already written, identically, in the TUI overlay, the
        // native CLI menu, and the Qt dialog, each with a comment saying core would own it
        // once this renderer existed. It does now.
        lines.push(DisplayLine::new(
            Notice,
            vec![Text(
                "Reset To Default is unavailable: the selected Main YAML Data retains no usable default Local Ignore to publish.",
            )],
        ));
    }

    RecoveryPrompt {
        lines,
        // Built by walking the contract's own variant list rather than by naming the two
        // decisions here, so the prompt cannot offer something the contract will not accept
        // and cannot omit something it will. The two `match`es below are exhaustive, so a
        // third variant stops this crate compiling until someone decides what it says and
        // when it is available — which is the point at which that addition becomes a
        // deliberate decision rather than an incidental one.
        decisions: LocalIgnoreRecoveryDecision::VARIANTS
            .iter()
            .copied()
            .map(|decision| RecoveryDecisionDescription {
                decision,
                label: decision.label(),
                description: vec![Text(decision_description(decision))],
                available: decision_available(decision, reset_available),
            })
            .collect(),
    }
}

/// Returns what choosing one decision will actually do.
///
/// Follows the shared glossary rather than any one frontend, for the reason
/// `LocalIgnoreRecoveryDecision::label` does: all three interactive frontends already said
/// roughly this and none of them agreed. Each description stands on its own, naming the file
/// rather than relying on a label sitting beside it, because a GUI puts a description under a
/// button where the label is the button's own text.
const fn decision_description(decision: LocalIgnoreRecoveryDecision) -> &'static str {
    match decision {
        LocalIgnoreRecoveryDecision::ProceedWithoutIgnore => {
            "Scan now with an empty ignore list. Your malformed Local Ignore file is left exactly as it is, and this choice applies to this scan only."
        }
        LocalIgnoreRecoveryDecision::ResetToDefault => {
            "Back up your malformed Local Ignore file byte-exactly, replace it with the selected Main defaults, then scan."
        }
    }
}

/// Returns whether this run can honor one decision.
const fn decision_available(decision: LocalIgnoreRecoveryDecision, reset_available: bool) -> bool {
    match decision {
        // Proceeding needs nothing from the installation — the ignore list is simply empty
        // for this operation — so no run can make it unavailable. That the two answers differ
        // is exactly why availability is a field on each decision rather than one flag beside
        // the prompt.
        LocalIgnoreRecoveryDecision::ProceedWithoutIgnore => true,
        LocalIgnoreRecoveryDecision::ResetToDefault => reset_available,
    }
}
