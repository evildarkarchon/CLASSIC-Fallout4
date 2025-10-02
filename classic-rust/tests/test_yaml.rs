//! Tests for the YAML module
//!
//! This test suite covers:
//! - Basic YAML parsing and dumping
//! - Python type conversions (null, bool, number, string, list, dict)
//! - File operations with caching
//! - Settings navigation (get/set with dot notation)
//! - Cache management
//! - Error handling

use std::fs;
use tempfile::TempDir;

// Unit tests that don't require PyO3
#[test]
fn test_yaml_format_config_defaults() {
    use classic_core::yaml::YamlFormatConfig;

    let config = YamlFormatConfig::default();
    assert!(config.preserve_quotes);
    assert_eq!(config.width, 120);
    assert_eq!(config.indent_mapping, 2);
    assert_eq!(config.indent_sequence, 4);
    assert_eq!(config.indent_offset, 2);
}

// Integration tests that require PyO3
#[cfg(test)]
mod integration_tests {
    use super::*;
    use pyo3::prelude::*;
    use pyo3::types::{PyDict, PyList};

    // Helper to create YAML ops instance via Python
    fn with_yaml_ops<F>(test_fn: F)
    where
        F: FnOnce(Python, Bound<PyAny>),
    {
        pyo3::Python::initialize();
        Python::attach(|py| {
            // Create the Rust module and get the class
            let module = pyo3::types::PyModule::new(py, "classic_core_yaml").unwrap();
            classic_core::yaml::init_module(&module).unwrap();

            let yaml_class = module.getattr("RustYamlOperations").unwrap();
            let yaml_ops = yaml_class.call0().unwrap();

            test_fn(py, yaml_ops);
        });
    }

    #[test]
    fn test_rust_yaml_operations_creation() {
        with_yaml_ops(|_py, _yaml_ops| {
            // If we got here, creation succeeded
            assert!(true);
        });
    }

    // ===== Basic Parsing Tests =====

    #[test]
    fn test_parse_yaml_simple_types() {
        with_yaml_ops(|_py, yaml_ops| {
            // Null
            let null_yaml = "null";
            let result = yaml_ops.call_method1("parse_yaml", (null_yaml,)).unwrap();
            assert!(result.is_none());

            // Boolean
            let bool_yaml = "true";
            let result = yaml_ops.call_method1("parse_yaml", (bool_yaml,)).unwrap();
            assert_eq!(result.extract::<bool>().unwrap(), true);

            // Integer
            let int_yaml = "42";
            let result = yaml_ops.call_method1("parse_yaml", (int_yaml,)).unwrap();
            assert_eq!(result.extract::<i64>().unwrap(), 42);

            // Float
            let float_yaml = "3.14";
            let result = yaml_ops.call_method1("parse_yaml", (float_yaml,)).unwrap();
            assert!((result.extract::<f64>().unwrap() - 3.14).abs() < 0.001);

            // String
            let string_yaml = "\"hello world\"";
            let result = yaml_ops.call_method1("parse_yaml", (string_yaml,)).unwrap();
            assert_eq!(result.extract::<String>().unwrap(), "hello world");
        });
    }

    #[test]
    fn test_parse_yaml_list() {
        with_yaml_ops(|_py, yaml_ops| {
            let list_yaml = r#"
- item1
- item2
- item3
"#;
            let result = yaml_ops.call_method1("parse_yaml", (list_yaml,)).unwrap();
            let list = result.downcast::<PyList>().unwrap();

            assert_eq!(list.len(), 3);
            assert_eq!(list.get_item(0).unwrap().extract::<String>().unwrap(), "item1");
            assert_eq!(list.get_item(1).unwrap().extract::<String>().unwrap(), "item2");
            assert_eq!(list.get_item(2).unwrap().extract::<String>().unwrap(), "item3");
        });
    }

    #[test]
    fn test_parse_yaml_dict() {
        with_yaml_ops(|_py, yaml_ops| {
            let dict_yaml = r#"
key1: value1
key2: 42
key3: true
"#;
            let result = yaml_ops.call_method1("parse_yaml", (dict_yaml,)).unwrap();
            let dict = result.downcast::<PyDict>().unwrap();

            assert_eq!(dict.len(), 3);
            assert_eq!(
                dict.get_item("key1").unwrap().unwrap().extract::<String>().unwrap(),
                "value1"
            );
            assert_eq!(
                dict.get_item("key2").unwrap().unwrap().extract::<i64>().unwrap(),
                42
            );
            assert_eq!(
                dict.get_item("key3").unwrap().unwrap().extract::<bool>().unwrap(),
                true
            );
        });
    }

    #[test]
    fn test_parse_yaml_nested_structure() {
        with_yaml_ops(|_py, yaml_ops| {
            let nested_yaml = r#"
database:
  host: localhost
  port: 5432
  credentials:
    username: admin
    password: secret
servers:
  - name: server1
    ip: 192.168.1.1
  - name: server2
    ip: 192.168.1.2
"#;
            let result = yaml_ops.call_method1("parse_yaml", (nested_yaml,)).unwrap();
            let dict = result.downcast::<PyDict>().unwrap();

            // Test nested dict
            let database_bound = dict.get_item("database").unwrap().unwrap();
            let database = database_bound.downcast::<PyDict>().unwrap();
            assert_eq!(
                database.get_item("host").unwrap().unwrap().extract::<String>().unwrap(),
                "localhost"
            );

            let credentials_bound = database.get_item("credentials").unwrap().unwrap();
            let credentials = credentials_bound.downcast::<PyDict>().unwrap();
            assert_eq!(
                credentials.get_item("username").unwrap().unwrap().extract::<String>().unwrap(),
                "admin"
            );

            // Test list of dicts
            let servers_bound = dict.get_item("servers").unwrap().unwrap();
            let servers = servers_bound.downcast::<PyList>().unwrap();
            assert_eq!(servers.len(), 2);

            let server1_bound = servers.get_item(0).unwrap();
            let server1 = server1_bound.downcast::<PyDict>().unwrap();
            assert_eq!(
                server1.get_item("name").unwrap().unwrap().extract::<String>().unwrap(),
                "server1"
            );
        });
    }

    #[test]
    fn test_parse_yaml_invalid() {
        with_yaml_ops(|_py, yaml_ops| {
            // Invalid YAML syntax
            let invalid_yaml = "{ invalid: yaml: content";
            let result = yaml_ops.call_method1("parse_yaml", (invalid_yaml,));
            assert!(result.is_err());

            // Verify error message contains "Failed to parse YAML"
            let err = result.unwrap_err();
            let err_msg = format!("{}", err);
            assert!(err_msg.contains("Failed to parse YAML"));
        });
    }

    // ===== Dumping Tests =====

    #[test]
    fn test_dump_yaml_simple_types() {
        with_yaml_ops(|py, yaml_ops| {
            // Boolean
            let bool_obj = true.into_pyobject(py).unwrap();
            let yaml_str = yaml_ops.call_method1("dump_yaml", (bool_obj,)).unwrap()
                .extract::<String>().unwrap();
            assert!(yaml_str.contains("true"));

            // Integer
            let int_obj = 42.into_pyobject(py).unwrap();
            let yaml_str = yaml_ops.call_method1("dump_yaml", (int_obj,)).unwrap()
                .extract::<String>().unwrap();
            assert!(yaml_str.contains("42"));

            // String
            let str_obj = "hello".into_pyobject(py).unwrap();
            let yaml_str = yaml_ops.call_method1("dump_yaml", (str_obj,)).unwrap()
                .extract::<String>().unwrap();
            assert!(yaml_str.contains("hello"));
        });
    }

    #[test]
    fn test_dump_yaml_complex() {
        with_yaml_ops(|py, yaml_ops| {
            // Create a complex structure
            let dict = PyDict::new(py);
            dict.set_item("name", "test").unwrap();
            dict.set_item("count", 42).unwrap();

            let list = PyList::new(py, &[1, 2, 3]).unwrap();
            dict.set_item("items", list).unwrap();

            let yaml_str = yaml_ops.call_method1("dump_yaml", (dict,)).unwrap()
                .extract::<String>().unwrap();

            // Verify it can be parsed back
            let reparsed = yaml_ops.call_method1("parse_yaml", (&yaml_str,)).unwrap();
            let reparsed_dict = reparsed.downcast::<PyDict>().unwrap();

            assert_eq!(
                reparsed_dict.get_item("name").unwrap().unwrap().extract::<String>().unwrap(),
                "test"
            );
            assert_eq!(
                reparsed_dict.get_item("count").unwrap().unwrap().extract::<i64>().unwrap(),
                42
            );
        });
    }

    #[test]
    fn test_roundtrip_yaml() {
        with_yaml_ops(|_py, yaml_ops| {
            let original_yaml = r#"
settings:
  enabled: true
  timeout: 30
  servers:
    - localhost
    - 127.0.0.1
"#;

            // Parse, dump, and parse again
            let parsed1 = yaml_ops.call_method1("parse_yaml", (original_yaml,)).unwrap();
            let dumped = yaml_ops.call_method1("dump_yaml", (parsed1,)).unwrap()
                .extract::<String>().unwrap();
            let parsed2 = yaml_ops.call_method1("parse_yaml", (&dumped,)).unwrap();

            // Verify structure is preserved
            let dict1 = parsed2.downcast::<PyDict>().unwrap();
            let settings_bound = dict1.get_item("settings").unwrap().unwrap();
            let settings = settings_bound.downcast::<PyDict>().unwrap();

            assert_eq!(
                settings.get_item("enabled").unwrap().unwrap().extract::<bool>().unwrap(),
                true
            );
            assert_eq!(
                settings.get_item("timeout").unwrap().unwrap().extract::<i64>().unwrap(),
                30
            );
        });
    }

    // ===== File Operations Tests =====

    #[test]
    fn test_load_yaml_file() {
        with_yaml_ops(|_py, yaml_ops| {
            let temp_dir = TempDir::new().unwrap();
            let yaml_file = temp_dir.path().join("test.yaml");

            let yaml_content = r#"
name: test_file
version: 1.0
features:
  - feature1
  - feature2
"#;
            fs::write(&yaml_file, yaml_content).unwrap();

            // Load file
            let result = yaml_ops.call_method1("load_yaml_file", (yaml_file.to_str().unwrap(),)).unwrap();
            let dict = result.downcast::<PyDict>().unwrap();

            assert_eq!(
                dict.get_item("name").unwrap().unwrap().extract::<String>().unwrap(),
                "test_file"
            );

            let features_bound = dict.get_item("features").unwrap().unwrap();
            let features = features_bound.downcast::<PyList>().unwrap();
            assert_eq!(features.len(), 2);
        });
    }

    #[test]
    fn test_load_yaml_file_nonexistent() {
        with_yaml_ops(|_py, yaml_ops| {
            let result = yaml_ops.call_method1("load_yaml_file", ("/nonexistent/path/file.yaml",));
            assert!(result.is_err());

            let err_msg = format!("{}", result.unwrap_err());
            assert!(err_msg.contains("Failed to read file"));
        });
    }

    #[test]
    fn test_load_yaml_file_invalid_content() {
        with_yaml_ops(|_py, yaml_ops| {
            let temp_dir = TempDir::new().unwrap();
            let yaml_file = temp_dir.path().join("invalid.yaml");

            // Write invalid YAML
            fs::write(&yaml_file, "{ invalid: yaml: syntax").unwrap();

            let result = yaml_ops.call_method1("load_yaml_file", (yaml_file.to_str().unwrap(),));
            assert!(result.is_err());

            let err_msg = format!("{}", result.unwrap_err());
            assert!(err_msg.contains("Failed to parse YAML"));
        });
    }

    #[test]
    fn test_save_yaml_file() {
        with_yaml_ops(|py, yaml_ops| {
            let temp_dir = TempDir::new().unwrap();
            let yaml_file = temp_dir.path().join("output.yaml");

            // Create data to save
            let dict = PyDict::new(py);
            dict.set_item("title", "Saved YAML").unwrap();
            dict.set_item("count", 100).unwrap();

            // Save file
            yaml_ops.call_method1("save_yaml_file", (yaml_file.to_str().unwrap(), dict)).unwrap();

            // Verify file exists and content is correct
            assert!(yaml_file.exists());

            let content = fs::read_to_string(&yaml_file).unwrap();
            assert!(content.contains("title"));
            assert!(content.contains("Saved YAML"));
            assert!(content.contains("100"));
        });
    }

    #[test]
    fn test_save_yaml_file_atomic_write() {
        with_yaml_ops(|py, yaml_ops| {
            let temp_dir = TempDir::new().unwrap();
            let yaml_file = temp_dir.path().join("atomic.yaml");
            let temp_file = yaml_file.with_extension("yaml.tmp");

            // Save file
            let dict = PyDict::new(py);
            dict.set_item("test", "data").unwrap();

            yaml_ops.call_method1("save_yaml_file", (yaml_file.to_str().unwrap(), dict)).unwrap();

            // Verify final file exists
            assert!(yaml_file.exists());

            // Verify temp file was cleaned up
            assert!(!temp_file.exists());
        });
    }

    #[test]
    fn test_save_yaml_file_cache_invalidation() {
        with_yaml_ops(|py, yaml_ops| {
            let temp_dir = TempDir::new().unwrap();
            let yaml_file = temp_dir.path().join("cache_test.yaml");

            // Create and load file (caches it)
            let original_dict = PyDict::new(py);
            original_dict.set_item("version", 1).unwrap();
            yaml_ops.call_method1("save_yaml_file", (yaml_file.to_str().unwrap(), original_dict)).unwrap();

            let _cached = yaml_ops.call_method1("load_yaml_file", (yaml_file.to_str().unwrap(),)).unwrap();

            // Save new data (should invalidate cache)
            let new_dict = PyDict::new(py);
            new_dict.set_item("version", 2).unwrap();
            yaml_ops.call_method1("save_yaml_file", (yaml_file.to_str().unwrap(), new_dict)).unwrap();

            // Load again - should get new data, not cached
            let reloaded = yaml_ops.call_method1("load_yaml_file", (yaml_file.to_str().unwrap(),)).unwrap();
            let reloaded_dict = reloaded.downcast::<PyDict>().unwrap();

            assert_eq!(
                reloaded_dict.get_item("version").unwrap().unwrap().extract::<i64>().unwrap(),
                2
            );
        });
    }

    // ===== Caching Tests =====

    #[test]
    fn test_yaml_file_caching() {
        with_yaml_ops(|_py, yaml_ops| {
            let temp_dir = TempDir::new().unwrap();
            let yaml_file = temp_dir.path().join("cached.yaml");

            // Create file
            fs::write(&yaml_file, "cached: true").unwrap();

            // First load - cache miss
            let _result1 = yaml_ops.call_method1("load_yaml_file", (yaml_file.to_str().unwrap(),)).unwrap();

            let stats1_bound = yaml_ops.call_method0("get_cache_stats").unwrap();
            let stats1 = stats1_bound.downcast::<PyDict>().unwrap();
            let cached_files_1 = stats1.get_item("cached_files").unwrap().unwrap().extract::<usize>().unwrap();
            assert!(cached_files_1 >= 1);

            // Second load - cache hit (no file modification)
            let _result2 = yaml_ops.call_method1("load_yaml_file", (yaml_file.to_str().unwrap(),)).unwrap();

            // Cache stats should be same or higher
            let stats2_bound = yaml_ops.call_method0("get_cache_stats").unwrap();
            let stats2 = stats2_bound.downcast::<PyDict>().unwrap();
            let cached_files_2 = stats2.get_item("cached_files").unwrap().unwrap().extract::<usize>().unwrap();
            assert!(cached_files_2 >= 1);
        });
    }

    #[test]
    fn test_cache_modification_detection() {
        with_yaml_ops(|_py, yaml_ops| {
            let temp_dir = TempDir::new().unwrap();
            let yaml_file = temp_dir.path().join("modified.yaml");

            // Create and load file
            fs::write(&yaml_file, "version: 1").unwrap();
            let result1 = yaml_ops.call_method1("load_yaml_file", (yaml_file.to_str().unwrap(),)).unwrap();
            let dict1 = result1.downcast::<PyDict>().unwrap();
            assert_eq!(
                dict1.get_item("version").unwrap().unwrap().extract::<i64>().unwrap(),
                1
            );

            // Wait a bit and modify file
            std::thread::sleep(std::time::Duration::from_millis(10));
            fs::write(&yaml_file, "version: 2").unwrap();

            // Load again - should detect modification and reload
            let result2 = yaml_ops.call_method1("load_yaml_file", (yaml_file.to_str().unwrap(),)).unwrap();
            let dict2 = result2.downcast::<PyDict>().unwrap();
            assert_eq!(
                dict2.get_item("version").unwrap().unwrap().extract::<i64>().unwrap(),
                2
            );
        });
    }

    #[test]
    fn test_clear_cache() {
        with_yaml_ops(|_py, yaml_ops| {
            let temp_dir = TempDir::new().unwrap();

            // Load multiple files to populate cache
            for i in 0..3 {
                let yaml_file = temp_dir.path().join(format!("file{}.yaml", i));
                fs::write(&yaml_file, format!("index: {}", i)).unwrap();
                let _result = yaml_ops.call_method1("load_yaml_file", (yaml_file.to_str().unwrap(),)).unwrap();
            }

            let stats_before_bound = yaml_ops.call_method0("get_cache_stats").unwrap();
            let stats_before = stats_before_bound.downcast::<PyDict>().unwrap();
            let cached_files_before = stats_before.get_item("cached_files").unwrap().unwrap().extract::<usize>().unwrap();
            assert!(cached_files_before >= 3);

            // Clear cache
            yaml_ops.call_method0("clear_cache").unwrap();

            let stats_after_bound = yaml_ops.call_method0("get_cache_stats").unwrap();
            let stats_after = stats_after_bound.downcast::<PyDict>().unwrap();
            let cached_files_after = stats_after.get_item("cached_files").unwrap().unwrap().extract::<usize>().unwrap();
            assert_eq!(cached_files_after, 0);
            let total_bytes = stats_after.get_item("total_bytes").unwrap().unwrap().extract::<usize>().unwrap();
            assert_eq!(total_bytes, 0);
        });
    }

    #[test]
    fn test_cache_stats() {
        with_yaml_ops(|_py, yaml_ops| {
            let temp_dir = TempDir::new().unwrap();

            // Clear cache first
            yaml_ops.call_method0("clear_cache").unwrap();

            let stats_empty_bound = yaml_ops.call_method0("get_cache_stats").unwrap();
            let stats_empty = stats_empty_bound.downcast::<PyDict>().unwrap();
            assert_eq!(
                stats_empty.get_item("cached_files").unwrap().unwrap().extract::<usize>().unwrap(),
                0
            );
            assert_eq!(
                stats_empty.get_item("total_bytes").unwrap().unwrap().extract::<usize>().unwrap(),
                0
            );

            // Add files to cache
            let content = "test: data\nmore: content";
            let yaml_file = temp_dir.path().join("stats_test.yaml");
            fs::write(&yaml_file, content).unwrap();

            let _result = yaml_ops.call_method1("load_yaml_file", (yaml_file.to_str().unwrap(),)).unwrap();

            let stats_filled_bound = yaml_ops.call_method0("get_cache_stats").unwrap();
            let stats_filled = stats_filled_bound.downcast::<PyDict>().unwrap();
            assert_eq!(
                stats_filled.get_item("cached_files").unwrap().unwrap().extract::<usize>().unwrap(),
                1
            );
            assert!(
                stats_filled.get_item("total_bytes").unwrap().unwrap().extract::<usize>().unwrap() > 0
            );
        });
    }

    // ===== Settings Navigation Tests =====

    #[test]
    fn test_get_setting_simple() {
        with_yaml_ops(|py, yaml_ops| {
            let dict = PyDict::new(py);
            dict.set_item("key1", "value1").unwrap();
            dict.set_item("key2", 42).unwrap();

            // Get existing key
            let result = yaml_ops.call_method1("get_setting", (dict, "key1")).unwrap();
            assert!(!result.is_none());
            assert_eq!(result.extract::<String>().unwrap(), "value1");

            // Get non-existent key
            let dict2 = PyDict::new(py);
            dict2.set_item("key1", "value1").unwrap();
            let result = yaml_ops.call_method1("get_setting", (dict2, "missing")).unwrap();
            assert!(result.is_none());
        });
    }

    #[test]
    fn test_get_setting_nested() {
        with_yaml_ops(|_py, yaml_ops| {
            let yaml_content = r#"
database:
  connection:
    host: localhost
    port: 5432
  pool:
    size: 10
"#;
            let data = yaml_ops.call_method1("parse_yaml", (yaml_content,)).unwrap();

            // Navigate nested path
            let result = yaml_ops.call_method1("get_setting", (data.clone(), "database.connection.host")).unwrap();
            assert!(!result.is_none());
            assert_eq!(result.extract::<String>().unwrap(), "localhost");

            // Navigate to integer value
            let result = yaml_ops.call_method1("get_setting", (data.clone(), "database.pool.size")).unwrap();
            assert!(!result.is_none());
            assert_eq!(result.extract::<i64>().unwrap(), 10);

            // Non-existent nested path
            let result = yaml_ops.call_method1("get_setting", (data, "database.connection.timeout")).unwrap();
            assert!(result.is_none());
        });
    }

    #[test]
    fn test_get_setting_non_mapping() {
        with_yaml_ops(|_py, yaml_ops| {
            let yaml_content = r#"
settings:
  value: 42
"#;
            let data = yaml_ops.call_method1("parse_yaml", (yaml_content,)).unwrap();

            // Try to navigate through non-mapping value
            let result = yaml_ops.call_method1("get_setting", (data, "settings.value.nested")).unwrap();
            assert!(result.is_none());
        });
    }

    #[test]
    fn test_set_setting_simple() {
        with_yaml_ops(|py, yaml_ops| {
            let dict = PyDict::new(py);
            dict.set_item("existing", "old").unwrap();

            // Set new value
            let new_value = "updated".into_pyobject(py).unwrap();
            let updated = yaml_ops.call_method1("set_setting", (dict, "existing", new_value)).unwrap();

            let updated_dict = updated.downcast::<PyDict>().unwrap();
            assert_eq!(
                updated_dict.get_item("existing").unwrap().unwrap().extract::<String>().unwrap(),
                "updated"
            );
        });
    }

    #[test]
    fn test_set_setting_create_nested() {
        with_yaml_ops(|py, yaml_ops| {
            // Start with empty dict
            let dict = PyDict::new(py);

            // Create nested path
            let value = 42.into_pyobject(py).unwrap();
            let updated = yaml_ops.call_method1("set_setting", (dict, "database.connection.port", value)).unwrap();

            // Verify nested structure was created
            let result = yaml_ops.call_method1("get_setting", (updated, "database.connection.port")).unwrap();
            assert!(!result.is_none());
            assert_eq!(result.extract::<i64>().unwrap(), 42);
        });
    }

    #[test]
    fn test_set_setting_overwrite_non_mapping() {
        with_yaml_ops(|py, yaml_ops| {
            let yaml_content = r#"
settings: 42
"#;
            let data = yaml_ops.call_method1("parse_yaml", (yaml_content,)).unwrap();

            // Try to create nested path where intermediate value is not a mapping
            let new_value = "test".into_pyobject(py).unwrap();
            let updated = yaml_ops.call_method1("set_setting", (data, "settings.nested.value", new_value)).unwrap();

            // Should convert settings to mapping and create nested structure
            let result = yaml_ops.call_method1("get_setting", (updated, "settings.nested.value")).unwrap();
            assert!(!result.is_none());
            assert_eq!(result.extract::<String>().unwrap(), "test");
        });
    }

    #[test]
    fn test_set_setting_empty_key_path() {
        with_yaml_ops(|py, yaml_ops| {
            let dict = PyDict::new(py);
            let value = "test".into_pyobject(py).unwrap();

            // Empty key path should error
            let result = yaml_ops.call_method1("set_setting", (dict, "", value));
            assert!(result.is_err());

            let err_msg = format!("{}", result.unwrap_err());
            assert!(err_msg.contains("Empty key path"));
        });
    }

    #[test]
    fn test_set_setting_update_existing_nested() {
        with_yaml_ops(|py, yaml_ops| {
            let yaml_content = r#"
server:
  host: localhost
  port: 8080
  ssl: false
"#;
            let data = yaml_ops.call_method1("parse_yaml", (yaml_content,)).unwrap();

            // Update existing nested value
            let new_port = 9000.into_pyobject(py).unwrap();
            let updated = yaml_ops.call_method1("set_setting", (data, "server.port", new_port)).unwrap();

            // Verify update
            let result = yaml_ops.call_method1("get_setting", (updated.clone(), "server.port")).unwrap();
            assert_eq!(result.extract::<i64>().unwrap(), 9000);

            // Verify other values unchanged
            let host_result = yaml_ops.call_method1("get_setting", (updated, "server.host")).unwrap();
            assert_eq!(host_result.extract::<String>().unwrap(), "localhost");
        });
    }

    // ===== Python Type Conversion Tests =====

    #[test]
    fn test_python_to_yaml_all_types() {
        with_yaml_ops(|py, yaml_ops| {
            // Create complex Python structure
            let root = PyDict::new(py);

            // Null
            root.set_item("null_value", py.None()).unwrap();

            // Bool
            root.set_item("bool_true", true).unwrap();
            root.set_item("bool_false", false).unwrap();

            // Numbers
            root.set_item("int_value", 42).unwrap();
            root.set_item("float_value", 3.14).unwrap();

            // String
            root.set_item("string_value", "hello").unwrap();

            // List
            let list = PyList::new(py, &[1, 2, 3]).unwrap();
            root.set_item("list_value", list).unwrap();

            // Nested dict
            let nested = PyDict::new(py);
            nested.set_item("nested_key", "nested_value").unwrap();
            root.set_item("dict_value", nested).unwrap();

            // Convert to YAML and back
            let yaml_str = yaml_ops.call_method1("dump_yaml", (root,)).unwrap()
                .extract::<String>().unwrap();
            let reparsed = yaml_ops.call_method1("parse_yaml", (&yaml_str,)).unwrap();
            let reparsed_dict = reparsed.downcast::<PyDict>().unwrap();

            // Verify all types preserved
            assert!(reparsed_dict.get_item("null_value").unwrap().unwrap().is_none());
            assert_eq!(
                reparsed_dict.get_item("bool_true").unwrap().unwrap().extract::<bool>().unwrap(),
                true
            );
            assert_eq!(
                reparsed_dict.get_item("int_value").unwrap().unwrap().extract::<i64>().unwrap(),
                42
            );

            let nested_result_bound = reparsed_dict.get_item("dict_value").unwrap().unwrap();
            let nested_result = nested_result_bound.downcast::<PyDict>().unwrap();
            assert_eq!(
                nested_result.get_item("nested_key").unwrap().unwrap().extract::<String>().unwrap(),
                "nested_value"
            );
        });
    }

    // ===== Integration Tests =====

    #[test]
    fn test_full_workflow() {
        with_yaml_ops(|py, yaml_ops| {
            let temp_dir = TempDir::new().unwrap();
            let config_file = temp_dir.path().join("config.yaml");

            // Create initial config
            let config = PyDict::new(py);
            config.set_item("app_name", "TestApp").unwrap();
            config.set_item("version", "1.0.0").unwrap();

            let db_config = PyDict::new(py);
            db_config.set_item("host", "localhost").unwrap();
            db_config.set_item("port", 5432).unwrap();
            config.set_item("database", db_config).unwrap();

            // Save config
            yaml_ops.call_method1("save_yaml_file", (config_file.to_str().unwrap(), config)).unwrap();

            // Load config
            let loaded = yaml_ops.call_method1("load_yaml_file", (config_file.to_str().unwrap(),)).unwrap();

            // Get nested setting
            let port = yaml_ops.call_method1("get_setting", (loaded.clone(), "database.port")).unwrap();
            assert_eq!(port.extract::<i64>().unwrap(), 5432);

            // Update setting
            let new_port = 6543.into_pyobject(py).unwrap();
            let updated = yaml_ops.call_method1("set_setting", (loaded, "database.port", new_port)).unwrap();

            // Save updated config
            yaml_ops.call_method1("save_yaml_file", (config_file.to_str().unwrap(), updated)).unwrap();

            // Load again and verify
            let final_config = yaml_ops.call_method1("load_yaml_file", (config_file.to_str().unwrap(),)).unwrap();
            let final_port = yaml_ops.call_method1("get_setting", (final_config, "database.port")).unwrap();
            assert_eq!(final_port.extract::<i64>().unwrap(), 6543);

            // Check cache stats
            let stats_bound = yaml_ops.call_method0("get_cache_stats").unwrap();
            let stats = stats_bound.downcast::<PyDict>().unwrap();
            assert!(stats.get_item("cached_files").unwrap().unwrap().extract::<usize>().unwrap() >= 1);
        });
    }

    #[test]
    fn test_concurrent_file_loads() {
        with_yaml_ops(|_py, yaml_ops| {
            // Clear cache from previous tests
            yaml_ops.call_method0("clear_cache").unwrap();

            let temp_dir = TempDir::new().unwrap();

            // Create multiple YAML files
            let mut files = vec![];
            for i in 0..5 {
                let file = temp_dir.path().join(format!("config{}.yaml", i));
                fs::write(&file, format!("index: {}", i)).unwrap();
                files.push(file);
            }

            // Load all files (cache should handle concurrent access)
            for (i, file) in files.iter().enumerate() {
                let loaded = yaml_ops.call_method1("load_yaml_file", (file.to_str().unwrap(),)).unwrap();
                let dict = loaded.downcast::<PyDict>().unwrap();
                assert_eq!(
                    dict.get_item("index").unwrap().unwrap().extract::<i64>().unwrap(),
                    i as i64
                );
            }

            // Verify cache stats
            let stats_bound = yaml_ops.call_method0("get_cache_stats").unwrap();
            let stats = stats_bound.downcast::<PyDict>().unwrap();
            assert_eq!(
                stats.get_item("cached_files").unwrap().unwrap().extract::<usize>().unwrap(),
                5
            );
        });
    }
}
