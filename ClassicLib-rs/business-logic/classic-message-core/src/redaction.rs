//! Redaction helpers for structured logging contract fields.
use std::collections::BTreeMap;

const SECRET_MASK: &str = "[REDACTED]";
const PATH_MASK: &str = "<path-redacted>";

const SECRET_KEY_TOKENS: [&str; 11] = [
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "session",
    "credential",
    "private_key",
];

const PATH_KEY_TOKENS: [&str; 7] = [
    "path",
    "file",
    "filename",
    "filepath",
    "directory",
    "dir",
    "location",
];

const SECRET_VALUE_MARKERS: [&str; 5] = ["token=", "password=", "secret=", "api_key=", "apikey="];

fn contains_token(haystack: &str, tokens: &[&str]) -> bool {
    tokens.iter().any(|token| haystack.contains(token))
}

fn normalized(text: &str) -> String {
    text.trim().to_ascii_lowercase()
}

/// Redact a contract field value based on field name and content.
#[must_use]
pub fn redact_field_value(field_name: &str, value: &str) -> String {
    let field_name = normalized(field_name);
    if contains_token(&field_name, &SECRET_KEY_TOKENS) {
        return SECRET_MASK.to_string();
    }
    if contains_token(&field_name, &PATH_KEY_TOKENS) {
        return PATH_MASK.to_string();
    }

    let value_normalized = normalized(value);
    if contains_token(&value_normalized, &SECRET_VALUE_MARKERS) {
        return SECRET_MASK.to_string();
    }

    value.to_string()
}

/// Redact all contract context fields.
#[must_use]
pub fn redact_contract_fields(fields: &BTreeMap<String, String>) -> BTreeMap<String, String> {
    fields
        .iter()
        .map(|(key, value)| (key.clone(), redact_field_value(key, value)))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_redact_secret_key() {
        assert_eq!(
            redact_field_value("api_key", "abc123"),
            "[REDACTED]".to_string()
        );
    }

    #[test]
    fn test_redact_path_key() {
        assert_eq!(
            redact_field_value("game_path", r"C:\Users\alice\Documents\My Games\Fallout4"),
            "<path-redacted>".to_string()
        );
    }

    #[test]
    fn test_redact_secret_marker_in_value() {
        assert_eq!(
            redact_field_value("details", "token=abc123"),
            "[REDACTED]".to_string()
        );
    }

    #[test]
    fn test_preserve_non_sensitive_value() {
        assert_eq!(
            redact_field_value("contract", "startup_all"),
            "startup_all".to_string()
        );
    }

    #[test]
    fn test_redact_contract_fields_map() {
        let mut fields = BTreeMap::new();
        fields.insert("contract".to_string(), "startup_all".to_string());
        fields.insert("api_key".to_string(), "secret-value".to_string());

        let redacted = redact_contract_fields(&fields);
        assert_eq!(redacted.get("contract"), Some(&"startup_all".to_string()));
        assert_eq!(redacted.get("api_key"), Some(&"[REDACTED]".to_string()));
    }
}
