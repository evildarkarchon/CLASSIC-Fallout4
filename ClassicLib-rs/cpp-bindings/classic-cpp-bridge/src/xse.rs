//! XSE bridge for CXX FFI (D-01, CXXS-09).
//!
//! Bridges `classic-xse-core` so C++ frontends can detect F4SE / SKSE / SFSE
//! installations and resolve version strings without going through the
//! string-based dispatch in `game.rs`.
//!
//! Per D-08, the existing string-form helpers (`detect_xse_version_string`,
//! `is_xse_installed_check`) remain available here AND keep delegation shims
//! in `game.rs` so existing C++ callers using `classic::game::*` continue
//! to compile. New code should use `classic::xse::*`.

use classic_shared_core::GameId;
use classic_xse_core::{
    detect_xse_version as core_detect_xse_version, get_xse_info as core_get_xse_info,
    is_xse_installed as core_is_xse_installed, XseInfo as CoreXseInfo, XseType as CoreXseType,
};
use std::path::Path;

// ─────────────────────────────────────────────────────────────────────
// XseType bridge ↔ core mapping
// ─────────────────────────────────────────────────────────────────────

fn from_bridge_xse_type(t: ffi::XseType) -> CoreXseType {
    match t {
        ffi::XseType::F4SE => CoreXseType::F4SE,
        ffi::XseType::F4SEVR => CoreXseType::F4SEVR,
        ffi::XseType::SKSE => CoreXseType::SKSE,
        ffi::XseType::SKSE64 => CoreXseType::SKSE64,
        ffi::XseType::SKSEVR => CoreXseType::SKSEVR,
        ffi::XseType::SFSE => CoreXseType::SFSE,
        _ => CoreXseType::F4SE, // CXX may add sentinel variants; default to F4SE
    }
}

// Used by both the typed and string-form helpers.
fn xse_type_from_str_internal(s: &str) -> Option<CoreXseType> {
    // Match the existing game.rs::xse_type_from_str logic — case-insensitive
    match s.to_uppercase().as_str() {
        "F4SE" => Some(CoreXseType::F4SE),
        "F4SEVR" => Some(CoreXseType::F4SEVR),
        "SKSE" => Some(CoreXseType::SKSE),
        "SKSE64" => Some(CoreXseType::SKSE64),
        "SKSEVR" => Some(CoreXseType::SKSEVR),
        "SFSE" => Some(CoreXseType::SFSE),
        _ => None,
    }
}

fn game_id_from_str(s: &str) -> Option<GameId> {
    match s {
        "Fallout4" => Some(GameId::Fallout4),
        "Fallout4VR" => Some(GameId::Fallout4VR),
        "Skyrim" => Some(GameId::Skyrim),
        "Starfield" => Some(GameId::Starfield),
        _ => None,
    }
}

// ─────────────────────────────────────────────────────────────────────
// Typed API (CXXS-09 widening — uses XseType shared enum)
// ─────────────────────────────────────────────────────────────────────

fn xse_get_loader_name(t: ffi::XseType) -> String {
    from_bridge_xse_type(t).loader_name().to_string()
}

fn xse_get_dll_prefix(t: ffi::XseType) -> String {
    // Codex LOW correction: returns the prefix WITH trailing underscore
    // (e.g., "f4se_") matching classic-xse-core/src/lib.rs:195.
    from_bridge_xse_type(t).dll_prefix().to_string()
}

fn xse_get_type_from_game_id(game_id_str: &str) -> String {
    // Codex LOW correction: from_game_id is INFALLIBLE (returns Self).
    // Only the string-decoding step can fail.
    let Some(game_id) = game_id_from_str(game_id_str) else {
        return String::new();
    };
    CoreXseType::from_game_id(game_id).as_str().to_string()
}

fn is_xse_installed(game_root: &str, t: ffi::XseType) -> bool {
    // Codex LOW correction: real signature takes &Path.
    if game_root.is_empty() {
        return false;
    }
    core_is_xse_installed(Path::new(game_root), from_bridge_xse_type(t))
}

fn detect_xse_version(exe_path: &str, t: ffi::XseType) -> String {
    // Codex LOW correction: real signature returns XseResult<semver::Version>.
    if exe_path.is_empty() {
        return String::new();
    }
    core_detect_xse_version(Path::new(exe_path), from_bridge_xse_type(t))
        .map(|v| v.to_string())
        .unwrap_or_default()
}

fn xse_get_info(game_path: &str, t: ffi::XseType) -> ffi::XseInfoDto {
    // Codex LOW correction: get_xse_info takes &Path; XseInfo.path is PathBuf,
    // version is Option<semver::Version>.
    let path_arg = if game_path.is_empty() {
        Path::new(".")
    } else {
        Path::new(game_path)
    };
    let info: CoreXseInfo = core_get_xse_info(path_arg, from_bridge_xse_type(t));
    ffi::XseInfoDto {
        xse_type: info.xse_type.as_str().to_string(),
        path: info.path.to_string_lossy().to_string(),
        version: info.version.map(|v| v.to_string()).unwrap_or_default(),
        installed: info.installed,
    }
}

// ─────────────────────────────────────────────────────────────────────
// String-form helpers (D-08 backward-compat, also called from game.rs shims)
// ─────────────────────────────────────────────────────────────────────

pub(crate) fn detect_xse_version_string_impl(exe_path: &str, xse_type_str: &str) -> String {
    let Some(xse_type) = xse_type_from_str_internal(xse_type_str) else {
        return String::new();
    };
    if exe_path.is_empty() {
        return String::new();
    }
    core_detect_xse_version(Path::new(exe_path), xse_type)
        .map(|v| v.to_string())
        .unwrap_or_default()
}

pub(crate) fn is_xse_installed_check_impl(game_root: &str, xse_type_str: &str) -> bool {
    let Some(xse_type) = xse_type_from_str_internal(xse_type_str) else {
        return false;
    };
    if game_root.is_empty() {
        return false;
    }
    core_is_xse_installed(Path::new(game_root), xse_type)
}

// Bridge fn aliases (the bridge block calls these names directly)
fn detect_xse_version_string(exe_path: &str, xse_type_str: &str) -> String {
    detect_xse_version_string_impl(exe_path, xse_type_str)
}
fn is_xse_installed_check(game_root: &str, xse_type_str: &str) -> bool {
    is_xse_installed_check_impl(game_root, xse_type_str)
}

// ─────────────────────────────────────────────────────────────────────
// CXX bridge block — D-04 shared enum + extern "Rust" fns
// ─────────────────────────────────────────────────────────────────────

#[cxx::bridge(namespace = "classic::xse")]
mod ffi {
    #[repr(u8)]
    enum XseType {
        F4SE = 0,
        F4SEVR = 1,
        SKSE = 2,
        SKSE64 = 3,
        SKSEVR = 4,
        SFSE = 5,
    }

    struct XseInfoDto {
        xse_type: String,
        path: String,
        version: String,
        installed: bool,
    }

    extern "Rust" {
        // Typed API (CXXS-09 widening)
        fn xse_get_loader_name(t: XseType) -> String;
        fn xse_get_dll_prefix(t: XseType) -> String;
        fn xse_get_type_from_game_id(game_id_str: &str) -> String;
        fn is_xse_installed(game_root: &str, t: XseType) -> bool;
        fn detect_xse_version(exe_path: &str, t: XseType) -> String;
        fn xse_get_info(game_path: &str, t: XseType) -> XseInfoDto;

        // String-form D-08 backward-compat
        fn detect_xse_version_string(exe_path: &str, xse_type_str: &str) -> String;
        fn is_xse_installed_check(game_root: &str, xse_type_str: &str) -> bool;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_xse_get_loader_name_f4se_exact_string() {
        // Codex LOW correction: verified literal at classic-xse-core/src/lib.rs:169
        assert_eq!(xse_get_loader_name(ffi::XseType::F4SE), "f4se_loader.exe");
    }

    #[test]
    fn test_xse_get_loader_name_skse64_exact_string() {
        assert_eq!(
            xse_get_loader_name(ffi::XseType::SKSE64),
            "skse64_loader.exe"
        );
    }

    #[test]
    fn test_xse_get_loader_name_all_variants_nonempty() {
        for t in [
            ffi::XseType::F4SE,
            ffi::XseType::F4SEVR,
            ffi::XseType::SKSE,
            ffi::XseType::SKSE64,
            ffi::XseType::SKSEVR,
            ffi::XseType::SFSE,
        ] {
            assert!(!xse_get_loader_name(t).is_empty());
            assert!(!xse_get_dll_prefix(t).is_empty());
        }
    }

    #[test]
    fn test_xse_get_dll_prefix_has_trailing_underscore() {
        // Codex LOW correction: dll_prefix returns "f4se_" / "skse64_" — with trailing underscore
        assert_eq!(xse_get_dll_prefix(ffi::XseType::F4SE), "f4se_");
        assert_eq!(xse_get_dll_prefix(ffi::XseType::SKSE64), "skse64_");
        assert_eq!(xse_get_dll_prefix(ffi::XseType::SFSE), "sfse_");
    }

    #[test]
    fn test_xse_get_type_from_game_id_total_mapping() {
        // Codex LOW correction: XseType::from_game_id is INFALLIBLE
        // Verified at classic-xse-core/src/lib.rs:143-150
        assert_eq!(xse_get_type_from_game_id("Fallout4"), "F4SE");
        assert_eq!(xse_get_type_from_game_id("Fallout4VR"), "F4SEVR");
        assert_eq!(xse_get_type_from_game_id("Skyrim"), "SKSE64");
        assert_eq!(xse_get_type_from_game_id("Starfield"), "SFSE");
    }

    #[test]
    fn test_xse_get_type_from_game_id_unknown_game_returns_empty() {
        // The only failure mode is the string-decoding step
        assert_eq!(xse_get_type_from_game_id("InvalidGame"), "");
    }

    #[test]
    fn test_is_xse_installed_nonexistent_returns_false() {
        assert!(!is_xse_installed("nonexistent\\path", ffi::XseType::F4SE));
    }

    #[test]
    fn test_is_xse_installed_empty_returns_false() {
        assert!(!is_xse_installed("", ffi::XseType::F4SE));
    }

    #[test]
    fn test_xse_get_info_nonexistent_returns_not_installed() {
        let info = xse_get_info("nonexistent\\path", ffi::XseType::F4SE);
        assert!(!info.installed);
        assert!(info.version.is_empty());
        assert_eq!(info.xse_type, "F4SE");
    }

    #[test]
    fn test_detect_xse_version_string_empty_returns_empty() {
        assert_eq!(detect_xse_version_string("", "F4SE"), "");
    }

    #[test]
    fn test_is_xse_installed_check_empty_returns_false() {
        assert!(!is_xse_installed_check("", "F4SE"));
    }

    #[test]
    fn test_xse_type_from_str_internal_known_and_unknown() {
        assert!(xse_type_from_str_internal("F4SE").is_some());
        assert!(xse_type_from_str_internal("f4se").is_some()); // case-insensitive
        assert!(xse_type_from_str_internal("SFSE").is_some());
        assert!(xse_type_from_str_internal("BOGUS").is_none());
    }
}
