//! YAML operations bridge for CXX FFI.
//!
//! Bridges `classic_yaml_core::YamlOperations` for file loading, parsing,
//! settings access via dot-notation keys, and cache management.
//!
//! Since CXX cannot pass `yaml_rust2::Yaml` objects across the FFI boundary,
//! YAML content is exchanged as strings and settings values are returned
//! as a `YamlValue` shared struct with type information.

use classic_yaml_core::YamlOperations;
use std::path::Path;
use yaml_rust2::Yaml;

/// Opaque wrapper around `YamlOperations` + a loaded YAML document.
pub struct YamlOps {
    ops: YamlOperations,
    doc: Option<Yaml>,
}

// ── Construction ────────────────────────────────────────────────────

fn yaml_ops_new() -> Box<YamlOps> {
    Box::new(YamlOps {
        ops: YamlOperations::new(),
        doc: None,
    })
}

// ── File operations ─────────────────────────────────────────────────

fn yaml_ops_load_file(ops: &mut YamlOps, path: &str) -> Result<(), String> {
    let yaml = ops
        .ops
        .load_yaml_file(Path::new(path))
        .map_err(|e| format!("{e}"))?;
    ops.doc = Some(yaml);
    Ok(())
}

fn yaml_ops_save_file(ops: &YamlOps, path: &str) -> Result<(), String> {
    let doc = ops.doc.as_ref().ok_or("No YAML document loaded")?;
    ops.ops
        .save_yaml_file(Path::new(path), doc)
        .map_err(|e| format!("{e}"))
}

// ── Parse/dump ──────────────────────────────────────────────────────

fn yaml_ops_parse(ops: &mut YamlOps, content: &str) -> Result<(), String> {
    let yaml = ops.ops.parse_yaml(content).map_err(|e| format!("{e}"))?;
    ops.doc = Some(yaml);
    Ok(())
}

fn yaml_ops_dump(ops: &YamlOps) -> Result<String, String> {
    let doc = ops.doc.as_ref().ok_or("No YAML document loaded")?;
    ops.ops.dump_yaml(doc).map_err(|e| format!("{e}"))
}

// ── Settings access ─────────────────────────────────────────────────

fn yaml_ops_get_string(ops: &YamlOps, key_path: &str, default_val: &str) -> String {
    match &ops.doc {
        Some(doc) => ops.ops.get_string_value(doc, key_path, default_val),
        None => default_val.to_string(),
    }
}

fn yaml_ops_get_vec(ops: &YamlOps, key_path: &str) -> Vec<String> {
    match &ops.doc {
        Some(doc) => ops.ops.get_vec_value(doc, key_path),
        None => Vec::new(),
    }
}

fn yaml_ops_get_setting_value(ops: &YamlOps, key_path: &str) -> ffi::YamlValue {
    match &ops.doc {
        Some(doc) => match ops.ops.get_setting(doc, key_path) {
            Some(yaml) => match yaml {
                Yaml::String(s) => ffi::YamlValue {
                    value: s,
                    is_null: false,
                    value_type: "string".to_string(),
                },
                Yaml::Boolean(b) => ffi::YamlValue {
                    value: b.to_string(),
                    is_null: false,
                    value_type: "bool".to_string(),
                },
                Yaml::Integer(i) => ffi::YamlValue {
                    value: i.to_string(),
                    is_null: false,
                    value_type: "integer".to_string(),
                },
                Yaml::Real(r) => ffi::YamlValue {
                    value: r,
                    is_null: false,
                    value_type: "real".to_string(),
                },
                Yaml::Null => ffi::YamlValue {
                    value: String::new(),
                    is_null: true,
                    value_type: "null".to_string(),
                },
                _ => ffi::YamlValue {
                    value: format!("{yaml:?}"),
                    is_null: false,
                    value_type: "complex".to_string(),
                },
            },
            None => ffi::YamlValue {
                value: String::new(),
                is_null: true,
                value_type: "null".to_string(),
            },
        },
        None => ffi::YamlValue {
            value: String::new(),
            is_null: true,
            value_type: "null".to_string(),
        },
    }
}

fn yaml_ops_set_string_setting(
    ops: &mut YamlOps,
    key_path: &str,
    value: &str,
) -> Result<(), String> {
    let doc = ops.doc.as_ref().ok_or("No YAML document loaded")?;
    let updated = ops
        .ops
        .set_setting(doc, key_path, Yaml::String(value.to_string()))
        .map_err(|e| format!("{e}"))?;
    ops.doc = Some(updated);
    Ok(())
}

fn yaml_ops_set_bool_setting(ops: &mut YamlOps, key_path: &str, value: bool) -> Result<(), String> {
    let doc = ops.doc.as_ref().ok_or("No YAML document loaded")?;
    let updated = ops
        .ops
        .set_setting(doc, key_path, Yaml::Boolean(value))
        .map_err(|e| format!("{e}"))?;
    ops.doc = Some(updated);
    Ok(())
}

fn yaml_ops_set_integer_setting(ops: &mut YamlOps, key_path: &str, value: i64) -> Result<(), String> {
    let doc = ops.doc.as_ref().ok_or("No YAML document loaded")?;
    let updated = ops
        .ops
        .set_setting(doc, key_path, Yaml::Integer(value))
        .map_err(|e| format!("{e}"))?;
    ops.doc = Some(updated);
    Ok(())
}

fn yaml_ops_set_vec_setting(ops: &mut YamlOps, key_path: &str, values: Vec<String>) -> Result<(), String> {
    let doc = ops.doc.as_ref().ok_or("No YAML document loaded")?;
    let yaml_array = Yaml::Array(values.into_iter().map(Yaml::String).collect());
    let updated = ops
        .ops
        .set_setting(doc, key_path, yaml_array)
        .map_err(|e| format!("{e}"))?;
    ops.doc = Some(updated);
    Ok(())
}

// ── Cache management ────────────────────────────────────────────────

fn yaml_ops_clear_cache(ops: &YamlOps) {
    ops.ops.clear_cache();
}

fn yaml_ops_cache_size(ops: &YamlOps) -> usize {
    let stats = ops.ops.get_cache_stats();
    stats.get("cached_files").copied().unwrap_or(0)
}

fn yaml_ops_has_document(ops: &YamlOps) -> bool {
    ops.doc.is_some()
}

#[cxx::bridge(namespace = "classic::yaml")]
mod ffi {
    /// Typed YAML value for cross-FFI returns.
    struct YamlValue {
        /// String representation of the value
        value: String,
        /// Whether the value is null/missing
        is_null: bool,
        /// Type hint: "string", "bool", "integer", "real", "null", "complex"
        value_type: String,
    }

    extern "Rust" {
        type YamlOps;

        // Construction
        fn yaml_ops_new() -> Box<YamlOps>;

        // File operations
        fn yaml_ops_load_file(ops: &mut YamlOps, path: &str) -> Result<()>;
        fn yaml_ops_save_file(ops: &YamlOps, path: &str) -> Result<()>;

        // Parse/dump
        fn yaml_ops_parse(ops: &mut YamlOps, content: &str) -> Result<()>;
        fn yaml_ops_dump(ops: &YamlOps) -> Result<String>;

        // Settings access
        fn yaml_ops_get_string(ops: &YamlOps, key_path: &str, default_val: &str) -> String;
        fn yaml_ops_get_vec(ops: &YamlOps, key_path: &str) -> Vec<String>;
        fn yaml_ops_get_setting_value(ops: &YamlOps, key_path: &str) -> YamlValue;
        fn yaml_ops_set_string_setting(
            ops: &mut YamlOps,
            key_path: &str,
            value: &str,
        ) -> Result<()>;
        fn yaml_ops_set_bool_setting(ops: &mut YamlOps, key_path: &str, value: bool) -> Result<()>;
        fn yaml_ops_set_integer_setting(ops: &mut YamlOps, key_path: &str, value: i64) -> Result<()>;
        fn yaml_ops_set_vec_setting(ops: &mut YamlOps, key_path: &str, values: Vec<String>) -> Result<()>;

        // Cache management
        fn yaml_ops_clear_cache(ops: &YamlOps);
        fn yaml_ops_cache_size(ops: &YamlOps) -> usize;
        fn yaml_ops_has_document(ops: &YamlOps) -> bool;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

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
    fn test_cache_management() {
        let ops = yaml_ops_new();
        assert_eq!(yaml_ops_cache_size(&ops), 0);
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
        // yaml-rust2 is very forgiving, but we can test a file load of nonexistent path
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
}
