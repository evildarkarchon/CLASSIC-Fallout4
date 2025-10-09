//! Encoding detection utilities (Pure Rust)

use encoding_rs::{Encoding, UTF_8, WINDOWS_1252};

/// Fast encoding detection for text files
pub struct EncodingDetector;

impl EncodingDetector {
    pub fn new() -> Self {
        Self
    }

    /// Detect encoding from byte content
    pub fn detect(&self, bytes: &[u8]) -> &'static Encoding {
        // Check for BOM markers
        if bytes.starts_with(&[0xEF, 0xBB, 0xBF]) {
            return UTF_8;
        }

        // Try UTF-8 first (most common)
        let (_, _, had_errors) = UTF_8.decode(bytes);
        if !had_errors {
            return UTF_8;
        }

        // Fallback to Windows-1252 for legacy logs
        WINDOWS_1252
    }

    /// Get encoding name as string
    pub fn detect_name(&self, bytes: &[u8]) -> String {
        self.detect(bytes).name().to_string()
    }
}

impl Default for EncodingDetector {
    fn default() -> Self {
        Self::new()
    }
}
