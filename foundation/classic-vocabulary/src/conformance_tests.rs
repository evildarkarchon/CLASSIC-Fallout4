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

// --- Delegating twins -----------------------------------------------------
//
// `Conforming` above plays the source enum. Each twin fixture below delegates
// correctly except in exactly one respect, for the same reason the fixtures
// above each break exactly one clause: a helper whose whole purpose is to fail
// is untested until it does.

/// A faithful twin: identity over `Conforming`, plus one locally owned variant.
#[derive(Clone, Copy)]
enum FaithfulTwin {
    First,
    Second,
    OnlyHere,
}

impl Vocabulary for FaithfulTwin {
    const VARIANTS: &'static [Self] = &[Self::First, Self::Second, Self::OnlyHere];

    fn as_str(self) -> &'static str {
        match self {
            Self::First => Conforming::First.as_str(),
            Self::Second => Conforming::Second.as_str(),
            Self::OnlyHere => "only_here",
        }
    }

    fn label(self) -> &'static str {
        match self {
            Self::First => Conforming::First.label(),
            Self::Second => Conforming::Second.label(),
            Self::OnlyHere => "Only here",
        }
    }
}

const fn faithful_source(variant: FaithfulTwin) -> Option<Conforming> {
    match variant {
        FaithfulTwin::First => Some(Conforming::First),
        FaithfulTwin::Second => Some(Conforming::Second),
        FaithfulTwin::OnlyHere => None,
    }
}

/// A twin that restates a Display Label instead of delegating it.
///
/// Its token still matches, which is the point: this is the drift a
/// token-only check would wave through, and it is the half a user reads.
#[derive(Clone, Copy)]
enum RestatedLabelTwin {
    First,
}

impl Vocabulary for RestatedLabelTwin {
    const VARIANTS: &'static [Self] = &[Self::First];

    fn as_str(self) -> &'static str {
        match self {
            Self::First => "first",
        }
    }

    fn label(self) -> &'static str {
        match self {
            Self::First => "1st",
        }
    }
}

const fn restated_label_source(variant: RestatedLabelTwin) -> Option<Conforming> {
    match variant {
        RestatedLabelTwin::First => Some(Conforming::First),
    }
}

/// A twin that stopped delegating a variant it could have delegated.
#[derive(Clone, Copy)]
enum UndeclaredLocalTwin {
    First,
    Second,
}

impl Vocabulary for UndeclaredLocalTwin {
    const VARIANTS: &'static [Self] = &[Self::First, Self::Second];

    fn as_str(self) -> &'static str {
        match self {
            Self::First => "first",
            Self::Second => "second",
        }
    }

    fn label(self) -> &'static str {
        match self {
            Self::First => Conforming::First.label(),
            Self::Second => "Second",
        }
    }
}

const fn undeclared_local_source(variant: UndeclaredLocalTwin) -> Option<Conforming> {
    match variant {
        UndeclaredLocalTwin::First => Some(Conforming::First),
        // The defect: this variant has a perfectly good counterpart and the
        // mapping declines to name it.
        UndeclaredLocalTwin::Second => None,
    }
}

/// A twin that was never extended when its source gained `Second`.
///
/// Written with a catch-all arm so the compiler has nothing to say, which is
/// the only case where this clause is doing work the type system could not.
#[derive(Clone, Copy)]
enum StaleTwin {
    First,
}

impl Vocabulary for StaleTwin {
    const VARIANTS: &'static [Self] = &[Self::First];

    fn as_str(self) -> &'static str {
        match self {
            Self::First => "first",
        }
    }

    fn label(self) -> &'static str {
        match self {
            Self::First => "First",
        }
    }
}

const fn stale_source(_variant: StaleTwin) -> Option<Conforming> {
    // Deliberately a catch-all rather than an exhaustive `match`. An exhaustive
    // one would stop compiling the moment the source gained a variant, and this
    // fixture exists to stand in for the mappings where that safety net was
    // given up.
    Some(Conforming::First)
}

#[test]
fn faithful_twin_passes() {
    assert_twin_vocabulary_conformance(faithful_source, &["only_here"]);
}

#[test]
#[should_panic(expected = "a twin delegates both forms, not just the token")]
fn a_twin_that_restates_a_display_label_is_rejected() {
    assert_twin_vocabulary_conformance(restated_label_source, &[]);
}

#[test]
#[should_panic(expected = "was not declared as locally owned")]
fn an_undeclared_locally_owned_variant_is_rejected() {
    assert_twin_vocabulary_conformance(undeclared_local_source, &[]);
}

#[test]
#[should_panic(expected = "a variant that can delegate must")]
fn a_delegable_variant_declared_as_locally_owned_is_rejected() {
    assert_twin_vocabulary_conformance(faithful_source, &["only_here", "first"]);
}

#[test]
#[should_panic(expected = "the twin was not extended when this variant was added")]
fn a_source_variant_no_twin_variant_reaches_is_rejected() {
    assert_twin_vocabulary_conformance(stale_source, &[]);
}
