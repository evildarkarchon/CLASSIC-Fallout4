//! Game-target DDS texture rules (Pure Rust)
//!
//! Resource core owns the game-specific decisions applied to DDS textures:
//! which [`GameTarget`] a scan validates against, the universal and
//! per-game texture rules in [`DDSAnalyzer`], and the [`DDSIssue`] messages
//! those rules produce for valid, missing, and malformed textures.
//!
//! Neutral DDS header parsing ([`DDSHeader`] and its dimension/format
//! predicates) stays in `classic-file-io-core`. This module consumes parsed
//! headers from there; file I/O never depends back on resource core, so the
//! analyzer is not reexported from `classic_file_io_core` (#249).

use std::path::{Path, PathBuf};

use classic_file_io_core::dds::DDSHeader;
use rayon::prelude::*;

/// Game-specific validation target
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GameTarget {
    /// Fallout 4 (default)
    Fallout4,
    /// Skyrim Special Edition
    SkyrimSE,
}

/// A single validation issue found in a DDS file
#[derive(Debug, Clone)]
pub struct DDSIssue {
    /// Human-readable description of the issue
    pub message: String,
}

impl std::fmt::Display for DDSIssue {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.message)
    }
}

/// DDS texture analyzer with game-specific validation rules
///
/// Extends the basic `DDSHeader` parsing with validation logic that
/// checks textures against game-specific requirements (dimension limits,
/// BC compression compatibility, mipmap recommendations, etc.).
///
/// # Example
///
/// ```rust,no_run
/// use classic_resource_core::dds::{DDSAnalyzer, GameTarget};
/// use std::path::Path;
///
/// let analyzer = DDSAnalyzer::new(GameTarget::Fallout4);
/// let issues = analyzer.validate_file(Path::new("texture.dds"));
/// for issue in &issues {
///     println!("Issue: {}", issue);
/// }
/// ```
pub struct DDSAnalyzer {
    /// Game target for validation rules
    game: GameTarget,
}

impl DDSAnalyzer {
    /// Create a new analyzer targeting a specific game
    pub fn new(game: GameTarget) -> Self {
        Self { game }
    }

    /// Validate a DDS file by reading its header from disk
    ///
    /// Returns a list of issues found. An empty list means the file is valid.
    /// If the file cannot be read or parsed, returns a single "Unable to read DDS header" issue.
    pub fn validate_file(&self, path: &Path) -> Vec<DDSIssue> {
        let bytes = match std::fs::read(path) {
            Ok(b) => b,
            Err(_) => {
                return vec![DDSIssue {
                    message: "Unable to read DDS file".to_string(),
                }];
            }
        };

        match DDSHeader::from_bytes(&bytes) {
            Ok(Some(header)) => self.validate_header(&header),
            Ok(None) => vec![DDSIssue {
                message: "Unable to read DDS header".to_string(),
            }],
            Err(_) => vec![DDSIssue {
                message: "Unable to read DDS header".to_string(),
            }],
        }
    }

    /// Validate a parsed DDS header against game-specific rules
    ///
    /// This is useful when you already have a parsed header and want to
    /// run validation without re-reading the file.
    pub fn validate_header(&self, header: &DDSHeader) -> Vec<DDSIssue> {
        let mut issues = Vec::new();

        // Universal checks
        if !header.is_reasonable_size() {
            issues.push(DDSIssue {
                message: format!("Unusual texture size: {}x{}", header.width, header.height),
            });
        }

        if header.is_bc_compressed() && !header.has_valid_bc_dimensions() {
            issues.push(DDSIssue {
                message: format!(
                    "BC-compressed texture has invalid dimensions (must be multiple of 4): {}x{}",
                    header.width, header.height
                ),
            });
        }

        if !header.has_power_of_2_dimensions() && header.has_mipmaps() {
            issues.push(DDSIssue {
                message: format!(
                    "Non-power-of-2 dimensions with mipmaps: {}x{}",
                    header.width, header.height
                ),
            });
        }

        if !header.has_mipmaps() {
            issues.push(DDSIssue {
                message: "No mipmaps (may cause performance issues)".to_string(),
            });
        }

        // Game-specific checks
        match self.game {
            GameTarget::Fallout4 => self.validate_fallout4(header, &mut issues),
            GameTarget::SkyrimSE => self.validate_skyrim_se(header, &mut issues),
        }

        issues
    }

    /// Fallout 4-specific texture validation
    fn validate_fallout4(&self, header: &DDSHeader, issues: &mut Vec<DDSIssue>) {
        if header.width > 4096 || header.height > 4096 {
            issues.push(DDSIssue {
                message: format!(
                    "Fallout 4 performs better with textures <=4096x4096 (got {}x{})",
                    header.width, header.height
                ),
            });
        }

        // DXT1 with alpha detection (format string contains "Dxt1" or "BC1")
        let fmt = &header.format;
        if (fmt.contains("Dxt1") || fmt.contains("DXT1") || fmt.contains("BC1"))
            && fmt.contains("UNorm")
        {
            // DXT1/BC1 with alpha may cause transparency issues
            // This is a heuristic -- the format string from ddsfile doesn't always indicate alpha
        }

        // Large uncompressed texture check
        if !header.is_bc_compressed() && header.width * header.height > 1024 * 1024 {
            issues.push(DDSIssue {
                message: "Large uncompressed texture may cause performance issues".to_string(),
            });
        }
    }

    /// Skyrim SE-specific texture validation
    fn validate_skyrim_se(&self, header: &DDSHeader, issues: &mut Vec<DDSIssue>) {
        if header.width > 4096 || header.height > 4096 {
            issues.push(DDSIssue {
                message: format!(
                    "Skyrim SE performs better with textures <=4096x4096 (got {}x{})",
                    header.width, header.height
                ),
            });
        }
    }

    /// Validate DDS dimensions from width/height only (fallback for non-parseable files)
    ///
    /// This matches the Python mmap-based fallback that only checks even dimensions.
    pub fn validate_dimensions(width: u32, height: u32) -> Vec<DDSIssue> {
        let mut issues = Vec::new();

        if !width.is_multiple_of(2) || !height.is_multiple_of(2) {
            issues.push(DDSIssue {
                message: format!("Non-even dimensions: {}x{}", width, height),
            });
        }

        if width > 4096 || height > 4096 {
            issues.push(DDSIssue {
                message: format!("Large texture dimensions: {}x{}", width, height),
            });
        }

        issues
    }

    /// Validate multiple DDS files in parallel using Rayon
    ///
    /// Returns a vector of `(path, issues)` pairs for files that had issues.
    /// Files with no issues are omitted from the result.
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// use classic_resource_core::dds::{DDSAnalyzer, GameTarget};
    /// use std::path::PathBuf;
    ///
    /// let analyzer = DDSAnalyzer::new(GameTarget::Fallout4);
    /// let files = vec![
    ///     PathBuf::from("texture1.dds"),
    ///     PathBuf::from("texture2.dds"),
    /// ];
    /// let results = analyzer.validate_batch(&files);
    /// for (path, issues) in &results {
    ///     println!("{}: {} issues", path.display(), issues.len());
    /// }
    /// ```
    pub fn validate_batch(&self, paths: &[PathBuf]) -> Vec<(PathBuf, Vec<DDSIssue>)> {
        paths
            .par_iter()
            .filter_map(|path| {
                let issues = self.validate_file(path);
                if issues.is_empty() {
                    None
                } else {
                    Some((path.clone(), issues))
                }
            })
            .collect()
    }
}

impl Default for DDSAnalyzer {
    fn default() -> Self {
        Self::new(GameTarget::Fallout4)
    }
}

#[cfg(test)]
#[path = "dds_tests.rs"]
mod tests;
