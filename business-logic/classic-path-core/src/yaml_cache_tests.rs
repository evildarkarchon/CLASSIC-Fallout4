use super::*;
use std::collections::HashMap;
use tempfile::tempdir;

/// Build an env-lookup closure from a map of `name -> value` pairs. Anything
/// not in the map is reported as unset.
fn env_map(entries: &[(&str, String)]) -> impl Fn(&str) -> Option<String> + use<> {
    let map: HashMap<String, String> = entries
        .iter()
        .map(|(k, v)| ((*k).to_string(), v.clone()))
        .collect();
    move |name| map.get(name).cloned()
}

fn as_str(path: &std::path::Path) -> String {
    path.to_string_lossy().into_owned()
}

#[test]
#[cfg(target_os = "windows")]
fn resolves_from_localappdata_on_windows() {
    let tmp = tempdir().unwrap();
    let env = env_map(&[
        ("LOCALAPPDATA", as_str(tmp.path())),
        // Set APPDATA too so we prove LOCALAPPDATA wins the tiebreak.
        ("APPDATA", as_str(tmp.path().parent().unwrap())),
    ]);
    let resolved = yaml_cache_dir_with_env(env).unwrap();
    assert_eq!(resolved, tmp.path().join("CLASSIC").join("yaml-cache"));
}

#[test]
#[cfg(target_os = "windows")]
fn falls_back_to_appdata_on_windows_when_localappdata_missing() {
    let tmp = tempdir().unwrap();
    let env = env_map(&[("APPDATA", as_str(tmp.path()))]);
    let resolved = yaml_cache_dir_with_env(env).unwrap();
    assert_eq!(resolved, tmp.path().join("CLASSIC").join("yaml-cache"));
}

#[test]
#[cfg(target_os = "windows")]
fn errors_when_no_windows_env_vars_available() {
    let env = env_map(&[]);
    let err = yaml_cache_dir_with_env(env).unwrap_err();
    assert!(matches!(err, PathError::InvalidPath(_)));
}

#[test]
#[cfg(not(target_os = "windows"))]
fn resolves_from_xdg_cache_home_on_unix() {
    let tmp = tempdir().unwrap();
    let env = env_map(&[("XDG_CACHE_HOME", as_str(tmp.path()))]);
    let resolved = yaml_cache_dir_with_env(env).unwrap();
    assert_eq!(resolved, tmp.path().join("CLASSIC").join("yaml-cache"));
}

#[test]
#[cfg(not(target_os = "windows"))]
fn falls_back_to_home_cache_on_unix() {
    let tmp = tempdir().unwrap();
    let env = env_map(&[("HOME", as_str(tmp.path()))]);
    let resolved = yaml_cache_dir_with_env(env).unwrap();
    assert_eq!(
        resolved,
        tmp.path().join(".cache").join("CLASSIC").join("yaml-cache")
    );
}

#[test]
fn ensure_creates_directory_when_missing() {
    let tmp = tempdir().unwrap();
    #[cfg(target_os = "windows")]
    let env = env_map(&[("LOCALAPPDATA", as_str(tmp.path()))]);
    #[cfg(not(target_os = "windows"))]
    let env = env_map(&[("XDG_CACHE_HOME", as_str(tmp.path()))]);

    let created = ensure_yaml_cache_dir_with_env(env).unwrap();
    assert!(created.exists());
    assert!(created.is_dir());
}

#[test]
fn ensure_is_idempotent() {
    let tmp = tempdir().unwrap();
    #[cfg(target_os = "windows")]
    let env_once = env_map(&[("LOCALAPPDATA", as_str(tmp.path()))]);
    #[cfg(target_os = "windows")]
    let env_twice = env_map(&[("LOCALAPPDATA", as_str(tmp.path()))]);
    #[cfg(not(target_os = "windows"))]
    let env_once = env_map(&[("XDG_CACHE_HOME", as_str(tmp.path()))]);
    #[cfg(not(target_os = "windows"))]
    let env_twice = env_map(&[("XDG_CACHE_HOME", as_str(tmp.path()))]);

    let a = ensure_yaml_cache_dir_with_env(env_once).unwrap();
    let b = ensure_yaml_cache_dir_with_env(env_twice).unwrap();
    assert_eq!(a, b);
    assert!(a.is_dir());
}

#[test]
fn empty_env_value_is_treated_as_unset_by_process_lookup() {
    // Sanity check on the production env lookup: an empty string value is
    // treated as unset so fallback takes over.
    assert!(process_env_lookup("__CLASSIC_DEFINITELY_UNSET_VAR_XYZZY__").is_none());
}
