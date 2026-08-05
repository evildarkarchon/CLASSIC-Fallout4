//! Node casing-transform tests.
//!
//! The transform is the only place in this change where a binding's published
//! string is not byte-identical to the core's, so it is the only place a
//! divergence could be reintroduced. These tests are exhaustive over every
//! token it is applied to rather than illustrative.
//!
//! These are deliberately *not* the projection tests. A projection test asks
//! whether this surface emits the core token, and derives its expectation from
//! the core; those live in `user_settings_tests.rs`. These ask the one question
//! no derived expectation can answer — whether the string a JavaScript consumer
//! already parses is still the string they get — so the right-hand column below
//! is hand-written on purpose, and frozen.

use super::*;
use classic_user_settings_core::{
    CommitEligibility, DocumentClassification, MigrationChangeKind, PreferenceOrigin,
    SourceLocation,
};

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

/// The frozen camelCase spellings for preference provenance.
const PUBLISHED_PREFERENCE_ORIGIN_TOKENS: &[(PreferenceOrigin, &str)] = &[
    (PreferenceOrigin::Document, "document"),
    (PreferenceOrigin::Default, "default"),
    (PreferenceOrigin::DegradedFallback, "degradedFallback"),
];

/// The frozen camelCase spellings for the selected source location.
///
/// Every variant is a single word, so the transform is an identity here. Worth
/// pinning rather than skipping: it is the evidence that this enum never needed
/// a camelCase table of its own, which is why deleting the one it had is safe.
const PUBLISHED_SOURCE_LOCATION_TOKENS: &[(SourceLocation, &str)] = &[
    (SourceLocation::Canonical, "canonical"),
    (SourceLocation::Legacy, "legacy"),
    (SourceLocation::Missing, "missing"),
];

/// The frozen camelCase spellings for document classification.
const PUBLISHED_DOCUMENT_CLASSIFICATION_TOKENS: &[(DocumentClassification, &str)] = &[
    (DocumentClassification::Current, "current"),
    (DocumentClassification::Unversioned, "unversioned"),
    (DocumentClassification::Older, "older"),
    (DocumentClassification::NewerCompatible, "newerCompatible"),
    (DocumentClassification::FutureMajor, "futureMajor"),
    (DocumentClassification::LegacyFlat, "legacyFlat"),
    (DocumentClassification::Malformed, "malformed"),
    (DocumentClassification::Missing, "missing"),
];

/// The frozen camelCase spellings for commit eligibility.
const PUBLISHED_COMMIT_ELIGIBILITY_TOKENS: &[(CommitEligibility, &str)] = &[
    (CommitEligibility::Eligible, "eligible"),
    (CommitEligibility::RequiresMigration, "requiresMigration"),
    (CommitEligibility::BlockedUntrusted, "blockedUntrusted"),
];

/// Asserts that camelizing each core token reproduces its published spelling.
fn assert_published_spellings<T>(published: &[(T, &str)])
where
    T: Vocabulary + PartialEq + std::fmt::Debug,
{
    for (variant, published_spelling) in published {
        assert_eq!(
            js_token(variant.as_str()),
            *published_spelling,
            "core token `{}` no longer camelizes to its published spelling",
            variant.as_str()
        );
    }
}

/// Asserts that a published-spelling table covers every variant of its enum.
fn assert_table_covers_every_variant<T>(published: &[(T, &str)])
where
    T: Vocabulary + PartialEq + std::fmt::Debug,
{
    assert_eq!(published.len(), T::VARIANTS.len());
    for variant in T::VARIANTS.iter().copied() {
        assert!(
            published.iter().any(|(covered, _)| *covered == variant),
            "no published camelCase spelling recorded for core token `{}`",
            variant.as_str()
        );
    }
}

/// Asserts that every projected token resolves back to the variant it came from.
fn assert_tokens_round_trip<T>()
where
    T: Vocabulary + PartialEq + std::fmt::Debug,
{
    for variant in T::VARIANTS.iter().copied() {
        let projected = js_token(variant.as_str());
        assert_eq!(
            from_js_token::<T>(&projected),
            Some(variant),
            "projected token `{projected}` did not resolve back to its variant"
        );
    }
}

/// Asserts that the canonical snake_case spelling is not a second accepted form.
fn assert_snake_case_is_rejected<T>()
where
    T: Vocabulary + PartialEq + std::fmt::Debug,
{
    for variant in T::VARIANTS
        .iter()
        .copied()
        .filter(|variant| variant.as_str().contains('_'))
    {
        assert_eq!(
            from_js_token::<T>(variant.as_str()),
            None,
            "snake_case token `{}` was accepted by the JavaScript surface",
            variant.as_str()
        );
    }
}

#[test]
fn every_projected_token_keeps_its_published_camel_case_spelling() {
    assert_published_spellings(PUBLISHED_MIGRATION_CHANGE_KIND_TOKENS);
    assert_published_spellings(PUBLISHED_PREFERENCE_ORIGIN_TOKENS);
    assert_published_spellings(PUBLISHED_SOURCE_LOCATION_TOKENS);
    assert_published_spellings(PUBLISHED_DOCUMENT_CLASSIFICATION_TOKENS);
    assert_published_spellings(PUBLISHED_COMMIT_ELIGIBILITY_TOKENS);
}

#[test]
fn the_published_token_table_covers_every_variant() {
    // Without this, a variant added to the core would be projected by an
    // untested path: the transform would still run, and nothing would say
    // whether its output was the spelling anyone intended.
    assert_table_covers_every_variant(PUBLISHED_MIGRATION_CHANGE_KIND_TOKENS);
    assert_table_covers_every_variant(PUBLISHED_PREFERENCE_ORIGIN_TOKENS);
    assert_table_covers_every_variant(PUBLISHED_SOURCE_LOCATION_TOKENS);
    assert_table_covers_every_variant(PUBLISHED_DOCUMENT_CLASSIFICATION_TOKENS);
    assert_table_covers_every_variant(PUBLISHED_COMMIT_ELIGIBILITY_TOKENS);
}

#[test]
fn every_projected_token_round_trips_back_to_its_variant() {
    assert_tokens_round_trip::<MigrationChangeKind>();
    assert_tokens_round_trip::<PreferenceOrigin>();
    assert_tokens_round_trip::<SourceLocation>();
    assert_tokens_round_trip::<DocumentClassification>();
    assert_tokens_round_trip::<CommitEligibility>();
}

#[test]
fn the_canonical_snake_case_token_is_not_itself_accepted() {
    // A consumer sending the core spelling is making a mistake this surface
    // should report, not absorb — accepting both would make the published
    // convention untrue and quietly permit two spellings per variant.
    //
    // Only multi-word tokens can express this: a single-word token is its own
    // camelCase spelling, so there is no second spelling to reject. That is why
    // `SourceLocation` is absent below rather than listed and passing vacuously.
    assert_snake_case_is_rejected::<MigrationChangeKind>();
    assert_snake_case_is_rejected::<PreferenceOrigin>();
    assert_snake_case_is_rejected::<DocumentClassification>();
    assert_snake_case_is_rejected::<CommitEligibility>();
}

#[test]
fn unknown_tokens_resolve_to_none() {
    assert_eq!(from_js_token::<MigrationChangeKind>("nope"), None);
    assert_eq!(from_js_token::<MigrationChangeKind>(""), None);
    assert_eq!(from_js_token::<SourceLocation>("nope"), None);
    assert_eq!(from_js_token::<SourceLocation>(""), None);
}

#[test]
fn single_word_tokens_pass_through_unchanged() {
    // The base case the multi-word behavior is defined against, and no longer
    // hypothetical: every `SourceLocation` token now takes this path.
    assert_eq!(js_token("canonical"), "canonical");
    assert_eq!(js_token(""), "");
}
