use super::*;
use serial_test::serial;
use std::io::Write;
use tempfile::NamedTempFile;

// ── YAML ops tests (pre-existing) ──────────────────────────────

#[test]
fn test_yaml_ops_new() {
    let ops = yaml_ops_new();
    assert!(!yaml_ops_has_document(&ops));
}

#[test]
fn test_parse_and_dump_round_trip() {
    let mut ops = yaml_ops_new();
    let yaml_str = "game: Fallout4\nversion: 1.10.163\n";
    yaml_ops_parse(&mut ops, yaml_str).unwrap();
    assert!(yaml_ops_has_document(&ops));

    let dumped = yaml_ops_dump(&ops).unwrap();
    assert!(dumped.contains("Fallout4"));
    assert!(dumped.contains("1.10.163"));
}

#[test]
fn test_get_string_setting() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "game: Fallout4\n").unwrap();
    assert_eq!(yaml_ops_get_string(&ops, "game", "default"), "Fallout4");
}

#[test]
fn test_get_string_default_when_missing() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "other: value\n").unwrap();
    assert_eq!(yaml_ops_get_string(&ops, "game", "default"), "default");
}

#[test]
fn test_get_string_no_document() {
    let ops = yaml_ops_new();
    assert_eq!(yaml_ops_get_string(&ops, "game", "default"), "default");
}

#[test]
fn test_get_setting_value_types() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "str_val: hello\nbool_val: true\nint_val: 42\n").unwrap();

    let str_v = yaml_ops_get_setting_value(&ops, "str_val");
    assert_eq!(str_v.value, "hello");
    assert_eq!(str_v.value_type, "string");
    assert!(!str_v.is_null);

    let bool_v = yaml_ops_get_setting_value(&ops, "bool_val");
    assert_eq!(bool_v.value, "true");
    assert_eq!(bool_v.value_type, "bool");

    let int_v = yaml_ops_get_setting_value(&ops, "int_val");
    assert_eq!(int_v.value, "42");
    assert_eq!(int_v.value_type, "integer");
}

#[test]
fn test_get_setting_value_missing() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "a: 1\n").unwrap();
    let missing = yaml_ops_get_setting_value(&ops, "nonexistent");
    assert!(missing.is_null);
    assert_eq!(missing.value_type, "null");
}

#[test]
fn test_set_string_setting() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "game: Fallout4\n").unwrap();
    yaml_ops_set_string_setting(&mut ops, "game", "Skyrim").unwrap();
    assert_eq!(yaml_ops_get_string(&ops, "game", ""), "Skyrim");
}

#[test]
fn test_set_bool_setting() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "enabled: false\n").unwrap();
    yaml_ops_set_bool_setting(&mut ops, "enabled", true).unwrap();
    let val = yaml_ops_get_setting_value(&ops, "enabled");
    assert_eq!(val.value, "true");
    assert_eq!(val.value_type, "bool");
}

#[test]
fn test_get_vec() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "items:\n  - a\n  - b\n  - c\n").unwrap();
    let vec = yaml_ops_get_vec(&ops, "items");
    assert_eq!(vec, vec!["a", "b", "c"]);
}

#[test]
fn test_get_vec_missing() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "other: value\n").unwrap();
    let vec = yaml_ops_get_vec(&ops, "nonexistent");
    assert!(vec.is_empty());
}

#[test]
#[serial]
fn test_cache_management() {
    let ops = yaml_ops_new();
    yaml_ops_clear_cache(&ops); // Clear first to ensure a clean state
    assert_eq!(yaml_ops_cache_size(&ops), 0);
    let stats = yaml_ops_cache_stats(&ops);
    assert_eq!(stats.size, 0);
    assert_eq!(stats.capacity, 128);
    yaml_ops_clear_cache(&ops); // Should not panic on empty cache
}

#[test]
fn test_dump_no_document_error() {
    let ops = yaml_ops_new();
    assert!(yaml_ops_dump(&ops).is_err());
}

#[test]
fn test_save_no_document_error() {
    let ops = yaml_ops_new();
    assert!(yaml_ops_save_file(&ops, "test.yaml").is_err());
}

#[test]
fn test_set_setting_no_document_error() {
    let mut ops = yaml_ops_new();
    assert!(yaml_ops_set_string_setting(&mut ops, "key", "val").is_err());
}

#[test]
fn test_invalid_yaml_parse() {
    let mut ops = yaml_ops_new();
    let result = yaml_ops_load_file(&mut ops, "nonexistent_file_12345.yaml");
    assert!(result.is_err());
}

#[test]
fn test_nested_settings() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(
        &mut ops,
        "settings:\n  fcx_mode: true\n  show_values: false\n",
    )
    .unwrap();
    let fcx = yaml_ops_get_setting_value(&ops, "settings.fcx_mode");
    assert_eq!(fcx.value, "true");
    assert_eq!(fcx.value_type, "bool");
}

#[test]
fn test_set_integer_setting() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "max_scans: 4\n").unwrap();
    yaml_ops_set_integer_setting(&mut ops, "max_scans", 8).unwrap();
    let val = yaml_ops_get_setting_value(&ops, "max_scans");
    assert_eq!(val.value, "8");
    assert_eq!(val.value_type, "integer");
}

#[test]
fn test_set_integer_setting_no_document() {
    let mut ops = yaml_ops_new();
    assert!(yaml_ops_set_integer_setting(&mut ops, "key", 1).is_err());
}

#[test]
fn test_set_vec_setting() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "items:\n  - old\n").unwrap();
    yaml_ops_set_vec_setting(
        &mut ops,
        "items",
        vec!["a".to_string(), "b".to_string(), "c".to_string()],
    )
    .unwrap();
    let vec = yaml_ops_get_vec(&ops, "items");
    assert_eq!(vec, vec!["a", "b", "c"]);
}

#[test]
fn test_set_vec_setting_empty() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "items:\n  - old\n").unwrap();
    yaml_ops_set_vec_setting(&mut ops, "items", vec![]).unwrap();
    let vec = yaml_ops_get_vec(&ops, "items");
    assert!(vec.is_empty());
}

#[test]
fn test_set_vec_setting_no_document() {
    let mut ops = yaml_ops_new();
    assert!(yaml_ops_set_vec_setting(&mut ops, "key", vec!["a".to_string()]).is_err());
}

// ── Settings cache ops tests (D-09 — new) ──────────────────────

fn make_settings_yaml(content: &str) -> NamedTempFile {
    let mut file = NamedTempFile::new().unwrap();
    file.write_all(content.as_bytes()).unwrap();
    file.flush().unwrap();
    file
}

#[test]
#[serial]
fn test_settings_load_sync() {
    settings_clear_cache();
    let file = make_settings_yaml("key: value\nnumber: 42\n");
    let count = settings_load_sync("t_sync", &file.path().display().to_string()).unwrap();
    assert_eq!(count, 1);
    assert!(settings_is_cached("t_sync"));
    settings_clear_cache();
}

#[test]
#[serial]
fn test_settings_load_async_blocking() {
    settings_clear_cache();
    let file = make_settings_yaml("key: value\n");
    let count =
        settings_load_async_blocking("t_async", &file.path().display().to_string()).unwrap();
    assert_eq!(count, 1);
    assert!(settings_is_cached("t_async"));
    settings_clear_cache();
}

#[test]
#[serial]
fn test_settings_load_batch_sync() {
    settings_clear_cache();
    let f1 = make_settings_yaml("a: 1\n");
    let f2 = make_settings_yaml("b: 2\n");
    let paths = vec![
        f1.path().display().to_string(),
        f2.path().display().to_string(),
    ];
    let count = settings_load_batch_sync(paths).unwrap();
    assert_eq!(count, 2);
    settings_clear_cache();
}

#[test]
#[serial]
fn test_settings_load_batch_async_blocking() {
    settings_clear_cache();
    let f1 = make_settings_yaml("a: 1\n");
    let f2 = make_settings_yaml("b: 2\n");
    let paths = vec![
        f1.path().display().to_string(),
        f2.path().display().to_string(),
    ];
    let count = settings_load_batch_async_blocking(paths).unwrap();
    assert_eq!(count, 2);
    settings_clear_cache();
}

#[test]
#[serial]
fn test_settings_cache_stats_and_size_on_empty_cache() {
    settings_clear_cache();
    settings_reset_cache_stats();
    let stats = settings_cache_stats();
    assert_eq!(stats.hits, 0);
    assert_eq!(stats.misses, 0);
    assert_eq!(stats.size, 0);
    assert_eq!(stats.capacity, 64);
    assert_eq!(settings_cache_size(), 0);
    assert!(settings_cache_keys().is_empty());
}

#[test]
#[serial]
fn test_settings_is_cached_and_invalidate() {
    settings_clear_cache();
    assert!(!settings_is_cached("nope"));
    assert!(!settings_invalidate("nope"));

    let file = make_settings_yaml("x: 1\n");
    settings_load_sync("inv_key", &file.path().display().to_string()).unwrap();
    assert!(settings_is_cached("inv_key"));
    assert!(settings_invalidate("inv_key"));
    assert!(!settings_is_cached("inv_key"));
    settings_clear_cache();
}

#[test]
#[serial]
fn test_settings_clear_cache_is_idempotent() {
    settings_clear_cache();
    settings_clear_cache();
    assert_eq!(settings_cache_size(), 0);
}

// ── Validator tests (D-09 — new) ───────────────────────────────

#[test]
fn test_settings_validate_structure_happy_path() {
    let issues = settings_validate_structure("CLASSIC_Settings:\n  VR Mode: false\n").unwrap();
    assert!(issues.is_empty());
}

#[test]
fn test_settings_validate_structure_non_mapping_root_is_error() {
    let issues = settings_validate_structure("42").unwrap();
    assert_eq!(issues.len(), 1);
    assert_eq!(issues[0].severity, "error");
}

#[test]
fn test_settings_validate_structure_empty_string() {
    // Empty yaml -> no documents -> null-document error
    let issues = settings_validate_structure("").unwrap();
    assert_eq!(issues.len(), 1);
    assert_eq!(issues[0].severity, "error");
}

#[test]
fn test_settings_validate_value_int_happy() {
    assert!(settings_validate_value("42", "int").unwrap());
    assert!(settings_validate_value("42", "integer").unwrap());
    assert!(!settings_validate_value("abc", "int").unwrap());
}

#[test]
fn test_settings_validate_value_unknown_type_errors() {
    let err = settings_validate_value("42", "quux").unwrap_err();
    assert!(err.contains("unknown setting type"));
}

#[test]
fn test_settings_validate_value_all_canonical_tokens() {
    assert!(settings_validate_value("1", "bool").unwrap());
    assert!(settings_validate_value("1", "boolean").unwrap());
    assert!(settings_validate_value("3.14", "float").unwrap());
    assert!(settings_validate_value("3.14", "double").unwrap());
    assert!(settings_validate_value("/tmp", "path").unwrap());
    assert!(settings_validate_value("anything", "string").unwrap());
    assert!(settings_validate_value("anything", "str").unwrap());
}

#[test]
fn test_settings_validate_value_case_insensitive() {
    assert!(settings_validate_value("42", "INT").unwrap());
    assert!(settings_validate_value("yes", "Bool").unwrap());
}

#[test]
fn test_settings_coerce_value_bool_yes() {
    let out = settings_coerce_value("yes", "bool").unwrap();
    assert_eq!(out.kind, "bool");
    assert!(out.bool_val);
}

#[test]
fn test_settings_coerce_value_path_vs_string_discriminator() {
    let p = settings_coerce_value("/tmp/x", "path").unwrap();
    assert_eq!(p.kind, "path");
    assert_eq!(p.string_val, "/tmp/x");

    let s = settings_coerce_value("/tmp/x", "string").unwrap();
    assert_eq!(s.kind, "string");
    assert_eq!(s.string_val, "/tmp/x");
}

#[test]
fn test_settings_coerce_value_int_and_float() {
    let i = settings_coerce_value("42", "int").unwrap();
    assert_eq!(i.kind, "int");
    assert_eq!(i.int_val, 42);

    let f = settings_coerce_value("3.125", "float").unwrap();
    assert_eq!(f.kind, "float");
    assert!((f.float_val - 3.125).abs() < 1e-9);
}

#[test]
fn test_settings_coerce_value_unknown_type_errors() {
    assert!(settings_coerce_value("42", "list").is_err());
}

#[test]
fn test_user_settings_update_preferences_bridge_is_fail_closed_with_diagnostics() {
    let root = tempfile::tempdir().unwrap();
    let content = "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Update Check: invalid\n";
    std::fs::write(root.path().join("CLASSIC Settings.yaml"), content).unwrap();

    let preferences = user_settings_open_update_preferences(&root.path().display().to_string());

    assert!(!preferences.update_check_enabled);
    assert_eq!(preferences.update_check_origin, "degraded_fallback");
    assert_eq!(preferences.source_location, "canonical");
    assert_eq!(preferences.classification, "current");
    assert!(preferences.has_schema_version);
    assert_eq!(preferences.schema_major, 1);
    assert_eq!(preferences.schema_minor, 0);
    assert_eq!(preferences.commit_eligibility, "eligible");
    assert_eq!(preferences.diagnostics.len(), 1);
    assert_eq!(preferences.diagnostics[0].code, "invalid_type_update_check");
    assert!(!preferences.diagnostics[0].message.is_empty());
    assert!(preferences.has_original_content);
    assert_eq!(preferences.original_content, content.as_bytes());
    assert!(preferences.revision.starts_with("sha256:"));
}
