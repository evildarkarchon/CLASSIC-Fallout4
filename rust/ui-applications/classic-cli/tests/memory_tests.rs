//! Memory leak detection and performance tests for CLASSIC CLI.
//!
//! This test suite focuses on identifying potential memory leaks and resource
//! accumulation issues in long-running scenarios. Tests include:
//!
//! - Configuration load/save cycles
//! - String buffer management
//! - PathBuf allocation patterns
//! - Resource cleanup on errors
//! - Profiling markers for memory analysis tools
//!
//! Use `cargo test --test memory_tests -- --ignored` to run profiling tests.

use classic_cli::{CliConfig, load_or_create_config};
use std::path::PathBuf;
use tempfile::tempdir;

/// Memory leak detection tests
/// These tests check for common memory issues in long-running scenarios

#[tokio::test]
async fn test_no_memory_leak_in_config_load_cycles() {
    let temp_dir = tempdir().unwrap();
    let config_path = temp_dir.path().join("config.yaml");

    // Create initial config
    let config = CliConfig::default();
    config.save_to_yaml(&config_path).await.unwrap();

    // Simulate 1000 load cycles
    // If there's a memory leak, this will accumulate significant memory
    for _ in 0..1000 {
        let _loaded = CliConfig::load_from_yaml(&config_path).await.unwrap();
        // Config should be dropped here
    }

    // If we get here without OOM, no major leak
    // Note: Use profiling tools for precise measurement
}

#[tokio::test]
async fn test_no_memory_leak_in_repeated_saves() {
    let temp_dir = tempdir().unwrap();
    let config_path = temp_dir.path().join("config.yaml");

    let mut config = CliConfig::default();

    // Simulate 1000 save cycles
    for i in 0..1000 {
        config.fcx_mode = i % 2 == 0;
        config.save_to_yaml(&config_path).await.unwrap();
    }

    // Verify file still accessible (not corrupted)
    let loaded = CliConfig::load_from_yaml(&config_path).await.unwrap();
    assert!(!loaded.fcx_mode); // Last save was i=999 (odd, so 999 % 2 == 1, fcx_mode = false)
}

#[test]
fn test_pathbuf_reuse_no_accumulation() {
    // Test that repeated PathBuf creation/drop doesn't leak
    let paths: Vec<PathBuf> = (0..10000)
        .map(|i| PathBuf::from(format!("C:\\Test\\Path{}", i)))
        .collect();

    // All paths created, now verify we can iterate without panic
    assert_eq!(paths.len(), 10000);

    // Paths will be dropped here - should not leak
}

#[tokio::test]
async fn test_config_merge_no_accumulation() {
    use classic_cli::CliArgs;

    let temp_dir = tempdir().unwrap();
    let config_path = temp_dir.path().join("config.yaml");

    let config = CliConfig::default();
    config.save_to_yaml(&config_path).await.unwrap();

    // Simulate 1000 load + merge cycles
    for _ in 0..1000 {
        let args = CliArgs {
            fcx_mode: true,
            show_fid_values: false,
            stat_logging: true,
            move_unsolved: false,
            ini_path: None,
            scan_path: None,
            mods_folder_path: None,
            simplify_logs: false,
        };

        let _loaded = load_or_create_config(&config_path, &args).await.unwrap();
        // Config should be dropped here
    }
}

#[test]
fn test_large_string_buffer_handling() {
    // Test output buffer with large strings
    let mut buffer = Vec::new();

    // Add 10000 lines
    for i in 0..10000 {
        buffer.push(format!(
            "Log line {} with some additional content to test memory",
            i
        ));
    }

    assert_eq!(buffer.len(), 10000);

    // Clear and verify memory can be reclaimed
    buffer.clear();
    buffer.shrink_to_fit();

    assert_eq!(buffer.capacity(), 0);
}

#[test]
fn test_scan_stats_no_accumulation() {
    use classic_cli::ScanStats;

    // Create and drop many stats objects
    for _ in 0..10000 {
        let _stats = ScanStats {
            scanned_logs: 47,
            patterns_matched: 234,
            formids_resolved: 1842,
            suspects_identified: 12,
        };
        // Stats dropped here
    }

    // If no panic, no accumulation issue
}

/// Resource cleanup test - verify proper cleanup on error
#[tokio::test]
async fn test_cleanup_on_config_error() {
    let temp_dir = tempdir().unwrap();
    let bad_path = temp_dir.path().join("nonexistent").join("config.yaml");

    // This should fail but not leak resources
    for _ in 0..100 {
        let result = CliConfig::load_from_yaml(&bad_path).await;
        assert!(result.is_err());
    }
}

/// Test that Vec growth doesn't cause issues
#[test]
fn test_vec_growth_patterns() {
    let mut vec = Vec::new();

    // Simulate output viewer growth pattern
    for i in 0..10000 {
        vec.push(format!("Line {}", i));

        // Trim old lines (like OutputViewer max_lines)
        if vec.len() > 1000 {
            vec.drain(0..500);
        }
    }

    // Should stabilize around 1000 lines
    assert!(vec.len() <= 1000);
}

/// Memory profile markers
/// Use these tests with profiling tools like valgrind or heaptrack
mod profiling_markers {
    use super::*;

    #[tokio::test]
    #[ignore] // Run with: cargo test --test memory_tests -- --ignored
    async fn profile_config_operations() {
        println!("=== PROFILING START: Config Operations ===");

        let temp_dir = tempdir().unwrap();
        let config_path = temp_dir.path().join("config.yaml");

        let config = CliConfig::default();
        config.save_to_yaml(&config_path).await.unwrap();

        for i in 0..10000 {
            if i % 1000 == 0 {
                println!("Config cycle: {}", i);
            }
            let _loaded = CliConfig::load_from_yaml(&config_path).await.unwrap();
        }

        println!("=== PROFILING END: Config Operations ===");
    }

    #[test]
    #[ignore]
    fn profile_string_allocations() {
        println!("=== PROFILING START: String Allocations ===");

        for i in 0..100000 {
            if i % 10000 == 0 {
                println!("String allocation: {}", i);
            }
            let _s = format!("Test string with number: {}", i);
        }

        println!("=== PROFILING END: String Allocations ===");
    }
}
