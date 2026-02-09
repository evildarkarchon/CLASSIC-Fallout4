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

#[macro_use]
extern crate napi_derive;

mod scanlog;
mod yaml;

/// Get the version of the classic-node bindings
#[napi]
pub fn get_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}
