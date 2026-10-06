use super::*;
use std::collections::HashMap;

/// Build an env-lookup closure from `name -> value` pairs. Anything not in the
/// map is reported as unset.
fn env_from(pairs: &[(&str, &str)]) -> impl Fn(&str) -> Option<String> + use<> {
    let map: HashMap<String, String> = pairs
        .iter()
        .map(|(k, v)| ((*k).to_string(), (*v).to_string()))
        .collect();
    move |name| map.get(name).cloned()
}

#[test]
#[cfg(target_os = "windows")]
fn windows_prefers_localappdata_over_appdata() {
    let env = env_from(&[
        ("LOCALAPPDATA", "C:\\Users\\me\\AppData\\Local"),
        ("APPDATA", "C:\\Users\\me\\AppData\\Roaming"),
    ]);
    assert_eq!(
        user_cache_root_with_env(env).unwrap(),
        PathBuf::from("C:\\Users\\me\\AppData\\Local")
    );
}

#[test]
#[cfg(target_os = "windows")]
fn windows_falls_back_to_appdata() {
    let env = env_from(&[("APPDATA", "C:\\Users\\me\\AppData\\Roaming")]);
    assert_eq!(
        user_cache_root_with_env(env).unwrap(),
        PathBuf::from("C:\\Users\\me\\AppData\\Roaming")
    );
}

#[test]
#[cfg(target_os = "windows")]
fn windows_reports_both_missing_variables() {
    // Unix variables must not satisfy the Windows lookup.
    let env = env_from(&[("XDG_CACHE_HOME", "/tmp"), ("HOME", "/home/me")]);
    let err = user_cache_root_with_env(env).unwrap_err();
    assert_eq!(err.to_string(), "neither LOCALAPPDATA nor APPDATA is set");
}

#[test]
#[cfg(not(target_os = "windows"))]
fn unix_prefers_xdg_cache_home_over_home() {
    let env = env_from(&[
        ("XDG_CACHE_HOME", "/var/cache/custom"),
        ("HOME", "/home/me"),
    ]);
    assert_eq!(
        user_cache_root_with_env(env).unwrap(),
        PathBuf::from("/var/cache/custom")
    );
}

#[test]
#[cfg(not(target_os = "windows"))]
fn unix_falls_back_to_home_dot_cache() {
    let env = env_from(&[("HOME", "/home/me")]);
    assert_eq!(
        user_cache_root_with_env(env).unwrap(),
        PathBuf::from("/home/me/.cache")
    );
}

#[test]
#[cfg(not(target_os = "windows"))]
fn unix_reports_both_missing_variables() {
    // Windows variables must not satisfy the Unix lookup.
    let env = env_from(&[("LOCALAPPDATA", "C:\\tmp")]);
    let err = user_cache_root_with_env(env).unwrap_err();
    assert_eq!(err.to_string(), "neither XDG_CACHE_HOME nor HOME is set");
}

#[test]
fn resolution_never_touches_the_filesystem() {
    // The resolved root does not need to exist; resolution is pure.
    let missing = std::env::temp_dir().join("classic-cache-root-never-created-12345");
    let missing_str = missing.to_string_lossy().into_owned();
    let env = env_from(&[
        ("LOCALAPPDATA", missing_str.as_str()),
        ("XDG_CACHE_HOME", missing_str.as_str()),
    ]);
    assert_eq!(user_cache_root_with_env(env).unwrap(), missing);
    assert!(!missing.exists());
}

#[test]
fn non_empty_env_var_treats_unset_as_none() {
    assert_eq!(
        non_empty_env_var("CLASSIC_SHARED_CORE_TEST_SURELY_UNSET_12345"),
        None
    );
}
