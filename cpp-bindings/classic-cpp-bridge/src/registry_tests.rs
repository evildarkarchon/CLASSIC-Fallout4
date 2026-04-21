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
