//! Web bridge for CXX FFI.
//!
//! Bridges the `classic-web-core` user-agent helper the GUI sends with its
//! web requests. The bridge is consumer-driven: URL validation, URL composition
//! and mod-site helpers stay Rust-only until a frontend calls them.
//!
//! # Examples
//!
//! ```cpp
//! // C++ usage
//! auto ua = classic::web::web_get_user_agent();
//! // → "CLASSIC/8.0.0"
//! ```

use classic_web_core::get_user_agent as core_get_user_agent;

// ─────────────────────────────────────────────────────────────────────────────
// User-agent helpers
// ─────────────────────────────────────────────────────────────────────────────

fn web_get_user_agent() -> String {
    core_get_user_agent()
}

// ─────────────────────────────────────────────────────────────────────────────
// CXX bridge block
// ─────────────────────────────────────────────────────────────────────────────

#[cxx::bridge(namespace = "classic::web")]
mod ffi {
    extern "Rust" {
        // ── User-agent helpers ───────────────────────────────────────────────

        /// Get the CLASSIC user agent string (e.g. `"CLASSIC/8.0.0"`).
        fn web_get_user_agent() -> String;
    }
}

#[cfg(test)]
#[path = "web_tests.rs"]
mod tests;
