//! classic-cpp-bridge: CXX FFI bindings for CLASSIC
//!
//! This crate exposes all CLASSIC business-logic crates to C++ via CXX FFI.
//! It follows the same thin-adapter pattern as the PyO3 and NAPI-RS bindings.
//!
//! # Architecture
//!
//! ```text
//! C++ Qt App  <-->  CXX FFI  <-->  classic-cpp-bridge (staticlib)  <-->  ~20 -core crates
//!                                   14 bridge modules
//!                                   Opaque types + shared DTOs
//!                                   block_on() for async wrapping
//! ```
//!
//! # ONE RUNTIME RULE
//!
//! All async operations use `classic_shared_core::get_runtime().block_on()`.
//! Never create additional Tokio runtimes.
//!
//! # Modules
//!
//! ## Foundation (Wave 1)
//! - [`types`] - Shared collection wrappers (StringMap, StringVecMap)
//! - [`runtime`] - Tokio runtime management
//! - [`registry`] - Global key-value store
//! - [`settings`] - YAML operations, settings cache, and validators
//! - [`config`] - YamlDataCore configuration loading
//!
//! ## Scanning (Wave 2)
//! - [`scanner`] - Crash log analysis (primary feature)
//! - [`database`] - FormID database
//!
//! ## File I/O (Wave 3)
//! - [`files`] - File operations, backups, log collection
//! - [`scangame`] - Game file scanning
//!
//! ## Game Support (Wave 4)
//! - [`game`] - Versions, XSE, paths
//!
//! ## Rendering (Wave 6)
//! - [`markdown`] - Markdown-to-HTML conversion for report display
//!
//! ## Utilities (Wave 5)
//! - [`update`] - GitHub update checking
//! - [`message`] - Logging
//! - [`perf`] - Performance monitoring

#[cfg(windows)]
pub mod config;
#[cfg(windows)]
pub mod constants;
#[cfg(windows)]
pub mod database;
#[cfg(windows)]
pub mod files;
#[cfg(windows)]
pub mod game;
#[cfg(windows)]
pub mod markdown;
#[cfg(windows)]
pub mod message;
#[cfg(windows)]
pub mod path;
#[cfg(windows)]
pub mod perf;
#[cfg(windows)]
pub mod registry;
#[cfg(windows)]
pub mod runtime;
#[cfg(windows)]
pub mod scangame;
#[cfg(windows)]
pub mod scanner;
#[cfg(windows)]
pub mod types;
#[cfg(windows)]
pub mod update;
#[cfg(windows)]
pub mod version_registry;
#[cfg(windows)]
pub mod web;
#[cfg(windows)]
pub mod xse;
#[cfg(windows)]
pub mod settings;

#[cfg(not(windows))]
pub const CPP_BRIDGE_UNAVAILABLE: &str = "classic-cpp-bridge is only available on Windows targets";
