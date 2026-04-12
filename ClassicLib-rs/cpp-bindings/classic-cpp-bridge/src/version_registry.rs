//! Version registry bridge for CXX FFI (D-02, CXXS-06).
//!
//! Bridges `classic-version-registry-core` so C++ frontends can resolve
//! Fallout 4 OG/NG/AE/VR variants, XSE configs, crashgen configs, and version
//! matching without going through the legacy `classic::game::version_registry_*`
//! namespace. The legacy fns remain available as delegation shims in `game.rs`
//! per D-08.
//!
//! NOTE: `src/registry.rs` is a SEPARATE bridge module for `classic-registry-core`
//! (the typed key/value singleton) — it is NOT this file (D-02 wording).

use classic_version_registry_core::{
    get_version_registry, Fallout4Version as CoreFallout4Version, GameVersion,
};

fn from_bridge_fallout4_version(v: ffi::Fallout4Version) -> CoreFallout4Version {
    match v {
        ffi::Fallout4Version::Original => CoreFallout4Version::Original,
        ffi::Fallout4Version::NextGen => CoreFallout4Version::NextGen,
        ffi::Fallout4Version::AnniversaryEdition => CoreFallout4Version::AnniversaryEdition,
        ffi::Fallout4Version::Vr => CoreFallout4Version::Vr,
        _ => CoreFallout4Version::Original,
    }
}

fn fallout4_version_as_str(v: ffi::Fallout4Version) -> String {
    from_bridge_fallout4_version(v).as_str().to_string()
}

fn fallout4_version_registry_id(v: ffi::Fallout4Version) -> String {
    from_bridge_fallout4_version(v).registry_id().to_string()
}

fn fallout4_version_is_vr(v: ffi::Fallout4Version) -> bool {
    from_bridge_fallout4_version(v).is_vr()
}

fn fallout4_version_is_standard(v: ffi::Fallout4Version) -> bool {
    from_bridge_fallout4_version(v).is_standard()
}

fn fallout4_version_exe_name(v: ffi::Fallout4Version) -> String {
    from_bridge_fallout4_version(v).exe_name().to_string()
}

fn fallout4_version_docs_folder_name(v: ffi::Fallout4Version) -> String {
    from_bridge_fallout4_version(v)
        .docs_folder_name()
        .to_string()
}

fn fallout4_version_steam_app_id(v: ffi::Fallout4Version) -> u32 {
    from_bridge_fallout4_version(v).steam_app_id()
}

fn is_null_version(major: u32, minor: u32, patch: u32) -> bool {
    major == 0 && minor == 0 && patch == 0
}

// ─────────────────────────────────────────────────────────────────────
// Wrapper bodies — verbatim from game.rs (Codex MEDIUM correction applied)
// All wrapper bodies are concrete; no placeholder implementations.
// ─────────────────────────────────────────────────────────────────────

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

// ─────────────────────────────────────────────────────────────────────
// NEW for CXXS-06 — uses existing registry.get_all() iteration helper
// (no missing core helper assumed — Codex review LOW correction)
// ─────────────────────────────────────────────────────────────────────

fn version_registry_get_all_for_game(game: &str, is_vr: bool) -> Vec<ffi::VersionInfoDto> {
    let registry = get_version_registry();
    registry
        .get_all()
        .iter()
        .filter(|info| info.game == game && info.is_vr == is_vr)
        .map(|info| ffi::VersionInfoDto {
            id: info.id.clone(),
            version_string: info.version_string(),
            short_name: info.short_name.clone(),
            game: info.game.clone(),
            docs_name: info.docs_name.clone(),
            steam_id: info.steam_id,
            is_vr: info.is_vr,
            found: true,
        })
        .collect()
}

// ─────────────────────────────────────────────────────────────────────
// CXX bridge block — moved DTOs + extern "Rust" declarations
// ─────────────────────────────────────────────────────────────────────

#[cxx::bridge(namespace = "classic::version_registry")]
mod ffi {
    #[repr(u8)]
    enum Fallout4Version {
        Original = 0,
        NextGen = 1,
        AnniversaryEdition = 2,
        Vr = 3,
    }

    // Shared structs — copy verbatim from game.rs (same field names + types)
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
        fn fallout4_version_as_str(v: Fallout4Version) -> String;
        fn fallout4_version_registry_id(v: Fallout4Version) -> String;
        fn fallout4_version_is_vr(v: Fallout4Version) -> bool;
        fn fallout4_version_is_standard(v: Fallout4Version) -> bool;
        fn fallout4_version_exe_name(v: Fallout4Version) -> String;
        fn fallout4_version_docs_folder_name(v: Fallout4Version) -> String;
        fn fallout4_version_steam_app_id(v: Fallout4Version) -> u32;
        fn is_null_version(major: u32, minor: u32, patch: u32) -> bool;

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
        fn parse_game_version(version_str: &str) -> GameVersionDto;

        // NEW for CXXS-06
        fn version_registry_get_all_for_game(game: &str, is_vr: bool) -> Vec<VersionInfoDto>;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_version_registry_get_all_count_at_least_four() {
        assert!(version_registry_get_all_count() >= 4);
    }

    #[test]
    fn test_version_registry_get_all_ids_nonempty() {
        let ids = version_registry_get_all_ids();
        assert!(!ids.is_empty());
    }

    #[test]
    fn test_version_registry_get_by_id_unknown_returns_not_found() {
        let result = version_registry_get_by_id("DEFINITELY_NOT_REAL_VERSION_ID");
        assert!(!result.found);
    }

    #[test]
    fn test_version_registry_get_all_for_game_fallout4_non_vr() {
        let entries = version_registry_get_all_for_game("Fallout4", false);
        assert!(
            !entries.is_empty(),
            "Fallout4 should have at least one non-VR variant"
        );
        for entry in &entries {
            assert!(!entry.is_vr);
            assert_eq!(entry.game, "Fallout4");
        }
    }

    #[test]
    fn test_version_registry_get_all_for_game_fallout4_vr() {
        let entries = version_registry_get_all_for_game("Fallout4", true);
        for entry in &entries {
            assert!(entry.is_vr);
            assert_eq!(entry.game, "Fallout4");
        }
    }

    #[test]
    fn test_parse_game_version_valid() {
        let v = parse_game_version("1.10.163.0");
        assert!(v.valid);
        assert_eq!(v.major, 1);
        assert_eq!(v.minor, 10);
        assert_eq!(v.patch, 163);
    }

    #[test]
    fn test_parse_game_version_invalid() {
        assert!(!parse_game_version("garbage").valid);
    }
}
