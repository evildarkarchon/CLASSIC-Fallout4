//! Conformance-helper tests.
//!
//! Each fixture enum violates exactly one clause of the contract, because a
//! helper that only ever sees conforming input is untested in the direction
//! that matters: the whole reason it exists is to fail.

use super::*;
use crate::Vocabulary;

#[derive(Clone, Copy)]
enum Conforming {
    First,
    Second,
}

impl Vocabulary for Conforming {
    const VARIANTS: &'static [Self] = &[Self::First, Self::Second];

    fn as_str(self) -> &'static str {
        match self {
            Self::First => "first",
            Self::Second => "second",
        }
    }

    fn label(self) -> &'static str {
        match self {
            Self::First => "First",
            Self::Second => "Second",
        }
    }
}

#[derive(Clone, Copy)]
enum EmptyVariantList {
    // Never constructed *because* it is missing from `VARIANTS` — that omission
    // is the defect this fixture reproduces, so the dead-code warning here is
    // the compiler agreeing with the test.
    #[expect(dead_code, reason = "deliberately absent from VARIANTS")]
    Unlisted,
}

impl Vocabulary for EmptyVariantList {
    const VARIANTS: &'static [Self] = &[];

    fn as_str(self) -> &'static str {
        match self {
            Self::Unlisted => "unlisted",
        }
    }

    fn label(self) -> &'static str {
        match self {
            Self::Unlisted => "Unlisted",
        }
    }
}

#[derive(Clone, Copy)]
enum BlankToken {
    Blank,
}

impl Vocabulary for BlankToken {
    const VARIANTS: &'static [Self] = &[Self::Blank];

    fn as_str(self) -> &'static str {
        match self {
            Self::Blank => "",
        }
    }

    fn label(self) -> &'static str {
        match self {
            Self::Blank => "Blank",
        }
    }
}

#[derive(Clone, Copy)]
enum BlankLabel {
    Blank,
}

impl Vocabulary for BlankLabel {
    const VARIANTS: &'static [Self] = &[Self::Blank];

    fn as_str(self) -> &'static str {
        match self {
            Self::Blank => "blank",
        }
    }

    fn label(self) -> &'static str {
        match self {
            Self::Blank => "",
        }
    }
}

#[derive(Clone, Copy)]
enum DuplicateToken {
    First,
    Second,
}

impl Vocabulary for DuplicateToken {
    const VARIANTS: &'static [Self] = &[Self::First, Self::Second];

    fn as_str(self) -> &'static str {
        match self {
            Self::First | Self::Second => "shared",
        }
    }

    fn label(self) -> &'static str {
        match self {
            Self::First => "First",
            Self::Second => "Second",
        }
    }
}

#[derive(Clone, Copy)]
enum DuplicateLabel {
    First,
    Second,
}

impl Vocabulary for DuplicateLabel {
    const VARIANTS: &'static [Self] = &[Self::First, Self::Second];

    fn as_str(self) -> &'static str {
        match self {
            Self::First => "first",
            Self::Second => "second",
        }
    }

    fn label(self) -> &'static str {
        match self {
            Self::First | Self::Second => "Shared",
        }
    }
}

#[test]
fn conforming_enum_passes() {
    assert_vocabulary_conformance::<Conforming>();
}

#[test]
#[should_panic(expected = "VARIANTS is empty")]
fn empty_variant_list_is_rejected() {
    assert_vocabulary_conformance::<EmptyVariantList>();
}

#[test]
#[should_panic(expected = "has an empty Vocabulary Token")]
fn blank_token_is_rejected() {
    assert_vocabulary_conformance::<BlankToken>();
}

#[test]
#[should_panic(expected = "has an empty Display Label")]
fn blank_label_is_rejected() {
    assert_vocabulary_conformance::<BlankLabel>();
}

#[test]
#[should_panic(
    expected = "Vocabulary Token `shared` is used by the variants at VARIANTS indexes 0 and 1"
)]
fn duplicate_token_is_rejected() {
    assert_vocabulary_conformance::<DuplicateToken>();
}

#[test]
#[should_panic(
    expected = "Display Label `Shared` is used by the variants at VARIANTS indexes 0 and 1"
)]
fn duplicate_label_is_rejected() {
    assert_vocabulary_conformance::<DuplicateLabel>();
}
