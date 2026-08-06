//! Migration vocabulary tests.
//!
//! Planning behavior is covered by `tests/migration_planning_behavior.rs`; this
//! sibling module exists for what only the owning crate can assert — that the
//! names it now owns satisfy the Vocabulary naming contract.

use super::*;
use classic_vocabulary::{Vocabulary, assert_vocabulary_conformance, from_token};

#[test]
fn migration_change_kind_satisfies_the_vocabulary_contract() {
    assert_vocabulary_conformance::<MigrationChangeKind>();
}

#[test]
fn migration_change_kind_tokens_are_the_frozen_published_spelling() {
    // The one place in the workspace where these literals are legitimate: this
    // is the definition of the frozen identifiers, not a restatement of them.
    // Every other assertion about these strings — in all three bindings —
    // derives its expectation from here, so a change to any arm below is a
    // breaking change to every binding consumer and must fail loudly right now.
    assert_eq!(
        MigrationChangeKind::LocationTransition.as_str(),
        "location_transition"
    );
    assert_eq!(
        MigrationChangeKind::SchemaVersionTransition.as_str(),
        "schema_version_transition"
    );
    assert_eq!(
        MigrationChangeKind::FieldTransition.as_str(),
        "field_transition"
    );
    assert_eq!(
        MigrationChangeKind::AliasCanonicalization.as_str(),
        "alias_canonicalization"
    );
    assert_eq!(
        MigrationChangeKind::KnownValueCanonicalization.as_str(),
        "known_value_canonicalization"
    );
}

#[test]
fn every_migration_change_kind_variant_is_listed_for_iteration() {
    // Nothing can ask a Rust enum how many variants it has, so this count is
    // the only guard against a variant that compiles — because `as_str` and
    // `label` are exhaustive matches — yet never appears in an exhaustive
    // iteration. A contributor adding a variant lands here and is told to add
    // it to `VARIANTS` too.
    assert_eq!(MigrationChangeKind::VARIANTS.len(), 5);
}

#[test]
fn every_migration_change_kind_token_resolves_back_to_its_variant() {
    for variant in MigrationChangeKind::VARIANTS.iter().copied() {
        assert_eq!(
            from_token::<MigrationChangeKind>(variant.as_str()),
            Some(variant),
            "token `{}` did not resolve back to its own variant",
            variant.as_str()
        );
    }
}

#[test]
fn migration_change_kind_labels_read_as_prose_rather_than_identifiers() {
    // Display Labels are reworded freely, so pinning their exact text here
    // would make a legitimate wording fix look like a regression. What must
    // hold is the property that separates the two forms: a label is prose, so
    // it never equals its own token and never carries token punctuation.
    for variant in MigrationChangeKind::VARIANTS.iter().copied() {
        let label = variant.label();
        assert_ne!(label, variant.as_str());
        assert!(
            !label.contains('_'),
            "Display Label `{label}` looks like a Vocabulary Token"
        );
    }
}
