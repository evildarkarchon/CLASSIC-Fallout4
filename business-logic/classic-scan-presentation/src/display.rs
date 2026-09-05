//! The typed display shape every Crash Log Scan Run renderer produces.
//!
//! A rendered surface is a flat, ordered sequence of [`DisplayLine`]s. It is deliberately
//! not a tree: grouping, sections, and collapsibility are Display Layout and belong to the
//! frontend, which composes them from lines.

use std::path::PathBuf;

/// How a display line should read in severity terms.
///
/// Adapters map this onto their own styling. Core never names a colour, a text attribute,
/// or a widget — only how gravely the line should read.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DisplaySeverity {
    /// Neutral fact about the run.
    Info,
    /// Worth noticing, but nothing failed.
    Notice,
    /// Something is wrong or incomplete and may need attention.
    Warning,
    /// Something failed.
    Failure,
    /// Something completed as intended.
    Success,
}

/// One typed piece of a display line.
///
/// [`Text`](Self::Text) and [`Label`](Self::Label) carry fixed prose that core owns. Every
/// other variant carries a value core refuses to splice into a sentence, so an adapter can
/// render a path as a clickable link or emphasise a number without re-deriving the wording
/// around it.
///
/// The taxonomy is fixed at six kinds for its first version. Each addition touches three
/// binding parity baselines, so growth must be a deliberate decision rather than incidental.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum DisplaySegment {
    /// Fixed core-owned prose. Never contains a placeholder.
    Text(&'static str),
    /// A Display Label obtained from `Vocabulary::label()`.
    Label(&'static str),
    /// A count and the noun it counts. `noun` is already resolved to its singular or
    /// plural form by core, so no adapter re-decides pluralization.
    Count {
        /// The counted quantity.
        value: u64,
        /// The noun, already in the form that agrees with `value`.
        noun: &'static str,
    },
    /// A filesystem path, whole and untruncated. Truncation is Display Layout.
    Path(PathBuf),
    /// The name of a domain entity that is not a filesystem path.
    ///
    /// No render path emits one yet. The variant exists because the taxonomy is fixed for
    /// this version and a later addition is a deliberate, baseline-touching decision — so
    /// the kind a non-path name will need is declared now rather than bolted on then.
    Name(String),
    /// A value core wants set apart from the prose around it: a free-text diagnostic, an
    /// ordinal position, a content hash.
    Emphasis(String),
}

/// One line of Display Content: a severity and an ordered list of typed segments.
///
/// An adapter concatenates `segments` in order and never reorders within a line. It may
/// reorder, group, or omit whole lines.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DisplayLine {
    /// How gravely this line should read.
    pub severity: DisplaySeverity,
    /// The line's content, in reading order.
    pub segments: Vec<DisplaySegment>,
}

impl DisplayLine {
    /// Builds a line from a severity and its segments.
    pub(crate) const fn new(severity: DisplaySeverity, segments: Vec<DisplaySegment>) -> Self {
        Self { severity, segments }
    }
}

/// A noun in both grammatical numbers, so a count can never disagree with the word beside it.
///
/// This exists so agreement is structural rather than remembered. A renderer cannot name a
/// noun without also naming its counterpart, and it cannot choose between the two — only
/// [`for_value`](Self::for_value) does, from the value itself. That is what removes the
/// duplicated `plural(count, "log", "logs")` helper each frontend wrote for itself, along
/// with every future chance for one of them to pass the arguments the wrong way round.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct CountedNoun {
    singular: &'static str,
    plural: &'static str,
}

impl CountedNoun {
    /// Declares a noun's singular and plural forms.
    const fn new(singular: &'static str, plural: &'static str) -> Self {
        Self { singular, plural }
    }

    /// Returns the form that agrees with `value`.
    pub(crate) const fn for_value(self, value: u64) -> &'static str {
        if value == 1 {
            self.singular
        } else {
            self.plural
        }
    }
}

/// Crash Logs, counted as the generic unit of scanning work.
pub(crate) const LOG: CountedNoun = CountedNoun::new("log", "logs");
/// Crash Logs, counted where the line does not already establish what is being counted.
pub(crate) const CRASH_LOG: CountedNoun = CountedNoun::new("crash log", "crash logs");
/// Explicit user-selected inputs that discovery refused.
pub(crate) const TARGETED_INPUT: CountedNoun =
    CountedNoun::new("targeted input", "targeted inputs");
/// Directories discovery searched.
pub(crate) const SEARCHED_LOCATION: CountedNoun = CountedNoun::new("location", "locations");
/// Crash Logs Rust admits concurrently.
pub(crate) const CONCURRENT_SCAN: CountedNoun =
    CountedNoun::new("concurrent scan", "concurrent scans");
/// Bytes of YAML Data content.
pub(crate) const BYTE: CountedNoun = CountedNoun::new("byte", "bytes");

/// Builds a count segment with the noun form that agrees with `value`.
pub(crate) const fn count(value: u64, noun: CountedNoun) -> DisplaySegment {
    DisplaySegment::Count {
        value,
        noun: noun.for_value(value),
    }
}

/// Builds a count segment from a `usize` quantity carried by the scan-run contract.
pub(crate) const fn count_usize(value: usize, noun: CountedNoun) -> DisplaySegment {
    count(value as u64, noun)
}
