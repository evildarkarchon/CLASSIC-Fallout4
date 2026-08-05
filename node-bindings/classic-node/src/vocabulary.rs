//! The Node projection of the core Vocabulary naming contract.
//!
//! The core owns one canonical snake_case spelling per variant. This surface
//! converts Rust identifiers to camelCase at the JavaScript boundary as a
//! documented convention, and its published tokens were written that way long
//! before the vocabulary moved into the core, so the two cannot simply be the
//! same string.
//!
//! One shared transform is what reconciles them. The alternative — keeping a
//! second, camelCase variant list next to the core one — is what this work
//! exists to delete: two lists compile independently, so the compiler is
//! satisfied whichever one is wrong.
//!
//! # Scope of the transform
//!
//! It handles the tokens CLASSIC actually has: lowercase ASCII words joined by
//! underscores. It is deliberately *not* a general identifier converter. A
//! future token with a digit boundary (`schema_v2_transition`) or a leading
//! acronym (`xse_folder_transition`) has no single obviously-correct camelCase
//! spelling, and picking one here would silently commit every binding consumer
//! to that guess. The exhaustive test pins today's behavior; it does not decide
//! what a token of that shape should become. Adding one is a decision, not a
//! transform.

use classic_vocabulary::Vocabulary;

/// Converts one canonical snake_case Vocabulary Token to its JavaScript spelling.
///
/// Each underscore is dropped and the character that followed it is uppercased.
/// The first character is left alone, which is what makes the result camelCase
/// rather than PascalCase.
pub(crate) fn js_token(token: &str) -> String {
    let mut spelling = String::with_capacity(token.len());
    let mut uppercase_next = false;

    for character in token.chars() {
        if character == '_' {
            uppercase_next = true;
            continue;
        }
        if uppercase_next {
            spelling.extend(character.to_uppercase());
            uppercase_next = false;
        } else {
            spelling.push(character);
        }
    }

    spelling
}

/// Resolves the variant whose JavaScript token spelling is exactly `token`.
///
/// This is a forward scan rather than a camel-to-snake inverse on purpose. An
/// inverse transform would be a second rule that could disagree with
/// [`js_token`] — it cannot know whether `schemaVersionTransition` came from
/// `schema_version_transition` or from some other spelling that happens to
/// camelize the same way. Comparing against the forward projection of each
/// known variant makes the two directions the same rule by construction.
pub(crate) fn from_js_token<T: Vocabulary>(token: &str) -> Option<T> {
    T::VARIANTS
        .iter()
        .copied()
        .find(|variant| js_token(variant.as_str()) == token)
}

#[cfg(test)]
#[path = "vocabulary_tests.rs"]
mod tests;
