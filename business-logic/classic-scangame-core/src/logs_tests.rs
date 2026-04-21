use super::*;
use std::fs;
use tempfile::TempDir;

#[test]
fn test_processor_creation() {
    let processor = LogProcessor::new(
        vec!["error".to_string()],
        vec!["crash-".to_string()],
        vec!["warning".to_string()],
    )
    .unwrap();

    assert_eq!(processor.error_patterns.len(), 1);
}

#[test]
fn test_error_detection() {
    let temp_dir = TempDir::new().unwrap();
    let log_file = temp_dir.path().join("test.log");

    // Create test log with errors
    fs::write(
        &log_file,
        "INFO: Starting\nERROR: Something failed\nINFO: Continuing\n",
    )
    .unwrap();

    let processor = LogProcessor::new(vec!["error".to_string()], vec![], vec![]).unwrap();

    let report = processor.process_logs(temp_dir.path()).unwrap();
    assert!(report.contains("ERROR > ERROR: Something failed"));
}

#[test]
fn test_error_exclusion() {
    let temp_dir = TempDir::new().unwrap();
    let log_file = temp_dir.path().join("test.log");

    fs::write(
        &log_file,
        "ERROR: This should be caught\nERROR: Warning - ignore this\n",
    )
    .unwrap();

    let processor = LogProcessor::new(
        vec!["error".to_string()],
        vec![],
        vec!["warning".to_string()],
    )
    .unwrap();

    let report = processor.process_logs(temp_dir.path()).unwrap();
    assert!(report.contains("This should be caught"));
    assert!(!report.contains("Warning - ignore this"));
}

#[test]
fn test_crash_log_exclusion() {
    let temp_dir = TempDir::new().unwrap();
    let crash_log = temp_dir.path().join("crash-2024.log");

    fs::write(&crash_log, "ERROR: Crash happened\n").unwrap();

    let processor = LogProcessor::new(vec!["error".to_string()], vec![], vec![]).unwrap();

    let report = processor.process_logs(temp_dir.path()).unwrap();
    assert!(report.is_empty());
}

#[test]
fn test_error_truncation() {
    let temp_dir = TempDir::new().unwrap();
    let log_file = temp_dir.path().join("test.log");

    // Create a log with 100 errors
    let mut log_content = String::new();
    for i in 1..=100 {
        log_content.push_str(&format!("ERROR: Error number {}\n", i));
    }
    fs::write(&log_file, log_content).unwrap();

    let processor = LogProcessor::new(vec!["error".to_string()], vec![], vec![]).unwrap();

    let report = processor.process_logs(temp_dir.path()).unwrap();

    // Should show truncation notice
    assert!(report.contains("Showing last 50 of 100 total errors"));

    // Should show total count as 100
    assert!(report.contains("TOTAL NUMBER OF DETECTED LOG ERRORS * : 100"));

    // Should contain last error (100) but not first error (1)
    assert!(report.contains("ERROR > ERROR: Error number 100"));
    // Use exact match with newline to avoid matching "10", "100", etc.
    assert!(!report.contains("ERROR > ERROR: Error number 1\n"));

    // Should contain error 51 (first of last 50)
    assert!(report.contains("ERROR > ERROR: Error number 51"));
}
