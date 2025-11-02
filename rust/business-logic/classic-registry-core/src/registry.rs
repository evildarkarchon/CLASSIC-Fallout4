//! Core registry implementation using DashMap for thread-safe concurrent access.
//!
//! This module provides the global registry storage and access functions.

use dashmap::DashMap;
use std::any::Any;
use std::path::PathBuf;
use std::sync::Arc;

use crate::Keys;

/// Type alias for registry values.
///
/// Values are stored as `Arc<dyn Any + Send + Sync>` to allow dynamic typing
/// while maintaining thread safety and efficient cloning.
type RegistryValue = Arc<dyn Any + Send + Sync>;

/// Global registry storage.
///
/// Uses `DashMap` for lock-free concurrent access with minimal contention.
/// The registry is lazily initialized on first access.
static REGISTRY: once_cell::sync::Lazy<DashMap<String, RegistryValue>> =
    once_cell::sync::Lazy::new(DashMap::new);

/// Register a value in the global registry.
///
/// The value is stored with the given key and can be retrieved later using `get()`.
/// If a value already exists for the key, it will be replaced.
///
/// # Type Parameters
///
/// - `K`: Key type (must be convertible to `String`)
/// - `V`: Value type (must implement `Any + Send + Sync + 'static`)
///
/// # Arguments
///
/// * `key` - The registry key to store the value under
/// * `value` - The value to store
///
/// # Examples
///
/// ```rust
/// use classic_registry_core::{register, Keys};
///
/// register(Keys::GAME, "Fallout4".to_string());
/// register("custom_key", 42);
/// register(Keys::IS_GUI_MODE, true);
/// ```
pub fn register<K, V>(key: K, value: V)
where
    K: Into<String>,
    V: Any + Send + Sync + 'static,
{
    let key_string = key.into();
    REGISTRY.insert(key_string, Arc::new(value));
}

/// Check if a key is registered in the global registry.
///
/// # Arguments
///
/// * `key` - The registry key to check
///
/// # Returns
///
/// Returns `true` if the key exists in the registry, `false` otherwise.
///
/// # Examples
///
/// ```rust
/// use classic_registry_core::{register, is_registered, Keys};
///
/// assert!(!is_registered(Keys::GAME));
/// register(Keys::GAME, "Fallout4".to_string());
/// assert!(is_registered(Keys::GAME));
/// ```
pub fn is_registered<K>(key: K) -> bool
where
    K: AsRef<str>,
{
    REGISTRY.contains_key(key.as_ref())
}

/// Retrieve a value from the global registry.
///
/// # Type Parameters
///
/// - `K`: Key type (must be convertible to `&str`)
/// - `V`: Expected value type (must implement `Clone + Any + Send + Sync`)
///
/// # Arguments
///
/// * `key` - The registry key to retrieve
///
/// # Returns
///
/// Returns `Some(value)` if the key exists and the type matches,
/// `None` otherwise.
///
/// # Examples
///
/// ```rust
/// use classic_registry_core::{register, get, Keys};
///
/// register(Keys::GAME, "Fallout4".to_string());
///
/// let game: Option<String> = get(Keys::GAME);
/// assert_eq!(game, Some("Fallout4".to_string()));
///
/// // Wrong type returns None
/// let wrong_type: Option<i32> = get(Keys::GAME);
/// assert_eq!(wrong_type, None);
/// ```
pub fn get<K, V>(key: K) -> Option<V>
where
    K: AsRef<str>,
    V: Clone + Any + Send + Sync + 'static,
{
    REGISTRY
        .get(key.as_ref())
        .and_then(|value| value.downcast_ref::<V>().cloned())
}

/// Clear all entries from the registry.
///
/// This function is primarily used for testing to ensure clean state
/// between test runs.
///
/// # Examples
///
/// ```rust
/// use classic_registry_core::{register, clear_all, is_registered, Keys};
///
/// register(Keys::GAME, "Fallout4".to_string());
/// assert!(is_registered(Keys::GAME));
///
/// clear_all();
/// assert!(!is_registered(Keys::GAME));
/// ```
pub fn clear_all() {
    REGISTRY.clear();
}

// ============================================================================
// Convenience Functions - Match Python API
// ============================================================================

/// Get the current game name.
///
/// # Returns
///
/// Returns the game name from the registry, defaulting to "Fallout4" if not set.
///
/// # Examples
///
/// ```rust
/// use classic_registry_core::{get_game, set_game, clear_all};
///
/// clear_all();
/// assert_eq!(get_game(), "Fallout4"); // Default
///
/// set_game("Skyrim");
/// assert_eq!(get_game(), "Skyrim");
/// ```
pub fn get_game() -> String {
    get::<_, String>(Keys::GAME).unwrap_or_else(|| "Fallout4".to_string())
}

/// Set the current game name.
///
/// # Arguments
///
/// * `game_name` - The game name to set (e.g., "Fallout4", "Skyrim")
///
/// # Examples
///
/// ```rust
/// use classic_registry_core::{set_game, get_game};
///
/// set_game("Skyrim");
/// assert_eq!(get_game(), "Skyrim");
/// ```
pub fn set_game<S: Into<String>>(game_name: S) {
    register(Keys::GAME, game_name.into());
}

/// Check if the application is running in GUI mode.
///
/// # Returns
///
/// Returns `true` if GUI mode is enabled, `false` otherwise (defaults to `false`).
///
/// # Examples
///
/// ```rust
/// use classic_registry_core::{is_gui_mode, register, Keys, clear_all};
///
/// clear_all();
/// assert!(!is_gui_mode()); // Default to CLI mode
///
/// register(Keys::IS_GUI_MODE, true);
/// assert!(is_gui_mode());
/// ```
pub fn is_gui_mode() -> bool {
    get::<_, bool>(Keys::IS_GUI_MODE).unwrap_or(false)
}

/// Get the YAML settings cache instance.
///
/// # Returns
///
/// Returns the YAML cache if registered, `None` otherwise.
///
/// # Note
///
/// The actual type depends on what was registered. In practice, this will be
/// a Python object reference when called from PyO3 bindings.
///
/// # Examples
///
/// ```rust
/// use classic_registry_core::{register, get_yaml_cache, Keys};
///
/// register(Keys::YAML_CACHE, "cache_instance".to_string());
/// let cache: Option<String> = get_yaml_cache();
/// assert_eq!(cache, Some("cache_instance".to_string()));
/// ```
pub fn get_yaml_cache<T: Clone + Any + Send + Sync + 'static>() -> Option<T> {
    get(Keys::YAML_CACHE)
}

/// Get the manual documents GUI widget reference.
///
/// # Returns
///
/// Returns the GUI widget reference if registered, `None` otherwise.
///
/// # Note
///
/// This is typically a Python Qt widget object when called from PyO3 bindings.
pub fn get_manual_docs_gui<T: Clone + Any + Send + Sync + 'static>() -> Option<T> {
    get(Keys::MANUAL_DOCS_GUI)
}

/// Get the game path GUI widget reference.
///
/// # Returns
///
/// Returns the GUI widget reference if registered, `None` otherwise.
///
/// # Note
///
/// This is typically a Python Qt widget object when called from PyO3 bindings.
pub fn get_game_path_gui<T: Clone + Any + Send + Sync + 'static>() -> Option<T> {
    get(Keys::GAME_PATH_GUI)
}

/// Get the VR game variant identifier.
///
/// # Returns
///
/// Returns the VR variant name if registered, empty string otherwise.
///
/// # Examples
///
/// ```rust
/// use classic_registry_core::{register, get_vr, Keys, clear_all};
///
/// clear_all();
/// assert_eq!(get_vr(), "");
///
/// register(Keys::VR, "SkyrimVR".to_string());
/// assert_eq!(get_vr(), "SkyrimVR");
/// ```
pub fn get_vr() -> String {
    get::<_, String>(Keys::VR).unwrap_or_else(|| String::new())
}

/// Get the local application directory.
///
/// # Returns
///
/// Returns the local directory path from the registry, defaulting to the
/// current working directory if not set.
///
/// # Examples
///
/// ```rust
/// use classic_registry_core::{register, get_local_dir, Keys};
/// use std::path::PathBuf;
///
/// let test_path = PathBuf::from("/test/path");
/// register(Keys::LOCAL_DIR, test_path.clone());
/// assert_eq!(get_local_dir(), test_path);
/// ```
pub fn get_local_dir() -> PathBuf {
    get::<_, PathBuf>(Keys::LOCAL_DIR)
        .unwrap_or_else(|| std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;

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
}
