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

/// Remove a key from the global registry.
///
/// # Arguments
///
/// * `key` - The registry key to remove
///
/// # Returns
///
/// Returns `true` if the key was found and removed, `false` if the key was not present.
///
/// # Examples
///
/// ```rust
/// use classic_registry_core::{register, unregister, is_registered};
///
/// register("temp_key", "temp_value".to_string());
/// assert!(is_registered("temp_key"));
///
/// assert!(unregister("temp_key"));
/// assert!(!is_registered("temp_key"));
///
/// assert!(!unregister("nonexistent"));
/// ```
pub fn unregister<K>(key: K) -> bool
where
    K: AsRef<str>,
{
    REGISTRY.remove(key.as_ref()).is_some()
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

/// Get the current Fallout 4 version.
///
/// This is the recommended way to check which version of Fallout 4 is being used,
/// including VR support. The version is stored as a `Fallout4Version` enum.
///
/// # Returns
///
/// Returns `Some(version)` if a version is registered, `None` otherwise.
///
/// # Note
///
/// The actual type depends on what was registered. When called from PyO3 bindings,
/// this will return a `Fallout4Version` enum value.
///
/// # Examples
///
/// ```rust,ignore
/// use classic_registry_core::{register, get_game_version, Keys};
/// use classic_constants_core::Fallout4Version;
///
/// register(Keys::GAME_VERSION, Fallout4Version::Vr);
/// let version = get_game_version::<Fallout4Version>();
/// assert_eq!(version, Some(Fallout4Version::Vr));
/// ```
pub fn get_game_version<T: Clone + std::any::Any + Send + Sync + 'static>() -> Option<T> {
    get(Keys::GAME_VERSION)
}

/// Check if the game version was auto-detected.
///
/// # Returns
///
/// Returns `true` if the version was auto-detected, `false` if manually selected
/// or not set.
///
/// # Examples
///
/// ```rust
/// use classic_registry_core::{register, is_version_auto_detected, Keys, clear_all};
///
/// clear_all();
/// assert!(!is_version_auto_detected()); // Default
///
/// register(Keys::VERSION_AUTO_DETECTED, true);
/// assert!(is_version_auto_detected());
/// ```
pub fn is_version_auto_detected() -> bool {
    get::<_, bool>(Keys::VERSION_AUTO_DETECTED).unwrap_or(false)
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

/// Set the application directory override for settings resolution.
///
/// When set, `classic-config-core` uses this directory instead of
/// `current_exe().parent()` to anchor settings and data file lookups.
///
/// # Examples
///
/// ```rust
/// use classic_registry_core::{set_application_dir, get_application_dir, clear_all};
/// use std::path::PathBuf;
///
/// clear_all();
/// assert_eq!(get_application_dir(), None);
///
/// set_application_dir(PathBuf::from("/my/app"));
/// assert_eq!(get_application_dir(), Some(PathBuf::from("/my/app")));
/// ```
pub fn set_application_dir(dir: PathBuf) {
    register(Keys::APP_DIR, dir);
}

/// Get the application directory override, if set.
///
/// Returns `None` when no override has been registered, signalling callers
/// to fall back to their own default (e.g., `current_exe().parent()`).
///
/// # Examples
///
/// ```rust
/// use classic_registry_core::{set_application_dir, get_application_dir, clear_all};
/// use std::path::PathBuf;
///
/// clear_all();
/// assert_eq!(get_application_dir(), None);
///
/// set_application_dir(PathBuf::from("/my/app"));
/// assert_eq!(get_application_dir(), Some(PathBuf::from("/my/app")));
/// ```
pub fn get_application_dir() -> Option<PathBuf> {
    get::<_, PathBuf>(Keys::APP_DIR)
}

/// Check if XSE validation passed.
///
/// # Returns
///
/// `true` if XSE validation passed, `false` if not set or failed.
///
/// # Examples
///
/// ```rust
/// use classic_registry_core::{register, is_xse_valid, Keys, clear_all};
///
/// clear_all();
/// assert!(!is_xse_valid());
///
/// register(Keys::XSE_VALID, true);
/// assert!(is_xse_valid());
/// ```
pub fn is_xse_valid() -> bool {
    get::<_, bool>(Keys::XSE_VALID).unwrap_or(false)
}

/// Check if ENB binaries are present.
///
/// # Returns
///
/// `true` if ENB binaries were detected, `false` if not set or not detected.
///
/// # Examples
///
/// ```rust
/// use classic_registry_core::{register, is_enb_present, Keys, clear_all};
///
/// clear_all();
/// assert!(!is_enb_present());
///
/// register(Keys::ENB_PRESENT, true);
/// assert!(is_enb_present());
/// ```
pub fn is_enb_present() -> bool {
    get::<_, bool>(Keys::ENB_PRESENT).unwrap_or(false)
}

/// Get the game version as a string.
///
/// Named `get_game_version_string` to avoid ambiguity with the existing
/// generic `get_game_version<T>()`.
///
/// # Returns
///
/// The game version string, defaulting to `"auto"` if not set.
///
/// # Examples
///
/// ```rust
/// use classic_registry_core::{register, get_game_version_string, Keys, clear_all};
///
/// clear_all();
/// assert_eq!(get_game_version_string(), "auto");
///
/// register(Keys::GAME_VERSION, "NextGen".to_string());
/// assert_eq!(get_game_version_string(), "NextGen");
/// ```
pub fn get_game_version_string() -> String {
    get::<_, String>(Keys::GAME_VERSION).unwrap_or_else(|| "auto".to_string())
}

#[cfg(test)]
mod tests {
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
}
