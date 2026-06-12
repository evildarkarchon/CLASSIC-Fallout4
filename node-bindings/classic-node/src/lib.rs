//! CLASSIC Node.js/Bun Bindings
//!
//! This crate provides NAPI-RS bindings for CLASSIC's pure Rust business logic crates.
//! It is the Node.js/Bun equivalent of the PyO3 `-py` crates.
//!
//! ## Architecture
//! This is a THIN ADAPTER layer that:
//! - Delegates all business logic to `-core` crates
//! - Only handles JavaScript <-> Rust type conversions
//! - Respects the ONE RUNTIME RULE via `classic_shared_core::get_runtime()`
//!
//! ## Modules
//! - **Wave 1** (Core Infrastructure): shared, version, message
//! - **Wave 2** (Complete Existing): yaml, scanlog
//! - **Wave 3** (File I/O & Data): fileio, database, settings, config
//! - **Wave 4** (Game Analysis): scangame, path, xse, version_registry
//! - **Wave 5** (Utilities & Polish): resource, web, update

#[macro_use]
extern crate napi_derive;

// Wave 1: Core Infrastructure
mod crashgen_rules;
mod logging_contract;
mod message;
mod runtime;
mod shared;
mod version;

// Wave 2: Complete Existing Modules
mod scanlog;

// Wave 3: File I/O & Data
mod config;
mod database;
mod fileio;
mod settings;

// Wave 4: Game Analysis
mod path;
mod scangame;
mod version_registry;
mod xse;

// Wave 5: Utilities & Polish
mod resource;
mod update;
mod web;

/// Get the version of the classic-node bindings
#[napi]
pub fn get_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}
