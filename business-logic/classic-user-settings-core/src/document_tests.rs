//! Document vocabulary and revision token tests.
//!
//! Document opening and classification are covered by `tests/open_behavior.rs`;
//! this sibling module exists for what only the owning crate can assert — that
//! the names it now owns satisfy the Vocabulary naming contract, and that the
//! revision token pair the three bindings delegate to keeps the exact wire
//! format, and the exact rejection set, that each binding used to carry as its
//! own byte-identical copy.

use super::*;
use classic_vocabulary::{Vocabulary, assert_vocabulary_conformance, from_token};

// ── Vocabulary conformance ──────────────────────────────────────────

#[test]
fn source_location_satisfies_the_vocabulary_contract() {
    assert_vocabulary_conformance::<SourceLocation>();
}

#[test]
fn document_classification_satisfies_the_vocabulary_contract() {
    assert_vocabulary_conformance::<DocumentClassification>();
}

#[test]
fn commit_eligibility_satisfies_the_vocabulary_contract() {
    assert_vocabulary_conformance::<CommitEligibility>();
}

#[test]
fn preference_origin_satisfies_the_vocabulary_contract() {
    assert_vocabulary_conformance::<PreferenceOrigin>();
}

// ── Frozen token spellings ──────────────────────────────────────────
//
// The one place in the workspace where these literals are legitimate: this is
// the definition of the frozen identifiers, not a restatement of them. Every
// other assertion about these strings — in all three bindings — derives its
// expectation from here, so a change to any arm below is a breaking change to
// every binding consumer and must fail loudly right now.

#[test]
fn source_location_tokens_are_the_frozen_published_spelling() {
    assert_eq!(SourceLocation::Canonical.as_str(), "canonical");
    assert_eq!(SourceLocation::Legacy.as_str(), "legacy");
    assert_eq!(SourceLocation::Missing.as_str(), "missing");
}

#[test]
fn document_classification_tokens_are_the_frozen_published_spelling() {
    assert_eq!(DocumentClassification::Current.as_str(), "current");
    assert_eq!(DocumentClassification::Unversioned.as_str(), "unversioned");
    assert_eq!(DocumentClassification::Older.as_str(), "older");
    assert_eq!(
        DocumentClassification::NewerCompatible.as_str(),
        "newer_compatible"
    );
    assert_eq!(DocumentClassification::FutureMajor.as_str(), "future_major");
    assert_eq!(DocumentClassification::LegacyFlat.as_str(), "legacy_flat");
    assert_eq!(DocumentClassification::Malformed.as_str(), "malformed");
    assert_eq!(DocumentClassification::Missing.as_str(), "missing");
}

#[test]
fn commit_eligibility_tokens_are_the_frozen_published_spelling() {
    assert_eq!(CommitEligibility::Eligible.as_str(), "eligible");
    assert_eq!(
        CommitEligibility::RequiresMigration.as_str(),
        "requires_migration"
    );
    assert_eq!(
        CommitEligibility::BlockedUntrusted.as_str(),
        "blocked_untrusted"
    );
}

#[test]
fn preference_origin_tokens_are_the_frozen_published_spelling() {
    assert_eq!(PreferenceOrigin::Document.as_str(), "document");
    assert_eq!(PreferenceOrigin::Default.as_str(), "default");
    assert_eq!(
        PreferenceOrigin::DegradedFallback.as_str(),
        "degraded_fallback"
    );
}

// ── Variant-list completeness ───────────────────────────────────────
//
// Nothing can ask a Rust enum how many variants it has, so these counts are the
// only guard against a variant that compiles — because `as_str` and `label` are
// exhaustive matches — yet never appears in an exhaustive iteration. A
// contributor adding a variant lands here and is told to add it to `VARIANTS`
// too. That matters more for these four than for the migration tracer: the
// bindings' reverse-parse paths now scan `VARIANTS`, so an omitted variant
// would make a legitimate token unparseable at every surface.

#[test]
fn every_source_location_variant_is_listed_for_iteration() {
    assert_eq!(SourceLocation::VARIANTS.len(), 3);
}

#[test]
fn every_document_classification_variant_is_listed_for_iteration() {
    assert_eq!(DocumentClassification::VARIANTS.len(), 8);
}

#[test]
fn every_commit_eligibility_variant_is_listed_for_iteration() {
    assert_eq!(CommitEligibility::VARIANTS.len(), 3);
}

#[test]
fn every_preference_origin_variant_is_listed_for_iteration() {
    assert_eq!(PreferenceOrigin::VARIANTS.len(), 3);
}

// ── Round-trips and label shape ─────────────────────────────────────

#[test]
fn every_document_vocabulary_token_resolves_back_to_its_variant() {
    fn assert_round_trips<T: Vocabulary + PartialEq + core::fmt::Debug>() {
        for variant in T::VARIANTS.iter().copied() {
            assert_eq!(
                from_token::<T>(variant.as_str()),
                Some(variant),
                "token `{}` did not resolve back to its own variant",
                variant.as_str()
            );
        }
    }

    assert_round_trips::<SourceLocation>();
    assert_round_trips::<DocumentClassification>();
    assert_round_trips::<CommitEligibility>();
    assert_round_trips::<PreferenceOrigin>();
}

#[test]
fn document_vocabulary_labels_read_as_prose_rather_than_identifiers() {
    // Display Labels are reworded freely, so pinning their exact text here
    // would make a legitimate wording fix look like a regression. What must
    // hold is the property that separates the two forms: a label is prose, so
    // it never equals its own token and never carries token punctuation.
    fn assert_prose<T: Vocabulary>() {
        for variant in T::VARIANTS.iter().copied() {
            let label = variant.label();
            assert_ne!(label, variant.as_str());
            assert!(
                !label.contains('_'),
                "Display Label `{label}` looks like a Vocabulary Token"
            );
        }
    }

    assert_prose::<SourceLocation>();
    assert_prose::<DocumentClassification>();
    assert_prose::<CommitEligibility>();
    assert_prose::<PreferenceOrigin>();
}

// ── Revision ────────────────────────────────────────────────────────

/// Every digest byte pattern worth round-tripping: the two sentinels plus
/// boundary and realistic content digests.
fn representative_revisions() -> Vec<Revision> {
    let mut ascending = [0_u8; 32];
    for (index, byte) in ascending.iter_mut().enumerate() {
        *byte = index as u8;
    }
    vec![
        Revision::Missing,
        Revision::Unavailable,
        Revision::ContentSha256([0x00; 32]),
        Revision::ContentSha256([0xff; 32]),
        Revision::ContentSha256(ascending),
        Revision::ContentSha256(Sha256::digest(b"update_check: true\n").into()),
    ]
}

#[test]
fn revision_tokens_are_the_frozen_published_spelling() {
    // The one place in the workspace where these literals are legitimate: this
    // is the definition of the frozen wire format, not a restatement of it. The
    // CXX, Node, and Python surfaces all publish exactly what `token()` returns.
    assert_eq!(Revision::Missing.token(), "missing");
    assert_eq!(Revision::Unavailable.token(), "unavailable");
    assert_eq!(
        Revision::ContentSha256([0x00; 32]).token(),
        format!("sha256:{}", "00".repeat(32))
    );
    assert_eq!(
        Revision::ContentSha256([0xff; 32]).token(),
        format!("sha256:{}", "ff".repeat(32))
    );
}

#[test]
fn content_digest_tokens_are_lowercase_hex_of_the_exact_digest() {
    let digest: [u8; 32] = Sha256::digest(b"update_check: true\n").into();
    let token = Revision::ContentSha256(digest).token();
    let encoded = token
        .strip_prefix("sha256:")
        .expect("content revision token carries the sha256 prefix");

    assert_eq!(encoded.len(), 64);
    assert!(
        encoded
            .chars()
            .all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase())
    );
}

#[test]
fn every_representable_revision_round_trips_through_its_token() {
    for revision in representative_revisions() {
        let token = revision.token();
        assert_eq!(
            Revision::from_token(&token),
            Some(revision.clone()),
            "revision {revision:?} did not round-trip through token {token:?}"
        );
    }
}

#[test]
fn revision_tokens_are_distinct_across_representable_revisions() {
    let tokens: Vec<String> = representative_revisions()
        .iter()
        .map(Revision::token)
        .collect();
    let mut unique = tokens.clone();
    unique.sort();
    unique.dedup();

    assert_eq!(
        unique.len(),
        tokens.len(),
        "revision tokens collided: {tokens:?}"
    );
}

#[test]
fn malformed_revision_tokens_are_rejected() {
    let malformed = vec![
        String::new(),
        " ".to_string(),
        "Missing".to_string(),
        "missing ".to_string(),
        " missing".to_string(),
        "unknown".to_string(),
        "sha256".to_string(),
        "sha256:".to_string(),
        format!("sha1:{}", "ab".repeat(32)),
        // One nibble short, one nibble long, and the right length with a
        // non-hex character in the final pair.
        format!("sha256:{}", "a".repeat(63)),
        format!("sha256:{}", "a".repeat(65)),
        format!("sha256:{}zz", "a".repeat(62)),
    ];

    for token in malformed {
        assert_eq!(
            Revision::from_token(&token),
            None,
            "token {token:?} should have been rejected"
        );
    }
}

#[test]
fn uppercase_hex_digests_are_accepted() {
    // Pinned deliberately: the copies this pair replaced parsed through
    // `u8::from_str_radix`, which is case-insensitive. Tightening to
    // lowercase-only would reject tokens that callers can round-trip today.
    let token = format!("sha256:{}", "AB".repeat(32));

    assert_eq!(
        Revision::from_token(&token),
        Some(Revision::ContentSha256([0xab; 32]))
    );
}

#[test]
fn signed_hex_pairs_stay_accepted_as_a_preserved_quirk() {
    // Not a designed feature: `u8::from_str_radix` accepts a leading `+`, so
    // each two-character pair may carry a sign. `token()` can never emit this,
    // so it only matters in one direction — but the three copies this pair
    // replaced all accepted it, and AC 4 requires the rejection set to be
    // unchanged. Pinned so a future tightening is a deliberate decision with a
    // failing test behind it, not a silent side effect.
    let token = format!("sha256:{}", "+a".repeat(32));

    assert_eq!(
        Revision::from_token(&token),
        Some(Revision::ContentSha256([0x0a; 32]))
    );
}

#[test]
fn non_ascii_tokens_are_rejected_rather_than_splitting_a_character() {
    // A 64-byte encoded segment made of multi-byte characters would land a
    // two-byte slice inside a character if parsing indexed by byte offset.
    // Every binding reaches this parse with a caller-supplied string, so the
    // rejection has to be a `None`, not a panic across the FFI boundary.
    let multibyte = "\u{20ac}".repeat(21); // 63 bytes
    let token = format!("sha256:{multibyte}a"); // 64 bytes, not 64 characters

    assert_eq!(token.len() - "sha256:".len(), 64);
    assert_eq!(Revision::from_token(&token), None);
}
