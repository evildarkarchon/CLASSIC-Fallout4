use super::*;
use serial_test::serial;
use std::path::PathBuf;

#[test]
#[serial]
fn test_register_and_get() {
    clear_all();

    register(Keys::GAME, "Fallout4".to_string());
    let game: Option<String> = get(Keys::GAME);
    assert_eq!(game, Some("Fallout4".to_string()));
}

#[test]
#[serial]
fn test_is_registered() {
    clear_all();

    assert!(!is_registered(Keys::GAME));
    register(Keys::GAME, "Fallout4".to_string());
    assert!(is_registered(Keys::GAME));
}

#[test]
#[serial]
fn test_get_nonexistent() {
    clear_all();

    let game: Option<String> = get("nonexistent");
    assert_eq!(game, None);
}

#[test]
#[serial]
fn test_convenience_functions() {
    clear_all();

    // Test set_game and get_game
    set_game("Skyrim");
    assert_eq!(get_game(), "Skyrim");

    // Test default game value
    clear_all();
    assert_eq!(get_game(), "Fallout4");

    // Test GUI mode
    clear_all();
    assert!(!is_gui_mode());
    register(Keys::IS_GUI_MODE, true);
    assert!(is_gui_mode());

    // Test local_dir
    clear_all();
    let test_path = PathBuf::from("/test/path");
    register(Keys::LOCAL_DIR, test_path.clone());
    assert_eq!(get_local_dir(), test_path);

    // Test application_dir override
    clear_all();
    assert_eq!(get_application_dir(), None);
    let app_path = PathBuf::from("/my/app");
    set_application_dir(app_path.clone());
    assert_eq!(get_application_dir(), Some(app_path));
}

#[test]
#[serial]
fn test_thread_safety() {
    use std::thread;

    clear_all();

    let handles: Vec<_> = (0..10)
        .map(|i| {
            thread::spawn(move || {
                let key = format!("thread_{}", i);
                register(&key, i);
                let value: Option<i32> = get(&key);
                assert_eq!(value, Some(i));
            })
        })
        .collect();

    for handle in handles {
        handle.join().unwrap();
    }
}
