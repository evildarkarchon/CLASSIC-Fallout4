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

    assert!(!issues.tex_frmt.is_empty());
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

    assert!(!issues.snd_frmt.is_empty());
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
