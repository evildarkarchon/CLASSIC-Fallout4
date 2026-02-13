//! classic-cpp-bridge: CXX FFI bindings for CLASSIC
//!
//! This crate exposes all CLASSIC business-logic crates to C++ via CXX FFI.
//! It follows the same thin-adapter pattern as the PyO3 and NAPI-RS bindings.
//!
//! # Architecture
//!
//! ```text
//! C++ Qt App  <-->  CXX FFI  <-->  classic-cpp-bridge (staticlib)  <-->  ~20 -core crates
//!                                   13 bridge modules
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
//! - [`yaml`] - YAML operations
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
//! ## Utilities (Wave 5)
//! - [`update`] - GitHub update checking
//! - [`message`] - Logging
//! - [`perf`] - Performance monitoring

pub mod types;
pub mod runtime;
pub mod registry;
pub mod yaml;
pub mod config;
pub mod scanner;
pub mod database;
pub mod files;
pub mod scangame;
pub mod game;
pub mod update;
pub mod message;
pub mod perf;
