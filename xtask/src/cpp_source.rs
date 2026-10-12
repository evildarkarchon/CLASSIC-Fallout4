//! C++ source preprocessing shared by the text-scanning gates.
//!
//! Both helpers replace what they remove with spaces and keep every newline,
//! so a byte offset or line number in the output points at the same place in
//! the original file. Neither is a C++ parser: they only know enough of the
//! lexical grammar (comments, string and character literals, raw strings,
//! digit separators) to tell code from non-code.
//!
//! - [`blank_comments_and_strings`] is for gates that match identifiers, where
//!   text inside a literal must never count (`cxx-bridge-gate`).
//! - [`blank_comments`] is for gates whose banned patterns are themselves
//!   string literals, such as a raw settings key (`user-settings-ownership`).
//!   It still lexes literals, so a `//` or `/*` inside a string is not taken
//!   for a comment, but it copies them through unchanged.

/// What the blanker removes besides comments.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Mode {
    /// Blank comments and string/character literals.
    CommentsAndStrings,
    /// Blank comments only; literals are copied through verbatim.
    CommentsOnly,
}

/// Raw-string prefixes (`R"delim(...)delim"`) recognised by the blanker.
const RAW_PREFIXES: [&str; 5] = ["R", "u8R", "uR", "UR", "LR"];

/// Replaces every comment and string/character literal in `source` with
/// spaces, keeping newlines so later line numbers match the original file.
///
/// Handles `//` comments (including backslash-newline continuation), `/* */`
/// comments, escaped `"..."`/`'...'` literals with encoding prefixes, raw
/// strings `R"delim(...)delim"`, and C++14 digit separators (`1'000`), which
/// must not be mistaken for character literals. An unterminated literal ends
/// at the end of its line, so one malformed literal cannot blank the file.
pub(crate) fn blank_comments_and_strings(source: &str) -> String {
    blank(source, Mode::CommentsAndStrings)
}

/// Replaces every comment in `source` with spaces, keeping newlines, and
/// copies string and character literals through unchanged.
///
/// Literals are still recognised with the same rules as
/// [`blank_comments_and_strings`], so `"https://example"` or `"/*"` inside a
/// literal does not start a comment.
pub(crate) fn blank_comments(source: &str) -> String {
    blank(source, Mode::CommentsOnly)
}

/// The shared lexer behind both public helpers; `mode` decides whether
/// literal text is blanked or copied.
fn blank(source: &str, mode: Mode) -> String {
    let chars: Vec<char> = source.chars().collect();
    let mut out = String::with_capacity(source.len());
    let at = |index: usize| chars.get(index).copied();
    let blank =
        |out: &mut String, ch: char| out.push(if ch == '\n' || ch == '\r' { ch } else { ' ' });
    // Literal text goes through this: blanked or kept depending on `mode`.
    let literal = |out: &mut String, ch: char| match mode {
        Mode::CommentsAndStrings => blank(out, ch),
        Mode::CommentsOnly => out.push(ch),
    };
    let mut i = 0;
    while i < chars.len() {
        let ch = chars[i];
        if ch == '/' && at(i + 1) == Some('/') {
            while i < chars.len() && chars[i] != '\n' {
                // A trailing backslash splices the next physical line into the
                // comment (translation phase 2), so keep blanking past it.
                if chars[i] == '\\'
                    && (at(i + 1) == Some('\n')
                        || (at(i + 1) == Some('\r') && at(i + 2) == Some('\n')))
                {
                    out.push(' ');
                    i += 1;
                    while i < chars.len() && chars[i] != '\n' {
                        blank(&mut out, chars[i]);
                        i += 1;
                    }
                    if i < chars.len() {
                        out.push('\n');
                        i += 1;
                    }
                    continue;
                }
                blank(&mut out, chars[i]);
                i += 1;
            }
            continue;
        }
        if ch == '/' && at(i + 1) == Some('*') {
            out.push_str("  ");
            i += 2;
            while i < chars.len() && !(chars[i] == '*' && at(i + 1) == Some('/')) {
                blank(&mut out, chars[i]);
                i += 1;
            }
            if i < chars.len() {
                out.push_str("  ");
                i += 2;
            }
            continue;
        }
        if ch.is_alphabetic() || ch == '_' {
            let start = i;
            while i < chars.len() && (chars[i].is_alphanumeric() || chars[i] == '_') {
                i += 1;
            }
            let word: String = chars[start..i].iter().collect();
            if at(i) == Some('"') && RAW_PREFIXES.contains(&word.as_str()) {
                for &c in &chars[start..i] {
                    literal(&mut out, c);
                }
                i = raw_string(&chars, i, &mut out, mode);
            } else {
                out.push_str(&word);
            }
            continue;
        }
        if ch.is_ascii_digit() || (ch == '.' && at(i + 1).is_some_and(|next| next.is_ascii_digit()))
        {
            // A pp-number may contain `'` digit separators; consume it whole.
            while i < chars.len() {
                let c = chars[i];
                let separator =
                    c == '\'' && at(i + 1).is_some_and(|next| next.is_ascii_alphanumeric());
                let exponent_sign = (c == '+' || c == '-')
                    && i > 0
                    && matches!(chars[i - 1], 'e' | 'E' | 'p' | 'P');
                if c.is_ascii_alphanumeric() || c == '_' || c == '.' || separator || exponent_sign {
                    out.push(c);
                    i += 1;
                } else {
                    break;
                }
            }
            continue;
        }
        if ch == '"' || ch == '\'' {
            literal(&mut out, ch);
            i += 1;
            while i < chars.len() && chars[i] != ch && chars[i] != '\n' {
                if chars[i] == '\\' && i + 1 < chars.len() && chars[i + 1] != '\n' {
                    literal(&mut out, '\\');
                    i += 1;
                }
                literal(&mut out, chars[i]);
                i += 1;
            }
            if i < chars.len() && chars[i] == ch {
                literal(&mut out, ch);
                i += 1;
            }
            continue;
        }
        out.push(ch);
        i += 1;
    }
    out
}

/// Handles a raw string whose opening `"` is at `quote` per `mode`; returns
/// the index just past it. An unterminated raw string runs to the end of the
/// input.
fn raw_string(chars: &[char], quote: usize, out: &mut String, mode: Mode) -> usize {
    let mut i = quote + 1;
    let mut delimiter = String::new();
    while i < chars.len() && chars[i] != '(' && chars[i] != '\n' {
        delimiter.push(chars[i]);
        i += 1;
    }
    let closing: Vec<char> = format!("){delimiter}\"").chars().collect();
    let mut end = chars.len();
    let mut j = i;
    while j < chars.len() {
        if chars[j..].starts_with(&closing) {
            end = j + closing.len();
            break;
        }
        j += 1;
    }
    for &c in &chars[quote..end] {
        out.push(match mode {
            Mode::CommentsOnly => c,
            Mode::CommentsAndStrings if c == '\n' || c == '\r' => c,
            Mode::CommentsAndStrings => ' ',
        });
    }
    end
}

#[cfg(test)]
#[path = "cpp_source_tests.rs"]
mod tests;
