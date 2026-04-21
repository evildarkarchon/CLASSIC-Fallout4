use super::*;
use std::io::{Seek, SeekFrom, Write};
use tempfile::NamedTempFile;

#[test]
fn test_papyrus_stats_ratios() {
    let mut stats = PapyrusStats::new();
    stats.dumps = 10;
    stats.stacks = 5;

    assert_eq!(stats.dumps_to_stacks_ratio(), 2.0);
}

#[test]
fn test_process_line() {
    let mut stats = PapyrusStats::new();

    stats.process_line("Some log content");
    assert_eq!(stats.lines_processed, 1);
    assert_eq!(stats.dumps, 0);

    stats.process_line("Dumping Stacks for thread 0x1234");
    assert_eq!(stats.dumps, 1);

    stats.process_line("Dumping Stack for function foo");
    assert_eq!(stats.stacks, 1);

    stats.process_line("[2024/01/01] warning: Variable not initialized");
    assert_eq!(stats.warnings, 1);

    stats.process_line("[2024/01/01] error: Null reference");
    assert_eq!(stats.errors, 1);
}

#[test]
fn test_analyze_full() {
    let mut temp_file = NamedTempFile::new().unwrap();
    writeln!(temp_file, "Some log content").unwrap();
    writeln!(temp_file, "Dumping Stacks for thread 0x1234").unwrap();
    writeln!(temp_file, "Dumping Stack for function foo").unwrap();
    writeln!(temp_file, "[2024/01/01] warning: Variable not initialized").unwrap();
    writeln!(temp_file, "[2024/01/01] error: Null reference").unwrap();
    writeln!(temp_file, "[2024/01/01] error: Stack overflow").unwrap();

    let mut analyzer = PapyrusAnalyzer::new(temp_file.path().to_path_buf());
    let stats = analyzer.analyze_full().unwrap();

    assert_eq!(stats.dumps, 1);
    assert_eq!(stats.stacks, 1);
    assert_eq!(stats.warnings, 1);
    assert_eq!(stats.errors, 2);
    assert_eq!(stats.lines_processed, 6);
}

#[test]
fn test_tail_behavior() {
    let mut temp_file = NamedTempFile::new().unwrap();
    writeln!(temp_file, "Initial line").unwrap();
    writeln!(temp_file, "Dumping Stacks").unwrap();
    temp_file.flush().unwrap();

    let mut analyzer = PapyrusAnalyzer::new(temp_file.path().to_path_buf());

    // Initial full analysis
    let stats = analyzer.analyze_full().unwrap();
    assert_eq!(stats.dumps, 1);
    assert_eq!(stats.lines_processed, 2);

    // No changes - should return None
    let result = analyzer.check_for_updates().unwrap();
    assert!(result.is_none());

    // Append new lines
    writeln!(temp_file, "New line added").unwrap();
    writeln!(temp_file, "Dumping Stack").unwrap();
    writeln!(temp_file, "[2024/01/01] error: Something bad").unwrap();
    temp_file.flush().unwrap();

    // Check for updates - should detect new lines
    let result = analyzer.check_for_updates().unwrap();
    assert!(result.is_some());

    let (new_lines, updated_stats) = result.unwrap();
    assert_eq!(new_lines.len(), 3);
    assert_eq!(updated_stats.dumps, 1); // Still 1 from before
    assert_eq!(updated_stats.stacks, 1); // New stack detected
    assert_eq!(updated_stats.errors, 1); // New error detected
    assert_eq!(updated_stats.lines_processed, 5); // Total lines
}

#[test]
fn test_file_truncation() {
    let mut temp_file = NamedTempFile::new().unwrap();
    writeln!(temp_file, "Line 1").unwrap();
    writeln!(temp_file, "Dumping Stacks").unwrap();
    temp_file.flush().unwrap();

    let mut analyzer = PapyrusAnalyzer::new(temp_file.path().to_path_buf());
    analyzer.analyze_full().unwrap();

    // Truncate file (simulate log rotation)
    temp_file.as_file_mut().seek(SeekFrom::Start(0)).unwrap();
    temp_file.as_file_mut().set_len(0).unwrap();
    writeln!(temp_file, "New start").unwrap();
    temp_file.flush().unwrap();

    // Should detect truncation and re-read from beginning
    let result = analyzer.check_for_updates().unwrap();
    assert!(result.is_some());

    let (_, stats) = result.unwrap();
    assert_eq!(stats.dumps, 0); // Old dump should be gone
    assert_eq!(stats.lines_processed, 1); // Only new line
}

#[test]
fn test_analyze_nonexistent_log() {
    let mut analyzer = PapyrusAnalyzer::new(PathBuf::from("/nonexistent/path/Papyrus.0.log"));
    let result = analyzer.analyze_full();

    assert!(result.is_err());
    assert!(matches!(result, Err(PapyrusError::LogNotFound(_))));
}
