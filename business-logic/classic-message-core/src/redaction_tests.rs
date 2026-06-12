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
