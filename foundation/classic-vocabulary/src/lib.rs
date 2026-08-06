//! Workspace-internal **Vocabulary naming contract** for CLASSIC domain enums.
//!
//! CLASSIC presents the same facts through three frontends and three binding
//! surfaces. Before this crate existed, each of those surfaces wrote its own
//! strings for the same underlying variant, and they had already drifted apart
//! without anything detecting it: every copy was independently exhaustive, so
//! every compiler was satisfied, and the binding parity gates compare symbol
//! names and arity rather than values.
//!
//! The fix is ownership, not a gate. The Rust core crate that defines a domain
//! concept also owns what that concept is called, and every adapter projects
//! those names instead of maintaining a table.
//!
//! # The two forms
//!
//! A variant carries two names, and **neither is derived from the other**:
//!
//! - A **Vocabulary Token** — [`Vocabulary::as_str`]. The frozen, adapter-facing
//!   identifier. Canonically snake_case.
//! - A **Display Label** — [`Vocabulary::label`]. Human-facing prose,
//!   capitalized the way the project glossary capitalizes the domain terms it
//!   names.
//!
//! A mechanical transform can turn `field_transition` into `Field transition`,
//! which is why the temptation to derive one from the other is real. It cannot
//! turn `local_ignore_reset` into `Local Ignore reset`, because that
//! capitalization carries meaning only the glossary knows. Deriving the label
//! would therefore be correct for the easy variants and quietly wrong for
//! exactly the ones that name domain terms.
//!
//! # Stability contracts
//!
//! The two forms are deliberately separate so they can be governed separately:
//!
//! - **Vocabulary Tokens are frozen.** Changing one is a breaking change to
//!   every binding consumer, because tokens are parsed. Adding a variant is
//!   additive; respelling an existing token is not.
//! - **Display Labels may be reworded freely.** They are presentation only and
//!   are never parsed. A wording fix here reaches every frontend at once, which
//!   is the point.
//!
//! Keeping them on one trait rather than in two places is what makes the
//! distinction visible at the definition site: a contributor editing a `label`
//! arm can see they are not touching a frozen identifier.
//!
//! # Casing at the binding seams
//!
//! The canonical spelling is snake_case, which the C++ and Python surfaces
//! consume unchanged. The Node surface converts Rust identifiers to camelCase
//! at the JavaScript boundary as a documented convention, so it applies one
//! shared transform over the same canonical token rather than keeping a second
//! variant list. That transform lives in the Node crate, next to the convention
//! it implements — this crate deliberately knows nothing about any binding.
//!
//! # No binding surface
//!
//! This crate is `publish = false` and is absent from the binding parity
//! matrix, the same category as `classic-operation-context` and
//! `classic-durable-publication`. Only the *enums* cross a binding seam; the
//! trait never does. That is what keeps the one-tier binding parity policy —
//! which applies to public symbols in the business-logic core crates — from
//! taxing a shared naming convention with three projections of its own.

mod conformance;

pub use conformance::{assert_twin_vocabulary_conformance, assert_vocabulary_conformance};

/// The two names one variant of a CLASSIC domain concept carries.
///
/// Implemented by the core crate that owns the enum, never by an adapter. The
/// `Copy + 'static` bound and the `&'static str` returns exist so that every
/// projection is allocation-free and so [`VARIANTS`](Self::VARIANTS) can be a
/// plain associated constant.
///
/// Implementations write both `as_str` and `label` as exhaustive `match`
/// expressions over `self`. That exhaustiveness is the enforcement mechanism:
/// a contributor adding a variant cannot ship it without supplying both forms,
/// because the crate will not compile.
///
/// # Contract
///
/// - [`VARIANTS`](Self::VARIANTS) lists every variant exactly once.
/// - Tokens and labels are non-empty, and each form is unique within the enum.
///
/// [`assert_vocabulary_conformance`] checks everything above except the
/// completeness of `VARIANTS`, which no runtime check can observe — nothing
/// can ask a Rust enum how many variants it has. A variant left out of the
/// list silently narrows every exhaustive iteration built on it, so treat the
/// constant as part of the variant definition rather than as a lookup table
/// maintained alongside it.
pub trait Vocabulary: Copy + 'static {
    /// Every variant, for exhaustive iteration by tests and adapters.
    const VARIANTS: &'static [Self];

    /// Frozen adapter-facing Vocabulary Token. snake_case.
    fn as_str(self) -> &'static str;

    /// Human-facing Display Label. Glossary capitalization.
    fn label(self) -> &'static str;
}

/// Resolves the variant whose Vocabulary Token is exactly `token`.
///
/// This is the parse counterpart to [`Vocabulary::as_str`], and the reason it
/// is a scan over [`VARIANTS`](Vocabulary::VARIANTS) rather than a second
/// `match` is structural: a hand-written reverse table is a second copy of the
/// vocabulary and can disagree with the forward one. Derived from the same
/// list, the two cannot.
///
/// Returns `None` for an unknown token; callers own the error shape, because
/// each binding surface reports a rejected token differently.
#[must_use]
pub fn from_token<T: Vocabulary>(token: &str) -> Option<T> {
    T::VARIANTS
        .iter()
        .copied()
        .find(|variant| variant.as_str() == token)
}

/// Resolves the Display Label for a value some adapter already projected.
///
/// A binding that mirrors a core enum as its own type needs to get back from
/// one of its own values to the core label. Running the adapter's *existing*
/// forward projection over [`VARIANTS`](Vocabulary::VARIANTS) is how it does so
/// without a reverse `match`, which would be a second variant mapping able to
/// disagree with the forward one. Derived from it, the two cannot. This is the
/// same reasoning [`from_token`] applies to strings.
///
/// Returns `""` for a value the projection cannot produce. Every adapter that
/// needs this wants the same answer there — render nothing rather than invent a
/// label or borrow another variant's — and the surfaces differ only in whether
/// that case is reachable at all: open CXX shared enums admit a fabricated
/// discriminant, while N-API rejects an unknown string at the boundary.
///
/// It lives here rather than in each binding because nothing about it is
/// surface-specific. The Node casing transform is the contrasting case: that
/// one encodes a JavaScript identifier convention, so it belongs to the surface
/// that has the convention.
#[must_use]
pub fn display_label<T, U>(value: U, project: fn(T) -> U) -> &'static str
where
    T: Vocabulary,
    U: PartialEq,
{
    T::VARIANTS
        .iter()
        .copied()
        .find(|variant| project(*variant) == value)
        .map_or("", Vocabulary::label)
}

#[rustfmt::skip]
#[cfg(test)] #[path = "lib_tests.rs"] mod tests;
