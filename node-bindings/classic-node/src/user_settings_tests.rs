//! Node User Settings projection tests.
//!
//! Behavioral coverage lives in `__test__/user_settings.spec.ts`, which drives
//! the built addon against real fixture documents. What only a Rust-side test
//! can do is compare this adapter's projection against the core it projects — a
//! TypeScript assertion can only restate the expected string, which is the
//! fourth copy of the vocabulary this work exists to remove.
//!
//! # What each seam covers
//!
//! These tests drive the *production* conversion functions for the two enums a
//! binding-safe constructor can reach exhaustively: `DocumentClassification`,
//! through the legacy-import outcome, and `SourceLocation`, through a
//! review-only migration plan. Both derive their expectation from
//! [`Vocabulary`] rather than restating it.
//!
//! `PreferenceOrigin` and `CommitEligibility` have no such constructor — they
//! are only reachable by opening a real document — so their exhaustive
//! projection check lives in `vocabulary_tests.rs`, which covers the pure
//! `js_token(variant.as_str())` rule every call site in this module now uses.
//! Nothing is left uncovered by that split, because after this change there is
//! no per-enum projection code left for a production path to exercise
//! differently.

use super::*;
use classic_user_settings_core::{DocumentClassification, SourceLocation};

/// Builds a review-only plan whose endpoints carry `location` on both sides.
///
/// Real planning only ever proposes the transitions a given document needs, so
/// a fixture-driven test can never reach every location. Reconstructing a plan
/// from binding-safe components is the same path this surface uses for
/// reversal, which keeps the exhaustive check on the production conversion
/// rather than a test-only one.
fn plan_anchored_at(location: SourceLocation) -> UserSettingsMigrationPlan {
    UserSettingsMigrationPlan::from((
        true,
        (location, None),
        (location, Some(UserSettingsSchemaVersion::new(1, 0))),
        Vec::new(),
        b"original".to_vec(),
        b"proposed".to_vec(),
    ))
}

#[test]
fn every_document_classification_projects_the_core_vocabulary_token() {
    // The expectation is the core token put through the one shared casing
    // rule, not a restated camelCase list. A test that listed the spellings
    // again would pass just as happily against a surface that had drifted.
    let projected: Vec<String> = DocumentClassification::VARIANTS
        .iter()
        .copied()
        .map(|classification| {
            legacy_tui_state_import_outcome_to_js(
                LegacyTuiStateImportOutcome::RequiresSettingsMigration {
                    classification,
                    revision: Revision::Missing,
                },
            )
            .classification
            .expect("a migration-required outcome carries a classification")
        })
        .collect();
    let expected: Vec<String> = DocumentClassification::VARIANTS
        .iter()
        .copied()
        .map(|classification| js_token(classification.as_str()))
        .collect();

    assert_eq!(projected, expected);
}

#[test]
fn every_source_location_projects_the_core_vocabulary_token() {
    let projected: Vec<String> = SourceLocation::VARIANTS
        .iter()
        .copied()
        .map(|location| {
            user_settings_migration_plan_to_js(&plan_anchored_at(location))
                .source
                .location
        })
        .collect();
    let expected: Vec<String> = SourceLocation::VARIANTS
        .iter()
        .copied()
        .map(|location| js_token(location.as_str()))
        .collect();

    assert_eq!(projected, expected);
}

#[test]
fn every_source_location_token_round_trips_through_the_js_plan() {
    // This surface's reversal path takes tokens back from JavaScript and
    // rebuilds a core plan, so emitting and parsing must be the same rule read
    // in two directions. Anything less corrupts a reversal silently.
    for location in SourceLocation::VARIANTS.iter().copied() {
        let js_plan = user_settings_migration_plan_to_js(&plan_anchored_at(location));

        let rebuilt = user_settings_migration_plan_from_js(js_plan)
            .expect("rebuild plan from its own JavaScript projection");

        assert_eq!(rebuilt.source().location(), location);
        assert_eq!(rebuilt.target().location(), location);
    }
}

#[test]
fn source_location_rejects_an_unknown_token() {
    let mut js_plan = user_settings_migration_plan_to_js(&plan_anchored_at(SourceLocation::Legacy));
    js_plan.source.location = "not_a_location".to_string();

    let error = user_settings_migration_plan_from_js(js_plan).unwrap_err();

    assert_eq!(
        error.reason,
        "unsupported User Settings source location: not_a_location"
    );
}

#[test]
fn a_near_miss_source_location_token_is_rejected_rather_than_prefix_matched() {
    // Every `SourceLocation` token is a single word, so its camelCase spelling
    // and its canonical spelling coincide and the usual "reject the snake_case
    // form" check cannot bite here. What can still be pinned is that the parse
    // is exact rather than lenient — the reverse scan compares whole tokens.
    let mut js_plan =
        user_settings_migration_plan_to_js(&plan_anchored_at(SourceLocation::Canonical));
    js_plan.source.location = "canonic".to_string();

    assert!(user_settings_migration_plan_from_js(js_plan).is_err());
}
