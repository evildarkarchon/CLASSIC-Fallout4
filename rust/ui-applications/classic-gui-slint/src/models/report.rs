// Report data models for Results Tab
#![allow(dead_code)]
//
// This module provides data structures for representing scan reports
// in the UI, with formatting helpers for display.

use std::path::PathBuf;
use std::time::SystemTime;

/// Report item for display in the report list
///
/// Contains all metadata needed to display a report in the list,
/// including the file path, size, and formatted display strings.
#[derive(Debug, Clone)]
pub struct ReportItem {
    /// Report filename (e.g., "crash-2025-10-11-AUTOSCAN.md")
    pub filename: String,

    /// Full path to the report file
    pub path: PathBuf,

    /// File modification time (for metadata, not used for sorting)
    pub date_modified: SystemTime,

    /// File size in bytes
    pub size_bytes: u64,

    /// Formatted date string for display (e.g., "2025-10-11 14:30")
    pub display_date: String,

    /// Formatted file size for display (e.g., "125 KB")
    pub file_size: String,
}

impl ReportItem {
    /// Create a new ReportItem from a file path
    ///
    /// Extracts metadata from the file system and formats display strings.
    ///
    /// # Arguments
    /// * `path` - Path to the report file
    ///
    /// # Returns
    /// * `Ok(ReportItem)` - Successfully created report item
    /// * `Err(std::io::Error)` - Failed to read file metadata
    pub fn from_path(path: PathBuf) -> std::io::Result<Self> {
        let metadata = path.metadata()?;
        let filename = path
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("Unknown")
            .to_string();

        let date_modified = metadata.modified()?;
        let size_bytes = metadata.len();

        // Format date for display
        let display_date = format_system_time(date_modified);

        // Format file size for display
        let file_size = format_file_size(size_bytes);

        Ok(Self {
            filename,
            path,
            date_modified,
            size_bytes,
            display_date,
            file_size,
        })
    }
}

/// Format a SystemTime for display
///
/// Converts a SystemTime to a human-readable string like "2025-10-11 14:30"
fn format_system_time(time: SystemTime) -> String {
    use std::time::UNIX_EPOCH;

    match time.duration_since(UNIX_EPOCH) {
        Ok(duration) => {
            let secs = duration.as_secs();
            let datetime = chrono::DateTime::from_timestamp(secs as i64, 0);

            match datetime {
                Some(dt) => dt.format("%Y-%m-%d %H:%M").to_string(),
                None => "Unknown".to_string(),
            }
        }
        Err(_) => "Unknown".to_string(),
    }
}

/// Format a file size for display
///
/// Converts bytes to a human-readable string with appropriate units (B, KB, MB, GB)
fn format_file_size(bytes: u64) -> String {
    const KB: u64 = 1024;
    const MB: u64 = KB * 1024;
    const GB: u64 = MB * 1024;

    if bytes >= GB {
        format!("{:.2} GB", bytes as f64 / GB as f64)
    } else if bytes >= MB {
        format!("{:.2} MB", bytes as f64 / MB as f64)
    } else if bytes >= KB {
        format!("{:.2} KB", bytes as f64 / KB as f64)
    } else {
        format!("{} B", bytes)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_format_file_size() {
        assert_eq!(format_file_size(500), "500 B");
        assert_eq!(format_file_size(1024), "1.00 KB");
        assert_eq!(format_file_size(1536), "1.50 KB");
        assert_eq!(format_file_size(1048576), "1.00 MB");
        assert_eq!(format_file_size(1073741824), "1.00 GB");
    }
}
