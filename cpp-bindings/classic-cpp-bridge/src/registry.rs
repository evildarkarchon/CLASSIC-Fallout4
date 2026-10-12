//! Global key-value registry bridge for CXX FFI.
//!
//! Bridges `classic_registry_core` which provides a thread-safe DashMap-backed
//! singleton for storing typed values (String, bool, i32) across the application.
//! Only the writes the CLI and GUI make cross the bridge; readers stay in Rust.

use classic_registry_core as reg;

// ── Bool operations ─────────────────────────────────────────────────

fn registry_set_bool(key: &str, value: bool) {
    reg::register(key, value);
}

// ── Convenience functions ───────────────────────────────────────────

fn registry_set_game(game: &str) {
    reg::set_game(game);
}

#[cxx::bridge(namespace = "classic::registry")]
mod ffi {
    extern "Rust" {
        // Bool set
        fn registry_set_bool(key: &str, value: bool);

        // Convenience
        fn registry_set_game(game: &str);
    }
}

#[cfg(test)]
#[path = "registry_tests.rs"]
mod tests;
