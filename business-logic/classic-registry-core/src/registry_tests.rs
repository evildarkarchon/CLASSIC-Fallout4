use super::*;
use serial_test::serial;

#[test]
fn test_registry_uses_std_lazy_lock() {
    assert!(std::any::type_name_of_val(&REGISTRY).contains("LazyLock"));
}

#[test]
#[serial]
fn test_register_and_get_string() {
    clear_all();

    register("test_key", "test_value".to_string());
    let value: Option<String> = get("test_key");
    assert_eq!(value, Some("test_value".to_string()));
}

#[test]
#[serial]
fn test_register_and_get_integer() {
    clear_all();

    register("int_key", 42);
    let value: Option<i32> = get("int_key");
    assert_eq!(value, Some(42));
}

#[test]
#[serial]
fn test_register_and_get_bool() {
    clear_all();

    register("bool_key", true);
    let value: Option<bool> = get("bool_key");
    assert_eq!(value, Some(true));
}

#[test]
#[serial]
fn test_register_and_get_pathbuf() {
    clear_all();

    let path = PathBuf::from("/test/path");
    register("path_key", path.clone());
    let value: Option<PathBuf> = get("path_key");
    assert_eq!(value, Some(path));
}

#[test]
#[serial]
fn test_get_wrong_type() {
    clear_all();

    register("string_key", "value".to_string());
    let value: Option<i32> = get("string_key");
    assert_eq!(value, None);
}

#[test]
#[serial]
fn test_is_registered() {
    clear_all();

    assert!(!is_registered("test_key"));
    register("test_key", "value".to_string());
    assert!(is_registered("test_key"));
}

#[test]
#[serial]
fn test_clear_all() {
    clear_all();

    register("key1", "value1".to_string());
    register("key2", 42);
    assert!(is_registered("key1"));
    assert!(is_registered("key2"));

    clear_all();
    assert!(!is_registered("key1"));
    assert!(!is_registered("key2"));
}

#[test]
#[serial]
fn test_overwrite_value() {
    clear_all();

    register("key", "first".to_string());
    let value1: Option<String> = get("key");
    assert_eq!(value1, Some("first".to_string()));

    register("key", "second".to_string());
    let value2: Option<String> = get("key");
    assert_eq!(value2, Some("second".to_string()));
}

#[test]
#[serial]
fn test_unregister_existing() {
    clear_all();

    register("temp_key", "temp_value".to_string());
    assert!(is_registered("temp_key"));

    let removed = unregister("temp_key");
    assert!(removed);
    assert!(!is_registered("temp_key"));
}

#[test]
#[serial]
fn test_unregister_nonexistent() {
    clear_all();

    let removed = unregister("nonexistent");
    assert!(!removed);
}

#[test]
#[serial]
fn test_is_xse_valid_default() {
    clear_all();
    assert!(!is_xse_valid());
}

#[test]
#[serial]
fn test_is_xse_valid_set_true() {
    clear_all();
    register(Keys::XSE_VALID, true);
    assert!(is_xse_valid());
}

#[test]
#[serial]
fn test_is_enb_present_default() {
    clear_all();
    assert!(!is_enb_present());
}

#[test]
#[serial]
fn test_is_enb_present_set_true() {
    clear_all();
    register(Keys::ENB_PRESENT, true);
    assert!(is_enb_present());
}

#[test]
#[serial]
fn test_get_game_version_string_default() {
    clear_all();
    assert_eq!(get_game_version_string(), "auto");
}

#[test]
#[serial]
fn test_get_game_version_string_set() {
    clear_all();
    register(Keys::GAME_VERSION, "NextGen".to_string());
    assert_eq!(get_game_version_string(), "NextGen");
}

#[test]
#[serial]
fn test_get_game_version_string_vr() {
    clear_all();
    register(Keys::GAME_VERSION, "VR".to_string());
    assert_eq!(get_game_version_string(), "VR");
}
