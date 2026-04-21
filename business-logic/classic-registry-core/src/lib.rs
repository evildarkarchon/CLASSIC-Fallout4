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
    get_game, get_game_path_gui, get_local_dir, get_manual_docs_gui, get_yaml_cache, is_gui_mode,
    set_game,
};

// Application directory override for binding scenarios
pub use registry::{get_application_dir, set_application_dir};

// New version-aware convenience functions
pub use registry::{get_game_version, is_version_auto_detected};

// Additional convenience functions
pub use registry::{get_game_version_string, is_enb_present, is_xse_valid};

#[cfg(test)]
#[path = "lib_tests.rs"]
mod tests;
