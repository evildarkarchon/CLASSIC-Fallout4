use super::*;
use classic_scanlog_core::papyrus::PapyrusStats;
use std::io::Write;
use tempfile::NamedTempFile;

#[test]
fn test_papyrus_analyzer_new() {
    let analyzer = papyrus_analyzer_new("/some/path/Papyrus.0.log");
    // Should not panic; analyzer wraps the path without file access
    assert!(!papyrus_log_exists(&analyzer));
}

#[test]
fn test_papyrus_log_exists_with_real_file() {
    let temp = NamedTempFile::new().unwrap();
    let path = temp.path().to_str().unwrap();
    let analyzer = papyrus_analyzer_new(path);
    assert!(papyrus_log_exists(&analyzer));
}

#[test]
fn test_papyrus_analyze_full() {
    let mut temp = NamedTempFile::new().unwrap();
    writeln!(temp, "Dumping Stacks for thread 0x1234").unwrap();
    writeln!(temp, "Dumping Stack for function foo").unwrap();
    writeln!(temp, "[2024/01/01] warning: Variable not initialized").unwrap();
    writeln!(temp, "[2024/01/01] error: Null reference").unwrap();
    temp.flush().unwrap();

    let path = temp.path().to_str().unwrap();
    let mut analyzer = papyrus_analyzer_new(path);
    let dto = papyrus_analyze_full(&mut analyzer).unwrap();

    assert_eq!(dto.dumps, 1);
    assert_eq!(dto.stacks, 1);
    assert_eq!(dto.warnings, 1);
    assert_eq!(dto.errors, 1);
    assert_eq!(dto.lines_processed, 4);
    assert!(dto.dumps_stacks_ratio > 0.0);
}

#[test]
fn test_papyrus_analyze_full_nonexistent() {
    let mut analyzer = papyrus_analyzer_new("/nonexistent/Papyrus.0.log");
    let result = papyrus_analyze_full(&mut analyzer);
    assert!(result.is_err());
}

#[test]
fn test_papyrus_start_monitoring_nonexistent() {
    let mut analyzer = papyrus_analyzer_new("/nonexistent/Papyrus.0.log");
    let result = papyrus_start_monitoring(&mut analyzer);
    assert!(result.is_err());
}

#[test]
fn test_papyrus_start_monitoring_and_check_updates() {
    let mut temp = NamedTempFile::new().unwrap();
    writeln!(temp, "Initial line").unwrap();
    temp.flush().unwrap();

    let path = temp.path().to_str().unwrap();
    let mut analyzer = papyrus_analyzer_new(path);

    // Start monitoring positions at end of file
    papyrus_start_monitoring(&mut analyzer).unwrap();

    // No new data yet -- stats should be empty
    let dto = papyrus_check_updates(&mut analyzer);
    assert_eq!(dto.dumps, 0);
    assert_eq!(dto.lines_processed, 0);

    // Append new data
    writeln!(temp, "Dumping Stacks for thread 0xABC").unwrap();
    writeln!(temp, "[2024/01/01] error: Something bad").unwrap();
    temp.flush().unwrap();

    // Now check_updates should pick up the new lines
    let dto = papyrus_check_updates(&mut analyzer);
    assert_eq!(dto.dumps, 1);
    assert_eq!(dto.errors, 1);
    assert_eq!(dto.lines_processed, 2);
}

#[test]
fn test_papyrus_reset() {
    let mut temp = NamedTempFile::new().unwrap();
    writeln!(temp, "Dumping Stacks").unwrap();
    writeln!(temp, "[2024/01/01] error: Null ref").unwrap();
    temp.flush().unwrap();

    let path = temp.path().to_str().unwrap();
    let mut analyzer = papyrus_analyzer_new(path);

    // Analyze to populate stats
    papyrus_analyze_full(&mut analyzer).unwrap();

    // Reset clears everything
    papyrus_reset(&mut analyzer);

    // check_updates after reset should re-read from beginning
    let dto = papyrus_check_updates(&mut analyzer);
    assert_eq!(dto.dumps, 1);
    assert_eq!(dto.errors, 1);
    assert_eq!(dto.lines_processed, 2);
}

#[test]
fn test_papyrus_stats_dto_no_activity() {
    let stats = PapyrusStats {
        dumps: 0,
        stacks: 0,
        warnings: 10,
        errors: 0,
        last_modified: None,
        lines_processed: 100,
    };
    let dto = papyrus_stats_to_dto(&stats);
    assert_eq!(dto.dumps_stacks_ratio, 0.0);
    assert_eq!(dto.warnings, 10);
    assert_eq!(dto.lines_processed, 100);
}

#[test]
fn test_papyrus_stats_dto_with_activity() {
    let stats = PapyrusStats {
        dumps: 5,
        stacks: 2,
        warnings: 0,
        errors: 10,
        last_modified: None,
        lines_processed: 50,
    };
    let dto = papyrus_stats_to_dto(&stats);
    assert_eq!(dto.dumps, 5);
    assert_eq!(dto.stacks, 2);
    assert_eq!(dto.errors, 10);
    assert_eq!(dto.dumps_stacks_ratio, 2.5);
}
