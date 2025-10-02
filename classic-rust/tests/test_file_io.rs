//! Tests for the file I/O module

use classic_core::file_io::{RustFileIOCore, DDSHeader, EncodingDetector};
use ddsfile::Dds;
use std::fs;
use std::io::Cursor;
use tempfile::TempDir;

/// Helper to create a valid DDS file with specified dimensions
fn create_dds_bytes(width: u32, height: u32) -> Vec<u8> {
    // Create minimal valid DDS using ddsfile crate
    let data = vec![0u8; (width * height / 2) as usize]; // DXT1 is 0.5 bytes per pixel

    let params = ddsfile::NewD3dParams {
        height,
        width,
        depth: None,
        format: ddsfile::D3DFormat::DXT1,
        mipmap_levels: None,
        caps2: None,
    };

    let mut dds = Dds::new_d3d(params).unwrap();
    dds.data = data;

    let mut cursor = Cursor::new(Vec::new());
    dds.write(&mut cursor).unwrap();
    cursor.into_inner()
}

#[test]
fn test_encoding_detection() {
    let detector = EncodingDetector::new();

    // UTF-8 content
    let utf8_bytes = "Hello, 世界".as_bytes();
    let encoding = detector.detect(utf8_bytes);
    assert_eq!(encoding.name(), "UTF-8");

    // UTF-8 with BOM
    let utf8_bom = b"\xEF\xBB\xBFHello";
    let encoding = detector.detect(utf8_bom);
    assert_eq!(encoding.name(), "UTF-8");

    // Invalid UTF-8 (should fall back to Windows-1252)
    let invalid_utf8 = b"\xFF\xFE\xFD";
    let encoding = detector.detect(invalid_utf8);
    assert_eq!(encoding.name(), "windows-1252");
}

#[test]
fn test_dds_header_parsing() {
    // Create a valid DDS file with proper header
    let dds_bytes = create_dds_bytes(2048, 1024);

    let result = DDSHeader::from_bytes(&dds_bytes).unwrap();
    assert!(result.is_some(), "Should parse valid DDS header");
    let parsed = result.unwrap();
    assert_eq!(parsed.width, 2048);
    assert_eq!(parsed.height, 1024);
    assert!(parsed.has_valid_bc_dimensions());
    assert!(parsed.is_reasonable_size());
}

#[test]
fn test_dds_invalid_dimensions() {
    // Create DDS with odd dimensions (not multiple of 4)
    let dds_bytes = create_dds_bytes(1023, 2047);

    let result = DDSHeader::from_bytes(&dds_bytes).unwrap();
    assert!(result.is_some(), "Should parse DDS header even with invalid BC dimensions");
    let parsed = result.unwrap();
    assert!(!parsed.has_valid_bc_dimensions());
}

#[test]
fn test_dds_unreasonable_size() {
    // Create DDS with too-large dimensions (exceeds 16384 limit)
    let dds_bytes = create_dds_bytes(20000, 20000);

    let result = DDSHeader::from_bytes(&dds_bytes).unwrap();
    assert!(result.is_some(), "Should parse DDS header even with unreasonable size");
    let parsed = result.unwrap();
    assert!(!parsed.is_reasonable_size());
}

#[cfg(test)]
mod integration_tests {
    use super::*;
    use pyo3::prelude::*;

    #[test]
    fn test_rust_file_io_core_creation() {
        pyo3::Python::initialize();

        Python::attach(|py| {
            let io_core = RustFileIOCore::new(
                "utf-8",
                "ignore",
                100,
                50,
            ).unwrap();

            // Test basic operations
            let temp_dir = TempDir::new().unwrap();
            let test_file = temp_dir.path().join("test.txt");
            let test_content = "Test content";

            // Write file
            fs::write(&test_file, test_content).unwrap();

            // Read file through Rust core
            let content = io_core.py_read_file(py, test_file.to_string_lossy().to_string()).unwrap();
            assert_eq!(content, test_content);

            // Test cache clearing
            io_core.clear_cache(py).unwrap();
        });
    }

    #[test]
    fn test_file_operations() {
        pyo3::Python::initialize();

        Python::attach(|py| {
            let io_core = RustFileIOCore::new(
                "utf-8",
                "ignore",
                100,
                50,
            ).unwrap();

            let temp_dir = TempDir::new().unwrap();

            // Test write and read
            let test_file = temp_dir.path().join("write_test.txt");
            let content = "Hello from Rust!";

            io_core.py_write_file(py, test_file.to_string_lossy().to_string(), content.to_string()).unwrap();

            let read_content = io_core.py_read_file(py, test_file.to_string_lossy().to_string()).unwrap();
            assert_eq!(read_content, content);

            // Test lines
            let lines_file = temp_dir.path().join("lines.txt");
            let lines = vec!["Line 1".to_string(), "Line 2".to_string(), "Line 3".to_string()];

            io_core.py_write_lines(py, lines_file.to_string_lossy().to_string(), lines.clone()).unwrap();

            let read_lines = io_core.py_read_lines(py, lines_file.to_string_lossy().to_string()).unwrap();
            assert_eq!(read_lines, lines);

            // Test file existence
            assert!(io_core.file_exists(py, test_file.to_string_lossy().to_string()));
            assert!(!io_core.file_exists(py, temp_dir.path().join("nonexistent.txt").to_string_lossy().to_string()));

            // Test file size
            let size = io_core.get_file_size(py, test_file.to_string_lossy().to_string());
            assert_eq!(size, content.len() as i64);
        });
    }

    #[test]
    fn test_dds_operations() {
        pyo3::Python::initialize();

        Python::attach(|py| {
            let io_core = RustFileIOCore::new(
                "utf-8",
                "ignore",
                100,
                50,
            ).unwrap();

            let temp_dir = TempDir::new().unwrap();
            let dds_file = temp_dir.path().join("test.dds");

            // Create a valid DDS file using helper
            let dds_bytes = create_dds_bytes(2048, 1024);
            fs::write(&dds_file, &dds_bytes).unwrap();

            // Test DDS header reading
            let dimensions = io_core.read_dds_header(py, dds_file.to_string_lossy().to_string()).unwrap();
            assert_eq!(dimensions, Some((2048, 1024)));

            // Test batch DDS processing
            let mut dds_files = vec![];
            for i in 0..3 {
                let path = temp_dir.path().join(format!("texture_{}.dds", i));
                let width = (i + 1) * 512;
                let height = (i + 1) * 256;
                let bytes = create_dds_bytes(width, height);
                fs::write(&path, &bytes).unwrap();
                dds_files.push(path.to_string_lossy().to_string());
            }

            let results = io_core.read_dds_headers_batch(py, dds_files.clone()).unwrap();
            let dict = results.bind(py);

            for (i, path) in dds_files.iter().enumerate() {
                let dims = dict.get_item(path).unwrap().unwrap();
                let (width, height): (u32, u32) = dims.extract().unwrap();
                assert_eq!(width, (i as u32 + 1) * 512);
                assert_eq!(height, (i as u32 + 1) * 256);
            }
        });
    }

    #[test]
    fn test_directory_traversal() {
        pyo3::Python::initialize();

        Python::attach(|py| {
            let io_core = RustFileIOCore::new(
                "utf-8",
                "ignore",
                100,
                50,
            ).unwrap();

            let temp_dir = TempDir::new().unwrap();

            // Create directory structure
            fs::create_dir_all(temp_dir.path().join("subdir1")).unwrap();
            fs::create_dir_all(temp_dir.path().join("subdir2/nested")).unwrap();

            fs::write(temp_dir.path().join("file1.txt"), "content").unwrap();
            fs::write(temp_dir.path().join("file2.py"), "code").unwrap();
            fs::write(temp_dir.path().join("subdir1/file3.txt"), "more").unwrap();
            fs::write(temp_dir.path().join("subdir2/file4.rs"), "rust").unwrap();
            fs::write(temp_dir.path().join("subdir2/nested/file5.txt"), "deep").unwrap();

            // Walk all files
            let all_files = io_core.py_walk_directory(
                py,
                temp_dir.path().to_string_lossy().to_string(),
                None,
                None,
            ).unwrap();

            let files = all_files.bind(py);
            assert_eq!(files.len(), 5);

            // Walk with pattern (only .txt files)
            let txt_files = io_core.py_walk_directory(
                py,
                temp_dir.path().to_string_lossy().to_string(),
                Some(r"\.txt$".to_string()),
                None,
            ).unwrap();

            let txt_list = txt_files.bind(py);
            assert_eq!(txt_list.len(), 3);

            // Walk with max depth
            let shallow_files = io_core.py_walk_directory(
                py,
                temp_dir.path().to_string_lossy().to_string(),
                None,
                Some(1),
            ).unwrap();

            let shallow_list = shallow_files.bind(py);
            // Should not include nested/file5.txt
            assert!(shallow_list.len() < 5);
        });
    }
}
