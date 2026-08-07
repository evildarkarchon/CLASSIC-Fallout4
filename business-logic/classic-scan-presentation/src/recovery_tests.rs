use super::*;
use classic_scanlog_core::scan_run::contract::LocalIgnoreRecoveryDecision;
use classic_vocabulary::Vocabulary;

use DisplaySegment::Text;
use DisplaySeverity::{Notice, Warning};

/// Verifies the prompt states why the run paused, and states only that.
///
/// One line, not two. The malformed file's identity is deliberately absent: the Installed
/// YAML Data block in `render_run_result` already carries it, and every surface receiving a
/// prompt receives the rendered run beside it — so a second copy here put the same line on
/// screen twice in all three interactive frontends.
#[test]
fn recovery_prompt_pins_its_situation_lines() {
    let prompt = render_recovery_prompt(true);

    assert_eq!(
        prompt.lines,
        vec![DisplayLine {
            severity: Warning,
            segments: vec![Text(
                "Your Local Ignore file is malformed, so this Crash Log Scan is paused until you choose how to continue."
            )],
        }]
    );
}

/// Verifies both decisions are described, in the contract's own variant order.
///
/// The descriptions are the locked Display Content this ticket exists to produce: pinned
/// once here, and identical in every frontend and on every binding surface.
#[test]
fn recovery_prompt_pins_both_decision_descriptions() {
    let prompt = render_recovery_prompt(true);

    assert_eq!(
        prompt.decisions,
        vec![
            RecoveryDecisionDescription {
                decision: LocalIgnoreRecoveryDecision::ProceedWithoutIgnore,
                label: "Proceed Without Ignore",
                description: vec![Text(
                    "Scan now with an empty ignore list. Your malformed Local Ignore file is left exactly as it is, and this choice applies to this scan only."
                )],
                available: true,
            },
            RecoveryDecisionDescription {
                decision: LocalIgnoreRecoveryDecision::ResetToDefault,
                label: "Reset To Default",
                description: vec![Text(
                    "Back up your malformed Local Ignore file byte-exactly, replace it with the selected Main defaults, then scan."
                )],
                available: true,
            },
        ]
    );
}

/// Verifies an unavailable reset stays listed, marked unavailable, and says why.
///
/// Listed rather than dropped on purpose. A frontend must be able to explain the absence it
/// is about to create, and it can only do that if core tells it what it is withholding.
#[test]
fn recovery_prompt_marks_an_unavailable_reset_and_explains_it() {
    let prompt = render_recovery_prompt(false);

    assert_eq!(
        prompt.lines.last(),
        Some(&DisplayLine {
            severity: Notice,
            segments: vec![Text(
                "Reset To Default is unavailable: the selected Main YAML Data retains no usable default Local Ignore to publish."
            )],
        })
    );
    let unavailable: Vec<LocalIgnoreRecoveryDecision> = prompt
        .decisions
        .iter()
        .filter(|description| !description.available)
        .map(|description| description.decision)
        .collect();
    assert_eq!(
        unavailable,
        vec![LocalIgnoreRecoveryDecision::ResetToDefault]
    );
}

/// Verifies proceeding is never withdrawn, whatever the run reported about reset.
///
/// This is the asymmetry that makes availability a per-decision field rather than one flag
/// beside the prompt: Proceed Without Ignore needs nothing from the installation, so nothing
/// can make it unavailable.
#[test]
fn recovery_prompt_never_withdraws_proceeding() {
    for reset_available in [true, false] {
        let prompt = render_recovery_prompt(reset_available);
        let proceed = prompt
            .decisions
            .iter()
            .find(|description| {
                description.decision == LocalIgnoreRecoveryDecision::ProceedWithoutIgnore
            })
            .expect("Proceed Without Ignore is always described");
        assert!(proceed.available);
    }
}

/// Verifies the prompt describes exactly the decisions the continuation contract accepts.
///
/// Backing out is deliberately not among them: it is spelled as the *absence* of a decision
/// and reaches the contract through `abandon`, so a frontend's cancel affordance is its own.
#[test]
fn recovery_prompt_describes_every_contract_decision_and_no_others() {
    let prompt = render_recovery_prompt(true);

    let described: Vec<LocalIgnoreRecoveryDecision> = prompt
        .decisions
        .iter()
        .map(|description| description.decision)
        .collect();
    assert_eq!(described, LocalIgnoreRecoveryDecision::VARIANTS.to_vec());
    assert_eq!(LocalIgnoreRecoveryDecision::VARIANTS.len(), 2);
}

/// Verifies a run that reported no Installed YAML Data keeps every decision on offer.
///
/// A run that reported nothing has not reported a denial. Withdrawing an option on silence
/// would regress the behaviour that shipped before the availability fact existed, and this
/// is the one place that rule is now written — the three frontends each used to write it.
///
/// Goes through the public entry point rather than [`render_recovery_prompt`], because the
/// `Option` this pins is resolved there and nowhere else.
#[test]
fn recovery_prompt_treats_absent_installed_yaml_data_as_available() {
    let prompt = render_local_ignore_recovery(None);

    assert!(
        prompt
            .decisions
            .iter()
            .all(|description| description.available)
    );
    assert_eq!(prompt.lines.len(), 1);
}
