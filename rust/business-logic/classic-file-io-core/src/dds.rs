//! DDS texture file header parsing (Pure Rust)
//!
//! This module provides fast DDS (DirectDraw Surface) header parsing
//! for texture dimension validation. Supports all DDS formats including
//! BC1-BC7 compression, mipmaps, and DX10 extended headers.

use anyhow::Result;
use ddsfile::Dds;
use std::io::Cursor;

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
}
