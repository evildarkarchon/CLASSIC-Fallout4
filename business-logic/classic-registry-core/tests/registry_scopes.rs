//! Public-interface probes for scoped typed registry stores (#241).
//!
//! `classic_registry_core` owns the typed registry, including the
//! application-directory key. Every store is reachable through an opaque
//! [`RegistryScope`] handle so a binding adapter (the merged Python
//! extension) can give each former extension facade its own registry, while
//! the unscoped free functions keep using one process default scope.
//!
//! These tests pin the contract the adapter relies on:
//!
//! - an isolated scope never sees, replaces, or clears another scope's values,
//!   including its application directory;
//! - the unscoped free functions are exactly the default scope;
//! - exact-type lookups behave per scope as they always have, so a generic
//!   value stored under the application-directory key never becomes the native
//!   `PathBuf` override (and vice versa);
//! - a handle can be moved into async work and keeps naming its own store.

use classic_registry_core::{
    Keys, RegistryScope, clear_all, get, get_application_dir, get_game, is_registered, register,
    set_application_dir, set_game,
};
use serial_test::serial;
use std::path::PathBuf;

#[test]
#[serial]
fn default_scope_is_the_store_behind_the_free_functions() {
    clear_all();
    let default = RegistryScope::default_scope();
    assert_eq!(default, RegistryScope::default_scope());

    set_application_dir(PathBuf::from("/free/fn"));
    assert_eq!(
        default.get_application_dir(),
        Some(PathBuf::from("/free/fn"))
    );

    default.set_game("Skyrim");
    assert_eq!(get_game(), "Skyrim");

    default.clear_all();
    assert_eq!(get_application_dir(), None);
    assert!(!is_registered(Keys::GAME));
}

#[test]
#[serial]
fn isolated_scopes_keep_independent_values_and_clears() {
    clear_all();
    let registry = RegistryScope::new_isolated();
    let config = RegistryScope::new_isolated();
    assert_ne!(registry, config);
    assert_ne!(registry, RegistryScope::default_scope());

    registry.set_application_dir(PathBuf::from("/registry"));
    config.set_application_dir(PathBuf::from("/config"));
    set_application_dir(PathBuf::from("/default"));
    registry.set_game("Skyrim");

    assert_eq!(
        registry.get_application_dir(),
        Some(PathBuf::from("/registry"))
    );
    assert_eq!(config.get_application_dir(), Some(PathBuf::from("/config")));
    assert_eq!(get_application_dir(), Some(PathBuf::from("/default")));
    assert_eq!(registry.get_game(), "Skyrim");
    assert_eq!(config.get_game(), "Fallout4", "defaults stay per scope");
    assert_eq!(get_game(), "Fallout4");

    // Clearing one facade's registry clears its own application directory only.
    registry.clear_all();
    assert_eq!(registry.get_application_dir(), None);
    assert_eq!(registry.get_game(), "Fallout4");
    assert_eq!(config.get_application_dir(), Some(PathBuf::from("/config")));
    assert_eq!(get_application_dir(), Some(PathBuf::from("/default")));

    assert!(config.unregister(Keys::APP_DIR));
    assert!(!config.unregister(Keys::APP_DIR));
    assert_eq!(get_application_dir(), Some(PathBuf::from("/default")));
    clear_all();
}

#[test]
fn cloned_handles_share_one_store() {
    let scope = RegistryScope::new_isolated();
    let alias = scope.clone();
    assert_eq!(scope, alias);

    alias.register("shared_key", 7_i32);
    assert_eq!(scope.get::<_, i32>("shared_key"), Some(7));
    assert!(scope.is_registered("shared_key"));

    scope.clear_all();
    assert!(!alias.is_registered("shared_key"));
}

#[test]
#[serial]
fn application_dir_key_keeps_exact_type_lookups_per_scope() {
    clear_all();
    let scope = RegistryScope::new_isolated();

    // A generic (non-PathBuf) value under the key is registered but is not the
    // native application-directory override.
    scope.register(Keys::APP_DIR, "/generic".to_string());
    assert!(scope.is_registered(Keys::APP_DIR));
    assert_eq!(scope.get_application_dir(), None);
    assert_eq!(
        scope.get::<_, String>(Keys::APP_DIR),
        Some("/generic".to_string())
    );

    // The native setter replaces it; the generic typed read no longer matches.
    scope.set_application_dir(PathBuf::from("/native"));
    assert_eq!(scope.get::<_, String>(Keys::APP_DIR), None);
    assert_eq!(scope.get_application_dir(), Some(PathBuf::from("/native")));

    // The collision stays inside the scope that made it.
    assert!(!is_registered(Keys::APP_DIR));
    register(Keys::APP_DIR, "/default-generic".to_string());
    assert_eq!(get_application_dir(), None);
    assert_eq!(scope.get_application_dir(), Some(PathBuf::from("/native")));
    assert_eq!(
        get::<_, String>(Keys::APP_DIR),
        Some("/default-generic".to_string())
    );
    clear_all();
}

#[test]
fn scoped_convenience_accessors_match_free_function_defaults() {
    let scope = RegistryScope::new_isolated();
    assert_eq!(scope.get_game(), "Fallout4");
    assert!(!scope.is_gui_mode());
    assert!(!scope.is_version_auto_detected());
    assert!(!scope.is_xse_valid());
    assert!(!scope.is_enb_present());
    assert_eq!(scope.get_game_version_string(), "auto");
    assert_eq!(scope.get_yaml_cache::<String>(), None);
    assert_eq!(scope.get_manual_docs_gui::<String>(), None);
    assert_eq!(scope.get_game_path_gui::<String>(), None);
    assert_eq!(scope.get_game_version::<String>(), None);
    assert_eq!(
        scope.get_local_dir(),
        std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
    );

    scope.register(Keys::IS_GUI_MODE, true);
    scope.register(Keys::VERSION_AUTO_DETECTED, true);
    scope.register(Keys::XSE_VALID, true);
    scope.register(Keys::ENB_PRESENT, true);
    scope.register(Keys::GAME_VERSION, "NextGen".to_string());
    scope.register(Keys::YAML_CACHE, "cache".to_string());
    scope.register(Keys::MANUAL_DOCS_GUI, "docs".to_string());
    scope.register(Keys::GAME_PATH_GUI, "path".to_string());
    scope.register(Keys::LOCAL_DIR, PathBuf::from("/local"));

    assert!(scope.is_gui_mode());
    assert!(scope.is_version_auto_detected());
    assert!(scope.is_xse_valid());
    assert!(scope.is_enb_present());
    assert_eq!(scope.get_game_version_string(), "NextGen");
    assert_eq!(scope.get_game_version::<String>(), Some("NextGen".into()));
    assert_eq!(scope.get_yaml_cache::<String>(), Some("cache".into()));
    assert_eq!(scope.get_manual_docs_gui::<String>(), Some("docs".into()));
    assert_eq!(scope.get_game_path_gui::<String>(), Some("path".into()));
    assert_eq!(scope.get_local_dir(), PathBuf::from("/local"));
}

#[test]
#[serial]
fn free_function_set_game_never_reaches_an_isolated_scope() {
    clear_all();
    let scope = RegistryScope::new_isolated();
    set_game("Skyrim");
    assert_eq!(scope.get_game(), "Fallout4");
    clear_all();
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn handles_moved_into_async_work_keep_their_own_store() {
    let scopes: Vec<RegistryScope> = (0..8).map(|_| RegistryScope::new_isolated()).collect();

    // Each task owns its handle; no ambient or thread-local selection is
    // involved, so a task resuming on another worker still reaches its store.
    let tasks: Vec<_> = scopes
        .iter()
        .cloned()
        .enumerate()
        .map(|(index, scope)| {
            tokio::spawn(async move {
                scope.set_application_dir(PathBuf::from(format!("/scope/{index}")));
                tokio::task::yield_now().await;
                scope.register("task_index", index);
                tokio::task::yield_now().await;
                (
                    scope.get_application_dir(),
                    scope.get::<_, usize>("task_index"),
                )
            })
        })
        .collect();

    for (index, task) in tasks.into_iter().enumerate() {
        let (app_dir, stored) = task.await.expect("task should complete");
        assert_eq!(app_dir, Some(PathBuf::from(format!("/scope/{index}"))));
        assert_eq!(stored, Some(index));
    }
    for (index, scope) in scopes.iter().enumerate() {
        assert_eq!(
            scope.get_application_dir(),
            Some(PathBuf::from(format!("/scope/{index}")))
        );
    }
}
