//! The user-settings YAML oracle: settings documents as type-tagged JSON nodes.
//!
//! The pack format forbids floating-point JSON, and YAML formatting (quoting,
//! key order, flow vs. block) varies between writers, so a settings document
//! is compared as a tree of tagged nodes:
//!
//! - `{"type": "null"}`;
//! - `{"type": "string" | "boolean" | "integer", "value": v}`;
//! - `{"type": "real", "value": "<sign><digits>e<exponent>"}` with trailing
//!   zeros moved into the exponent (`1.50` → `"15e-1"`), or `"0"` for any
//!   zero (the sign of `-0.0` is dropped);
//! - `{"type": "mapping", "value": {key: node}}` (string keys only);
//! - `{"type": "sequence", "value": [node]}`.
//!
//! This reproduces the retired Python oracle (ruamel, YAML 1.2, reals as
//! `Decimal`) exactly, except for the divergences pinned in the sibling tests:
//! `yaml-rust2` reads underscored numerals (`1_000`) and `Null`/`NULL` as
//! strings. The product parses settings with `yaml-rust2` too.
//!
//! Parsing uses `yaml-rust2`'s `YamlLoader`, which already rejects duplicate
//! keys and undefined aliases. A self-referencing alias loads as
//! `Yaml::BadValue`, so rejecting `BadValue` also rejects alias cycles.

use serde_json::{Map, Value, json};
use yaml_rust2::{Yaml, YamlLoader};

/// Parses one YAML document into type-tagged, deterministic JSON nodes.
///
/// An empty stream (or one holding only comments) is `{"type": "null"}`,
/// as a YAML loader returns no value for it.
///
/// # Errors
///
/// Returns a message for content that is not UTF-8, is not valid YAML (which
/// includes duplicate keys and undefined aliases), holds more than one
/// document, or contains a node the oracle does not support: a bad value
/// (a self-referencing alias or a mistyped tagged scalar), a non-finite real,
/// or a mapping key that is not a string.
pub(crate) fn yaml_nodes(content: &[u8]) -> Result<Value, String> {
    let text = std::str::from_utf8(content)
        .map_err(|error| format!("User Settings YAML is not UTF-8: {error}"))?;
    let documents = YamlLoader::load_from_str(text)
        .map_err(|error| format!("invalid User Settings YAML observation: {error}"))?;
    match documents.as_slice() {
        [] => Ok(json!({"type": "null"})),
        [document] => node(document),
        _ => Err(
            "invalid User Settings YAML observation: expected a single document in the stream"
                .into(),
        ),
    }
}

/// Converts one loaded node.
fn node(value: &Yaml) -> Result<Value, String> {
    Ok(match value {
        Yaml::Null => json!({"type": "null"}),
        Yaml::String(text) => json!({"type": "string", "value": text}),
        Yaml::Boolean(flag) => json!({"type": "boolean", "value": flag}),
        Yaml::Integer(number) => json!({"type": "integer", "value": number}),
        Yaml::Real(text) => json!({"type": "real", "value": real(text)?}),
        Yaml::Array(items) => json!({
            "type": "sequence",
            "value": items.iter().map(node).collect::<Result<Vec<_>, _>>()?,
        }),
        Yaml::Hash(entries) => {
            let mut mapping = Map::new();
            for (key, value) in entries {
                let Yaml::String(key) = key else {
                    return Err("unsupported YAML node type: non-string mapping key".into());
                };
                mapping.insert(key.clone(), node(value)?);
            }
            json!({"type": "mapping", "value": mapping})
        }
        Yaml::Alias(_) | Yaml::BadValue => {
            return Err(
                "unsupported YAML node type: bad value (a cyclic alias or mistyped tag)".into(),
            );
        }
    })
}

/// Normalizes a real's authored text the way Python's `Decimal` tuple does.
///
/// The coefficient's digits keep every authored significant digit (no `f64`
/// rounding); trailing zeros move into the exponent, and zero is `"0"`.
fn real(text: &str) -> Result<String, String> {
    let unsupported = || format!("unsupported YAML real {text:?}");
    let (negative, unsigned) = match text.as_bytes().first() {
        Some(b'-') => (true, &text[1..]),
        Some(b'+') => (false, &text[1..]),
        _ => (false, text),
    };
    // `yaml-rust2` loads `.inf` and `.nan` (any case) as reals; the oracle
    // cannot represent them, as Python's `Decimal` check could not either.
    if unsigned.eq_ignore_ascii_case(".inf") || unsigned.eq_ignore_ascii_case(".nan") {
        return Err(format!("unsupported nonfinite YAML real {text:?}"));
    }
    let (mantissa, exponent) = match unsigned.find(['e', 'E']) {
        Some(index) => (
            &unsigned[..index],
            unsigned[index + 1..]
                .parse::<i64>()
                .map_err(|_| unsupported())?,
        ),
        None => (unsigned, 0),
    };
    let (whole, fraction) = mantissa.split_once('.').unwrap_or((mantissa, ""));
    let all_digits = |part: &str| part.bytes().all(|byte| byte.is_ascii_digit());
    if whole.is_empty() && fraction.is_empty() || !all_digits(whole) || !all_digits(fraction) {
        return Err(unsupported());
    }
    let fraction_length = i64::try_from(fraction.len()).map_err(|_| unsupported())?;
    let coefficient = format!("{whole}{fraction}");
    let significant = coefficient.trim_start_matches('0').trim_end_matches('0');
    if significant.is_empty() {
        return Ok("0".into());
    }
    let trailing = coefficient.len() - coefficient.trim_end_matches('0').len();
    let trailing = i64::try_from(trailing).map_err(|_| unsupported())?;
    let exponent = exponent
        .checked_sub(fraction_length)
        .and_then(|value| value.checked_add(trailing))
        .ok_or_else(unsupported)?;
    let sign = if negative { "-" } else { "" };
    Ok(format!("{sign}{significant}e{exponent}"))
}

#[cfg(test)]
#[path = "yaml_nodes_tests.rs"]
mod tests;
