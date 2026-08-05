//! Python projection tests.
//!
//! Behavioral coverage lives in `python-bindings/tests/`, which exercises the
//! built extension module. What only a Rust-side test can do is compare this
//! adapter's projection against the core it projects — a pytest assertion can
//! only restate the expected string, which is the fourth copy of the vocabulary
//! this work exists to remove.

use super::*;
use classic_user_settings_core::MigrationChangeKind;

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
    for kind in MigrationChangeKind::VARIANTS.iter().copied() {
        let token = kind.as_str();
        assert_eq!(token, token.to_lowercase());
        assert!(!token.contains(' '));
    }
}
