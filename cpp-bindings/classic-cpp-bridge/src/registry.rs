//! Global key-value registry bridge for CXX FFI.
//!
//! Bridges `classic_registry_core` which provides a thread-safe DashMap-backed
//! singleton for storing typed values (String, bool, i32) across the application.

use classic_registry_core::{self as reg, Keys};

// ── String operations ───────────────────────────────────────────────

fn registry_set_string(key: &str, value: String) {
    reg::register(key, value);
}

fn registry_get_string(key: &str) -> String {
    reg::get::<_, String>(key).unwrap_or_default()
}

// ── Bool operations ─────────────────────────────────────────────────

fn registry_set_bool(key: &str, value: bool) {
    reg::register(key, value);
}

fn registry_get_bool(key: &str) -> bool {
    reg::get::<_, bool>(key).unwrap_or(false)
}

// ── i32 operations ──────────────────────────────────────────────────

fn registry_set_i32(key: &str, value: i32) {
    reg::register(key, value);
}

fn registry_get_i32(key: &str) -> i32 {
    reg::get::<_, i32>(key).unwrap_or(-1)
}

// ── General operations ──────────────────────────────────────────────

fn registry_is_registered(key: &str) -> bool {
    reg::is_registered(key)
}

fn registry_unregister(key: &str) {
    reg::unregister(key);
}

fn registry_clear_all() {
    reg::clear_all();
}

// ── Convenience functions ───────────────────────────────────────────

fn registry_set_game(game: &str) {
    reg::set_game(game);
}

fn registry_get_game() -> String {
    reg::get_game()
}

fn registry_is_gui_mode() -> bool {
    reg::is_gui_mode()
}

fn registry_key_game() -> String {
    Keys::GAME.to_string()
}

fn registry_key_is_gui_mode() -> String {
    Keys::IS_GUI_MODE.to_string()
}

#[cxx::bridge(namespace = "classic::registry")]
mod ffi {
    extern "Rust" {
        // String get/set
        fn registry_set_string(key: &str, value: String);
        fn registry_get_string(key: &str) -> String;

        // Bool get/set
        fn registry_set_bool(key: &str, value: bool);
        fn registry_get_bool(key: &str) -> bool;

        // i32 get/set
        fn registry_set_i32(key: &str, value: i32);
        fn registry_get_i32(key: &str) -> i32;

        // General
        fn registry_is_registered(key: &str) -> bool;
        fn registry_unregister(key: &str);
        fn registry_clear_all();

        // Convenience
        fn registry_set_game(game: &str);
        fn registry_get_game() -> String;
        fn registry_is_gui_mode() -> bool;

        // Key constants
        fn registry_key_game() -> String;
        fn registry_key_is_gui_mode() -> String;
    }
}

#[cfg(test)]
#[path = "registry_tests.rs"]
mod tests;
