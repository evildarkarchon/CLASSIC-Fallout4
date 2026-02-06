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
}
