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
