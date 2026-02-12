//! DDS texture file header parsing and analysis (Pure Rust)
//!
//! This module provides fast DDS (DirectDraw Surface) header parsing
//! for texture dimension validation. Supports all DDS formats including
//! BC1-BC7 compression, mipmaps, and DX10 extended headers.
//!
//! Also provides game-specific validation via [`DDSAnalyzer`], which checks
//! textures against requirements for Fallout 4, Skyrim SE, and other titles.

use std::io::Cursor;
use std::path::{Path, PathBuf};

use anyhow::Result;
use ddsfile::Dds;
use rayon::prelude::*;

/// DDS file header information for validation
#[derive(Clone, Debug)]
pub struct DDSHeader {
    /// Texture width in pixels
    pub width: u32,
    /// Texture height in pixels
    pub height: u32,
    /// Texture depth (for 3D textures)
    pub depth: u32,
    /// Number of mipmap levels
    pub mipmap_count: u32,
    /// Texture compression format (e.g., "BC7", "DXT5")
    pub format: String,
}

impl DDSHeader {
    /// Parse DDS header from bytes using ddsfile crate
    pub fn from_bytes(bytes: &[u8]) -> Result<Option<DDSHeader>> {
        // Minimum size check for DDS header
        if bytes.len() < 128 {
            return Ok(None);
        }

        // Quick magic number check before full parsing
        if bytes.len() >= 4 {
            let magic = u32::from_le_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]);
            if magic != 0x20534444 {
                // "DDS " in little-endian
                return Ok(None);
            }
        }

        // Parse using ddsfile crate
        let cursor = Cursor::new(bytes);
        let dds = match Dds::read(cursor) {
            Ok(dds) => dds,
            Err(e) => {
                // If it's not a valid DDS, return None rather than error
                // This allows batch processing to continue
                log::debug!("Failed to parse DDS: {}", e);
                return Ok(None);
            }
        };

        // Extract format information
        let format = if let Some(dxgi) = dds.get_dxgi_format() {
            format!("{:?}", dxgi)
        } else if let Some(d3d) = dds.get_d3d_format() {
            format!("{:?}", d3d)
        } else {
            "Unknown".to_string()
        };

        Ok(Some(DDSHeader {
            width: dds.get_width(),
            height: dds.get_height(),
            depth: dds.get_depth(),
            mipmap_count: dds.get_num_mipmap_levels(),
            format,
        }))
    }

    /// Check if dimensions are power of 2 (optimal for mipmaps)
    pub fn has_power_of_2_dimensions(&self) -> bool {
        is_power_of_2(self.width) && is_power_of_2(self.height)
    }

    /// Check if dimensions are valid for BC compression (multiple of 4)
    pub fn has_valid_bc_dimensions(&self) -> bool {
        self.width % 4 == 0 && self.height % 4 == 0
    }

    /// Check if dimensions are within reasonable bounds
    pub fn is_reasonable_size(&self) -> bool {
        self.width > 0 && self.width <= 16384 && self.height > 0 && self.height <= 16384
    }

    /// Check if texture has mipmaps
    pub fn has_mipmaps(&self) -> bool {
        self.mipmap_count > 1
    }

    /// Check if format is a BC compressed format
    pub fn is_bc_compressed(&self) -> bool {
        self.format.contains("Bc")
            || self.format.contains("Dxt")
            || self.format.contains("BC")
            || self.format.contains("DXT")
    }
}

/// Helper function to check if a number is a power of 2
fn is_power_of_2(n: u32) -> bool {
    n > 0 && (n & (n - 1)) == 0
}

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
/// use classic_file_io_core::dds::{DDSAnalyzer, GameTarget};
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

        if width % 2 != 0 || height % 2 != 0 {
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
    /// use classic_file_io_core::dds::{DDSAnalyzer, GameTarget};
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
mod tests {
    use super::*;
    use ddsfile::{Dds, DxgiFormat, NewDxgiParams};
    use std::io::Cursor;

    fn create_test_dds(width: u32, height: u32) -> Vec<u8> {
        let params = NewDxgiParams {
            width,
            height,
            depth: None,
            format: DxgiFormat::BC3_UNorm,
            mipmap_levels: Some(1),
            array_layers: None,
            caps2: None,
            is_cubemap: false,
            resource_dimension: ddsfile::D3D10ResourceDimension::Texture2D,
            alpha_mode: ddsfile::AlphaMode::Unknown,
        };

        let dds = Dds::new_dxgi(params).unwrap();
        let mut buffer = Vec::new();
        let mut cursor = Cursor::new(&mut buffer);
        dds.write(&mut cursor).unwrap();
        buffer
    }

    #[test]
    fn test_dds_header_parsing() {
        let dds_data = create_test_dds(2048, 1024);
        let parsed = DDSHeader::from_bytes(&dds_data).unwrap().unwrap();

        assert_eq!(parsed.width, 2048);
        assert_eq!(parsed.height, 1024);
        assert!(parsed.has_power_of_2_dimensions());
        assert!(parsed.is_reasonable_size());
        assert!(parsed.is_bc_compressed());
    }

    #[test]
    fn test_invalid_dds_header() {
        let small = vec![0u8; 100];
        assert!(DDSHeader::from_bytes(&small).unwrap().is_none());

        let mut wrong_magic = vec![0u8; 128];
        wrong_magic[0..4].copy_from_slice(&[0x00, 0x00, 0x00, 0x00]);
        assert!(DDSHeader::from_bytes(&wrong_magic).unwrap().is_none());
    }

    #[test]
    fn test_power_of_2_dimensions() {
        let dds_data = create_test_dds(1024, 512);
        let parsed = DDSHeader::from_bytes(&dds_data).unwrap().unwrap();
        assert!(parsed.has_power_of_2_dimensions());

        assert!(is_power_of_2(1));
        assert!(is_power_of_2(2));
        assert!(is_power_of_2(1024));
        assert!(!is_power_of_2(0));
        assert!(!is_power_of_2(1023));
    }

    #[test]
    fn test_bc_dimension_validation() {
        let dds_data = create_test_dds(256, 256);
        let parsed = DDSHeader::from_bytes(&dds_data).unwrap().unwrap();
        assert!(parsed.has_valid_bc_dimensions());
    }

    // ---- DDSAnalyzer tests ----

    #[test]
    fn test_analyzer_default_is_fallout4() {
        let analyzer = DDSAnalyzer::default();
        assert_eq!(analyzer.game, GameTarget::Fallout4);
    }

    #[test]
    fn test_analyzer_valid_texture_no_issues() {
        // 1024x1024 BC3 with 1 mipmap -- only issue should be "no mipmaps"
        // since mipmap_count=1 means no extra mipmaps
        let dds_data = create_test_dds(1024, 1024);
        let header = DDSHeader::from_bytes(&dds_data).unwrap().unwrap();
        let analyzer = DDSAnalyzer::new(GameTarget::Fallout4);
        let issues = analyzer.validate_header(&header);
        // mipmap_count=1 means no mipmaps, so we get the mipmap warning
        assert!(issues.iter().any(|i| i.message.contains("No mipmaps")));
        // But no dimension issues
        assert!(
            !issues
                .iter()
                .any(|i| i.message.contains("Unusual texture size"))
        );
        assert!(
            !issues
                .iter()
                .any(|i| i.message.contains("invalid dimensions"))
        );
    }

    #[test]
    fn test_analyzer_large_fallout4_texture() {
        // 8192x8192 triggers Fallout 4 warning (>4096)
        let dds_data = create_test_dds(8192, 8192);
        let header = DDSHeader::from_bytes(&dds_data).unwrap().unwrap();
        let analyzer = DDSAnalyzer::new(GameTarget::Fallout4);
        let issues = analyzer.validate_header(&header);
        assert!(
            issues
                .iter()
                .any(|i| i.message.contains("Fallout 4 performs better"))
        );
    }

    #[test]
    fn test_analyzer_large_skyrim_texture() {
        let dds_data = create_test_dds(8192, 8192);
        let header = DDSHeader::from_bytes(&dds_data).unwrap().unwrap();
        let analyzer = DDSAnalyzer::new(GameTarget::SkyrimSE);
        let issues = analyzer.validate_header(&header);
        assert!(
            issues
                .iter()
                .any(|i| i.message.contains("Skyrim SE performs better"))
        );
    }

    #[test]
    fn test_validate_dimensions_even() {
        let issues = DDSAnalyzer::validate_dimensions(1024, 512);
        assert!(issues.is_empty());
    }

    #[test]
    fn test_validate_dimensions_odd() {
        let issues = DDSAnalyzer::validate_dimensions(1023, 512);
        assert!(issues.iter().any(|i| i.message.contains("Non-even")));
    }

    #[test]
    fn test_validate_dimensions_large() {
        let issues = DDSAnalyzer::validate_dimensions(8192, 8192);
        assert!(issues.iter().any(|i| i.message.contains("Large texture")));
    }

    #[test]
    fn test_validate_file_nonexistent() {
        let analyzer = DDSAnalyzer::new(GameTarget::Fallout4);
        let issues = analyzer.validate_file(Path::new("nonexistent.dds"));
        assert_eq!(issues.len(), 1);
        assert!(issues[0].message.contains("Unable to read"));
    }

    #[test]
    fn test_validate_file_from_disk() {
        let temp_dir = tempfile::TempDir::new().unwrap();
        let dds_path = temp_dir.path().join("test.dds");
        let dds_data = create_test_dds(512, 512);
        std::fs::write(&dds_path, &dds_data).unwrap();

        let analyzer = DDSAnalyzer::new(GameTarget::Fallout4);
        let issues = analyzer.validate_file(&dds_path);
        // Should parse successfully -- only issue is "no mipmaps"
        assert!(issues.iter().all(|i| !i.message.contains("Unable to read")));
    }

    #[test]
    fn test_validate_batch() {
        let temp_dir = tempfile::TempDir::new().unwrap();

        // Create a valid DDS
        let good_path = temp_dir.path().join("good.dds");
        let good_data = create_test_dds(1024, 1024);
        std::fs::write(&good_path, &good_data).unwrap();

        // Create a non-existent path
        let bad_path = temp_dir.path().join("missing.dds");

        let analyzer = DDSAnalyzer::new(GameTarget::Fallout4);
        let results = analyzer.validate_batch(&[good_path, bad_path.clone()]);

        // The missing file should have issues
        assert!(results.iter().any(|(p, _)| p == &bad_path));
    }

    #[test]
    fn test_dds_issue_display() {
        let issue = DDSIssue {
            message: "test issue".to_string(),
        };
        assert_eq!(format!("{}", issue), "test issue");
    }
}
