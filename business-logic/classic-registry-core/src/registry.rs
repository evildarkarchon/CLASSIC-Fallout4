//! Core registry implementation using DashMap for thread-safe concurrent access.
//!
//! This module provides the registry storage, its scope handles, and the
//! unscoped access functions.
//!
//! # Scopes
//!
//! Every typed registry store lives behind a [`RegistryScope`] handle. The
//! unscoped free functions in this module use one lazily created process
//! default scope, which is what Rust, CXX, and Node callers have always
//! observed. A binding adapter that links several former extension images
//! into one library (the merged Python extension) creates
//! [`RegistryScope::new_isolated`] handles so each facade keeps its own
//! values, application directory, and `clear_all` effect. Scope selection is
//! always explicit: callers hold a handle and pass it (or move it into async
//! work); nothing is selected through thread-local or ambient state, which
//! would not follow a task that resumes on another worker thread.

use dashmap::DashMap;
use std::any::Any;
use std::fmt;
use std::path::PathBuf;
use std::sync::{Arc, LazyLock};

use crate::Keys;

/// Type alias for registry values.
///
/// Values are stored as `Arc<dyn Any + Send + Sync>` to allow dynamic typing
/// while maintaining thread safety and efficient cloning.
type RegistryValue = Arc<dyn Any + Send + Sync>;

/// Process default registry scope used by the unscoped functions.
///
/// Uses `DashMap` for lock-free concurrent access with minimal contention.
/// The store is lazily initialized on first access.
static DEFAULT_SCOPE: LazyLock<RegistryScope> = LazyLock::new(RegistryScope::new_isolated);

/// Opaque handle to one typed registry store.
///
/// Cloning a handle shares the same store; two handles compare equal exactly
/// when they name the same store. [`RegistryScope::default_scope`] is the
/// store behind this crate's unscoped functions ([`register`], [`get`],
/// [`clear_all`], [`set_application_dir`], ...).
/// [`RegistryScope::new_isolated`] creates a fresh, empty store that shares
/// nothing with any other scope. Each method behaves exactly like the free
/// function of the same name, applied to this scope's store, including its
/// defaults and exact-type lookup rules.
///
/// Handles are `Send + Sync + 'static`, so an adapter can move one into async
/// work and the work keeps naming the same store wherever it resumes.
///
/// # Example
///
/// ```rust
/// use classic_registry_core::{RegistryScope, get_application_dir};
/// use std::path::PathBuf;
///
/// let scope = RegistryScope::new_isolated();
/// scope.set_application_dir(PathBuf::from("/facade/app"));
/// assert_eq!(scope.get_application_dir(), Some(PathBuf::from("/facade/app")));
/// assert_ne!(get_application_dir(), Some(PathBuf::from("/facade/app")));
/// ```
#[derive(Clone)]
pub struct RegistryScope {
    store: Arc<DashMap<String, RegistryValue>>,
}

impl RegistryScope {
    /// Return a handle to the process default scope used by the unscoped
    /// functions in this crate.
    #[must_use]
    pub fn default_scope() -> Self {
        DEFAULT_SCOPE.clone()
    }

    /// Create a new, empty scope that shares no values with any other scope,
    /// including the default one.
    #[must_use]
    pub fn new_isolated() -> Self {
        Self {
            store: Arc::new(DashMap::new()),
        }
    }

    /// Register a value in this scope, replacing any value under `key`.
    /// See [`register`].
    pub fn register<K, V>(&self, key: K, value: V)
    where
        K: Into<String>,
        V: Any + Send + Sync + 'static,
    {
        self.store.insert(key.into(), Arc::new(value));
    }

    /// Return whether `key` holds a value of any type in this scope.
    /// See [`is_registered`].
    #[must_use]
    pub fn is_registered<K>(&self, key: K) -> bool
    where
        K: AsRef<str>,
    {
        self.store.contains_key(key.as_ref())
    }

    /// Return a clone of the value under `key` when it is exactly type `V`.
    /// See [`get`].
    #[must_use]
    pub fn get<K, V>(&self, key: K) -> Option<V>
    where
        K: AsRef<str>,
        V: Clone + Any + Send + Sync + 'static,
    {
        self.store
            .get(key.as_ref())
            .and_then(|value| value.downcast_ref::<V>().cloned())
    }

    /// Remove every value from this scope, including its application
    /// directory. Other scopes are unaffected. See [`clear_all`].
    pub fn clear_all(&self) {
        self.store.clear();
    }

    /// Remove `key` from this scope, returning whether it was present.
    /// See [`unregister`].
    pub fn unregister<K>(&self, key: K) -> bool
    where
        K: AsRef<str>,
    {
        self.store.remove(key.as_ref()).is_some()
    }

    /// Return this scope's game name, defaulting to `"Fallout4"`.
    /// See [`get_game`].
    #[must_use]
    pub fn get_game(&self) -> String {
        self.get::<_, String>(Keys::GAME)
            .unwrap_or_else(|| "Fallout4".to_string())
    }

    /// Store the game name in this scope. See [`set_game`].
    pub fn set_game<S: Into<String>>(&self, game_name: S) {
        self.register(Keys::GAME, game_name.into());
    }

    /// Return this scope's native GUI-mode flag, defaulting to `false`.
    /// See [`is_gui_mode`].
    #[must_use]
    pub fn is_gui_mode(&self) -> bool {
        self.get::<_, bool>(Keys::IS_GUI_MODE).unwrap_or(false)
    }

    /// Return this scope's YAML cache reference when it is exactly type `T`.
    /// See [`get_yaml_cache`].
    #[must_use]
    pub fn get_yaml_cache<T: Clone + Any + Send + Sync + 'static>(&self) -> Option<T> {
        self.get(Keys::YAML_CACHE)
    }

    /// Return this scope's manual-documents GUI reference when it is exactly
    /// type `T`. See [`get_manual_docs_gui`].
    #[must_use]
    pub fn get_manual_docs_gui<T: Clone + Any + Send + Sync + 'static>(&self) -> Option<T> {
        self.get(Keys::MANUAL_DOCS_GUI)
    }

    /// Return this scope's game-path GUI reference when it is exactly type
    /// `T`. See [`get_game_path_gui`].
    #[must_use]
    pub fn get_game_path_gui<T: Clone + Any + Send + Sync + 'static>(&self) -> Option<T> {
        self.get(Keys::GAME_PATH_GUI)
    }

    /// Return this scope's game version when it is exactly type `T`.
    /// See [`get_game_version`].
    #[must_use]
    pub fn get_game_version<T: Clone + Any + Send + Sync + 'static>(&self) -> Option<T> {
        self.get(Keys::GAME_VERSION)
    }

    /// Return this scope's native version-auto-detected flag, defaulting to
    /// `false`. See [`is_version_auto_detected`].
    #[must_use]
    pub fn is_version_auto_detected(&self) -> bool {
        self.get::<_, bool>(Keys::VERSION_AUTO_DETECTED)
            .unwrap_or(false)
    }

    /// Return this scope's native local directory, defaulting to the current
    /// working directory (or `.` when that cannot be read).
    /// See [`get_local_dir`].
    #[must_use]
    pub fn get_local_dir(&self) -> PathBuf {
        self.get::<_, PathBuf>(Keys::LOCAL_DIR)
            .unwrap_or_else(|| std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")))
    }

    /// Store this scope's native application-directory override.
    ///
    /// Replaces any value under [`Keys::APP_DIR`] in this scope, including a
    /// generic value registered there with [`RegistryScope::register`].
    /// See [`set_application_dir`].
    pub fn set_application_dir(&self, dir: PathBuf) {
        self.register(Keys::APP_DIR, dir);
    }

    /// Return this scope's native application-directory override.
    ///
    /// Only a `PathBuf` stored under [`Keys::APP_DIR`] counts; a value of any
    /// other type under that key reads as `None`. See [`get_application_dir`].
    #[must_use]
    pub fn get_application_dir(&self) -> Option<PathBuf> {
        self.get::<_, PathBuf>(Keys::APP_DIR)
    }

    /// Return this scope's native XSE-validation flag, defaulting to `false`.
    /// See [`is_xse_valid`].
    #[must_use]
    pub fn is_xse_valid(&self) -> bool {
        self.get::<_, bool>(Keys::XSE_VALID).unwrap_or(false)
    }

    /// Return this scope's native ENB-presence flag, defaulting to `false`.
    /// See [`is_enb_present`].
    #[must_use]
    pub fn is_enb_present(&self) -> bool {
        self.get::<_, bool>(Keys::ENB_PRESENT).unwrap_or(false)
    }

    /// Return this scope's game version string, defaulting to `"auto"`.
    /// See [`get_game_version_string`].
    #[must_use]
    pub fn get_game_version_string(&self) -> String {
        self.get::<_, String>(Keys::GAME_VERSION)
            .unwrap_or_else(|| "auto".to_string())
    }
}

impl PartialEq for RegistryScope {
    /// Two handles are equal when they name the same store.
    fn eq(&self, other: &Self) -> bool {
        Arc::ptr_eq(&self.store, &other.store)
    }
}

impl Eq for RegistryScope {}

impl fmt::Debug for RegistryScope {
    // Report identity and occupancy only; stored values are type-erased.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("RegistryScope")
            .field("is_default", &(*self == *DEFAULT_SCOPE))
            .field("len", &self.store.len())
            .finish()
    }
}

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
    DEFAULT_SCOPE.register(key, value);
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
    DEFAULT_SCOPE.is_registered(key)
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
    DEFAULT_SCOPE.get(key)
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
    DEFAULT_SCOPE.clear_all();
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
    DEFAULT_SCOPE.unregister(key)
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
    DEFAULT_SCOPE.get_game()
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
    DEFAULT_SCOPE.set_game(game_name);
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
    DEFAULT_SCOPE.is_gui_mode()
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
    DEFAULT_SCOPE.get_yaml_cache()
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
    DEFAULT_SCOPE.get_manual_docs_gui()
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
    DEFAULT_SCOPE.get_game_path_gui()
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
/// use classic_version_registry_core::Fallout4Version;
///
/// register(Keys::GAME_VERSION, Fallout4Version::Vr);
/// let version = get_game_version::<Fallout4Version>();
/// assert_eq!(version, Some(Fallout4Version::Vr));
/// ```
pub fn get_game_version<T: Clone + std::any::Any + Send + Sync + 'static>() -> Option<T> {
    DEFAULT_SCOPE.get_game_version()
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
    DEFAULT_SCOPE.is_version_auto_detected()
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
    DEFAULT_SCOPE.get_local_dir()
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
    DEFAULT_SCOPE.set_application_dir(dir);
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
    DEFAULT_SCOPE.get_application_dir()
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
    DEFAULT_SCOPE.is_xse_valid()
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
    DEFAULT_SCOPE.is_enb_present()
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
    DEFAULT_SCOPE.get_game_version_string()
}

#[cfg(test)]
#[path = "registry_tests.rs"]
mod tests;
