//! Python projection tests.
//!
//! Behavioral coverage lives in `python-bindings/tests/`, which exercises the
//! built extension module. What only a Rust-side test can do is compare this
//! adapter's projection against the core it projects — a pytest assertion can
//! only restate the expected string, which is the fourth copy of the vocabulary
//! this work exists to remove.

use super::*;
// The four document enums are imported here rather than in `lib.rs`: the
// binding no longer names those types, because it asks each value for its own
// Vocabulary Token instead of matching on it.
use classic_user_settings_core::{
    CommitEligibility, DocumentClassification, MigrationChangeKind, PreferenceOrigin, Revision,
    SourceLocation,
};

/// Builds a review-only plan carrying one change per migration change kind.
///
/// Real planning only ever emits the subset of kinds a given document needs, so
/// a fixture-driven test can never reach every variant.
fn plan_with_every_migration_change_kind() -> UserSettingsMigrationPlan {
    UserSettingsMigrationPlan::from((
        true,
        (SourceLocation::Legacy, None),
        (
            SourceLocation::Canonical,
            Some(UserSettingsSchemaVersion::new(1, 0)),
        ),
        MigrationChangeKind::VARIANTS
            .iter()
            .copied()
            .map(|kind| (kind, None, None, None, None))
            .collect(),
        b"original".to_vec(),
        b"proposed".to_vec(),
    ))
}

#[test]
fn every_migration_change_kind_projects_the_core_vocabulary_token() {
    // Derived from the core rather than restated: a passing assertion here
    // means the two agree, not that two hand-written lists happen to match.
    let plan = plan_with_every_migration_change_kind();

    let projected: Vec<String> = plan
        .changes()
        .iter()
        .map(|change| migration_change_to_py(change).kind)
        .collect();
    let expected: Vec<String> = MigrationChangeKind::VARIANTS
        .iter()
        .copied()
        .map(|kind| kind.as_str().to_string())
        .collect();

    assert_eq!(projected, expected);
}

#[test]
fn the_python_surface_publishes_the_canonical_snake_case_spelling() {
    // Python's documented convention is that tokens stay snake_case, so unlike
    // the Node surface this one applies no transform at all. Asserting the
    // absence of one keeps a future "helpful" casing change from slipping in.
    fn assert_untransformed<T: Vocabulary>() {
        for variant in T::VARIANTS.iter().copied() {
            let token = variant.as_str();
            assert_eq!(token, token.to_lowercase());
            assert!(!token.contains(' '));
        }
    }

    assert_untransformed::<MigrationChangeKind>();
    assert_untransformed::<PreferenceOrigin>();
    assert_untransformed::<SourceLocation>();
    assert_untransformed::<DocumentClassification>();
    assert_untransformed::<CommitEligibility>();
}

// ── Document vocabulary projection ──────────────────────────────────
//
// These drive the *production* conversions for the two document enums a
// binding-safe constructor can reach exhaustively: `DocumentClassification`,
// through the legacy-import outcome, and `SourceLocation`, through a
// review-only plan. Both derive their expectation from the core.
//
// `PreferenceOrigin` and `CommitEligibility` are only reachable by opening a
// real document, so no exhaustive constructor exists for them. That leaves
// nothing untested, because after this change the binding holds no per-enum
// projection code at all — every one of these four is projected by the same
// `Vocabulary::as_str` call, and `python-bindings/tests/` still pins the token
// each fixture actually yields at the built extension module.
//
// There is no reverse-parse counterpart to test on this surface: Python
// retains the immutable core plan rather than reopening against a
// caller-supplied token.

/// Builds a review-only plan whose endpoints carry `location` on both sides.
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
    let projected: Vec<String> = DocumentClassification::VARIANTS
        .iter()
        .copied()
        .map(|classification| {
            legacy_tui_state_import_outcome_to_py(
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
        .map(|classification| classification.as_str().to_string())
        .collect();

    assert_eq!(projected, expected);
}

#[test]
fn every_source_location_projects_the_core_vocabulary_token() {
    let projected: Vec<String> = SourceLocation::VARIANTS
        .iter()
        .copied()
        .map(|location| {
            migration_plan_to_py(plan_anchored_at(location))
                .source
                .location
        })
        .collect();
    let expected: Vec<String> = SourceLocation::VARIANTS
        .iter()
        .copied()
        .map(|location| location.as_str().to_string())
        .collect();

    assert_eq!(projected, expected);
}
