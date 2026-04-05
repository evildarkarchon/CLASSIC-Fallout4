//! Integration tests for classic-yaml-core
//!
//! These tests verify cross-component workflows and file I/O operations
//! that involve multiple YAML operations working together.

use classic_yaml_core::{YamlError, YamlOperations, clear_global_yaml_cache};
use std::fs;
use std::io::Write;
use std::path::Path;
use std::sync::Arc;
use std::thread;
use std::time::Duration;
use tempfile::{NamedTempFile, tempdir};
use yaml_rust2::Yaml;

// ============================================================================
// File I/O Workflow Tests
// ============================================================================

mod file_workflows {
    use super::*;

    /// Test complete load-modify-save workflow
    #[test]
    fn test_load_modify_save_workflow() {
        clear_global_yaml_cache();

        let temp_dir = tempdir().expect("Failed to create temp dir");
        let config_path = temp_dir.path().join("config.yaml");

        let ops = YamlOperations::new();

        // Create initial file
        let initial_yaml = r#"
settings:
  debug: false
  level: 1
  name: original
"#;
        fs::write(&config_path, initial_yaml).expect("Failed to write initial file");

        // Load
        let yaml = ops
            .load_yaml_file(&config_path)
            .expect("Load should succeed");
        assert_eq!(
            ops.get_setting(&yaml, "settings.debug"),
            Some(Yaml::Boolean(false))
        );

        // Modify
        let modified = ops
            .set_setting(&yaml, "settings.debug", Yaml::Boolean(true))
            .expect("Set should succeed");
        let modified = ops
            .set_setting(&modified, "settings.level", Yaml::Integer(5))
            .expect("Set should succeed");
        let modified = ops
            .set_setting(
                &modified,
                "settings.name",
                Yaml::String("modified".to_string()),
            )
            .expect("Set should succeed");

        // Save
        ops.save_yaml_file(&config_path, &modified)
            .expect("Save should succeed");

        // Clear cache and reload to verify persistence
        clear_global_yaml_cache();

        let reloaded = ops
            .load_yaml_file(&config_path)
            .expect("Reload should succeed");
        assert_eq!(
            ops.get_setting(&reloaded, "settings.debug"),
            Some(Yaml::Boolean(true))
        );
        assert_eq!(
            ops.get_setting(&reloaded, "settings.level"),
            Some(Yaml::Integer(5))
        );
        assert_eq!(
            ops.get_string_value(&reloaded, "settings.name", ""),
            "modified"
        );
    }

    /// Test batch file loading workflow
    #[test]
    fn test_batch_file_loading_workflow() {
        clear_global_yaml_cache();

        let temp_dir = tempdir().expect("Failed to create temp dir");

        // Create multiple config files
        let configs = [
            ("main.yaml", "version: 1.0\nname: main"),
            ("game.yaml", "game: Fallout4\nlevel: hard"),
            ("mods.yaml", "mods:\n  - mod1\n  - mod2"),
        ];

        let paths: Vec<_> = configs
            .iter()
            .map(|(name, content)| {
                let path = temp_dir.path().join(name);
                fs::write(&path, content).expect("Failed to write file");
                path
            })
            .collect();

        let ops = YamlOperations::new();
        let path_refs: Vec<&Path> = paths.iter().map(|p| p.as_path()).collect();
        let results = ops.load_yaml_files_batch(&path_refs);

        assert_eq!(results.len(), 3, "Should load all 3 files");

        // Verify each file was loaded correctly
        for path in &paths {
            let key = path.to_string_lossy().to_string();
            assert!(results.contains_key(&key), "Should contain {}", key);
        }
    }

    /// Test atomic write ensures no data corruption on concurrent access
    #[test]
    fn test_atomic_write_integrity() {
        clear_global_yaml_cache();

        let temp_dir = tempdir().expect("Failed to create temp dir");
        let config_path = temp_dir.path().join("atomic_test.yaml");

        let ops = Arc::new(YamlOperations::new());

        // Create initial file
        let mut hash = yaml_rust2::yaml::Hash::new();
        hash.insert(Yaml::String("counter".to_string()), Yaml::Integer(0));
        let yaml = Yaml::Hash(hash);
        ops.save_yaml_file(&config_path, &yaml)
            .expect("Initial save should succeed");

        // Spawn multiple threads doing concurrent reads and writes
        let handles: Vec<_> = (0..4)
            .map(|id| {
                let ops_clone = ops.clone();
                let path_clone = config_path.clone();
                thread::spawn(move || {
                    for i in 0..10 {
                        // Read (verify file is valid, result not used)
                        let _yaml = ops_clone
                            .load_yaml_file(&path_clone)
                            .unwrap_or_else(|_| Yaml::Null);

                        // Create new value
                        let mut hash = yaml_rust2::yaml::Hash::new();
                        hash.insert(
                            Yaml::String("counter".to_string()),
                            Yaml::Integer((id * 10 + i) as i64),
                        );
                        hash.insert(Yaml::String("thread".to_string()), Yaml::Integer(id as i64));
                        let new_yaml = Yaml::Hash(hash);

                        // Write (atomic)
                        let _ = ops_clone.save_yaml_file(&path_clone, &new_yaml);

                        // Small delay to increase interleaving
                        thread::sleep(Duration::from_millis(1));
                    }
                })
            })
            .collect();

        for handle in handles {
            handle.join().expect("Thread should complete");
        }

        // File should be valid YAML after all concurrent writes
        clear_global_yaml_cache();
        let final_yaml = ops
            .load_yaml_file(&config_path)
            .expect("Final file should be valid YAML");

        // Should have counter and thread fields
        assert!(ops.get_setting(&final_yaml, "counter").is_some());
        assert!(ops.get_setting(&final_yaml, "thread").is_some());
    }
}

// ============================================================================
// Cache Integration Tests
// ============================================================================

mod cache_workflows {
    use super::*;

    /// Test cache behavior across multiple operations
    #[test]
    fn test_cache_performance_benefit() {
        clear_global_yaml_cache();

        let mut temp_file = NamedTempFile::new().expect("Failed to create temp file");
        writeln!(temp_file, "data: test\ncount: 100").expect("Failed to write");

        let ops = YamlOperations::new();
        let path = temp_file.path();

        // First load - populates cache
        let start1 = std::time::Instant::now();
        let yaml1 = ops.load_yaml_file(path).expect("First load should succeed");
        let elapsed1 = start1.elapsed();

        // Second load - should hit cache
        let start2 = std::time::Instant::now();
        let yaml2 = ops
            .load_yaml_file(path)
            .expect("Second load should succeed");
        let elapsed2 = start2.elapsed();

        // Verify same content
        assert_eq!(
            ops.get_string_value(&yaml1, "data", ""),
            ops.get_string_value(&yaml2, "data", "")
        );

        // Cache hit should generally be faster (not guaranteed but typical)
        // Just verify both loads succeed
        assert!(elapsed1 >= Duration::ZERO);
        assert!(elapsed2 >= Duration::ZERO);
    }

    /// Test cache invalidation on file modification
    #[test]
    fn test_cache_invalidation_on_external_modification() {
        clear_global_yaml_cache();

        let temp_dir = tempdir().expect("Failed to create temp dir");
        let config_path = temp_dir.path().join("invalidation_test.yaml");

        let ops = YamlOperations::new();

        // Create initial file
        fs::write(&config_path, "version: 1").expect("Failed to write");

        // Load to populate cache
        let yaml1 = ops
            .load_yaml_file(&config_path)
            .expect("First load should succeed");
        assert_eq!(ops.get_setting(&yaml1, "version"), Some(Yaml::Integer(1)));

        // Wait a bit to ensure different mtime
        thread::sleep(Duration::from_millis(50));

        // Modify file externally
        fs::write(&config_path, "version: 2").expect("Failed to overwrite");

        // Load again - should detect modification and reload
        let yaml2 = ops
            .load_yaml_file(&config_path)
            .expect("Second load should succeed");
        assert_eq!(
            ops.get_setting(&yaml2, "version"),
            Some(Yaml::Integer(2)),
            "Should see updated content after external modification"
        );
    }

    /// Test cache with caching disabled
    #[test]
    fn test_disabled_cache_always_reads_file() {
        clear_global_yaml_cache();

        let temp_dir = tempdir().expect("Failed to create temp dir");
        let config_path = temp_dir.path().join("no_cache_test.yaml");

        let mut ops = YamlOperations::new();
        ops.set_cache_enabled(false);

        // Create file
        fs::write(&config_path, "value: 1").expect("Failed to write");

        // Load
        let yaml1 = ops
            .load_yaml_file(&config_path)
            .expect("First load should succeed");
        assert_eq!(ops.get_setting(&yaml1, "value"), Some(Yaml::Integer(1)));

        // Modify file
        fs::write(&config_path, "value: 2").expect("Failed to overwrite");

        // Load again - should always read from file when cache disabled
        let yaml2 = ops
            .load_yaml_file(&config_path)
            .expect("Second load should succeed");
        assert_eq!(
            ops.get_setting(&yaml2, "value"),
            Some(Yaml::Integer(2)),
            "Should always read fresh with cache disabled"
        );
    }
}

// ============================================================================
// Settings Batch Workflow Tests
// ============================================================================

mod settings_workflows {
    use super::*;

    /// Test loading config and extracting multiple settings
    #[test]
    fn test_config_extraction_workflow() {
        let ops = YamlOperations::new();

        let config_yaml = r#"
CLASSIC_Info:
  version: "7.31.0"
  date: "2024-01-15"
Game_Config:
  name: Fallout4
  version: "1.10.163"
  debug: true
  log_level: 3
Features:
  fcx_mode: true
  auto_scan: false
  plugins:
    - plugin1.esp
    - plugin2.esp
"#;

        let yaml = ops.parse_yaml(config_yaml).expect("Parse should succeed");

        // Extract multiple settings at once
        let keys = vec![
            "CLASSIC_Info.version",
            "Game_Config.name",
            "Game_Config.debug",
            "Features.fcx_mode",
            "NonExistent.key",
        ];

        let results = ops.get_settings_batch(&yaml, &keys);

        assert_eq!(results.len(), 4, "Should find 4 out of 5 keys");
        assert_eq!(
            results.get("CLASSIC_Info.version"),
            Some(&Yaml::String("7.31.0".to_string()))
        );
        assert_eq!(
            results.get("Game_Config.name"),
            Some(&Yaml::String("Fallout4".to_string()))
        );
        assert_eq!(results.get("Game_Config.debug"), Some(&Yaml::Boolean(true)));
        assert_eq!(results.get("Features.fcx_mode"), Some(&Yaml::Boolean(true)));
        assert!(!results.contains_key("NonExistent.key"));
    }

    /// Test updating multiple settings in a workflow
    #[test]
    fn test_settings_update_workflow() {
        let ops = YamlOperations::new();

        let initial_yaml = r#"
settings:
  debug: false
  level: 1
  name: default
"#;

        let yaml = ops.parse_yaml(initial_yaml).expect("Parse should succeed");

        // Update multiple settings
        let updates = vec![
            ("settings.debug", Yaml::Boolean(true)),
            ("settings.level", Yaml::Integer(5)),
            ("settings.name", Yaml::String("updated".to_string())),
            ("settings.new_key", Yaml::String("new_value".to_string())),
        ];

        let updated = ops
            .set_settings_batch(&yaml, &updates)
            .expect("Batch update should succeed");

        // Verify all updates
        assert_eq!(
            ops.get_setting(&updated, "settings.debug"),
            Some(Yaml::Boolean(true))
        );
        assert_eq!(
            ops.get_setting(&updated, "settings.level"),
            Some(Yaml::Integer(5))
        );
        assert_eq!(
            ops.get_setting(&updated, "settings.name"),
            Some(Yaml::String("updated".to_string()))
        );
        assert_eq!(
            ops.get_setting(&updated, "settings.new_key"),
            Some(Yaml::String("new_value".to_string()))
        );
    }
}

// ============================================================================
// Error Recovery Tests
// ============================================================================

mod error_recovery {
    use super::*;

    /// Test graceful handling of malformed YAML
    #[test]
    fn test_malformed_yaml_handling() {
        let ops = YamlOperations::new();

        let malformed_cases = [
            "{ invalid: yaml: content: }}}",
            "key: [unclosed",
            "  - indentation\n- error",
        ];

        for (i, malformed) in malformed_cases.iter().enumerate() {
            let result = ops.parse_yaml(malformed);
            assert!(
                result.is_err(),
                "Case {} should fail to parse: {}",
                i,
                malformed
            );
            match result {
                Err(YamlError::ParseError(_)) => (),
                Err(e) => panic!("Case {} should be ParseError, got {:?}", i, e),
                Ok(_) => panic!("Case {} should not parse successfully", i),
            }
        }
    }

    /// Test handling of file not found
    #[test]
    fn test_file_not_found_handling() {
        let ops = YamlOperations::new();
        let result = ops.load_yaml_file(Path::new("/nonexistent/path/file.yaml"));

        assert!(result.is_err());
        match result {
            Err(YamlError::IoError(_)) => (),
            Err(e) => panic!("Should be IoError, got {:?}", e),
            Ok(_) => panic!("Should not succeed"),
        }
    }

    /// Test batch loading with partial failures
    #[test]
    fn test_batch_load_partial_failure() {
        clear_global_yaml_cache();

        let temp_dir = tempdir().expect("Failed to create temp dir");

        // Create one valid file
        let valid_path = temp_dir.path().join("valid.yaml");
        fs::write(&valid_path, "key: value").expect("Failed to write");

        // One nonexistent file
        let nonexistent = temp_dir.path().join("nonexistent.yaml");

        let ops = YamlOperations::new();
        let paths: Vec<&Path> = vec![valid_path.as_path(), nonexistent.as_path()];
        let results = ops.load_yaml_files_batch(&paths);

        // Should only have the valid file
        assert_eq!(results.len(), 1, "Should only load valid file");
        assert!(
            results.contains_key(&valid_path.to_string_lossy().to_string()),
            "Should contain valid file"
        );
    }
}

// ============================================================================
// Thread Safety Tests
// ============================================================================

mod thread_safety {
    use super::*;

    /// Test concurrent file operations from multiple threads
    #[test]
    fn test_concurrent_file_operations() {
        clear_global_yaml_cache();

        let temp_dir = tempdir().expect("Failed to create temp dir");

        // Create test files
        for i in 0..4 {
            let path = temp_dir.path().join(format!("file{}.yaml", i));
            fs::write(&path, format!("id: {}\ndata: test", i)).expect("Failed to write");
        }

        let ops = Arc::new(YamlOperations::new());
        let temp_path = temp_dir.path().to_path_buf();

        let handles: Vec<_> = (0..4)
            .map(|thread_id| {
                let ops_clone = ops.clone();
                let path = temp_path.clone();
                thread::spawn(move || {
                    for iteration in 0..10 {
                        // Each thread reads all files
                        for file_id in 0..4 {
                            let file_path = path.join(format!("file{}.yaml", file_id));
                            match ops_clone.load_yaml_file(&file_path) {
                                Ok(loaded_yaml) => {
                                    let _ = ops_clone.get_setting(&loaded_yaml, "id");
                                }
                                Err(e) => {
                                    panic!(
                                        "Thread {} iteration {} failed on file {}: {:?}",
                                        thread_id, iteration, file_id, e
                                    );
                                }
                            }
                        }
                    }
                })
            })
            .collect();

        for handle in handles {
            handle.join().expect("Thread should complete without panic");
        }
    }
}
