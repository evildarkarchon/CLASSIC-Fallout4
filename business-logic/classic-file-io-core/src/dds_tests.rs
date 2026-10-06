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
