//! Trait and token-lookup tests.

use super::*;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Sample {
    First,
    SecondWord,
}

impl Vocabulary for Sample {
    const VARIANTS: &'static [Self] = &[Self::First, Self::SecondWord];

    fn as_str(self) -> &'static str {
        match self {
            Self::First => "first",
            Self::SecondWord => "second_word",
        }
    }

    fn label(self) -> &'static str {
        match self {
            Self::First => "First",
            Self::SecondWord => "Second word",
        }
    }
}

#[test]
fn every_variant_round_trips_through_its_own_token() {
    for variant in Sample::VARIANTS.iter().copied() {
        assert_eq!(from_token::<Sample>(variant.as_str()), Some(variant));
    }
}

#[test]
fn unknown_token_resolves_to_none() {
    assert_eq!(from_token::<Sample>("third"), None);
}

#[test]
fn token_lookup_is_exact_rather_than_case_insensitive_or_prefixed() {
    // Tokens are frozen identifiers, so a near-miss is a caller bug worth
    // reporting rather than something to helpfully absorb.
    assert_eq!(from_token::<Sample>("First"), None);
    assert_eq!(from_token::<Sample>("second"), None);
    assert_eq!(from_token::<Sample>("second_word "), None);
}

#[test]
fn tokens_and_labels_are_independent_forms() {
    // The whole reason both exist: `Second word` is not derivable back to
    // `second_word` by any rule the trait could encode, and the reverse
    // direction is what a naive implementation would try to collapse.
    assert_ne!(Sample::SecondWord.as_str(), Sample::SecondWord.label());
}
