//! CLASSIC File I/O Core - Pure Rust file operations
//!
//! This crate provides the core file I/O operations for CLASSIC without any PyO3 dependencies.
//! It can be used directly by Rust applications (CLI/TUI) or through the Python bindings
//! in the classic-python-bindings adapter crate.
//!
//! ## Features
//! - Async file operations with Tokio
//! - Memory-mapped file support
//! - DDS header parsing
//! - Parallel directory traversal
//! - Multi-level caching
//! - Encoding detection
//! - SHA256 file hashing with caching
//!
//! Ignore/Local YAML generation and the YAML Data install, rollback, and
//! self-heal operations are owned by `classic-config-core` (#248).

pub mod core;
pub mod dds;
pub mod encoding;
pub mod error;
pub mod hash;
pub mod similarity;

// YAML Data install/rollback/self-heal (`install_atomic`, `rollback`,
// `self_heal`, and their outcomes) and Ignore/Local YAML generation
// (`FileGenerator`, `FileGeneratorConfig`, `generate_ignore_file`,
// `generate_local_yaml`) are owned by classic-config-core (#248). No re-export
// here: config depends on file I/O, so a re-export would close a dependency
// cycle.
// The game-target backup (`BackupManager`, `BackupType`, `BackupInfo`) and
// game-file operations (`GameFilesManager`, `FileOperation`,
// `FileOperationResult`) are owned by classic-resource-core (#250). No
// re-export here: resource depends on file I/O, so a re-export would close a
// dependency cycle.
pub use core::FileIOCore;
pub use dds::DDSHeader;
// Game-target DDS rules (DDSAnalyzer, GameTarget, DDSIssue) are owned by
// classic-resource-core (#249). No re-export here: resource core depends on
// file I/O, so a re-export would close a dependency cycle.
pub use encoding::EncodingDetector;
pub use error::FileIOError;
pub use hash::{FileHashScope, FileHasher};
// Crash Log collection and Targeted input resolution are owned by
// classic-scanlog-core (#254). No re-export here: scanlog depends on file I/O,
// so a re-export would close a dependency cycle.
pub use similarity::{calculate_similarity, similarity_ratio};
