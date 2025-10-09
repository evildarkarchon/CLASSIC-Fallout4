//! CLASSIC File I/O Core - Pure Rust file operations
//!
//! This crate provides the core file I/O operations for CLASSIC without any PyO3 dependencies.
//! It can be used directly by Rust applications (CLI/TUI) or through the Python bindings
//! in classic-file-io-py.
//!
//! ## Features
//! - Async file operations with Tokio
//! - Memory-mapped file support
//! - DDS header parsing
//! - Parallel directory traversal
//! - Multi-level caching
//! - Encoding detection

pub mod core;
pub mod dds;
pub mod encoding;
pub mod error;

pub use core::FileIOCore;
pub use dds::DDSHeader;
pub use encoding::EncodingDetector;
pub use error::FileIOError;
