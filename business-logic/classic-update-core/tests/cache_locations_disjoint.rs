//! The YAML Data and app-notification update channels keep disjoint caches.
//!
//! Design D-06: a diagnostic cleanup of one per-user cache must not remove the
//! other. The two locations have different owners — config owns the YAML Data
//! cache (`classic_config_core::yaml_cache_dir_with_env`) and path owns the
//! app-notification cache (`classic_path_core::notification_cache_dir_with_env`)
//! — so the disjointness check lives here, in the update crate that consumes
//! both.

use std::collections::HashMap;
use std::path::PathBuf;

fn env_from_map(pairs: &[(&str, &str)]) -> impl Fn(&str) -> Option<String> + use<> {
    let map: HashMap<String, String> = pairs
        .iter()
        .map(|(k, v)| ((*k).to_string(), (*v).to_string()))
        .collect();
    move |key: &str| map.get(key).cloned()
}

#[test]
fn yaml_data_and_notification_caches_are_disjoint_siblings() {
    #[cfg(target_os = "windows")]
    let (env_pairs, root) = (
        [("LOCALAPPDATA", "C:\\Users\\me\\AppData\\Local")],
        PathBuf::from("C:\\Users\\me\\AppData\\Local"),
    );
    #[cfg(not(target_os = "windows"))]
    let (env_pairs, root) = ([("HOME", "/home/me")], PathBuf::from("/home/me/.cache"));

    let yaml = classic_config_core::yaml_cache_dir_with_env(env_from_map(&env_pairs)).unwrap();
    let notification = classic_path_core::notification_cache_dir_with_env(
        "evildarkarchon",
        "CLASSIC-Fallout4",
        env_from_map(&env_pairs),
    )
    .unwrap();

    assert_eq!(yaml, root.join("CLASSIC").join("yaml-cache"));
    assert_eq!(
        notification,
        root.join("CLASSIC")
            .join("app-notification")
            .join("evildarkarchon")
            .join("CLASSIC-Fallout4")
    );
    assert!(!notification.starts_with(&yaml));
    assert!(!yaml.starts_with(&notification));
}
