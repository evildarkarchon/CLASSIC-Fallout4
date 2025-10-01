//! Tests for the file I/O module

use classic_core::file_io::{RustFileIOCore, DDSHeader, EncodingDetector};
use std::fs;
use std::path::PathBuf;
use tempfile::TempDir;

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
    // Create a valid DDS header
    let mut header = vec![0u8; 128];

    // Magic number "DDS "
    header[0..4].copy_from_slice(b"DDS ");

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
    assert!(parsed.is_reasonable_size());
}

#[test]
fn test_dds_invalid_dimensions() {
    let mut header = vec![0u8; 128];
    header[0..4].copy_from_slice(b"DDS ");
    header[4..8].copy_from_slice(&124u32.to_le_bytes());

    // Odd dimensions (not power of 2 compatible)
    header[12..16].copy_from_slice(&1023u32.to_le_bytes());
    header[16..20].copy_from_slice(&2047u32.to_le_bytes());

    let parsed = DDSHeader::from_bytes(&header).unwrap().unwrap();
    assert!(!parsed.has_valid_dimensions());
}

#[test]
fn test_dds_unreasonable_size() {
    let mut header = vec![0u8; 128];
    header[0..4].copy_from_slice(b"DDS ");
    header[4..8].copy_from_slice(&124u32.to_le_bytes());

    // Too large dimensions
    header[12..16].copy_from_slice(&20000u32.to_le_bytes());
    header[16..20].copy_from_slice(&20000u32.to_le_bytes());

    let parsed = DDSHeader::from_bytes(&header).unwrap().unwrap();
    assert!(!parsed.is_reasonable_size());
}

#[cfg(test)]
mod integration_tests {
    use super::*;
    use pyo3::prelude::*;

    #[test]
    fn test_rust_file_io_core_creation() {
        pyo3::prepare_freethreaded_python();

        Python::attach(|py| {
            let io_core = RustFileIOCore::new(
                "utf-8".to_string(),
                "ignore".to_string(),
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
        pyo3::prepare_freethreaded_python();

        Python::attach(|py| {
            let io_core = RustFileIOCore::new(
                "utf-8".to_string(),
                "ignore".to_string(),
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
        pyo3::prepare_freethreaded_python();

        Python::attach(|py| {
            let io_core = RustFileIOCore::new(
                "utf-8".to_string(),
                "ignore".to_string(),
                100,
                50,
            ).unwrap();

            let temp_dir = TempDir::new().unwrap();
            let dds_file = temp_dir.path().join("test.dds");

            // Create a valid DDS file
            let mut header = vec![0u8; 128];
            header[0..4].copy_from_slice(b"DDS ");
            header[4..8].copy_from_slice(&124u32.to_le_bytes());
            header[12..16].copy_from_slice(&1024u32.to_le_bytes());
            header[16..20].copy_from_slice(&2048u32.to_le_bytes());

            fs::write(&dds_file, &header).unwrap();

            // Test DDS header reading
            let dimensions = io_core.py_read_dds_header(py, dds_file.to_string_lossy().to_string()).unwrap();
            assert_eq!(dimensions, Some((2048, 1024)));

            // Test batch DDS processing
            let mut dds_files = vec![];
            for i in 0..3 {
                let path = temp_dir.path().join(format!("texture_{}.dds", i));
                let mut h = header.clone();
                h[12..16].copy_from_slice(&((i + 1) * 256u32).to_le_bytes());
                h[16..20].copy_from_slice(&((i + 1) * 512u32).to_le_bytes());
                fs::write(&path, &h).unwrap();
                dds_files.push(path.to_string_lossy().to_string());
            }

            let results = io_core.py_read_dds_headers_batch(py, dds_files.clone()).unwrap();
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
        pyo3::prepare_freethreaded_python();

        Python::attach(|py| {
            let io_core = RustFileIOCore::new(
                "utf-8".to_string(),
                "ignore".to_string(),
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
            assert_eq!(files.len().unwrap(), 5);

            // Walk with pattern (only .txt files)
            let txt_files = io_core.py_walk_directory(
                py,
                temp_dir.path().to_string_lossy().to_string(),
                Some(r"\.txt$".to_string()),
                None,
            ).unwrap();

            let txt_list = txt_files.bind(py);
            assert_eq!(txt_list.len().unwrap(), 3);

            // Walk with max depth
            let shallow_files = io_core.py_walk_directory(
                py,
                temp_dir.path().to_string_lossy().to_string(),
                None,
                Some(1),
            ).unwrap();

            let shallow_list = shallow_files.bind(py);
            // Should not include nested/file5.txt
            assert!(shallow_list.len().unwrap() < 5);
        });
    }
}
