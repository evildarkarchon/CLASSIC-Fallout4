#![allow(missing_docs)]

use classic_file_io_core::{EncodingDetector, FileIOCore};
use memmap2::MmapOptions;
use std::fs::File;
use std::path::Path;
use tempfile::TempDir;

const PHASE6_MMAP_SIZES: &[(usize, &str)] = &[
    (1_048_576 + 4_096, "1mb_plus_4kb"),
    (4 * 1_048_576, "4mb"),
    (16 * 1_048_576, "16mb"),
];

fn generate_utf8_content(size: usize) -> Vec<u8> {
    let line = "Fallout 4 v1.10.163 - Buffout 4 v1.26.2 - [RSP+50] 0x7FF123456789\n";
    let mut content = Vec::with_capacity(size);

    while content.len() < size {
        let remaining = size - content.len();
        if remaining >= line.len() {
            content.extend_from_slice(line.as_bytes());
        } else {
            content.extend_from_slice(&line.as_bytes()[..remaining]);
        }
    }

    content
}

fn decode_like_read_file_mmap(path: &Path, bytes: &[u8]) -> Result<String, String> {
    let detector = EncodingDetector::new();
    let encoding = detector.detect(&bytes[..bytes.len().min(8192)]);

    if encoding.name() == "UTF-8" || encoding.name() == "ASCII" {
        match std::str::from_utf8(bytes) {
            Ok(text) => return Ok(text.to_string()),
            Err(_) => {
                let (decoded, _) = encoding.decode_without_bom_handling(bytes);
                return Ok(decoded.into_owned());
            }
        }
    }

    let (decoded, had_errors) = encoding.decode_without_bom_handling(bytes);
    if had_errors {
        return Err(format!("Encoding errors in file: {}", path.display()));
    }

    Ok(decoded.into_owned())
}

#[allow(unsafe_code)]
fn map_shared(file: &File) -> Result<memmap2::Mmap, String> {
    unsafe { MmapOptions::new().map(file).map_err(|err| err.to_string()) }
}

#[allow(unsafe_code)]
fn map_copy(file: &File) -> Result<memmap2::MmapMut, String> {
    unsafe {
        MmapOptions::new()
            .map_copy(file)
            .map_err(|err| err.to_string())
    }
}

#[allow(unsafe_code)]
fn map_copy_read_only(file: &File) -> Result<memmap2::Mmap, String> {
    unsafe {
        MmapOptions::new()
            .map_copy_read_only(file)
            .map_err(|err| err.to_string())
    }
}

#[tokio::test]
async fn test_phase6_mmap_variants_preserve_decode_contract_above_threshold() {
    let temp_dir = TempDir::new().expect("create temp dir");
    let core = FileIOCore::new("utf-8", "strict", 128, 8);

    for (size, label) in PHASE6_MMAP_SIZES {
        let path = temp_dir.path().join(format!("{label}.log"));
        let fixture = generate_utf8_content(*size);
        std::fs::write(&path, &fixture).expect("write phase 6 mmap fixture");

        let expected = String::from_utf8(fixture).expect("fixture stays valid utf-8");

        let actual = core
            .read_file_mmap(&path)
            .await
            .expect("decode production mmap content");
        assert_eq!(actual, expected, "public mmap contract changed for {label}");

        let file = File::open(&path).expect("open mmap fixture");
        let shared = map_shared(&file).expect("map shared variant");
        assert_eq!(
            decode_like_read_file_mmap(&path, &shared).expect("decode shared variant"),
            expected,
            "shared mmap decode contract changed for {label}"
        );

        let copy = map_copy(&file).expect("map copy variant");
        assert_eq!(
            decode_like_read_file_mmap(&path, &copy).expect("decode copy variant"),
            expected,
            "copy mmap decode contract changed for {label}"
        );

        let copy_read_only = map_copy_read_only(&file).expect("map copy read only variant");
        assert_eq!(
            decode_like_read_file_mmap(&path, &copy_read_only)
                .expect("decode copy read only variant"),
            expected,
            "copy-read-only mmap decode contract changed for {label}"
        );
    }
}
