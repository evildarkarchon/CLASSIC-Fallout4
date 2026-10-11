//! Strict text scan of C++ frontend sources for bridge references.
//!
//! The scan is deliberately not a C++ parser. Comments and string/character
//! literals are blanked first (newlines kept, so line numbers survive), the
//! remainder is tokenized into identifiers, `::` and punctuation, and every
//! qualified name (`a::b::c`) is classified against the known bridge
//! namespaces. Exactly two forms count as a reference; any other form that
//! names a bridge namespace is reported as unsupported so the gate fails
//! closed instead of silently missing a caller.

use std::collections::HashMap;

/// A name that production code references inside a bridge namespace.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) struct Reference {
    /// Index into the namespace list passed to [`scan`].
    pub namespace: usize,
    /// The first name after the namespace (`f` in `classic::m::f::g`).
    pub name: String,
}

/// A reference to a bridge namespace in a form the matcher refuses to model.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) struct Unsupported {
    /// 1-based line of the offending form.
    pub line: usize,
    /// The form as written, normalized to single spaces, e.g.
    /// `using namespace classic::m`.
    pub form: String,
}

/// Everything one source file contributes to the gate.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub(super) struct FileScan {
    pub references: Vec<Reference>,
    pub unsupported: Vec<Unsupported>,
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
pub(super) fn blank_comments_and_strings(source: &str) -> String {
    let chars: Vec<char> = source.chars().collect();
    let mut out = String::with_capacity(source.len());
    let at = |index: usize| chars.get(index).copied();
    let blank =
        |out: &mut String, ch: char| out.push(if ch == '\n' || ch == '\r' { ch } else { ' ' });
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
                for _ in start..i {
                    out.push(' ');
                }
                i = blank_raw_string(&chars, i, &mut out);
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
            out.push(' ');
            i += 1;
            while i < chars.len() && chars[i] != ch && chars[i] != '\n' {
                if chars[i] == '\\' && i + 1 < chars.len() && chars[i + 1] != '\n' {
                    out.push(' ');
                    i += 1;
                }
                blank(&mut out, chars[i]);
                i += 1;
            }
            if i < chars.len() && chars[i] == ch {
                out.push(' ');
                i += 1;
            }
            continue;
        }
        out.push(ch);
        i += 1;
    }
    out
}

/// Blanks a raw string whose opening `"` is at `quote`; returns the index just
/// past it. An unterminated raw string blanks to the end of the input.
fn blank_raw_string(chars: &[char], quote: usize, out: &mut String) -> usize {
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
        out.push(if c == '\n' || c == '\r' { c } else { ' ' });
    }
    end
}

#[derive(Debug, Clone, PartialEq, Eq)]
enum Kind {
    Ident(String),
    Scope,
    Punct(char),
}

#[derive(Debug, Clone)]
struct Token {
    kind: Kind,
    line: usize,
}

/// Tokenizes blanked source into identifiers, `::` and single punctuation.
/// Numbers become a placeholder punctuation token; they never start a name.
fn tokenize(text: &str) -> Vec<Token> {
    let chars: Vec<char> = text.chars().collect();
    let mut tokens = Vec::new();
    let mut line = 1;
    let mut i = 0;
    while i < chars.len() {
        let ch = chars[i];
        if ch == '\n' {
            line += 1;
            i += 1;
        } else if ch.is_whitespace() {
            i += 1;
        } else if ch.is_alphabetic() || ch == '_' {
            let start = i;
            while i < chars.len() && (chars[i].is_alphanumeric() || chars[i] == '_') {
                i += 1;
            }
            tokens.push(Token {
                kind: Kind::Ident(chars[start..i].iter().collect()),
                line,
            });
        } else if ch.is_ascii_digit() {
            while i < chars.len()
                && (chars[i].is_alphanumeric()
                    || chars[i] == '_'
                    || chars[i] == '.'
                    || chars[i] == '\'')
            {
                i += 1;
            }
            tokens.push(Token {
                kind: Kind::Punct('0'),
                line,
            });
        } else if ch == ':' && chars.get(i + 1) == Some(&':') {
            tokens.push(Token {
                kind: Kind::Scope,
                line,
            });
            i += 2;
        } else {
            tokens.push(Token {
                kind: Kind::Punct(ch),
                line,
            });
            i += 1;
        }
    }
    tokens
}

/// A maximal qualified name `[::] a :: b :: c` starting at token `start`.
struct Chain {
    start: usize,
    /// Index of the first token after the chain.
    end: usize,
    global: bool,
    segments: Vec<String>,
}

impl Chain {
    fn text(&self) -> String {
        let joined = self.segments.join("::");
        if self.global {
            format!("::{joined}")
        } else {
            joined
        }
    }
}

fn ident(tokens: &[Token], index: usize) -> Option<&str> {
    match tokens.get(index).map(|token| &token.kind) {
        Some(Kind::Ident(name)) => Some(name),
        _ => None,
    }
}

fn is_punct(tokens: &[Token], index: Option<usize>, want: char) -> bool {
    index
        .and_then(|i| tokens.get(i))
        .is_some_and(|token| token.kind == Kind::Punct(want))
}

/// C++ keywords. A keyword never starts a qualified name, so in
/// `return ::classic::m::f();` the `::` begins a new, globally qualified chain
/// instead of extending `return`.
const KEYWORDS: &[&str] = &[
    "alignas",
    "alignof",
    "asm",
    "auto",
    "bool",
    "break",
    "case",
    "catch",
    "char",
    "class",
    "co_await",
    "co_return",
    "co_yield",
    "concept",
    "const",
    "consteval",
    "constexpr",
    "constinit",
    "const_cast",
    "continue",
    "decltype",
    "default",
    "delete",
    "do",
    "double",
    "dynamic_cast",
    "else",
    "enum",
    "explicit",
    "export",
    "extern",
    "float",
    "for",
    "friend",
    "goto",
    "if",
    "inline",
    "int",
    "long",
    "mutable",
    "namespace",
    "new",
    "noexcept",
    "operator",
    "private",
    "protected",
    "public",
    "register",
    "reinterpret_cast",
    "requires",
    "return",
    "short",
    "signed",
    "sizeof",
    "static",
    "static_cast",
    "struct",
    "switch",
    "template",
    "throw",
    "typedef",
    "typename",
    "union",
    "unsigned",
    "using",
    "virtual",
    "void",
    "volatile",
    "while",
];

fn chain_at(tokens: &[Token], start: usize) -> Option<Chain> {
    let global = tokens[start].kind == Kind::Scope;
    let mut i = if global { start + 1 } else { start };
    let first = ident(tokens, i)?;
    let mut segments = vec![first.to_owned()];
    i += 1;
    let extendable = global || !KEYWORDS.contains(&first);
    while extendable && tokens.get(i).is_some_and(|token| token.kind == Kind::Scope) {
        let Some(name) = ident(tokens, i + 1) else {
            break;
        };
        segments.push(name.to_owned());
        i += 2;
    }
    Some(Chain {
        start,
        end: i,
        global,
        segments,
    })
}

/// How a chain reaches a bridge namespace.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Form {
    /// `classic::<module>::...` (optionally with a leading `::`).
    Qualified,
    /// `<alias>::...` through `namespace <alias> = classic::<module>;`.
    Alias,
    /// `<module>::...` relying on enclosing-namespace lookup inside `classic`.
    Relative,
}

/// Resolves `chain` to (namespace index, form, number of segments the
/// namespace part consumed). The longest qualified match wins.
fn resolve(
    chain: &Chain,
    namespaces: &[Vec<String>],
    aliases: &HashMap<String, usize>,
) -> Option<(usize, Form, usize)> {
    let segments = &chain.segments;
    let qualified = namespaces
        .iter()
        .enumerate()
        .filter(|(_, namespace)| segments.starts_with(namespace))
        .max_by_key(|(_, namespace)| namespace.len());
    if let Some((index, namespace)) = qualified {
        return Some((index, Form::Qualified, namespace.len()));
    }
    if chain.global {
        return None;
    }
    if let Some(&index) = aliases.get(&segments[0]) {
        return Some((index, Form::Alias, 1));
    }
    namespaces
        .iter()
        .enumerate()
        .filter(|(_, namespace)| namespace.len() > 1 && segments.starts_with(&namespace[1..]))
        .max_by_key(|(_, namespace)| namespace.len())
        .map(|(index, namespace)| (index, Form::Relative, namespace.len() - 1))
}

/// Iterates over every maximal chain in `tokens`, skipping chains that follow
/// `>` or `)` with a leading `::` (`Foo<T>::bar`), which are dependent member
/// names rather than global qualification.
fn chains(tokens: &[Token]) -> Vec<Chain> {
    let mut found = Vec::new();
    let mut i = 0;
    while i < tokens.len() {
        match chain_at(tokens, i) {
            Some(chain) => {
                let dependent = chain.global
                    && (is_punct(tokens, i.checked_sub(1), '>')
                        || is_punct(tokens, i.checked_sub(1), ')'));
                i = chain.end;
                if !dependent {
                    found.push(chain);
                }
            }
            None => i += 1,
        }
    }
    found
}

/// Scans one C++ source file (comments and literals are blanked here) for references to `namespaces` (each a
/// list of segments, e.g. `["classic", "scanner"]`).
///
/// Accepted forms are `classic::<module>::name` and `<alias>::name` after a
/// `namespace <alias> = classic::<module>;` in the same file. Unsupported:
/// `using namespace` or `using` declarations naming a bridge namespace,
/// reopening one (`namespace classic::<module> {`), aliasing anything but the
/// full namespace, naming the namespace with no member, and relative
/// `<module>::name` lookup without an alias. Namespaces that are not bridge
/// namespaces (`classic::gui`, ...) are ignored entirely.
pub(super) fn scan(source: &str, namespaces: &[Vec<String>]) -> FileScan {
    let tokens = tokenize(&blank_comments_and_strings(source));
    let all = chains(&tokens);
    let previous_ident = |chain: &Chain, back: usize| {
        chain
            .start
            .checked_sub(back)
            .and_then(|i| ident(&tokens, i))
    };
    let previous_punct = |chain: &Chain, back: usize, want: char| {
        is_punct(&tokens, chain.start.checked_sub(back), want)
    };

    // Pass 1: `namespace <alias> = classic::<module>;` declarations.
    let mut aliases = HashMap::new();
    for chain in &all {
        let is_alias_target = previous_punct(chain, 1, '=')
            && previous_ident(chain, 2).is_some()
            && previous_ident(chain, 3) == Some("namespace");
        if !is_alias_target {
            continue;
        }
        if let Some((index, Form::Qualified, consumed)) =
            resolve(chain, namespaces, &HashMap::new())
            && consumed == chain.segments.len()
        {
            let alias = previous_ident(chain, 2).expect("checked above").to_owned();
            aliases.insert(alias, index);
        }
    }

    let mut scan = FileScan::default();
    for chain in &all {
        let Some((namespace, form, consumed)) = resolve(chain, namespaces, &aliases) else {
            continue;
        };
        let context = Context {
            using: previous_ident(chain, 1) == Some("using"),
            using_namespace: previous_ident(chain, 1) == Some("namespace")
                && previous_ident(chain, 2) == Some("using"),
            namespace_keyword: previous_ident(chain, 1) == Some("namespace"),
            alias_name: is_punct(&tokens, Some(chain.end), '='),
            alias_target: (previous_punct(chain, 1, '=')
                && previous_ident(chain, 3) == Some("namespace"))
            .then(|| previous_ident(chain, 2).unwrap_or("?").to_owned()),
        };
        match classify(chain, form, consumed, &context) {
            Classified::Ignore => {}
            Classified::Reference(name) => scan.references.push(Reference { namespace, name }),
            Classified::Unsupported(form) => scan.unsupported.push(Unsupported {
                line: tokens[chain.start].line,
                form,
            }),
        }
    }
    scan
}

/// The tokens around a chain that decide which declaration form it is in.
struct Context {
    /// Preceded by `using` (a using-declaration).
    using: bool,
    /// Preceded by `using namespace` (a using-directive).
    using_namespace: bool,
    /// Preceded by `namespace` (a namespace definition or alias name).
    namespace_keyword: bool,
    /// Followed by `=` (the alias name in `namespace X = ...`).
    alias_name: bool,
    /// `Some(alias)` when the chain is the target of `namespace alias = ...`.
    alias_target: Option<String>,
}

enum Classified {
    Ignore,
    Reference(String),
    Unsupported(String),
}

/// Decides what a chain that resolves to a bridge namespace means in its
/// `context`; see [`scan`] for the accepted and unsupported forms.
fn classify(chain: &Chain, form: Form, consumed: usize, context: &Context) -> Classified {
    let text = chain.text();
    if context.using_namespace {
        return Classified::Unsupported(format!("using namespace {text}"));
    }
    if context.namespace_keyword {
        // `namespace X = ...` introduces a new alias name here, which is not a
        // reference; anything else reopens the bridge namespace.
        return if context.alias_name {
            Classified::Ignore
        } else {
            Classified::Unsupported(format!("namespace {text}"))
        };
    }
    if let Some(alias) = &context.alias_target {
        // Pass 1 already recorded full-namespace aliases; aliasing an alias or
        // a nested name would hide callers from the matcher.
        return if form == Form::Qualified && consumed == chain.segments.len() {
            Classified::Ignore
        } else {
            Classified::Unsupported(format!("namespace {alias} = {text}"))
        };
    }
    if context.using {
        return Classified::Unsupported(format!("using {text}"));
    }
    if chain.segments.len() == 1 {
        // A lone identifier (`path`, `config`) is an ordinary name, not a
        // namespace reference, outside the declaration forms above.
        return Classified::Ignore;
    }
    if form == Form::Relative {
        return Classified::Unsupported(format!(
            "{text} (relative lookup without a namespace alias)"
        ));
    }
    match chain.segments.get(consumed) {
        Some(name) => Classified::Reference(name.clone()),
        None => Classified::Unsupported(format!("{text} (namespace named without a member)")),
    }
}

#[cfg(test)]
#[path = "cpp_tests.rs"]
mod tests;
