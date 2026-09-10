//! Unit tests for the Crash Log Scan Run module's own types.
//!
//! The run *behaviour* is exercised from `scan_run/contract_tests.rs`, which
//! drives whole runs through the public contract. What belongs here is what only
//! this module can assert about the types it declares - starting with the
//! Vocabulary naming contract for `CrashLogScanRunStatus`, whose tokens are the
//! exact bytes three binding surfaces already publish.

use super::*;
use classic_vocabulary::{Vocabulary, assert_vocabulary_conformance};

#[test]
fn crash_log_scan_run_status_satisfies_the_vocabulary_contract() {
    assert_vocabulary_conformance::<CrashLogScanRunStatus>();
}

#[test]
fn every_crash_log_scan_run_status_variant_is_listed_for_iteration() {
    // Nothing at runtime can observe whether `VARIANTS` is complete - no Rust
    // construct reports how many variants an enum has - so adding a status must
    // land a contributor on a line that says so. This count is also the arity
    // every binding's exhaustive projection test iterates, and the arity of the
    // three parallel status enums the bridge, the Qt GUI, and the Python surface
    // still maintain by hand.
    assert_eq!(CrashLogScanRunStatus::VARIANTS.len(), 6);
}

#[test]
fn crash_log_scan_run_status_tokens_are_the_frozen_published_spelling() {
    // One of the few places in the workspace where these literals are legitimate:
    // this is the definition of the frozen identifiers, not a restatement of
    // them. They are byte-identical to what the inherent `as_str` this trait
    // method replaced already published, so a change to any arm below is a
    // breaking change to every binding consumer and must fail loudly right now.
    assert_eq!(CrashLogScanRunStatus::Completed.as_str(), "completed");
    assert_eq!(
        CrashLogScanRunStatus::NoCrashLogsFound.as_str(),
        "no_crash_logs_found"
    );
    assert_eq!(CrashLogScanRunStatus::SetupFailed.as_str(), "setup_failed");
    assert_eq!(
        CrashLogScanRunStatus::LocalIgnoreRecoveryRequired.as_str(),
        "local_ignore_recovery_required"
    );
    assert_eq!(
        CrashLogScanRunStatus::CancelledBeforeDiscovery.as_str(),
        "cancelled_before_discovery"
    );
    assert_eq!(CrashLogScanRunStatus::Cancelled.as_str(), "cancelled");
}

#[test]
fn every_crash_log_scan_run_status_label_stays_distinct_from_its_token() {
    // The per-variant shape of `every_infrastructure_stage_renders_its_display
    // _label` in the TUI, exhaustive over `VARIANTS` rather than over a literal
    // table, so a status added later is covered from the day it lands.
    //
    // The negative half carries the weight, and `Completed` is why it needs a
    // per-variant shape rather than a blanket one. Its two forms are the same
    // word, legitimately - `completed` is already the right prose - so a test
    // asserting every label differs from every token would be wrong here, and a
    // test asserting none does would be vacuous. Pinning which variants are
    // which is what makes a later collapse of the two forms fail.
    for status in CrashLogScanRunStatus::VARIANTS.iter().copied() {
        let token = Vocabulary::as_str(status);
        let label = status.label();
        match status {
            CrashLogScanRunStatus::Completed => assert_eq!(
                label, token,
                "`completed` is already the right prose for this status"
            ),
            other => assert_ne!(
                label, token,
                "the Display Label for {other:?} is still its Vocabulary Token"
            ),
        }
        assert!(
            !label.contains('_'),
            "Display Label `{label}` looks like a Vocabulary Token"
        );
    }
}

#[test]
fn the_run_status_labels_are_the_glossary_wording() {
    // The wording decision this module is the arbiter of, pinned exactly because
    // it is a settled decision rather than free prose. Every label below is the
    // prose `CONTEXT.md` already uses to define this concept, so this adoption
    // records a decision the glossary had made rather than making a new one.
    //
    // Two of them could not have been derived from their tokens. `no Crash Logs
    // found` capitalizes a glossary domain term, and `cancelled after discovery`
    // says something its token `cancelled` does not - without the qualifier it is
    // indistinguishable from `cancelled before discovery`, and telling those two
    // apart is the whole reason both variants exist.
    assert_eq!(CrashLogScanRunStatus::Completed.label(), "completed");
    assert_eq!(
        CrashLogScanRunStatus::NoCrashLogsFound.label(),
        "no Crash Logs found"
    );
    assert_eq!(CrashLogScanRunStatus::SetupFailed.label(), "setup failed");
    assert_eq!(
        CrashLogScanRunStatus::LocalIgnoreRecoveryRequired.label(),
        "Local Ignore recovery required"
    );
    assert_eq!(
        CrashLogScanRunStatus::CancelledBeforeDiscovery.label(),
        "cancelled before discovery"
    );
    assert_eq!(
        CrashLogScanRunStatus::Cancelled.label(),
        "cancelled after discovery"
    );
}

#[test]
fn the_two_cancellation_labels_stay_tellable_apart() {
    // The one relationship between two labels that matters to a person reading
    // them. Both statuses mean a cancelled run, and a frontend shows one line, so
    // a label that did not distinguish before-discovery from after-discovery
    // would leave the user unable to tell whether anything was scanned. Asserted
    // rather than reviewed because the shorter of the two is one word away from
    // collapsing back onto its token.
    assert_ne!(
        CrashLogScanRunStatus::Cancelled.label(),
        CrashLogScanRunStatus::CancelledBeforeDiscovery.label()
    );
}
