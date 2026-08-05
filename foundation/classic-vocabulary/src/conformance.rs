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

#[cfg(test)]
#[path = "conformance_tests.rs"]
mod tests;
