//! Shared benchmark utilities for CLASSIC Rust crates.
//!
//! This module provides common configuration and fixtures for Criterion benchmarks
//! across the workspace. Individual benchmark files include this module via `#[path]`
//! attribute since it's not part of any crate's lib.rs.
//!
//! # Usage
//!
//! In benchmark files:
//!
//! ```ignore
//! #[path = "../../../../benches/common/mod.rs"]
//! mod common;
//! use common::config::configure_criterion;
//! use common::fixtures;
//! ```
//!
//! # Modules
//!
//! - [`config`]: Criterion configuration with quick/thorough modes
//! - [`fixtures`]: Test data loading and synthetic data generation

pub mod config;
pub mod fixtures;
