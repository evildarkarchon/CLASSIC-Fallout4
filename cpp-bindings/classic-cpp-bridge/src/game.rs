//! Game support bridge for CXX FFI.
//!
//! Bridges version registry, version parsing, PE version extraction,
//! XSE detection, and path validation/detection.

use classic_path_core::{GamePathFinder, is_restricted_path, is_valid_path};
use classic_version_core::pe_version::extract_pe_version;
use classic_version_registry_core::{GameVersion, get_version_registry};
use classic_xse_core::{XseType, detect_xse_version, is_xse_installed};
use std::path::{Path, PathBuf};

// ── Version Registry ────────────────────────────────────────────────

fn version_registry_get_by_id(id: &str) -> ffi::VersionInfoDto {
    let registry = get_version_registry();
    match registry.get_by_id(id) {
        Some(info) => ffi::VersionInfoDto {
            id: info.id.clone(),
            version_string: info.version_string(),
            short_name: info.short_name.clone(),
            game: info.game.clone(),
            docs_name: info.docs_name.clone(),
            steam_id: info.steam_id,
            is_vr: info.is_vr,
            found: true,
        },
        None => ffi::VersionInfoDto {
            id: id.to_string(),
            version_string: String::new(),
            short_name: String::new(),
            game: String::new(),
            docs_name: String::new(),
            steam_id: 0,
            is_vr: false,
            found: false,
        },
    }
}

fn version_registry_get_all_ids() -> Vec<String> {
    let registry = get_version_registry();
    registry.get_all().iter().map(|v| v.id.clone()).collect()
}

fn version_registry_get_all_count() -> usize {
    let registry = get_version_registry();
    registry.get_all().len()
}

fn version_registry_match_version(
    version_str: &str,
    game: &str,
    is_vr: bool,
) -> ffi::MatchResultDto {
    let registry = get_version_registry();
    match GameVersion::parse(version_str) {
        Ok(detected) => {
            let result = registry.match_version(&detected, game, is_vr);
            let is_match = result.version_info.is_some();
            ffi::MatchResultDto {
                matched_id: result
                    .version_info
                    .map(|v| v.id.clone())
                    .unwrap_or_default(),
                confidence: format!("{:?}", result.confidence),
                message: result.message.clone(),
                is_match,
            }
        }
        Err(e) => ffi::MatchResultDto {
            matched_id: String::new(),
            confidence: "None".to_string(),
            message: format!("Failed to parse version: {e}"),
            is_match: false,
        },
    }
}

fn version_registry_get_xse_config(id: &str) -> ffi::XseConfigDto {
    let registry = get_version_registry();
    match registry.get_by_id(id).and_then(|info| info.xse.as_ref()) {
        Some(xse) => ffi::XseConfigDto {
            acronym: xse.acronym.clone(),
            full_name: xse.full_name.clone(),
            compatible_version: xse.compatible_version.clone(),
            loader: xse.loader.clone(),
            file_count: xse.file_count,
            found: true,
        },
        None => ffi::XseConfigDto {
            acronym: String::new(),
            full_name: String::new(),
            compatible_version: String::new(),
            loader: String::new(),
            file_count: 0,
            found: false,
        },
    }
}

fn version_registry_get_crashgen_configs(id: &str) -> Vec<ffi::CrashgenConfigDto> {
    let registry = get_version_registry();
    registry
        .get_crashgen_versions(id)
        .iter()
        .map(|c| ffi::CrashgenConfigDto {
            version: c.version.clone(),
            name: c.name.clone(),
            acronym: c.acronym.clone(),
            dll_file: c.dll_file.clone(),
            description: c.description.clone(),
            download_url: c.download_url.clone(),
        })
        .collect()
}

fn version_registry_get_crashgen_config(
    id: &str,
    crashgen_version: &str,
) -> ffi::CrashgenConfigDto {
    let registry = get_version_registry();
    match registry.get_crashgen_for_version(id, crashgen_version) {
        Some(c) => ffi::CrashgenConfigDto {
            version: c.version.clone(),
            name: c.name.clone(),
            acronym: c.acronym.clone(),
            dll_file: c.dll_file.clone(),
            description: c.description.clone(),
            download_url: c.download_url.clone(),
        },
        None => ffi::CrashgenConfigDto {
            version: String::new(),
            name: String::new(),
            acronym: String::new(),
            dll_file: String::new(),
            description: String::new(),
            download_url: String::new(),
        },
    }
}

// ── Version parsing ─────────────────────────────────────────────────

fn parse_game_version(version_str: &str) -> ffi::GameVersionDto {
    match GameVersion::parse(version_str) {
        Ok(v) => ffi::GameVersionDto {
            major: v.major,
            minor: v.minor,
            patch: v.patch,
            build: v.build,
            valid: true,
        },
        Err(_) => ffi::GameVersionDto {
            major: 0,
            minor: 0,
            patch: 0,
            build: 0,
            valid: false,
        },
    }
}

// ── PE version extraction ───────────────────────────────────────────

fn extract_pe_version_string(exe_path: &str) -> String {
    match extract_pe_version(Path::new(exe_path)) {
        Ok((major, minor, patch, build)) => format!("{major}.{minor}.{patch}.{build}"),
        Err(_) => String::new(),
    }
}

// ── XSE detection ───────────────────────────────────────────────────

fn xse_type_from_str(s: &str) -> Result<XseType, String> {
    match s.to_uppercase().as_str() {
        "F4SE" => Ok(XseType::F4SE),
        "F4SEVR" => Ok(XseType::F4SEVR),
        "SKSE" => Ok(XseType::SKSE),
        "SKSE64" => Ok(XseType::SKSE64),
        "SKSEVR" => Ok(XseType::SKSEVR),
        "SFSE" => Ok(XseType::SFSE),
        _ => Err(format!("Unknown XSE type: {s}")),
    }
}

fn detect_xse_version_string(exe_path: &str, xse_type_str: &str) -> String {
    let xse_type = match xse_type_from_str(xse_type_str) {
        Ok(t) => t,
        Err(_) => return String::new(),
    };
    match detect_xse_version(Path::new(exe_path), xse_type) {
        Ok(v) => v.to_string(),
        Err(_) => String::new(),
    }
}

fn is_xse_installed_check(game_root: &str, xse_type_str: &str) -> bool {
    let xse_type = match xse_type_from_str(xse_type_str) {
        Ok(t) => t,
        Err(_) => return false,
    };
    is_xse_installed(Path::new(game_root), xse_type)
}

// ── Path detection and validation ───────────────────────────────────

fn find_game_path(
    game_exe: &str,
    xse_loader: &str,
    game_name: &str,
    is_vr: bool,
    cached_path: &str,
    xse_log_path: &str,
) -> String {
    let xse = if xse_loader.is_empty() {
        None::<&str>
    } else {
        Some(xse_loader)
    };
    let cached = if cached_path.is_empty() {
        None
    } else {
        Some(PathBuf::from(cached_path))
    };
    let xse_log = if xse_log_path.is_empty() {
        None
    } else {
        Some(PathBuf::from(xse_log_path))
    };
    let finder = GamePathFinder::new(game_exe, xse, game_name, is_vr);
    match finder.find_game_path(cached.as_deref(), xse_log.as_deref()) {
        Ok(path) => path.to_string_lossy().to_string(),
        Err(_) => String::new(),
    }
}

fn validate_path(path: &str) -> bool {
    is_valid_path(&PathBuf::from(path))
}

fn check_restricted_path(path: &str) -> bool {
    is_restricted_path(&PathBuf::from(path))
}

#[cxx::bridge(namespace = "classic::game")]
mod ffi {
    struct VersionInfoDto {
        id: String,
        version_string: String,
        short_name: String,
        game: String,
        docs_name: String,
        steam_id: u32,
        is_vr: bool,
        found: bool,
    }

    struct XseConfigDto {
        acronym: String,
        full_name: String,
        compatible_version: String,
        loader: String,
        file_count: u32,
        found: bool,
    }

    struct CrashgenConfigDto {
        version: String,
        name: String,
        acronym: String,
        dll_file: String,
        description: String,
        download_url: String,
    }

    struct MatchResultDto {
        matched_id: String,
        confidence: String,
        message: String,
        is_match: bool,
    }

    struct GameVersionDto {
        major: u32,
        minor: u32,
        patch: u32,
        build: u32,
        valid: bool,
    }

    extern "Rust" {
        // Version Registry
        fn version_registry_get_by_id(id: &str) -> VersionInfoDto;
        fn version_registry_get_all_ids() -> Vec<String>;
        fn version_registry_get_all_count() -> usize;
        fn version_registry_match_version(
            version_str: &str,
            game: &str,
            is_vr: bool,
        ) -> MatchResultDto;
        fn version_registry_get_xse_config(id: &str) -> XseConfigDto;
        fn version_registry_get_crashgen_configs(id: &str) -> Vec<CrashgenConfigDto>;
        fn version_registry_get_crashgen_config(
            id: &str,
            crashgen_version: &str,
        ) -> CrashgenConfigDto;

        // Version parsing
        fn parse_game_version(version_str: &str) -> GameVersionDto;

        // PE version
        fn extract_pe_version_string(exe_path: &str) -> String;

        // XSE
        fn detect_xse_version_string(exe_path: &str, xse_type_str: &str) -> String;
        fn is_xse_installed_check(game_root: &str, xse_type_str: &str) -> bool;

        // Path
        fn find_game_path(
            game_exe: &str,
            xse_loader: &str,
            game_name: &str,
            is_vr: bool,
            cached_path: &str,
            xse_log_path: &str,
        ) -> String;
        fn validate_path(path: &str) -> bool;
        fn check_restricted_path(path: &str) -> bool;
    }
}

#[cfg(test)]
mod tests {
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
}
