//! Strict JSON for the conformance protocol.
//!
//! - [`parse_strict`] accepts exactly the JSON the protocol allows: duplicate
//!   object keys, floating-point lexemes (`1.0`, `1e5`), the non-finite
//!   extensions (`NaN`, `Infinity`), a byte-order mark and lone surrogates all
//!   fail. Every value's line is recorded under its JSON pointer, so a later
//!   semantic finding can point at the line it is about.
//! - [`canonical_bytes`] is the protocol's canonical form: keys sorted by code
//!   point, `,`/`:` separators with no whitespace, non-ASCII written as UTF-8,
//!   and control characters escaped (`\uXXXX` in lowercase hex, except the
//!   short escapes `\b \f \n \r \t`).
//! - [`FramedDigest`] is the protocol's type-tagged, length-prefixed SHA-256.
//!   The frame layout is part of the run-plan and receipt protocol; the bytes
//!   need not match the retired Python engine's.

use std::collections::HashMap;
use std::fmt;

use serde_json::{Map, Number, Value};
use sha2::{Digest, Sha256};

use crate::digest;

/// A strictly parsed JSON document with the line of every value.
#[derive(Debug, Clone)]
pub struct Document {
    value: Value,
    lines: HashMap<String, usize>,
}

impl Document {
    /// The parsed value.
    pub fn value(&self) -> &Value {
        &self.value
    }

    /// The 1-based line where the value at the RFC 6901 `pointer` starts.
    ///
    /// Falls back to the nearest recorded ancestor, then to line 1, so a
    /// finding about a missing member still points somewhere sensible.
    pub fn line(&self, pointer: &str) -> usize {
        let mut current = pointer;
        loop {
            if let Some(line) = self.lines.get(current) {
                return *line;
            }
            match current.rfind('/') {
                Some(index) => current = &current[..index],
                None => return 1,
            }
        }
    }
}

/// Why a document is not strict JSON, and the line where parsing stopped.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct JsonError {
    /// 1-based line of the offending token.
    pub line: usize,
    /// Human-readable reason.
    pub message: String,
}

impl fmt::Display for JsonError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "line {}: {}", self.line, self.message)
    }
}

impl std::error::Error for JsonError {}

/// Appends one RFC 6901 reference token to `parent` (`~` and `/` escaped).
pub fn pointer(parent: &str, token: impl fmt::Display) -> String {
    let token = token.to_string().replace('~', "~0").replace('/', "~1");
    format!("{parent}/{token}")
}

/// Parses `text` as strict protocol JSON.
///
/// # Errors
///
/// Returns the first violation: a syntax error, a duplicate object key, a
/// floating-point or non-finite number, an integer outside the 64-bit range,
/// an unescaped control character, a lone surrogate, a byte-order mark, or
/// trailing content after the value.
pub fn parse_strict(text: &str) -> Result<Document, JsonError> {
    let mut parser = Parser {
        bytes: text.as_bytes(),
        text,
        position: 0,
        line: 1,
        lines: HashMap::new(),
    };
    if text.starts_with('\u{feff}') {
        return Err(parser.error("a byte-order mark is not allowed"));
    }
    parser.skip_whitespace();
    let value = parser.value(String::new())?;
    parser.skip_whitespace();
    if parser.position != parser.bytes.len() {
        return Err(parser.error("trailing content after the JSON value"));
    }
    Ok(Document {
        value,
        lines: parser.lines,
    })
}

/// A recursive-descent parser over UTF-8 text that tracks the current line.
struct Parser<'a> {
    bytes: &'a [u8],
    text: &'a str,
    position: usize,
    line: usize,
    lines: HashMap<String, usize>,
}

impl Parser<'_> {
    /// A [`JsonError`] at the current line.
    fn error(&self, message: impl Into<String>) -> JsonError {
        JsonError {
            line: self.line,
            message: message.into(),
        }
    }

    fn peek(&self) -> Option<u8> {
        self.bytes.get(self.position).copied()
    }

    /// Skips JSON whitespace, counting newlines so later values get the right line.
    fn skip_whitespace(&mut self) {
        while let Some(byte) = self.peek() {
            match byte {
                b' ' | b'\t' | b'\r' => self.position += 1,
                b'\n' => {
                    self.position += 1;
                    self.line += 1;
                }
                _ => break,
            }
        }
    }

    /// Consumes `byte`, or fails naming it.
    fn expect(&mut self, byte: u8) -> Result<(), JsonError> {
        if self.peek() == Some(byte) {
            self.position += 1;
            Ok(())
        } else {
            Err(self.error(format!("expected `{}`", byte as char)))
        }
    }

    /// Parses one value at `pointer` and records its starting line.
    fn value(&mut self, pointer: String) -> Result<Value, JsonError> {
        self.lines.insert(pointer.clone(), self.line);
        match self.peek() {
            Some(b'{') => self.object(&pointer),
            Some(b'[') => self.array(&pointer),
            Some(b'"') => self.string().map(Value::String),
            Some(b'-' | b'0'..=b'9') => self.number(),
            Some(b't') => self.literal("true", Value::Bool(true)),
            Some(b'f') => self.literal("false", Value::Bool(false)),
            Some(b'n') => self.literal("null", Value::Null),
            Some(b'N' | b'I') => Err(self.error(
                "floating-point JSON value is forbidden: non-finite token (NaN or Infinity)",
            )),
            Some(_) => Err(self.error("expected a JSON value")),
            None => Err(self.error("unexpected end of input")),
        }
    }

    /// Consumes the keyword `word` (`true`, `false` or `null`) and returns `value`.
    fn literal(&mut self, word: &str, value: Value) -> Result<Value, JsonError> {
        if self.bytes[self.position..].starts_with(word.as_bytes()) {
            self.position += word.len();
            Ok(value)
        } else {
            Err(self.error("expected a JSON value"))
        }
    }

    /// Parses an object at `pointer`, rejecting duplicate keys and non-string keys.
    /// Each member value is parsed at its own pointer so its line is recorded.
    fn object(&mut self, pointer: &str) -> Result<Value, JsonError> {
        self.expect(b'{')?;
        let mut map = Map::new();
        self.skip_whitespace();
        if self.peek() == Some(b'}') {
            self.position += 1;
            return Ok(Value::Object(map));
        }
        loop {
            self.skip_whitespace();
            if self.peek() != Some(b'"') {
                return Err(self.error("expected a string object key"));
            }
            let key = self.string()?;
            if map.contains_key(&key) {
                return Err(self.error(format!("duplicate JSON object key: {key:?}")));
            }
            self.skip_whitespace();
            self.expect(b':')?;
            self.skip_whitespace();
            let child = self.value(self::pointer(pointer, &key))?;
            map.insert(key, child);
            self.skip_whitespace();
            match self.peek() {
                Some(b',') => self.position += 1,
                Some(b'}') => {
                    self.position += 1;
                    return Ok(Value::Object(map));
                }
                _ => return Err(self.error("expected `,` or `}` in object")),
            }
        }
    }

    /// Parses an array at `pointer`; each element is parsed at its own pointer so
    /// its line is recorded.
    fn array(&mut self, pointer: &str) -> Result<Value, JsonError> {
        self.expect(b'[')?;
        let mut items = Vec::new();
        self.skip_whitespace();
        if self.peek() == Some(b']') {
            self.position += 1;
            return Ok(Value::Array(items));
        }
        loop {
            self.skip_whitespace();
            let child = self.value(self::pointer(pointer, items.len()))?;
            items.push(child);
            self.skip_whitespace();
            match self.peek() {
                Some(b',') => self.position += 1,
                Some(b']') => {
                    self.position += 1;
                    return Ok(Value::Array(items));
                }
                _ => return Err(self.error("expected `,` or `]` in array")),
            }
        }
    }

    /// Parses an integer that fits `i64` or `u64`. A fraction or exponent is
    /// rejected: the protocol forbids floating-point values.
    fn number(&mut self) -> Result<Value, JsonError> {
        let start = self.position;
        if self.peek() == Some(b'-') {
            self.position += 1;
        }
        match self.peek() {
            Some(b'0') => self.position += 1,
            Some(b'1'..=b'9') => {
                while matches!(self.peek(), Some(b'0'..=b'9')) {
                    self.position += 1;
                }
            }
            _ => return Err(self.error("invalid number")),
        }
        if matches!(self.peek(), Some(b'.' | b'e' | b'E')) {
            return Err(self.error(
                "floating-point JSON value is forbidden; use an integer or an explicitly formatted string",
            ));
        }
        let lexeme = &self.text[start..self.position];
        if let Ok(value) = lexeme.parse::<i64>() {
            return Ok(Value::Number(Number::from(value)));
        }
        if let Ok(value) = lexeme.parse::<u64>() {
            return Ok(Value::Number(Number::from(value)));
        }
        Err(self.error(format!("integer {lexeme} is outside the 64-bit range")))
    }

    /// Parses a string literal, decoding escapes and rejecting unescaped control
    /// characters.
    fn string(&mut self) -> Result<String, JsonError> {
        self.expect(b'"')?;
        let mut out = String::new();
        loop {
            let Some(byte) = self.peek() else {
                return Err(self.error("unterminated string"));
            };
            match byte {
                b'"' => {
                    self.position += 1;
                    return Ok(out);
                }
                b'\\' => {
                    self.position += 1;
                    let escape = self
                        .peek()
                        .ok_or_else(|| self.error("unterminated escape"))?;
                    self.position += 1;
                    match escape {
                        b'"' => out.push('"'),
                        b'\\' => out.push('\\'),
                        b'/' => out.push('/'),
                        b'b' => out.push('\u{8}'),
                        b'f' => out.push('\u{c}'),
                        b'n' => out.push('\n'),
                        b'r' => out.push('\r'),
                        b't' => out.push('\t'),
                        b'u' => out.push(self.unicode_escape()?),
                        _ => return Err(self.error("invalid string escape")),
                    }
                }
                0x00..=0x1f => return Err(self.error("unescaped control character in string")),
                _ => {
                    // Copy one whole UTF-8 character; `text` is valid UTF-8, so
                    // a character boundary always follows a non-ASCII lead byte.
                    let rest = &self.text[self.position..];
                    let character = rest.chars().next().expect("non-empty rest");
                    out.push(character);
                    self.position += character.len_utf8();
                }
            }
        }
    }

    /// Reads the four hex digits of a `\u` escape.
    fn hex4(&mut self) -> Result<u32, JsonError> {
        let digits = self
            .text
            .get(self.position..self.position + 4)
            .ok_or_else(|| self.error("truncated \\u escape"))?;
        let value =
            u32::from_str_radix(digits, 16).map_err(|_| self.error("invalid \\u escape"))?;
        self.position += 4;
        Ok(value)
    }

    /// Decodes a `\u` escape (after the `\u`), combining a surrogate pair and
    /// rejecting a lone surrogate.
    fn unicode_escape(&mut self) -> Result<char, JsonError> {
        let first = self.hex4()?;
        let code = if (0xD800..0xDC00).contains(&first) {
            if !self.bytes[self.position..].starts_with(b"\\u") {
                return Err(self.error("lone surrogate in \\u escape"));
            }
            self.position += 2;
            let second = self.hex4()?;
            if !(0xDC00..0xE000).contains(&second) {
                return Err(self.error("lone surrogate in \\u escape"));
            }
            0x10000 + ((first - 0xD800) << 10) + (second - 0xDC00)
        } else if (0xDC00..0xE000).contains(&first) {
            return Err(self.error("lone surrogate in \\u escape"));
        } else {
            first
        };
        char::from_u32(code).ok_or_else(|| self.error("invalid \\u escape"))
    }
}

/// Serializes `value` in the protocol's canonical form.
///
/// Object keys are sorted here explicitly rather than relying on
/// `serde_json::Map` ordering, because another crate in the workspace build
/// can turn on `serde_json/preserve_order` through feature unification.
pub fn canonical_bytes(value: &Value) -> Vec<u8> {
    let mut out = String::new();
    write_canonical(value, &mut out);
    out.into_bytes()
}

/// Appends the canonical form of `value` to `out`: no whitespace, object keys
/// in sorted order, integers as written, and strings escaped by
/// [`write_string`].
fn write_canonical(value: &Value, out: &mut String) {
    match value {
        Value::Null => out.push_str("null"),
        Value::Bool(true) => out.push_str("true"),
        Value::Bool(false) => out.push_str("false"),
        Value::Number(number) => out.push_str(&number.to_string()),
        Value::String(text) => write_string(text, out),
        Value::Array(items) => {
            out.push('[');
            for (index, item) in items.iter().enumerate() {
                if index > 0 {
                    out.push(',');
                }
                write_canonical(item, out);
            }
            out.push(']');
        }
        Value::Object(map) => {
            let mut keys: Vec<&String> = map.keys().collect();
            keys.sort();
            out.push('{');
            for (index, key) in keys.into_iter().enumerate() {
                if index > 0 {
                    out.push(',');
                }
                write_string(key, out);
                out.push(':');
                write_canonical(&map[key], out);
            }
            out.push('}');
        }
    }
}

/// Appends `text` as a JSON string: `"` and `\` escaped, the short escapes for
/// backspace, form feed, newline, carriage return and tab, `\u00XX` for other
/// control characters, and everything else (including non-ASCII) as is.
fn write_string(text: &str, out: &mut String) {
    out.push('"');
    for character in text.chars() {
        match character {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\u{8}' => out.push_str("\\b"),
            '\u{c}' => out.push_str("\\f"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            control if u32::from(control) < 0x20 => {
                out.push_str(&format!("\\u{:04x}", u32::from(control)));
            }
            other => out.push(other),
        }
    }
    out.push('"');
}

/// The protocol's framed SHA-256: each frame is
/// `u64_be(len(tag)) || tag || u64_be(len(payload)) || payload`.
///
/// The first frame is always `contract` with the digest's contract name, so
/// digests of different kinds (expectation, source, run plan) never collide.
pub struct FramedDigest {
    hasher: Sha256,
}

impl FramedDigest {
    /// Starts a digest whose first frame is `contract` = `contract`.
    pub fn new(contract: &str) -> Self {
        let mut digest = Self {
            hasher: Sha256::new(),
        };
        digest.frame("contract", contract.as_bytes());
        digest
    }

    /// Adds one tagged, length-prefixed frame.
    pub fn frame(&mut self, tag: &str, payload: &[u8]) {
        self.hasher.update((tag.len() as u64).to_be_bytes());
        self.hasher.update(tag.as_bytes());
        self.hasher.update((payload.len() as u64).to_be_bytes());
        self.hasher.update(payload);
    }

    /// Finishes the digest as `sha256:<lowercase hex>`.
    pub fn finish(self) -> String {
        format!("sha256:{}", digest::hex(&self.hasher.finalize()))
    }
}

#[cfg(test)]
#[path = "json_tests.rs"]
mod tests;
