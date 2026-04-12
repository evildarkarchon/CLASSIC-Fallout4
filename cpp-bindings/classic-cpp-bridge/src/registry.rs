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
mod tests {
    use super::*;
    use serial_test::serial;

    // NOTE: Tests use unique key names to avoid interference from parallel
    // execution. The registry is a global DashMap singleton, so clear_all()
    // in one test would wipe state set by another concurrent test.

    #[test]
    #[serial]
    fn test_string_round_trip() {
        registry_set_string("cxx_test_str", "hello".to_string());
        assert_eq!(registry_get_string("cxx_test_str"), "hello");
    }

    #[test]
    #[serial]
    fn test_bool_round_trip() {
        registry_set_bool("cxx_test_bool", true);
        assert!(registry_get_bool("cxx_test_bool"));
    }

    #[test]
    #[serial]
    fn test_i32_round_trip() {
        registry_set_i32("cxx_test_i32", 42);
        assert_eq!(registry_get_i32("cxx_test_i32"), 42);
    }

    #[test]
    #[serial]
    fn test_missing_key_defaults() {
        assert_eq!(registry_get_string("cxx_nonexistent_str"), "");
        assert!(!registry_get_bool("cxx_nonexistent_bool"));
        assert_eq!(registry_get_i32("cxx_nonexistent_i32"), -1);
    }

    #[test]
    #[serial]
    fn test_is_registered() {
        assert!(!registry_is_registered("cxx_test_reg"));
        registry_set_string("cxx_test_reg", "val".to_string());
        assert!(registry_is_registered("cxx_test_reg"));
    }

    #[test]
    #[serial]
    fn test_unregister() {
        registry_set_string("cxx_to_remove", "val".to_string());
        assert!(registry_is_registered("cxx_to_remove"));
        registry_unregister("cxx_to_remove");
        assert!(!registry_is_registered("cxx_to_remove"));
    }

    #[test]
    #[serial]
    fn test_clear_all() {
        registry_set_string("cxx_ca_a", "1".to_string());
        registry_set_bool("cxx_ca_b", true);
        registry_set_i32("cxx_ca_c", 3);
        registry_clear_all();
        assert!(!registry_is_registered("cxx_ca_a"));
        assert!(!registry_is_registered("cxx_ca_b"));
        assert!(!registry_is_registered("cxx_ca_c"));
    }

    #[test]
    #[serial]
    fn test_set_get_game() {
        registry_set_game("Skyrim");
        assert_eq!(registry_get_game(), "Skyrim");
        // Restore default
        registry_set_game("Fallout4");
    }

    #[test]
    #[serial]
    fn test_is_gui_mode() {
        registry_set_bool(&registry_key_is_gui_mode(), true);
        assert!(registry_is_gui_mode());
        // Clean up
        registry_set_bool(&registry_key_is_gui_mode(), false);
    }

    #[test]
    #[serial]
    fn test_key_constants() {
        assert!(!registry_key_game().is_empty());
        assert!(!registry_key_is_gui_mode().is_empty());
    }
}
