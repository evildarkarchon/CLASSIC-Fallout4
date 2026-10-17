use super::*;
use classic_registry_core::Keys;
use serial_test::serial;

// NOTE: Tests use unique key names to avoid interference from parallel
// execution. The registry is a global DashMap singleton, so clear_all()
// in one test would wipe state set by another concurrent test.

#[test]
#[serial]
fn test_bool_round_trip() {
    registry_set_bool("cxx_test_bool", true);
    assert_eq!(reg::get::<_, bool>("cxx_test_bool"), Some(true));
    reg::unregister("cxx_test_bool");
}

#[test]
#[serial]
fn test_set_get_game() {
    registry_set_game("Skyrim");
    assert_eq!(reg::get_game(), "Skyrim");
    // Restore default
    registry_set_game("Fallout4");
}

#[test]
#[serial]
fn test_is_gui_mode() {
    registry_set_bool(Keys::IS_GUI_MODE, true);
    assert!(reg::is_gui_mode());
    // Clean up
    registry_set_bool(Keys::IS_GUI_MODE, false);
}
