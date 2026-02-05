//! CLASSIC GUI - Rust-native graphical interface
//!
//! This crate provides the Slint-based GUI for CLASSIC crash log analyzer.
//! It uses the existing Tokio runtime from classic-shared-core and the
//! AsyncBridge for coordinating between UI and async operations.

// Re-export for potential testing
pub use classic_shared_core::AsyncBridge;
