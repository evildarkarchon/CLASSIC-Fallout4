//! Unpacked Mod Scanner Module
//!
//! Provides high-performance scanning of unpacked (loose) mod files in game directories.
//! Replaces Python UnpackedModsScanner with native Rust implementation offering:
//! - Parallel directory traversal
//! - Efficient file type detection
//! - Memory-efficient issue tracking
//! - Fast pattern matching for XSE scripts
//!
//! ## Architecture
//!
//! Scans mod directories recursively and detects:
//! - Animation data directories
//! - Texture format issues (TGA/PNG instead of DDS)
//! - Sound format issues (MP3/M4A instead of XWM)
//! - XSE script files
//! - Previs/Precombine files
//! - DDS files for batch dimension checking

use std::collections::HashSet;
use std::path::{Path, PathBuf};

use rayon::prelude::*;
use thiserror::Error;
use walkdir::WalkDir;

/// Errors that can occur during unpacked mod scanning
#[derive(Debug, Error)]
pub enum UnpackedError {
    /// Failed to access directory
    #[error("Failed to access directory: {0}")]
    IoError(#[from] std::io::Error),

    /// Invalid path
    #[error("Invalid file path")]
    InvalidPath,

    /// Directory not found
    #[error("Directory not found: {0}")]
    DirectoryNotFound(String),
}

/// Result type for unpacked scanning operations
pub type Result<T> = std::result::Result<T, UnpackedError>;

/// Issues detected during unpacked mod scanning
#[derive(Debug, Default, Clone)]
pub struct UnpackedIssues {
    /// Animation data directories detected
    pub animdata: HashSet<String>,

    /// Texture format issues (TGA/PNG instead of DDS)
    pub tex_frmt: HashSet<String>,

    /// Sound format issues (MP3/M4A instead of XWM)
    pub snd_frmt: HashSet<String>,

    /// XSE script files detected
    pub xse_file: HashSet<String>,

    /// Previs/Precombine files detected
    pub previs: HashSet<String>,

    /// DDS files found (for batch dimension checking)
    pub dds_files: Vec<PathBuf>,
}

impl UnpackedIssues {
    /// Create a new empty issues collection
    pub fn new() -> Self {
        Self::default()
    }

    /// Check if any issues were detected
    pub fn has_issues(&self) -> bool {
        !self.animdata.is_empty()
            || !self.tex_frmt.is_empty()
            || !self.snd_frmt.is_empty()
            || !self.xse_file.is_empty()
            || !self.previs.is_empty()
    }

    /// Get total number of issues
    pub fn total_count(&self) -> usize {
        self.animdata.len() + self.tex_frmt.len() + self.snd_frmt.len() + self.xse_file.len() + self.previs.len()
    }
}

/// Unpacked mod scanner
///
/// Scans directories for unpacked mod files and detects various issues.
/// Provides high-performance parallel scanning with efficient issue tracking.
///
/// # Example
///
/// ```rust
/// use classic_scangame_core::unpacked::UnpackedScanner;
/// use std::path::Path;
///
/// let scanner = UnpackedScanner::new();
/// let xse_scripts = vec!["f4se.dll".to_string(), "f4se_loader.exe".to_string()];
/// let issues = scanner.scan_directory(Path::new("/games/fallout4/data"), &xse_scripts)?;
/// println!("Found {} issues", issues.total_count());
/// ```
pub struct UnpackedScanner {
    /// Patterns to exclude from BodySlide filtering
    bodyslide_exceptions: Vec<String>,
}

impl UnpackedScanner {
    /// Create a new unpacked scanner
    pub fn new() -> Self {
        Self {
            bodyslide_exceptions: vec!["BodySlide".to_string()],
        }
    }

    /// Scan a mod directory for issues
    ///
    /// # Arguments
    ///
    /// * `mod_path` - Root directory to scan
    /// * `xse_scriptfiles` - List of XSE script filenames to detect (e.g., ["f4se.dll", "f4se_loader.exe"])
    ///
    /// # Returns
    ///
    /// UnpackedIssues containing all detected issues
    ///
    /// # Example
    ///
    /// ```rust
    /// let issues = scanner.scan_directory(
    ///     Path::new("/mods"),
    ///     &["f4se.dll".to_string()]
    /// )?;
    /// ```
    pub fn scan_directory(&self, mod_path: &Path, xse_scriptfiles: &[String]) -> Result<UnpackedIssues> {
        if !mod_path.exists() {
            return Err(UnpackedError::DirectoryNotFound(
                mod_path.display().to_string(),
            ));
        }

        // Collect all entries
        let entries: Vec<_> = WalkDir::new(mod_path)
            .follow_links(false)
            .into_iter()
            .filter_map(|e| e.ok())
            .collect();

        // Process in parallel using rayon
        let results: Vec<UnpackedIssues> = entries
            .par_iter()
            .filter_map(|entry| {
                let path = entry.path();
                self.process_entry(path, mod_path, xse_scriptfiles)
            })
            .collect();

        // Merge all results
        Ok(self.merge_issues(results))
    }

    /// Process a single directory entry
    fn process_entry(
        &self,
        path: &Path,
        mod_path: &Path,
        xse_scriptfiles: &[String],
    ) -> Option<UnpackedIssues> {
        let mut issues = UnpackedIssues::new();

        // Get relative path for issue reporting
        let relative_path = match path.strip_prefix(mod_path) {
            Ok(p) => p,
            Err(_) => return None,
        };

        // Check if this is a directory
        if path.is_dir() {
            // Check for AnimationFileData directory
            if let Some(dir_name) = path.file_name() {
                if dir_name.to_string_lossy().to_lowercase() == "animationfiledata" {
                    if let Some(parent) = relative_path.parent() {
                        issues.animdata.insert(format!("  - {}\n", parent.display()));
                    }
                }
            }
            return Some(issues);
        }

        // Process files
        if !path.is_file() {
            return None;
        }

        let file_name = path.file_name()?.to_string_lossy();
        let file_name_lower = file_name.to_lowercase();
        let file_ext = path.extension()?.to_string_lossy().to_lowercase();

        // Check texture formats (TGA/PNG - should be DDS)
        if (file_ext == "tga" || file_ext == "png")
            && !self.is_bodyslide_file(path)
        {
            issues.tex_frmt.insert(format!(
                "  - {} : {}\n",
                file_ext.to_uppercase(),
                relative_path.display()
            ));
            return Some(issues);
        }

        // Check sound formats (MP3/M4A - should be XWM)
        if file_ext == "mp3" || file_ext == "m4a" {
            issues.snd_frmt.insert(format!(
                "  - {} : {}\n",
                file_ext.to_uppercase(),
                relative_path.display()
            ));
            return Some(issues);
        }

        // Check for DDS files (collect for batch processing)
        if file_ext == "dds" {
            issues.dds_files.push(path.to_path_buf());
            return Some(issues);
        }

        // Check for XSE script files
        if self.is_xse_script(path, &file_name_lower, xse_scriptfiles) {
            if let Some(parent) = relative_path.parent() {
                issues.xse_file.insert(format!("  - {}\n", parent.display()));
            }
            return Some(issues);
        }

        // Check for previs/precombine files
        if file_name_lower.ends_with(".uvd") || file_name_lower.ends_with("_oc.nif") {
            if let Some(parent) = relative_path.parent() {
                issues.previs.insert(format!("  - {}\n", parent.display()));
            }
            return Some(issues);
        }

        Some(issues)
    }

    /// Check if file is in BodySlide directory
    fn is_bodyslide_file(&self, path: &Path) -> bool {
        path.components().any(|comp| {
            self.bodyslide_exceptions
                .iter()
                .any(|pattern| comp.as_os_str().to_string_lossy().contains(pattern))
        })
    }

    /// Check if file is an XSE script file
    fn is_xse_script(&self, path: &Path, file_name_lower: &str, xse_scriptfiles: &[String]) -> bool {
        // Must be in Scripts directory
        let path_str = path.to_string_lossy().to_lowercase();
        if !path_str.contains("scripts\\") && !path_str.contains("scripts/") {
            return false;
        }

        // Exclude Workshop Framework
        if path_str.contains("workshop framework") {
            return false;
        }

        // Check if filename matches any XSE script
        xse_scriptfiles
            .iter()
            .any(|script| file_name_lower == script.to_lowercase())
    }

    /// Merge multiple issue collections
    fn merge_issues(&self, issues_vec: Vec<UnpackedIssues>) -> UnpackedIssues {
        let mut merged = UnpackedIssues::new();

        for issues in issues_vec {
            merged.animdata.extend(issues.animdata);
            merged.tex_frmt.extend(issues.tex_frmt);
            merged.snd_frmt.extend(issues.snd_frmt);
            merged.xse_file.extend(issues.xse_file);
            merged.previs.extend(issues.previs);
            merged.dds_files.extend(issues.dds_files);
        }

        merged
    }
}

impl Default for UnpackedScanner {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    #[test]
    fn test_scanner_creation() {
        let scanner = UnpackedScanner::new();
        assert_eq!(scanner.bodyslide_exceptions.len(), 1);
    }

    #[test]
    fn test_texture_format_detection() {
        let temp_dir = TempDir::new().unwrap();
        let mod_path = temp_dir.path();

        // Create test TGA file
        let tga_file = mod_path.join("texture.tga");
        fs::write(&tga_file, b"test").unwrap();

        let scanner = UnpackedScanner::new();
        let issues = scanner.scan_directory(mod_path, &[]).unwrap();

        assert!(issues.tex_frmt.len() > 0);
    }

    #[test]
    fn test_sound_format_detection() {
        let temp_dir = TempDir::new().unwrap();
        let mod_path = temp_dir.path();

        // Create test MP3 file
        let mp3_file = mod_path.join("sound.mp3");
        fs::write(&mp3_file, b"test").unwrap();

        let scanner = UnpackedScanner::new();
        let issues = scanner.scan_directory(mod_path, &[]).unwrap();

        assert!(issues.snd_frmt.len() > 0);
    }

    #[test]
    fn test_dds_file_collection() {
        let temp_dir = TempDir::new().unwrap();
        let mod_path = temp_dir.path();

        // Create test DDS file
        let dds_file = mod_path.join("texture.dds");
        fs::write(&dds_file, b"test").unwrap();

        let scanner = UnpackedScanner::new();
        let issues = scanner.scan_directory(mod_path, &[]).unwrap();

        assert_eq!(issues.dds_files.len(), 1);
    }

    #[test]
    fn test_bodyslide_exclusion() {
        let temp_dir = TempDir::new().unwrap();
        let mod_path = temp_dir.path();

        // Create BodySlide directory with TGA file
        let bodyslide_dir = mod_path.join("BodySlide");
        fs::create_dir(&bodyslide_dir).unwrap();
        let tga_file = bodyslide_dir.join("texture.tga");
        fs::write(&tga_file, b"test").unwrap();

        let scanner = UnpackedScanner::new();
        let issues = scanner.scan_directory(mod_path, &[]).unwrap();

        // Should be excluded
        assert_eq!(issues.tex_frmt.len(), 0);
    }
}
