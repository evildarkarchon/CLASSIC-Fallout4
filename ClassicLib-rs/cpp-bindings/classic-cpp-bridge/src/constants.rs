//! Constants bridge for CXX FFI.
//!
//! Bridges `classic-constants-core` enums and helpers so C++ frontends can
//! reference the canonical game / YAML file / Fallout 4 version identifiers
//! without hardcoding strings. Per D-04, enums cross the boundary as CXX
//! shared enums declared inside `#[cxx::bridge(namespace = "classic::constants")]`.
//!
//! # Architecture
//!
//! This module provides the `classic::constants` C++ namespace. All three
//! primary enums (`GameId`, `Fallout4Version`, `YamlFile`) are bridged as
//! CXX shared enums with `#[repr(u8)]`. Methods that take `&self` are
//! exposed as free functions that accept the bridge enum by value and
//! delegate to the matching `classic-constants-core` method.
//!
//! Constants that cannot cross the FFI boundary (slices, semver types) are
//! exposed as predicate functions instead:
//! - `SETTINGS_IGNORE_NONE` → `settings_ignore_none_contains(key: &str) -> bool`
//! - `NULL_VERSION` → `is_null_version(major, minor, patch: u32) -> bool`
//!
//! # CXXS-01 surface
//!
//! - Enums: `GameId`, `Fallout4Version`, `YamlFile` (all 7 variants)
//! - GameId helpers: `game_id_as_str`
//! - Fallout4Version helpers: `fallout4_version_as_str`, `fallout4_version_registry_id`,
//!   `fallout4_version_is_vr`, `fallout4_version_is_standard`, `fallout4_version_exe_name`,
//!   `fallout4_version_docs_folder_name`, `fallout4_version_steam_app_id`
//! - YamlFile helpers: `yaml_file_as_str`, `yaml_file_description`
//! - Predicate helpers: `must_not_be_none_key`, `settings_ignore_none_contains`,
//!   `is_null_version`
//!
//! # Examples
//!
//! ```cpp
//! // C++ usage
//! auto name = classic::constants::game_id_as_str(classic::constants::GameId::Fallout4);
//! // → "Fallout4"
//!
//! auto ver_str = classic::constants::fallout4_version_as_str(classic::constants::Fallout4Version::Vr);
//! // → "VR"
//! ```

use classic_constants_core::{
    Fallout4Version as CoreFallout4Version, GameId as CoreGameId, SETTINGS_IGNORE_NONE,
    YamlFile as CoreYamlFile, must_not_be_none as core_must_not_be_none,
};

// ─────────────────────────────────────────────────────────────────────────────
// GameId helpers
// ─────────────────────────────────────────────────────────────────────────────

fn from_bridge_game_id(id: ffi::GameId) -> CoreGameId {
    match id {
        ffi::GameId::Fallout4 => CoreGameId::Fallout4,
        ffi::GameId::Fallout4VR => CoreGameId::Fallout4VR,
        ffi::GameId::Skyrim => CoreGameId::Skyrim,
        ffi::GameId::Starfield => CoreGameId::Starfield,
        _ => CoreGameId::Fallout4, // unreachable in safe usage
    }
}

fn game_id_as_str(id: ffi::GameId) -> String {
    from_bridge_game_id(id).as_str().to_string()
}

// ─────────────────────────────────────────────────────────────────────────────
// Fallout4Version helpers
// NOTE: Vr.as_str() returns "VR" (uppercase) — Codex review LOW correction
// ─────────────────────────────────────────────────────────────────────────────

fn from_bridge_f4_version(v: ffi::Fallout4Version) -> CoreFallout4Version {
    match v {
        ffi::Fallout4Version::Original => CoreFallout4Version::Original,
        ffi::Fallout4Version::NextGen => CoreFallout4Version::NextGen,
        ffi::Fallout4Version::AnniversaryEdition => CoreFallout4Version::AnniversaryEdition,
        ffi::Fallout4Version::Vr => CoreFallout4Version::Vr,
        _ => CoreFallout4Version::Original, // unreachable in safe usage
    }
}

fn fallout4_version_as_str(v: ffi::Fallout4Version) -> String {
    from_bridge_f4_version(v).as_str().to_string()
}

fn fallout4_version_registry_id(v: ffi::Fallout4Version) -> String {
    from_bridge_f4_version(v).registry_id().to_string()
}

fn fallout4_version_is_vr(v: ffi::Fallout4Version) -> bool {
    from_bridge_f4_version(v).is_vr()
}

fn fallout4_version_is_standard(v: ffi::Fallout4Version) -> bool {
    from_bridge_f4_version(v).is_standard()
}

fn fallout4_version_exe_name(v: ffi::Fallout4Version) -> String {
    from_bridge_f4_version(v).exe_name().to_string()
}

fn fallout4_version_docs_folder_name(v: ffi::Fallout4Version) -> String {
    from_bridge_f4_version(v).docs_folder_name().to_string()
}

fn fallout4_version_steam_app_id(v: ffi::Fallout4Version) -> u32 {
    from_bridge_f4_version(v).steam_app_id()
}

// ─────────────────────────────────────────────────────────────────────────────
// YamlFile helpers — ALL 7 variants (Codex review MEDIUM correction)
// ─────────────────────────────────────────────────────────────────────────────

fn from_bridge_yaml_file(f: ffi::YamlFile) -> CoreYamlFile {
    match f {
        ffi::YamlFile::Main => CoreYamlFile::Main,
        ffi::YamlFile::Settings => CoreYamlFile::Settings,
        ffi::YamlFile::Ignore => CoreYamlFile::Ignore,
        ffi::YamlFile::Game => CoreYamlFile::Game,
        ffi::YamlFile::GameLocal => CoreYamlFile::GameLocal,
        ffi::YamlFile::Test => CoreYamlFile::Test,
        ffi::YamlFile::Cache => CoreYamlFile::Cache,
        _ => CoreYamlFile::Settings, // unreachable in safe usage
    }
}

fn yaml_file_as_str(f: ffi::YamlFile) -> String {
    from_bridge_yaml_file(f).as_str().to_string()
}

fn yaml_file_description(f: ffi::YamlFile) -> String {
    from_bridge_yaml_file(f).description().to_string()
}

// ─────────────────────────────────────────────────────────────────────────────
// SETTINGS_IGNORE_NONE / must_not_be_none predicates
// (slices and consts are not directly bridgeable; expose as predicates)
// ─────────────────────────────────────────────────────────────────────────────

fn must_not_be_none_key(key: &str) -> bool {
    core_must_not_be_none(key)
}

fn settings_ignore_none_contains(key: &str) -> bool {
    SETTINGS_IGNORE_NONE.contains(&key)
}

// ─────────────────────────────────────────────────────────────────────────────
// NULL_VERSION predicate (semver types are not bridgeable as values)
// ─────────────────────────────────────────────────────────────────────────────

fn is_null_version(major: u32, minor: u32, patch: u32) -> bool {
    major == 0 && minor == 0 && patch == 0
}

// ─────────────────────────────────────────────────────────────────────────────
// CXX bridge block — D-04 shared enums + extern "Rust" helper fns
// ─────────────────────────────────────────────────────────────────────────────

#[cxx::bridge(namespace = "classic::constants")]
mod ffi {
    /// Supported game identifiers.
    ///
    /// Mirrors `classic_constants_core::GameId` exactly.
    #[repr(u8)]
    enum GameId {
        Fallout4 = 0,
        Fallout4VR = 1,
        Skyrim = 2,
        Starfield = 3,
    }

    /// Fallout 4 version variants.
    ///
    /// NOTE: `Vr.as_str()` returns `"VR"` (uppercase), not `"Vr"`.
    /// Mirrors `classic_constants_core::Fallout4Version` exactly.
    #[repr(u8)]
    enum Fallout4Version {
        Original = 0,
        NextGen = 1,
        AnniversaryEdition = 2,
        Vr = 3,
    }

    /// YAML configuration file identifiers — ALL 7 variants.
    ///
    /// Mirrors `classic_constants_core::YamlFile` exactly.
    /// Codex review MEDIUM correction: includes all 7 variants (not just 4).
    #[repr(u8)]
    enum YamlFile {
        Main = 0,
        Settings = 1,
        Ignore = 2,
        Game = 3,
        GameLocal = 4,
        Test = 5,
        Cache = 6,
    }

    extern "Rust" {
        /// Get the string representation of a `GameId` value.
        fn game_id_as_str(id: GameId) -> String;

        /// Get the `as_str()` representation of a `Fallout4Version` value.
        ///
        /// NOTE: `Vr` returns `"VR"` (uppercase).
        fn fallout4_version_as_str(v: Fallout4Version) -> String;

        /// Get the VersionRegistry ID for a `Fallout4Version` value.
        fn fallout4_version_registry_id(v: Fallout4Version) -> String;

        /// Returns `true` if this is the VR version.
        fn fallout4_version_is_vr(v: Fallout4Version) -> bool;

        /// Returns `true` if this is a standard (non-VR) version.
        fn fallout4_version_is_standard(v: Fallout4Version) -> bool;

        /// Get the game executable name for a `Fallout4Version` value.
        fn fallout4_version_exe_name(v: Fallout4Version) -> String;

        /// Get the Documents folder name for a `Fallout4Version` value.
        fn fallout4_version_docs_folder_name(v: Fallout4Version) -> String;

        /// Get the Steam App ID for a `Fallout4Version` value.
        fn fallout4_version_steam_app_id(v: Fallout4Version) -> u32;

        /// Get the `as_str()` representation of a `YamlFile` value.
        fn yaml_file_as_str(f: YamlFile) -> String;

        /// Get the human-readable description of a `YamlFile` value.
        fn yaml_file_description(f: YamlFile) -> String;

        /// Returns `true` if the given settings key must not be None.
        ///
        /// Delegates to `classic_constants_core::must_not_be_none`.
        fn must_not_be_none_key(key: &str) -> bool;

        /// Returns `true` if the given key is in the `SETTINGS_IGNORE_NONE` list.
        fn settings_ignore_none_contains(key: &str) -> bool;

        /// Returns `true` if the given (major, minor, patch) triple represents
        /// the `NULL_VERSION` (0.0.0).
        fn is_null_version(major: u32, minor: u32, patch: u32) -> bool;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_game_id_as_str_fallout4() {
        assert_eq!(game_id_as_str(ffi::GameId::Fallout4), "Fallout4");
    }

    #[test]
    fn test_game_id_as_str_fallout4vr() {
        assert_eq!(game_id_as_str(ffi::GameId::Fallout4VR), "Fallout4VR");
    }

    #[test]
    fn test_game_id_as_str_all_variants_match_core() {
        let pairs = [
            (ffi::GameId::Fallout4, CoreGameId::Fallout4),
            (ffi::GameId::Fallout4VR, CoreGameId::Fallout4VR),
            (ffi::GameId::Skyrim, CoreGameId::Skyrim),
            (ffi::GameId::Starfield, CoreGameId::Starfield),
        ];
        for (bridge, core) in pairs {
            assert_eq!(
                game_id_as_str(bridge),
                core.as_str(),
                "GameId bridge and core as_str() disagree"
            );
        }
    }

    #[test]
    fn test_fallout4_version_as_str_vr_is_uppercase_vr() {
        // Codex review LOW correction: Vr.as_str() returns literal "VR" (uppercase)
        assert_eq!(fallout4_version_as_str(ffi::Fallout4Version::Vr), "VR");
        // Sanity: also matches the core
        assert_eq!(
            fallout4_version_as_str(ffi::Fallout4Version::Vr),
            CoreFallout4Version::Vr.as_str()
        );
    }

    #[test]
    fn test_fallout4_version_as_str_original() {
        assert_eq!(
            fallout4_version_as_str(ffi::Fallout4Version::Original),
            "Original"
        );
    }

    #[test]
    fn test_fallout4_version_as_str_all_variants() {
        assert_eq!(
            fallout4_version_as_str(ffi::Fallout4Version::Original),
            "Original"
        );
        assert_eq!(
            fallout4_version_as_str(ffi::Fallout4Version::NextGen),
            "NextGen"
        );
        assert_eq!(
            fallout4_version_as_str(ffi::Fallout4Version::AnniversaryEdition),
            CoreFallout4Version::AnniversaryEdition.as_str()
        );
        // VR must be uppercase "VR", not "Vr"
        assert_eq!(fallout4_version_as_str(ffi::Fallout4Version::Vr), "VR");
    }

    #[test]
    fn test_fallout4_version_registry_id_original() {
        let expected = CoreFallout4Version::Original.registry_id();
        assert_eq!(
            fallout4_version_registry_id(ffi::Fallout4Version::Original),
            expected
        );
    }

    #[test]
    fn test_fallout4_version_is_vr_only_true_for_vr() {
        assert!(fallout4_version_is_vr(ffi::Fallout4Version::Vr));
        assert!(!fallout4_version_is_vr(ffi::Fallout4Version::Original));
        assert!(!fallout4_version_is_vr(ffi::Fallout4Version::NextGen));
        assert!(!fallout4_version_is_vr(
            ffi::Fallout4Version::AnniversaryEdition
        ));
    }

    #[test]
    fn test_fallout4_version_steam_app_id_nonzero_for_original() {
        assert!(fallout4_version_steam_app_id(ffi::Fallout4Version::Original) > 0);
    }

    #[test]
    fn test_fallout4_version_steam_app_id_vr_differs_from_original() {
        let orig = fallout4_version_steam_app_id(ffi::Fallout4Version::Original);
        let vr = fallout4_version_steam_app_id(ffi::Fallout4Version::Vr);
        assert_ne!(
            orig, vr,
            "VR and Original should have different Steam App IDs"
        );
        assert!(vr > 0, "VR Steam App ID should be non-zero");
    }

    #[test]
    fn test_yaml_file_as_str_all_seven_variants() {
        // Codex review MEDIUM correction: ALL 7 variants must be bridged
        let pairs = [
            (ffi::YamlFile::Main, "Main"),
            (ffi::YamlFile::Settings, "Settings"),
            (ffi::YamlFile::Ignore, "Ignore"),
            (ffi::YamlFile::Game, "Game"),
            (ffi::YamlFile::GameLocal, "GameLocal"),
            (ffi::YamlFile::Test, "Test"),
            (ffi::YamlFile::Cache, "Cache"),
        ];
        for (bridge, expected) in pairs {
            assert_eq!(
                yaml_file_as_str(bridge),
                expected,
                "YamlFile bridge as_str() mismatch"
            );
        }
    }

    #[test]
    fn test_yaml_file_description_returns_nonempty_for_all_seven() {
        for f in [
            ffi::YamlFile::Main,
            ffi::YamlFile::Settings,
            ffi::YamlFile::Ignore,
            ffi::YamlFile::Game,
            ffi::YamlFile::GameLocal,
            ffi::YamlFile::Test,
            ffi::YamlFile::Cache,
        ] {
            assert!(
                !yaml_file_description(f).is_empty(),
                "yaml_file_description should not be empty"
            );
        }
    }

    #[test]
    fn test_must_not_be_none_key_matches_settings_ignore_none() {
        for key in SETTINGS_IGNORE_NONE {
            assert!(
                must_not_be_none_key(key),
                "must_not_be_none_key should be true for key '{}'",
                key
            );
            assert!(
                settings_ignore_none_contains(key),
                "settings_ignore_none_contains should be true for key '{}'",
                key
            );
        }
    }

    #[test]
    fn test_must_not_be_none_key_false_for_unknown() {
        assert!(!must_not_be_none_key("definitely_not_a_real_key_xyz_789"));
        assert!(!settings_ignore_none_contains(
            "definitely_not_a_real_key_xyz_789"
        ));
    }

    #[test]
    fn test_is_null_version_predicate() {
        assert!(is_null_version(0, 0, 0));
        assert!(!is_null_version(1, 0, 0));
        assert!(!is_null_version(0, 1, 0));
        assert!(!is_null_version(0, 0, 1));
    }
}
