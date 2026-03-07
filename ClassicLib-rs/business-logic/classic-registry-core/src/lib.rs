//! Global registry for singleton management in CLASSIC.
//!
//! This crate provides a thread-safe global registry for storing and retrieving
//! singleton instances and configuration values across the CLASSIC application.
//!
//! # Features
//!
//! - **Thread-Safe**: All operations are protected by efficient concurrent data structures
//! - **Type-Safe**: Values are stored with their concrete types
//! - **Predefined Keys**: Common registry keys are provided via the `Keys` struct
//! - **Flexible Storage**: Support for any type that implements `Send + Sync`
//!
//! # Architecture
//!
//! The registry uses a `DashMap` for lock-free concurrent access with minimal contention.
//! Values are stored as `Arc<dyn Any + Send + Sync>` to allow dynamic typing while
//! maintaining thread safety.
//!
//! # Examples
//!
//! ```rust
//! use classic_registry_core::{register, get, is_registered, Keys};
//! use std::path::PathBuf;
//!
//! // Register a value
//! register(Keys::GAME, "Fallout4".to_string());
//! register(Keys::LOCAL_DIR, PathBuf::from("/path/to/game"));
//!
//! // Check if registered
//! assert!(is_registered(Keys::GAME));
//!
//! // Retrieve values
//! let game: Option<String> = get(Keys::GAME);
//! assert_eq!(game, Some("Fallout4".to_string()));
//!
//! let local_dir: Option<PathBuf> = get(Keys::LOCAL_DIR);
//! assert_eq!(local_dir, Some(PathBuf::from("/path/to/game")));
//! ```

mod keys;
mod registry;

pub use keys::Keys;
pub use registry::{clear_all, get, is_registered, register, unregister};

// Convenience functions matching Python API
pub use registry::{
    get_game, get_game_path_gui, get_local_dir, get_manual_docs_gui, get_vr, get_yaml_cache,
    is_gui_mode, set_game,
};

// New version-aware convenience functions
pub use registry::{get_game_version, is_version_auto_detected};

// Additional convenience functions
pub use registry::{
    get_config_suffix, get_game_version_string, is_enb_present, is_vr_version, is_xse_valid,
};

#[cfg(test)]
mod tests {
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
}
