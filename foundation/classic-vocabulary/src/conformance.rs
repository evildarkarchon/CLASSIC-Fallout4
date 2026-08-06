//! The reusable conformance assertion for the Vocabulary naming contract.
//!
//! One generic function rather than a macro or a derive, so that a new adopter
//! costs one call from the owning crate's existing sibling test module and the
//! failure message points at the enum a contributor is actually editing.

use crate::Vocabulary;

/// Asserts that one enum satisfies the Vocabulary naming contract.
///
/// Call this once per adopting enum from the owning crate's sibling test
/// module:
///
/// ```ignore
/// #[test]
/// fn migration_change_kind_satisfies_the_vocabulary_contract() {
///     assert_vocabulary_conformance::<MigrationChangeKind>();
/// }
/// ```
///
/// # Checks
///
/// - [`VARIANTS`](Vocabulary::VARIANTS) is non-empty, so that a list a
///   contributor forgot to populate fails here instead of turning every
///   exhaustive iteration built on it into a vacuous pass.
/// - Every variant yields a non-empty Vocabulary Token and a non-empty Display
///   Label — a variant that renders as nothing is the failure this contract
///   exists to make impossible.
/// - Tokens are unique within the enum. Two variants sharing a token cannot be
///   told apart by any adapter, and [`from_token`](crate::from_token) would
///   resolve both to whichever comes first.
/// - Labels are unique within the enum, so that two outcomes a user needs to
///   distinguish do not read identically.
///
/// Uniqueness is deliberately scoped *within* an enum and not across the
/// workspace: two unrelated enums may each legitimately have a `missing`
/// variant, and the owning type is what disambiguates them.
///
/// # Panics
///
/// Panics on the first violation, naming the enum and the offending token so
/// the message is actionable without opening the test.
pub fn assert_vocabulary_conformance<T: Vocabulary>() {
    let enum_name = core::any::type_name::<T>();
    let variants = T::VARIANTS;

    assert!(
        !variants.is_empty(),
        "{enum_name}: VARIANTS is empty, so every exhaustive iteration over \
         this enum would pass without checking anything"
    );

    // Linear scans over a handful of variants. A set would be asymptotically
    // better and would cost the position of the *earlier* offender, which is
    // the half of the message that tells a contributor where the duplicate
    // came from.
    let mut tokens: Vec<&'static str> = Vec::with_capacity(variants.len());
    let mut labels: Vec<&'static str> = Vec::with_capacity(variants.len());

    for (index, variant) in variants.iter().copied().enumerate() {
        let token = variant.as_str();
        assert!(
            !token.is_empty(),
            "{enum_name}: the variant at VARIANTS index {index} has an empty \
             Vocabulary Token"
        );

        let label = variant.label();
        assert!(
            !label.is_empty(),
            "{enum_name}: the variant with Vocabulary Token `{token}` has an \
             empty Display Label"
        );

        if let Some(first) = tokens.iter().position(|seen| *seen == token) {
            panic!(
                "{enum_name}: Vocabulary Token `{token}` is used by the \
                 variants at VARIANTS indexes {first} and {index}; no adapter \
                 could tell those two apart"
            );
        }
        if let Some(first) = labels.iter().position(|seen| *seen == label) {
            panic!(
                "{enum_name}: Display Label `{label}` is used by the variants \
                 at VARIANTS indexes {first} and {index}; a user could not \
                 tell those two outcomes apart"
            );
        }

        tokens.push(token);
        labels.push(label);
    }
}

/// Asserts that a delegating twin enum cannot disagree with the enum it mirrors.
///
/// A *twin* is an enum one crate declares so that another crate's type does not
/// leak into its contract, and which is a near-identity mirror of that other
/// enum. The twin keeps its own type but obtains both naming forms by
/// delegating through the mapping between them, so this assertion checks the
/// delegation actually holds rather than trusting that two `match` expressions
/// were kept in step.
///
/// Call this *instead of* [`assert_vocabulary_conformance`] for a twin — it
/// runs the full base contract on the twin first, then the twin-specific
/// clauses below.
///
/// `source_of` is the twin-to-source direction of the near-identity mapping,
/// returning `None` for a twin variant the source has no counterpart for.
/// `locally_owned_tokens` names exactly those variants: they are the ones
/// allowed — and required — to supply both forms themselves.
///
/// ```ignore
/// #[test]
/// fn local_ignore_run_state_delegates_to_the_configuration_state() {
///     assert_twin_vocabulary_conformance(source_local_ignore_state, &["recovery_required"]);
/// }
/// ```
///
/// # Checks
///
/// - The twin satisfies the base Vocabulary contract in its own right.
/// - Every twin variant with a counterpart agrees with it on *both* forms. One
///   form matching is not enough: a twin that restated a Display Label would
///   still project the right token, and the drift would surface only in shipped
///   prose.
/// - The variants without a counterpart are exactly `locally_owned_tokens`.
///   Pinning the set in both directions is what makes an asymmetric twin
///   assertable — a twin that quietly stopped delegating a variant would
///   otherwise read as one more locally owned variant.
/// - Every *source* variant is claimed by some twin variant. This is the clause
///   that catches a variant added to the source and not to the twin. A twin
///   whose forward mapping is an exhaustive `match` already fails to compile in
///   that case, and this is the backstop for one written with a catch-all arm,
///   where the compiler has nothing to say.
///
/// Variants are compared by Vocabulary Token rather than by value, so that this
/// helper does not force a `PartialEq` bound onto the naming contract for the
/// sake of a test. The base assertion has already established that tokens are
/// unique within each enum, which is what makes a token a sound identity here.
///
/// # Panics
///
/// Panics on the first violation, naming both enums and the offending token.
pub fn assert_twin_vocabulary_conformance<Twin, Source>(
    source_of: fn(Twin) -> Option<Source>,
    locally_owned_tokens: &[&str],
) where
    Twin: Vocabulary,
    Source: Vocabulary,
{
    assert_vocabulary_conformance::<Twin>();

    let twin_name = core::any::type_name::<Twin>();
    let source_name = core::any::type_name::<Source>();

    let mut unpaired: Vec<&'static str> = Vec::new();
    let mut claimed: Vec<&'static str> = Vec::new();

    for variant in Twin::VARIANTS.iter().copied() {
        let token = variant.as_str();
        let Some(source) = source_of(variant) else {
            unpaired.push(token);
            continue;
        };

        assert_eq!(
            token,
            source.as_str(),
            "{twin_name}: the variant with Vocabulary Token `{token}` maps to a \
             {source_name} variant whose token is `{}`; a twin delegates its \
             token rather than spelling its own",
            source.as_str()
        );
        assert_eq!(
            variant.label(),
            source.label(),
            "{twin_name}: the variant with Vocabulary Token `{token}` has \
             Display Label `{}` while its {source_name} counterpart has `{}`; a \
             twin delegates both forms, not just the token",
            variant.label(),
            source.label()
        );

        claimed.push(source.as_str());
    }

    for token in &unpaired {
        assert!(
            locally_owned_tokens.iter().any(|owned| owned == token),
            "{twin_name}: the variant with Vocabulary Token `{token}` has no \
             {source_name} counterpart but was not declared as locally owned; \
             either restore its delegation or add it to the locally owned set"
        );
    }
    for owned in locally_owned_tokens {
        assert!(
            unpaired.iter().any(|token| token == owned),
            "{twin_name}: `{owned}` is declared as locally owned but does map to \
             a {source_name} counterpart; a variant that can delegate must"
        );
    }

    for source in Source::VARIANTS.iter().copied() {
        let token = source.as_str();
        assert!(
            claimed.contains(&token),
            "{source_name}: the variant with Vocabulary Token `{token}` is not \
             reachable from any {twin_name} variant; the twin was not extended \
             when this variant was added"
        );
    }
}

#[rustfmt::skip]
#[cfg(test)] #[path = "conformance_tests.rs"] mod tests;
