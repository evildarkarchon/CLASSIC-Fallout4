use super::*;

#[test]
fn test_keys_are_unique() {
    let keys = vec![
        Keys::YAML_CACHE,
        Keys::MANUAL_DOCS_GUI,
        Keys::GAME_PATH_GUI,
        Keys::GAME_PATH,
        Keys::DOCS_PATH,
        Keys::IS_GUI_MODE,
        Keys::OPEN_FILE_FUNC,
        Keys::GAME,
        Keys::GAME_VERSION,
        Keys::VERSION_AUTO_DETECTED,
        Keys::LOCAL_DIR,
        Keys::APP_DIR,
        Keys::IS_PRERELEASE,
        Keys::XSE_VALID,
        Keys::XSE_VERSION,
        Keys::ENB_PRESENT,
        Keys::GAME_VERSION_DETECTED,
    ];

    let mut unique_keys = keys.clone();
    unique_keys.sort();
    unique_keys.dedup();

    assert_eq!(keys.len(), unique_keys.len(), "Keys must be unique");
}

#[test]
fn test_key_values() {
    assert_eq!(Keys::YAML_CACHE, "yaml_cache");
    assert_eq!(Keys::GAME, "gamevars_game");
    assert_eq!(Keys::IS_GUI_MODE, "is_gui_mode");
    assert_eq!(Keys::LOCAL_DIR, "local_dir");
    assert_eq!(Keys::GAME_VERSION, "gamevars_version");
    assert_eq!(Keys::VERSION_AUTO_DETECTED, "gamevars_version_auto");
}
