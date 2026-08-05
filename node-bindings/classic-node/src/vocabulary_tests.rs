//! Node casing-transform tests.
//!
//! The transform is the only place in this change where a binding's published
//! string is not byte-identical to the core's, so it is the only place a
//! divergence could be reintroduced. These tests are exhaustive over every
//! token it is applied to rather than illustrative.

use super::*;
use classic_user_settings_core::MigrationChangeKind;

/// Every Vocabulary Token this surface projects, paired with the exact
/// camelCase spelling `classic-node` published before the core owned the
/// vocabulary.
///
/// The right-hand column is frozen: a JavaScript consumer parses these. The
/// table is checked for *completeness* against `VARIANTS` below, so it cannot
/// quietly stop covering the enum it claims to cover.
const PUBLISHED_MIGRATION_CHANGE_KIND_TOKENS: &[(MigrationChangeKind, &str)] = &[
    (
        MigrationChangeKind::LocationTransition,
        "locationTransition",
    ),
    (
        MigrationChangeKind::SchemaVersionTransition,
        "schemaVersionTransition",
    ),
    (MigrationChangeKind::FieldTransition, "fieldTransition"),
    (
        MigrationChangeKind::AliasCanonicalization,
        "aliasCanonicalization",
    ),
    (
        MigrationChangeKind::KnownValueCanonicalization,
        "knownValueCanonicalization",
    ),
];

#[test]
fn every_projected_token_keeps_its_published_camel_case_spelling() {
    for (variant, published) in PUBLISHED_MIGRATION_CHANGE_KIND_TOKENS.iter().copied() {
        assert_eq!(
            js_token(variant.as_str()),
            published,
            "core token `{}` no longer camelizes to its published spelling",
            variant.as_str()
        );
    }
}

#[test]
fn the_published_token_table_covers_every_variant() {
    // Without this, a variant added to the core would be projected by an
    // untested path: the transform would still run, and nothing would say
    // whether its output was the spelling anyone intended.
    assert_eq!(
        PUBLISHED_MIGRATION_CHANGE_KIND_TOKENS.len(),
        MigrationChangeKind::VARIANTS.len()
    );
    for variant in MigrationChangeKind::VARIANTS.iter().copied() {
        assert!(
            PUBLISHED_MIGRATION_CHANGE_KIND_TOKENS
                .iter()
                .any(|(covered, _)| *covered == variant),
            "no published camelCase spelling recorded for core token `{}`",
            variant.as_str()
        );
    }
}

#[test]
fn every_projected_token_round_trips_back_to_its_variant() {
    for variant in MigrationChangeKind::VARIANTS.iter().copied() {
        let projected = js_token(variant.as_str());
        assert_eq!(
            from_js_token::<MigrationChangeKind>(&projected),
            Some(variant),
            "projected token `{projected}` did not resolve back to its variant"
        );
    }
}

#[test]
fn the_canonical_snake_case_token_is_not_itself_accepted() {
    // A consumer sending the core spelling is making a mistake this surface
    // should report, not absorb — accepting both would make the published
    // convention untrue and quietly permit two spellings per variant.
    //
    // Only multi-word tokens can express this: a single-word token is its own
    // camelCase spelling, so there is no second spelling to reject.
    for variant in MigrationChangeKind::VARIANTS
        .iter()
        .copied()
        .filter(|variant| variant.as_str().contains('_'))
    {
        assert_eq!(
            from_js_token::<MigrationChangeKind>(variant.as_str()),
            None,
            "snake_case token `{}` was accepted by the JavaScript surface",
            variant.as_str()
        );
    }
}

#[test]
fn unknown_tokens_resolve_to_none() {
    assert_eq!(from_js_token::<MigrationChangeKind>("nope"), None);
    assert_eq!(from_js_token::<MigrationChangeKind>(""), None);
}

#[test]
fn single_word_tokens_pass_through_unchanged() {
    // Not currently exercised by any adopting enum, but it is the base case
    // the multi-word behavior is defined against.
    assert_eq!(js_token("canonical"), "canonical");
    assert_eq!(js_token(""), "");
}
