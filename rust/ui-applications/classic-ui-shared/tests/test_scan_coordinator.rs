//! Tests for scan coordinator module

use classic_ui_shared::scan_coordinator::{ScanStatistics, discover_xse_folder};
use std::fs;
use std::path::PathBuf;
use tempfile::TempDir;

#[test]
fn test_scan_statistics_new() {
    let stats = ScanStatistics::new();
    assert_eq!(stats.total_logs, 0);
    assert_eq!(stats.analyzed_logs, 0);
    assert_eq!(stats.failed_logs, 0);
    assert_eq!(stats.total_plugins, 0);
    assert_eq!(stats.total_records, 0);
    assert_eq!(stats.duration_ms, 0);
}

#[test]
fn test_scan_statistics_success_rate_empty() {
    let stats = ScanStatistics::new();
    assert_eq!(
        stats.success_rate(),
        0.0,
        "Empty stats should have 0% success rate"
    );
}

#[test]
fn test_scan_statistics_success_rate_all_success() {
    let stats = ScanStatistics {
        total_logs: 10,
        analyzed_logs: 10,
        failed_logs: 0,
        total_plugins: 0,
        total_records: 0,
        duration_ms: 0,
    };
    assert_eq!(stats.success_rate(), 100.0, "All successful should be 100%");
}

#[test]
fn test_scan_statistics_success_rate_half() {
    let stats = ScanStatistics {
        total_logs: 10,
        analyzed_logs: 5,
        failed_logs: 5,
        total_plugins: 0,
        total_records: 0,
        duration_ms: 0,
    };
    assert_eq!(stats.success_rate(), 50.0, "Half successful should be 50%");
}

#[test]
fn test_scan_statistics_failure_rate_empty() {
    let stats = ScanStatistics::new();
    assert_eq!(
        stats.failure_rate(),
        0.0,
        "Empty stats should have 0% failure rate"
    );
}

#[test]
fn test_scan_statistics_failure_rate_all_failed() {
    let stats = ScanStatistics {
        total_logs: 10,
        analyzed_logs: 0,
        failed_logs: 10,
        total_plugins: 0,
        total_records: 0,
        duration_ms: 0,
    };
    assert_eq!(stats.failure_rate(), 100.0, "All failed should be 100%");
}

#[test]
fn test_scan_statistics_format() {
    let stats = ScanStatistics {
        total_logs: 20,
        analyzed_logs: 15,
        failed_logs: 5,
        total_plugins: 100,
        total_records: 5000,
        duration_ms: 1500,
    };

    let formatted = stats.format();
    assert!(formatted.contains("20"), "Should contain total count");
    assert!(formatted.contains("15"), "Should contain analyzed count");
    assert!(formatted.contains("5"), "Should contain failure count");
    assert!(formatted.contains("100"), "Should contain plugins count");
    assert!(formatted.contains("5000"), "Should contain records count");
    assert!(formatted.contains("1500"), "Should contain duration");
}

#[tokio::test]
async fn test_discover_xse_folder_f4se() {
    let temp_dir = TempDir::new().unwrap();

    // Create F4SE directory structure (Data/F4SE/Logs)
    let f4se_logs = temp_dir.path().join("Data").join("F4SE").join("Logs");
    fs::create_dir_all(&f4se_logs).unwrap();

    let result = discover_xse_folder(temp_dir.path()).await;
    assert!(
        result.is_ok(),
        "Should find F4SE logs directory: {:?}",
        result
    );
    assert_eq!(result.unwrap(), f4se_logs);
}

#[tokio::test]
async fn test_discover_xse_folder_skse() {
    let temp_dir = TempDir::new().unwrap();

    // Create SKSE directory structure (Data/SKSE/Logs)
    let skse_logs = temp_dir.path().join("Data").join("SKSE").join("Logs");
    fs::create_dir_all(&skse_logs).unwrap();

    let result = discover_xse_folder(temp_dir.path()).await;
    assert!(
        result.is_ok(),
        "Should find SKSE logs directory: {:?}",
        result
    );
    assert_eq!(result.unwrap(), skse_logs);
}

#[tokio::test]
async fn test_discover_xse_folder_both_exists() {
    let temp_dir = TempDir::new().unwrap();

    // Create both directories (F4SE should be preferred)
    let f4se_logs = temp_dir.path().join("Data").join("F4SE").join("Logs");
    let skse_logs = temp_dir.path().join("Data").join("SKSE").join("Logs");
    fs::create_dir_all(&f4se_logs).unwrap();
    fs::create_dir_all(&skse_logs).unwrap();

    let result = discover_xse_folder(temp_dir.path()).await;
    assert!(
        result.is_ok(),
        "Should find XSE logs directory: {:?}",
        result
    );
    // F4SE should be checked first
    assert_eq!(
        result.unwrap(),
        f4se_logs,
        "Should prefer F4SE when both exist"
    );
}

#[tokio::test]
async fn test_discover_xse_folder_none_exists() {
    let temp_dir = TempDir::new().unwrap();

    let result = discover_xse_folder(temp_dir.path()).await;
    assert!(
        result.is_err(),
        "Should return error when no XSE directories exist"
    );
}

#[tokio::test]
async fn test_discover_xse_folder_case_insensitive() {
    let temp_dir = TempDir::new().unwrap();

    // Create lowercase directory structure
    let f4se_logs = temp_dir.path().join("Data").join("f4se").join("Logs");
    fs::create_dir_all(&f4se_logs).unwrap();

    let result = discover_xse_folder(temp_dir.path()).await;
    // Behavior depends on filesystem case sensitivity
    // On Windows (case-insensitive), should find it
    // On Linux (case-sensitive), won't find it
    #[cfg(windows)]
    assert!(
        result.is_ok(),
        "Should find lowercase f4se on Windows: {:?}",
        result
    );

    #[cfg(unix)]
    assert!(
        result.is_err(),
        "Should not find lowercase f4se on Unix (case-sensitive)"
    );
}

#[tokio::test]
async fn test_discover_xse_folder_nonexistent_path() {
    let nonexistent = PathBuf::from("/this/path/does/not/exist");

    let result = discover_xse_folder(&nonexistent).await;
    assert!(result.is_err(), "Should return error for nonexistent path");
}

#[test]
fn test_scan_statistics_zero_division() {
    let stats = ScanStatistics {
        total_logs: 0,
        analyzed_logs: 0,
        failed_logs: 0,
        total_plugins: 0,
        total_records: 0,
        duration_ms: 0,
    };

    // These should not panic with division by zero
    assert_eq!(stats.success_rate(), 0.0);
    assert_eq!(stats.failure_rate(), 0.0);
    let _ = stats.format(); // Should not panic
}

#[test]
fn test_scan_statistics_default_trait() {
    let stats1 = ScanStatistics::new();
    let stats2 = ScanStatistics::default();

    assert_eq!(stats1.total_logs, stats2.total_logs);
    assert_eq!(stats1.analyzed_logs, stats2.analyzed_logs);
    assert_eq!(stats1.failed_logs, stats2.failed_logs);
}
