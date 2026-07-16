//! Run-scoped FCX configuration issue data.
//!
//! FCX setup is evaluated once per final Crash Log Scan Run. This module retains only
//! the immutable issue payload included in that run-owned setup snapshot.

/// Configuration issue detected by FCX mode
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ConfigIssue {
    /// Path to the configuration file
    pub file_path: String,

    /// INI section name (None for TOML or non-sectioned files)
    pub section: Option<String>,

    /// Setting/key name
    pub setting: String,

    /// Current value in the file
    pub current_value: String,

    /// Recommended value to fix the issue
    pub recommended_value: String,

    /// Human-readable description of the issue
    pub description: String,

    /// Issue severity level ("error", "warning", "info")
    pub severity: String,
}

impl ConfigIssue {
    /// Create a new configuration issue
    pub fn new(
        file_path: String,
        section: Option<String>,
        setting: String,
        current_value: String,
        recommended_value: String,
        description: String,
        severity: String,
    ) -> Self {
        Self {
            file_path,
            section,
            setting,
            current_value,
            recommended_value,
            description,
            severity,
        }
    }

    /// Format issue as human-readable report section
    pub fn format_report(&self) -> String {
        let icon = match self.severity.as_str() {
            "error" => "❌",
            "warning" => "⚠️",
            "info" => "ℹ️",
            _ => "⚠️",
        };

        let section_str = self
            .section
            .as_ref()
            .map(|s| format!("[{}]", s))
            .unwrap_or_else(|| "N/A".to_string());

        format!(
            "{} DETECTED ISSUE: {}\n   File: {}\n   Section: {}\n   Setting: {}\n   Current Value: {}\n   Recommended Value: {}\n\n",
            icon,
            self.description,
            self.file_path,
            section_str,
            self.setting,
            self.current_value,
            self.recommended_value
        )
    }
}
