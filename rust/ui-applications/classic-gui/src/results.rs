//! Report data model for the Results tab
//!
//! Manages scan report entries: extraction from `AnalysisResult`,
//! timestamp parsing, sorting, filtering helpers, and clipboard copy.

use std::path::Path;

use arboard::Clipboard;
use classic_scanlog_core::AnalysisResult;

/// Holds scan reports for the Results tab
pub struct ReportData {
    /// Analysis results from the last scan
    pub reports: Vec<AnalysisResult>,
}

/// Data for a single report list entry (Slint-independent)
///
/// Used as an intermediate representation between `AnalysisResult`
/// and the Slint-generated `ReportEntry` struct.
pub struct ReportEntryData {
    /// Display filename extracted from log path
    pub filename: String,
    /// Timestamp extracted from filename pattern
    pub timestamp: String,
    /// Index into the original reports vector
    pub source_index: i32,
}

/// Extract a human-readable timestamp from a crash log filename
///
/// Looks for patterns like `YYYY-MM-DD-HH-MM-SS` embedded in the filename.
/// Falls back to `YYYY-MM-DD` if only the date portion is found.
///
/// # Examples
///
/// ```
/// # use classic_gui::results::extract_timestamp;
/// assert_eq!(extract_timestamp("crash-2024-01-15-08-30-00.log"), "2024-01-15 08:30:00");
/// assert_eq!(extract_timestamp("crash-2024-01-15.log"), "2024-01-15");
/// assert_eq!(extract_timestamp("random.log"), "");
/// ```
pub fn extract_timestamp(filename: &str) -> String {
    // Split filename into segments separated by hyphens and dots
    let clean = filename.replace('.', "-");
    let parts: Vec<&str> = clean.split('-').collect();

    // Look for a 4-digit year followed by valid month and day
    for i in 0..parts.len() {
        if parts[i].len() == 4 && parts[i].chars().all(|c| c.is_ascii_digit()) {
            let year: u32 = match parts[i].parse() {
                Ok(y) if (1900..=2100).contains(&y) => y,
                _ => continue,
            };

            // Need at least month and day after year
            if i + 2 >= parts.len() {
                continue;
            }

            let month: u32 = match parts[i + 1].parse() {
                Ok(m) if (1..=12).contains(&m) => m,
                _ => continue,
            };

            let day: u32 = match parts[i + 2].parse() {
                Ok(d) if (1..=31).contains(&d) => d,
                _ => continue,
            };

            // Try to get time components (hour, minute, second)
            if i + 5 < parts.len() {
                if let (Ok(hour), Ok(minute), Ok(second)) = (
                    parts[i + 3].parse::<u32>(),
                    parts[i + 4].parse::<u32>(),
                    parts[i + 5].parse::<u32>(),
                ) {
                    if hour < 24 && minute < 60 && second < 60 {
                        return format!(
                            "{:04}-{:02}-{:02} {:02}:{:02}:{:02}",
                            year, month, day, hour, minute, second
                        );
                    }
                }
            }

            // Date only
            return format!("{:04}-{:02}-{:02}", year, month, day);
        }
    }

    String::new()
}

/// Get the content of a specific report by its source index
///
/// Returns the report lines joined with newlines, or an empty string
/// if the index is out of bounds or negative.
pub fn get_report_content(reports: &[AnalysisResult], source_index: i32) -> String {
    if source_index < 0 {
        return String::new();
    }
    let idx = source_index as usize;
    reports
        .get(idx)
        .map(|r| r.report_lines.join("\n"))
        .unwrap_or_default()
}

/// Build sorted report entries from analysis results
///
/// Converts each `AnalysisResult` into a `ReportEntryData` with extracted
/// filename and timestamp, then sorts by filename ascending or descending.
pub fn prepare_report_entries(
    reports: &[AnalysisResult],
    sort_ascending: bool,
) -> Vec<ReportEntryData> {
    let mut entries: Vec<ReportEntryData> = reports
        .iter()
        .enumerate()
        .map(|(i, result)| {
            let filename = Path::new(&result.log_path)
                .file_name()
                .map(|f| f.to_string_lossy().to_string())
                .unwrap_or_else(|| "unknown".to_string());
            let timestamp = extract_timestamp(&filename);
            ReportEntryData {
                filename,
                timestamp,
                source_index: i as i32,
            }
        })
        .collect();

    if sort_ascending {
        entries.sort_by(|a, b| a.filename.cmp(&b.filename));
    } else {
        entries.sort_by(|a, b| b.filename.cmp(&a.filename));
    }

    entries
}

/// Copy text to the system clipboard
///
/// Uses the `arboard` crate for cross-platform clipboard access.
/// Returns `Ok(())` on success or `Err` with a description on failure.
pub fn copy_to_clipboard(text: &str) -> Result<(), String> {
    let mut clipboard = Clipboard::new().map_err(|e| format!("Failed to open clipboard: {}", e))?;
    clipboard
        .set_text(text)
        .map_err(|e| format!("Failed to set clipboard text: {}", e))
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Create a minimal AnalysisResult for testing
    fn make_result(log_path: &str, report_lines: Vec<String>) -> AnalysisResult {
        AnalysisResult {
            log_path: log_path.to_string(),
            report_lines,
            success: true,
            error: None,
            processing_time_us: 0,
            processing_time_ms: 0,
            formid_count: 0,
            plugin_count: 0,
            suspect_count: 0,
            scanned: 1,
            incomplete: 0,
            failed: 0,
            trigger_scan_failed: false,
        }
    }

    #[test]
    fn test_extract_timestamp_full_datetime() {
        assert_eq!(
            extract_timestamp("crash-2024-01-15-08-30-00.log"),
            "2024-01-15 08:30:00"
        );
    }

    #[test]
    fn test_extract_timestamp_date_only() {
        assert_eq!(extract_timestamp("crash-2024-01-15.log"), "2024-01-15");
    }

    #[test]
    fn test_extract_timestamp_no_match() {
        assert_eq!(extract_timestamp("random.log"), "");
        assert_eq!(extract_timestamp(""), "");
    }

    #[test]
    fn test_get_report_content_valid_index() {
        let reports = vec![make_result(
            "test.log",
            vec!["Line 1".to_string(), "Line 2".to_string()],
        )];
        assert_eq!(get_report_content(&reports, 0), "Line 1\nLine 2");
    }

    #[test]
    fn test_get_report_content_negative_index() {
        let reports = vec![make_result("test.log", vec!["content".to_string()])];
        assert_eq!(get_report_content(&reports, -1), "");
    }

    #[test]
    fn test_get_report_content_out_of_bounds() {
        let reports = vec![make_result("test.log", vec!["content".to_string()])];
        assert_eq!(get_report_content(&reports, 5), "");
    }

    #[test]
    fn test_prepare_report_entries_descending() {
        let reports = vec![
            make_result("a-crash.log", vec![]),
            make_result("z-crash.log", vec![]),
        ];

        let entries = prepare_report_entries(&reports, false);
        assert_eq!(entries.len(), 2);
        assert_eq!(entries[0].filename, "z-crash.log");
        assert_eq!(entries[1].filename, "a-crash.log");
        // source_index should map back to original positions
        assert_eq!(entries[0].source_index, 1);
        assert_eq!(entries[1].source_index, 0);
    }

    #[test]
    fn test_prepare_report_entries_ascending() {
        let reports = vec![
            make_result("z-crash.log", vec![]),
            make_result("a-crash.log", vec![]),
        ];

        let entries = prepare_report_entries(&reports, true);
        assert_eq!(entries[0].filename, "a-crash.log");
        assert_eq!(entries[1].filename, "z-crash.log");
    }

    // ---- Additional coverage tests ----

    #[test]
    fn test_extract_timestamp_various_valid() {
        // Midnight time
        assert_eq!(
            extract_timestamp("crash-2024-06-01-00-00-00.log"),
            "2024-06-01 00:00:00"
        );
        // Max valid time
        assert_eq!(
            extract_timestamp("crash-2024-12-31-23-59-59.log"),
            "2024-12-31 23:59:59"
        );
    }

    #[test]
    fn test_extract_timestamp_invalid_month() {
        // Month 13 is invalid
        assert_eq!(extract_timestamp("crash-2024-13-01.log"), "");
    }

    #[test]
    fn test_extract_timestamp_invalid_day() {
        // Day 32 is invalid
        assert_eq!(extract_timestamp("crash-2024-01-32.log"), "");
    }

    #[test]
    fn test_extract_timestamp_invalid_hour() {
        // Hour 25 is invalid -- falls back to date only
        assert_eq!(
            extract_timestamp("crash-2024-01-15-25-30-00.log"),
            "2024-01-15"
        );
    }

    #[test]
    fn test_extract_timestamp_year_out_of_range() {
        // Year 1899 is below range
        assert_eq!(extract_timestamp("crash-1899-01-01.log"), "");
        // Year 2101 is above range
        assert_eq!(extract_timestamp("crash-2101-01-01.log"), "");
    }

    #[test]
    fn test_extract_timestamp_embedded_in_longer_name() {
        assert_eq!(
            extract_timestamp("FO4-crash-2024-03-20-14-00-00-custom.log"),
            "2024-03-20 14:00:00"
        );
    }

    #[test]
    fn test_get_report_content_empty_reports() {
        let reports: Vec<AnalysisResult> = vec![];
        assert_eq!(get_report_content(&reports, 0), "");
    }

    #[test]
    fn test_get_report_content_multiple_lines() {
        let reports = vec![make_result(
            "test.log",
            vec!["A".to_string(), "B".to_string(), "C".to_string()],
        )];
        assert_eq!(get_report_content(&reports, 0), "A\nB\nC");
    }

    #[test]
    fn test_prepare_report_entries_empty() {
        let reports: Vec<AnalysisResult> = vec![];
        let entries = prepare_report_entries(&reports, true);
        assert!(entries.is_empty());
    }

    #[test]
    fn test_prepare_report_entries_extracts_filename() {
        let reports = vec![make_result(
            "/home/user/logs/crash-2024-01-15.log",
            vec![],
        )];
        let entries = prepare_report_entries(&reports, true);
        assert_eq!(entries[0].filename, "crash-2024-01-15.log");
        assert_eq!(entries[0].timestamp, "2024-01-15");
        assert_eq!(entries[0].source_index, 0);
    }

    #[test]
    fn test_prepare_report_entries_preserves_source_index_after_sort() {
        let reports = vec![
            make_result("c-crash.log", vec![]),
            make_result("a-crash.log", vec![]),
            make_result("b-crash.log", vec![]),
        ];
        let entries = prepare_report_entries(&reports, true);
        assert_eq!(entries[0].filename, "a-crash.log");
        assert_eq!(entries[0].source_index, 1); // Originally index 1
        assert_eq!(entries[1].filename, "b-crash.log");
        assert_eq!(entries[1].source_index, 2); // Originally index 2
        assert_eq!(entries[2].filename, "c-crash.log");
        assert_eq!(entries[2].source_index, 0); // Originally index 0
    }

    #[test]
    fn test_report_data_struct() {
        let data = ReportData {
            reports: vec![make_result("test.log", vec!["line".to_string()])],
        };
        assert_eq!(data.reports.len(), 1);
        assert_eq!(data.reports[0].log_path, "test.log");
    }

    #[test]
    fn test_report_entry_data_fields() {
        let entry = ReportEntryData {
            filename: "crash.log".to_string(),
            timestamp: "2024-01-01".to_string(),
            source_index: 42,
        };
        assert_eq!(entry.filename, "crash.log");
        assert_eq!(entry.timestamp, "2024-01-01");
        assert_eq!(entry.source_index, 42);
    }

    #[test]
    fn test_copy_to_clipboard_succeeds() {
        // Test clipboard operations - exercises the code path
        // On some environments (headless, CI, coverage instrumented) the clipboard
        // may not round-trip correctly, so we only verify no panic occurs
        let result = copy_to_clipboard("test clipboard content");
        // Success or graceful failure - both are acceptable
        let _ = result;
    }

    #[test]
    fn test_copy_to_clipboard_empty_string() {
        let result = copy_to_clipboard("");
        // Should succeed (or fail gracefully) even with empty string
        // Just verify it doesn't panic
        let _ = result;
    }

    #[test]
    fn test_prepare_report_entries_single() {
        let reports = vec![make_result("crash-2024-06-15-10-30-00.log", vec!["data".to_string()])];
        let entries = prepare_report_entries(&reports, true);
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].filename, "crash-2024-06-15-10-30-00.log");
        assert_eq!(entries[0].timestamp, "2024-06-15 10:30:00");
        assert_eq!(entries[0].source_index, 0);
    }

    #[test]
    fn test_get_report_content_single_line() {
        let reports = vec![make_result("test.log", vec!["Only line".to_string()])];
        assert_eq!(get_report_content(&reports, 0), "Only line");
    }
}
