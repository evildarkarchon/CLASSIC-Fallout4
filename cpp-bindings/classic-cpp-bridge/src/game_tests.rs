use super::*;

#[test]
fn test_version_registry_get_by_id() {
    let info = version_registry_get_by_id("FO4_OG");
    assert!(info.found);
    assert_eq!(info.id, "FO4_OG");
    assert!(!info.version_string.is_empty());
}

#[test]
fn test_version_registry_get_by_id_docs_name() {
    let info = version_registry_get_by_id("FO4_OG");
    assert!(info.found);
    assert!(!info.docs_name.is_empty());
}

#[test]
fn test_version_registry_get_by_id_steam_id() {
    let info = version_registry_get_by_id("FO4_OG");
    assert!(info.found);
    assert!(info.steam_id > 0);
}

#[test]
fn test_version_registry_get_by_id_missing() {
    let info = version_registry_get_by_id("NONEXISTENT");
    assert!(!info.found);
    assert!(info.docs_name.is_empty());
    assert_eq!(info.steam_id, 0);
}

#[test]
fn test_version_registry_get_all() {
    let count = version_registry_get_all_count();
    assert!(count > 0);
    let ids = version_registry_get_all_ids();
    assert_eq!(ids.len(), count);
}

#[test]
fn test_version_registry_get_xse_config_found() {
    let xse = version_registry_get_xse_config("FO4_OG");
    assert!(xse.found);
    assert!(!xse.acronym.is_empty());
    assert!(!xse.full_name.is_empty());
    assert!(!xse.compatible_version.is_empty());
    assert!(!xse.loader.is_empty());
    assert!(xse.file_count > 0);
}

#[test]
fn test_version_registry_get_xse_config_missing() {
    let xse = version_registry_get_xse_config("NONEXISTENT");
    assert!(!xse.found);
    assert!(xse.acronym.is_empty());
    assert!(xse.full_name.is_empty());
    assert_eq!(xse.file_count, 0);
}

#[test]
fn test_version_registry_get_crashgen_configs() {
    let configs = version_registry_get_crashgen_configs("FO4_OG");
    assert!(!configs.is_empty());
    for c in &configs {
        assert!(!c.version.is_empty());
        assert!(!c.name.is_empty());
    }
}

#[test]
fn test_version_registry_get_crashgen_configs_missing() {
    let configs = version_registry_get_crashgen_configs("NONEXISTENT");
    assert!(configs.is_empty());
}

#[test]
fn test_version_registry_get_crashgen_config_found() {
    let c = version_registry_get_crashgen_config("FO4_OG", "1.28.6");
    assert_eq!(c.version, "1.28.6");
    assert!(!c.name.is_empty());
    assert!(!c.acronym.is_empty());
    assert!(!c.dll_file.is_empty());
}

#[test]
fn test_version_registry_get_crashgen_config_missing() {
    let c = version_registry_get_crashgen_config("FO4_OG", "9.99.99");
    assert!(c.version.is_empty());
    assert!(c.name.is_empty());
    assert!(c.acronym.is_empty());
    assert!(c.dll_file.is_empty());
}

#[test]
fn test_version_registry_match() {
    let result = version_registry_match_version("1.10.163.0", "Fallout4", false);
    assert!(result.is_match);
    assert!(!result.matched_id.is_empty());
}

#[test]
fn test_parse_game_version_valid() {
    let v = parse_game_version("1.10.163.0");
    assert!(v.valid);
    assert_eq!(v.major, 1);
    assert_eq!(v.minor, 10);
    assert_eq!(v.patch, 163);
    assert_eq!(v.build, 0);
}

#[test]
fn test_parse_game_version_invalid() {
    let v = parse_game_version("not_a_version");
    assert!(!v.valid);
}

#[test]
fn test_extract_pe_version_nonexistent() {
    let result = extract_pe_version_string("nonexistent.exe");
    assert!(result.is_empty());
}

#[test]
fn test_xse_type_from_str() {
    assert!(xse_type_from_str("F4SE").is_ok());
    assert!(xse_type_from_str("SKSE64").is_ok());
    assert!(xse_type_from_str("UNKNOWN").is_err());
}

#[test]
fn test_validate_path() {
    // Existing path should be valid (use crate directory, always exists during tests)
    assert!(validate_path(env!("CARGO_MANIFEST_DIR")));
    // Garbage path should be invalid
    assert!(!validate_path(""));
}

#[test]
fn test_check_restricted_path() {
    // Program Files is restricted
    assert!(check_restricted_path("C:\\Program Files\\SomeGame"));
}
