//! DDS texture file header parsing with zero-copy operations
//!
//! This module provides fast DDS (DirectDraw Surface) header parsing
//! for texture dimension validation. Optimized for batch processing
//! with minimal allocations.

use anyhow::{Result, bail};

/// DDS file header structure (minimal fields for dimension checking)
#[derive(Clone, Debug)]
pub struct DDSHeader {
    pub width: u32,
    pub height: u32,
}

impl DDSHeader {
    /// Parse DDS header from bytes (zero-copy)
    pub fn from_bytes(bytes: &[u8]) -> Result<Option<DDSHeader>> {
        // Check for DDS magic number
        if bytes.len() < 128 {
            return Ok(None);
        }

        // Check DDS signature (0x20534444 = "DDS ")
        let magic = u32::from_le_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]);
        if magic != 0x20534444 {
            return Ok(None);
        }

        // DDS header structure (after magic):
        // +4: dwSize (should be 124)
        // +8: dwFlags
        // +12: dwHeight
        // +16: dwWidth

        let header_size = u32::from_le_bytes([bytes[4], bytes[5], bytes[6], bytes[7]]);
        if header_size != 124 {
            bail!("Invalid DDS header size: {}", header_size);
        }

        let height = u32::from_le_bytes([bytes[12], bytes[13], bytes[14], bytes[15]]);
        let width = u32::from_le_bytes([bytes[16], bytes[17], bytes[18], bytes[19]]);

        Ok(Some(DDSHeader { width, height }))
    }

    /// Check if dimensions are power of 2 (required for mipmaps)
    pub fn has_valid_dimensions(&self) -> bool {
        self.width % 2 == 0 && self.height % 2 == 0
    }

    /// Check if dimensions are within reasonable bounds
    pub fn is_reasonable_size(&self) -> bool {
        self.width > 0 && self.width <= 16384 &&
        self.height > 0 && self.height <= 16384
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dds_header_parsing() {
        // Create a minimal valid DDS header
        let mut header = vec![0u8; 128];

        // Magic number "DDS "
        header[0..4].copy_from_slice(&[0x44, 0x44, 0x53, 0x20]);

        // Header size (124)
        header[4..8].copy_from_slice(&124u32.to_le_bytes());

        // Height (1024)
        header[12..16].copy_from_slice(&1024u32.to_le_bytes());

        // Width (2048)
        header[16..20].copy_from_slice(&2048u32.to_le_bytes());

        let parsed = DDSHeader::from_bytes(&header).unwrap().unwrap();
        assert_eq!(parsed.width, 2048);
        assert_eq!(parsed.height, 1024);
        assert!(parsed.has_valid_dimensions());
    }

    #[test]
    fn test_invalid_dds_header() {
        // Too small
        let small = vec![0u8; 100];
        assert!(DDSHeader::from_bytes(&small).unwrap().is_none());

        // Wrong magic
        let mut wrong_magic = vec![0u8; 128];
        wrong_magic[0..4].copy_from_slice(&[0x00, 0x00, 0x00, 0x00]);
        assert!(DDSHeader::from_bytes(&wrong_magic).unwrap().is_none());
    }

    #[test]
    fn test_odd_dimensions() {
        let mut header = vec![0u8; 128];
        header[0..4].copy_from_slice(&[0x44, 0x44, 0x53, 0x20]);
        header[4..8].copy_from_slice(&124u32.to_le_bytes());
        header[12..16].copy_from_slice(&1023u32.to_le_bytes()); // Odd height
        header[16..20].copy_from_slice(&2048u32.to_le_bytes());

        let parsed = DDSHeader::from_bytes(&header).unwrap().unwrap();
        assert!(!parsed.has_valid_dimensions());
    }
}
