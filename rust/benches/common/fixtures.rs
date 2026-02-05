//! Benchmark fixtures for loading test data and generating synthetic content.
//!
//! This module is included via `#[path]` attribute from individual benchmark files,
//! so some items may appear unused depending on which benchmark uses this module.

#![allow(dead_code)]
#![allow(unused_imports)]
//!
//! This module provides utilities for loading real crash logs and generating
//! synthetic data for benchmark scaling tests.
//!
//! # Fixture Categories
//!
//! Crash logs are categorized by size:
//!
//! | Category | Size Range  | Typical Use Case          |
//! |----------|-------------|---------------------------|
//! | Small    | ~12-15 KB   | Quick iteration           |
//! | Medium   | ~40-55 KB   | Realistic workload        |
//! | Large    | ~100+ KB    | Stress testing            |
//! | XLarge   | ~1 MB+      | Extreme performance tests |
//!
//! # Performance Characteristics
//!
//! - File loading uses `std::fs::read_to_string` (runtime I/O)
//! - Synthetic generation is pure computation (no I/O)
//! - For repeated benchmarks, consider caching loaded fixtures
//!
//! # Example
//!
//! ```ignore
//! use common::fixtures::{load_crash_log_fixture, generate_synthetic_lines};
//!
//! // Load a real crash log
//! let log = load_crash_log_fixture("small");
//!
//! // Generate synthetic data for scaling tests
//! let lines = generate_synthetic_lines(10000);
//! ```

use std::fs;
use std::path::{Path, PathBuf};

/// Size category for crash log fixtures.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FixtureSize {
    /// Small logs (~12-15 KB) - fast iteration
    Small,
    /// Medium logs (~40-55 KB) - realistic workload
    Medium,
    /// Large logs (~100 KB+) - stress testing
    Large,
    /// Extra large logs (~1 MB+) - extreme performance tests
    XLarge,
}

impl FixtureSize {
    /// Returns the approximate size range in bytes for this category.
    pub fn size_range(&self) -> (usize, usize) {
        match self {
            FixtureSize::Small => (10_000, 20_000),
            FixtureSize::Medium => (35_000, 70_000),
            FixtureSize::Large => (100_000, 500_000),
            FixtureSize::XLarge => (1_000_000, usize::MAX),
        }
    }
}

/// Returns the path to the sample_logs/FO4 directory.
///
/// This function searches for the sample_logs directory relative to
/// common Rust build locations (workspace root, target directory).
fn find_sample_logs_dir() -> Option<PathBuf> {
    // Try relative paths from typical cargo bench working directories
    let candidates = [
        // From rust/ directory (cargo bench runs here)
        PathBuf::from("../sample_logs/FO4"),
        // From project root
        PathBuf::from("sample_logs/FO4"),
        // From target directory
        PathBuf::from("../../sample_logs/FO4"),
        PathBuf::from("../../../sample_logs/FO4"),
    ];

    for candidate in candidates {
        if candidate.exists() && candidate.is_dir() {
            return Some(candidate);
        }
    }

    // Try using CARGO_MANIFEST_DIR if available
    if let Ok(manifest_dir) = std::env::var("CARGO_MANIFEST_DIR") {
        let from_manifest = PathBuf::from(manifest_dir)
            .parent()? // Go up from crate dir
            .parent()? // Go up from category dir (business-logic, etc.)
            .join("sample_logs/FO4");
        if from_manifest.exists() {
            return Some(from_manifest);
        }
    }

    None
}

/// Returns the path to the CLASSIC Data/databases directory.
fn find_databases_dir() -> Option<PathBuf> {
    let candidates = [
        PathBuf::from("../CLASSIC Data/databases"),
        PathBuf::from("CLASSIC Data/databases"),
        PathBuf::from("../../CLASSIC Data/databases"),
        PathBuf::from("../../../CLASSIC Data/databases"),
    ];

    for candidate in candidates {
        if candidate.exists() && candidate.is_dir() {
            return Some(candidate);
        }
    }

    if let Ok(manifest_dir) = std::env::var("CARGO_MANIFEST_DIR") {
        let from_manifest = PathBuf::from(manifest_dir)
            .parent()?
            .parent()?
            .join("CLASSIC Data/databases");
        if from_manifest.exists() {
            return Some(from_manifest);
        }
    }

    None
}

/// Loads a crash log fixture by size category.
///
/// Returns the content of a crash log file matching the specified size category.
/// If no exact match is found, returns the closest available file.
///
/// # Arguments
///
/// * `size` - The desired size category for the fixture
///
/// # Returns
///
/// The crash log content as a String, or an error message if loading fails.
///
/// # Performance
///
/// This function performs file I/O on each call. For repeated benchmarks,
/// consider caching the result.
///
/// # Example
///
/// ```ignore
/// let small_log = load_crash_log_by_size(FixtureSize::Small);
/// let large_log = load_crash_log_by_size(FixtureSize::Large);
/// ```
pub fn load_crash_log_by_size(size: FixtureSize) -> String {
    let dir = match find_sample_logs_dir() {
        Some(d) => d,
        None => {
            return format!(
                "ERROR: Could not find sample_logs/FO4 directory. \
                 Run benchmarks from project root or rust/ directory."
            );
        }
    };

    let (min_size, max_size) = size.size_range();

    // Find files matching the size range
    let entries: Vec<_> = match fs::read_dir(&dir) {
        Ok(entries) => entries
            .filter_map(|e| e.ok())
            .filter(|e| {
                e.path().extension().map(|ext| ext == "log").unwrap_or(false)
            })
            .filter_map(|e| {
                let metadata = e.metadata().ok()?;
                let file_size = metadata.len() as usize;
                if file_size >= min_size && file_size <= max_size {
                    Some((e.path(), file_size))
                } else {
                    None
                }
            })
            .collect(),
        Err(e) => {
            return format!("ERROR: Could not read sample_logs directory: {}", e);
        }
    };

    if entries.is_empty() {
        // Fall back to any log file if no exact match
        return load_crash_log_fixture("any");
    }

    // Pick a file from the middle of the range for consistency
    let (path, _) = &entries[entries.len() / 2];

    match fs::read_to_string(path) {
        Ok(content) => content,
        Err(e) => format!("ERROR: Could not read {}: {}", path.display(), e),
    }
}

/// Loads a crash log fixture by name pattern or size.
///
/// Accepts either:
/// - Size categories: "small", "medium", "large", "xlarge"
/// - Literal name: exact filename (without extension)
/// - "any": returns the first available log file
///
/// # Arguments
///
/// * `name` - Size category, filename pattern, or "any"
///
/// # Returns
///
/// The crash log content as a String.
///
/// # Example
///
/// ```ignore
/// let log = load_crash_log_fixture("small");
/// let specific = load_crash_log_fixture("crash-0DB9300");
/// ```
pub fn load_crash_log_fixture(name: &str) -> String {
    // Check for size categories
    match name.to_lowercase().as_str() {
        "small" => return load_crash_log_by_size(FixtureSize::Small),
        "medium" => return load_crash_log_by_size(FixtureSize::Medium),
        "large" => return load_crash_log_by_size(FixtureSize::Large),
        "xlarge" | "xl" => return load_crash_log_by_size(FixtureSize::XLarge),
        _ => {}
    }

    let dir = match find_sample_logs_dir() {
        Some(d) => d,
        None => {
            return format!(
                "ERROR: Could not find sample_logs/FO4 directory. \
                 Run benchmarks from project root or rust/ directory."
            );
        }
    };

    // Handle "any" - return first available log
    if name.to_lowercase() == "any" {
        if let Ok(mut entries) = fs::read_dir(&dir) {
            if let Some(Ok(entry)) = entries.find(|e| {
                e.as_ref()
                    .ok()
                    .map(|e| e.path().extension().map(|ext| ext == "log").unwrap_or(false))
                    .unwrap_or(false)
            }) {
                if let Ok(content) = fs::read_to_string(entry.path()) {
                    return content;
                }
            }
        }
        return "ERROR: No log files found in sample_logs/FO4".to_string();
    }

    // Try exact filename match
    let filename = if name.ends_with(".log") {
        name.to_string()
    } else {
        format!("{}.log", name)
    };

    let path = dir.join(&filename);
    if path.exists() {
        return fs::read_to_string(&path).unwrap_or_else(|e| {
            format!("ERROR: Could not read {}: {}", path.display(), e)
        });
    }

    // Try partial match
    if let Ok(entries) = fs::read_dir(&dir) {
        for entry in entries.filter_map(|e| e.ok()) {
            let file_name = entry.file_name();
            if file_name.to_string_lossy().contains(name) {
                if let Ok(content) = fs::read_to_string(entry.path()) {
                    return content;
                }
            }
        }
    }

    format!("ERROR: Could not find crash log matching '{}'", name)
}

/// Loads a YAML fixture from the databases directory.
///
/// # Arguments
///
/// * `name` - YAML filename (with or without .yaml extension)
///
/// # Returns
///
/// The YAML content as a String.
///
/// # Example
///
/// ```ignore
/// let yaml = load_yaml_fixture("CLASSIC Main");
/// let fallout_yaml = load_yaml_fixture("CLASSIC Fallout4.yaml");
/// ```
pub fn load_yaml_fixture(name: &str) -> String {
    let dir = match find_databases_dir() {
        Some(d) => d,
        None => {
            return format!(
                "ERROR: Could not find 'CLASSIC Data/databases' directory. \
                 Run benchmarks from project root or rust/ directory."
            );
        }
    };

    let filename = if name.ends_with(".yaml") {
        name.to_string()
    } else {
        format!("{}.yaml", name)
    };

    let path = dir.join(&filename);
    fs::read_to_string(&path).unwrap_or_else(|e| {
        format!("ERROR: Could not read {}: {}", path.display(), e)
    })
}

/// Generates synthetic crash log lines for scaling tests.
///
/// Creates realistic-looking crash log lines including:
/// - Header lines (game version, exception info)
/// - Stack frames with addresses and module names
/// - Register dumps with pointer values
/// - Plugin/mod entries
///
/// # Arguments
///
/// * `count` - Number of lines to generate
///
/// # Returns
///
/// A vector of synthetic crash log lines.
///
/// # Performance
///
/// Pure computation, no I/O. Generation is O(n) with count.
/// Expect ~0.5-1 microseconds per line on modern hardware.
///
/// # Example
///
/// ```ignore
/// let lines = generate_synthetic_lines(10000);
/// assert_eq!(lines.len(), 10000);
/// ```
pub fn generate_synthetic_lines(count: usize) -> Vec<String> {
    let mut lines = Vec::with_capacity(count);

    // Add header lines
    let headers = [
        "Fallout 4 v1.10.163".to_string(),
        "Buffout 4 v1.26.2".to_string(),
        String::new(),
        "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x7FF7060B9300 Fallout4.exe+0DB9300".to_string(),
        String::new(),
    ];

    for header in headers.iter().take(count.min(headers.len())) {
        lines.push(header.clone());
    }

    let remaining = count.saturating_sub(headers.len());

    // Generate mixed content
    for i in 0..remaining {
        let line = match i % 10 {
            0 => format!("\t[ {}] 0x7FF{:07X}      Fallout4.exe+{:07X} -> {}+0x{:X}",
                i % 100, i * 17 % 0xFFFFFF, i * 13 % 0xFFFFFF, i * 7 % 2000000, i % 0xFFF),
            1 => format!("\t\t{}: {}",
                ["F4EE", "ActorIsHostileToActor", "CellInit", "SafeExit"][i % 4],
                if i % 2 == 0 { "true" } else { "false" }),
            2 => format!("\tR{} 0x{:016X}      ({})",
                ["AX", "BX", "CX", "DX", "SP", "BP", "SI", "DI"][i % 8],
                i as u64 * 0x1234567890,
                ["size_t", "void*", "PlayerCharacter*", "TESObjectREFR*"][i % 4]),
            3 => format!("\t\tFile: \"{}\"",
                ["", "Fallout4.esm", "DLCCoast.esm", "SomePlugin.esp"][i % 4]),
            4 => format!("\t\tForm ID: 0x{:08X}", i * 0x12345 % 0xFFFFFF),
            5 => format!("\t\tFlags: 0x{:08X}", i * 0x1111 % 0xFFFF),
            6 => format!("\t[{}] {}.dll+{:07X}", i % 100,
                ["KERNEL32", "ntdll", "f4se_1_10_163", "steam_api64"][i % 4],
                i * 0x111 % 0xFFFFFF),
            7 => format!("\t\t\tForm Type: {}", i % 200),
            8 => format!("\tPlugin: [{:02X}] {}.esp", i % 0xFF,
                ["SomeWeaponMod", "ArmorOverhaul", "QuestExpansion", "SettlementStuff"][i % 4]),
            _ => format!("\t\tObject Reference: FormID 0x{:08X}", i * 0x7777 % 0xFFFFFF),
        };
        lines.push(line);
    }

    lines
}

/// Generates synthetic YAML content for scaling tests.
///
/// Creates valid YAML documents with nested structures suitable for
/// benchmarking YAML parsing performance.
///
/// # Arguments
///
/// * `entries` - Number of top-level entries to generate
///
/// # Returns
///
/// A YAML string with the specified number of entries.
///
/// # Performance
///
/// Pure computation, no I/O. Generation is O(n) with entries.
///
/// # Example
///
/// ```ignore
/// let yaml = generate_synthetic_yaml(1000);
/// assert!(yaml.contains("entry_500:"));
/// ```
pub fn generate_synthetic_yaml(entries: usize) -> String {
    let mut yaml = String::with_capacity(entries * 200);

    yaml.push_str("# Synthetic YAML for benchmark testing\n");
    yaml.push_str("version: 1.0\n");
    yaml.push_str("generated: true\n");
    yaml.push_str("\n");
    yaml.push_str("entries:\n");

    for i in 0..entries {
        yaml.push_str(&format!("  entry_{}:\n", i));
        yaml.push_str(&format!("    name: \"Test Entry {}\"\n", i));
        yaml.push_str(&format!("    id: {}\n", i * 1000 + 100));
        yaml.push_str(&format!("    enabled: {}\n", i % 2 == 0));
        yaml.push_str(&format!("    priority: {}\n", i % 10));
        yaml.push_str("    tags:\n");
        yaml.push_str(&format!("      - tag_{}\n", i % 5));
        yaml.push_str(&format!("      - category_{}\n", i % 3));
        yaml.push_str("    metadata:\n");
        yaml.push_str(&format!("      created: 2026-01-{:02}\n", (i % 28) + 1));
        yaml.push_str(&format!("      updated: 2026-02-{:02}\n", (i % 28) + 1));
        yaml.push_str(&format!("      version: {}.{}.{}\n", i % 10, i % 100, i % 1000));
    }

    yaml
}

/// Returns a list of available fixture files with their sizes.
///
/// Useful for discovering what fixtures are available for benchmarking.
///
/// # Returns
///
/// A vector of (filename, size_in_bytes) tuples, sorted by size.
pub fn list_available_fixtures() -> Vec<(String, usize)> {
    let mut fixtures = Vec::new();

    if let Some(dir) = find_sample_logs_dir() {
        if let Ok(entries) = fs::read_dir(dir) {
            for entry in entries.filter_map(|e| e.ok()) {
                if let Ok(metadata) = entry.metadata() {
                    let name = entry.file_name().to_string_lossy().to_string();
                    if name.ends_with(".log") {
                        fixtures.push((name, metadata.len() as usize));
                    }
                }
            }
        }
    }

    fixtures.sort_by_key(|(_, size)| *size);
    fixtures
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_size_ranges() {
        assert!(FixtureSize::Small.size_range().0 < FixtureSize::Medium.size_range().0);
        assert!(FixtureSize::Medium.size_range().0 < FixtureSize::Large.size_range().0);
        assert!(FixtureSize::Large.size_range().0 < FixtureSize::XLarge.size_range().0);
    }

    #[test]
    fn test_generate_synthetic_lines() {
        let lines = generate_synthetic_lines(100);
        assert_eq!(lines.len(), 100);
        assert!(lines[0].contains("Fallout 4"));
    }

    #[test]
    fn test_generate_synthetic_lines_large() {
        let lines = generate_synthetic_lines(10000);
        assert_eq!(lines.len(), 10000);
    }

    #[test]
    fn test_generate_synthetic_yaml() {
        let yaml = generate_synthetic_yaml(10);
        assert!(yaml.contains("entry_5:"));
        assert!(yaml.contains("name:"));
        assert!(yaml.contains("tags:"));
    }

    #[test]
    fn test_generate_synthetic_yaml_structure() {
        let yaml = generate_synthetic_yaml(5);
        // Should be valid YAML structure
        assert!(yaml.starts_with("# Synthetic"));
        assert!(yaml.contains("entries:"));
        assert!(yaml.contains("entry_0:"));
        assert!(yaml.contains("entry_4:"));
    }
}
