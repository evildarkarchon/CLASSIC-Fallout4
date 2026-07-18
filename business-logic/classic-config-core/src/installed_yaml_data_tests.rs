use super::{
    InstalledYamlDataDiagnosticKind, InstalledYamlDataInspectionError,
    InstalledYamlDataInspectionRequest, InstalledYamlDataProvenance, InstalledYamlDataRole,
    inspect_installed_yaml_data_with_env,
};
use classic_shared_core::GameId;
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};
use tempfile::tempdir;

const MAIN_YAML: &str = r#"schema_version: "2.0"
CLASSIC_Info:
  version: "9.1.0"
  version_date: "2026-07-17"
CLASSIC_Interface:
  autoscan_text_Fallout4: "Bundled autoscan"
catch_log_records: []
"#;

const GAME_YAML: &str = r#"schema_version: "1.0"
Game_Info:
  Main_Root_Name: "Fallout 4"
  XSE_Acronym: "F4SE"
  GameVersion: "1.10.163"
Crashlog_Error_Check: []
Crashlog_Stack_Check: []
Mods_FREQ: []
Mods_SOLU: []
"#;

fn bundled_dir(installation_root: &Path) -> PathBuf {
    installation_root.join("CLASSIC Data").join("databases")
}

fn cache_dir(cache_root: &Path) -> PathBuf {
    cache_root.join("CLASSIC").join("yaml-cache")
}

fn isolated_cache_env(cache_root: &Path) -> impl Fn(&str) -> Option<String> + use<> {
    let cache_root = cache_root.to_string_lossy().into_owned();
    move |name| match name {
        #[cfg(target_os = "windows")]
        "LOCALAPPDATA" => Some(cache_root.clone()),
        #[cfg(not(target_os = "windows"))]
        "XDG_CACHE_HOME" => Some(cache_root.clone()),
        _ => None,
    }
}

fn write_bundled_install(installation_root: &Path) {
    let databases = bundled_dir(installation_root);
    std::fs::create_dir_all(&databases).expect("bundled YAML Data directory should be created");
    std::fs::write(databases.join("CLASSIC Main.yaml"), MAIN_YAML)
        .expect("bundled Main should be written");
    std::fs::write(databases.join("CLASSIC Fallout4.yaml"), GAME_YAML)
        .expect("bundled game should be written");
}

#[test]
fn inspection_selects_updated_main_and_bundled_game_independently() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install(installation.path());
    let cache = cache_dir(cache_root.path());
    std::fs::create_dir_all(&cache).expect("cache directory should be created");
    let updated_main = MAIN_YAML.replace("Bundled autoscan", "Updated autoscan");
    std::fs::write(cache.join("CLASSIC Main.yaml"), &updated_main)
        .expect("updated Main should be written");

    let inspection = inspect_installed_yaml_data_with_env(
        InstalledYamlDataInspectionRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
        },
        isolated_cache_env(cache_root.path()),
    )
    .expect("compatible updated Main and bundled game should be inspected");

    assert_eq!(
        inspection.main().provenance(),
        InstalledYamlDataProvenance::Updated
    );
    assert_eq!(
        inspection.game_file().provenance(),
        InstalledYamlDataProvenance::Bundled
    );
    assert_eq!(
        inspection.main().identity().byte_len(),
        updated_main.len() as u64
    );
    assert_eq!(
        inspection.game_file().identity().byte_len(),
        GAME_YAML.len() as u64
    );
}

#[test]
fn invalid_previous_candidate_is_attributed_before_bundled_fallback() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install(installation.path());
    let cache = cache_dir(cache_root.path());
    std::fs::create_dir_all(&cache).expect("cache directory should be created");
    let previous = cache.join("CLASSIC Main.yaml.prev");
    std::fs::write(&previous, "schema_version: [unterminated")
        .expect("invalid previous candidate should be written");

    let inspection = inspect_installed_yaml_data_with_env(
        InstalledYamlDataInspectionRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
        },
        isolated_cache_env(cache_root.path()),
    )
    .expect("invalid previous candidate should fall back to bundled data");

    assert_eq!(
        inspection.main().provenance(),
        InstalledYamlDataProvenance::Bundled
    );
    assert!(inspection.diagnostics().iter().any(|diagnostic| {
        diagnostic.role() == Some(InstalledYamlDataRole::Main)
            && diagnostic.candidate() == Some(InstalledYamlDataProvenance::Previous)
            && diagnostic.kind() == InstalledYamlDataDiagnosticKind::Parse
            && diagnostic.path() == Some(previous.as_path())
    }));
}

#[test]
fn incompatible_and_semantically_invalid_updated_candidates_fall_back_independently() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install(installation.path());
    let cache = cache_dir(cache_root.path());
    std::fs::create_dir_all(&cache).expect("cache directory should be created");
    std::fs::write(
        cache.join("CLASSIC Main.yaml"),
        MAIN_YAML.replace("schema_version: \"2.0\"", "schema_version: \"3.0\""),
    )
    .expect("incompatible updated Main should be written");
    std::fs::write(
        cache.join("CLASSIC Fallout4.yaml"),
        GAME_YAML.replace(
            "Main_Root_Name: \"Fallout 4\"",
            "Main_Root_Name: \"Skyrim\"",
        ),
    )
    .expect("semantically invalid updated game should be written");

    let inspection = inspect_installed_yaml_data_with_env(
        InstalledYamlDataInspectionRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
        },
        isolated_cache_env(cache_root.path()),
    )
    .expect("both rejected updates should fall back independently");

    assert_eq!(
        inspection.main().provenance(),
        InstalledYamlDataProvenance::Bundled
    );
    assert_eq!(
        inspection.game_file().provenance(),
        InstalledYamlDataProvenance::Bundled
    );
    assert!(inspection.diagnostics().iter().any(|diagnostic| {
        diagnostic.role() == Some(InstalledYamlDataRole::Main)
            && diagnostic.kind() == InstalledYamlDataDiagnosticKind::IncompatibleSchema
    }));
    assert!(inspection.diagnostics().iter().any(|diagnostic| {
        diagnostic.role() == Some(InstalledYamlDataRole::Game)
            && diagnostic.kind() == InstalledYamlDataDiagnosticKind::InvalidRoleData
    }));
}

#[test]
fn missing_canonical_selects_previous_without_promoting_it() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install(installation.path());
    let cache = cache_dir(cache_root.path());
    std::fs::create_dir_all(&cache).expect("cache directory should be created");
    let previous = cache.join("CLASSIC Main.yaml.prev");
    let previous_main = MAIN_YAML.replace("Bundled autoscan", "Recovered autoscan");
    std::fs::write(&previous, &previous_main).expect("previous Main should be written");

    let inspection = inspect_installed_yaml_data_with_env(
        InstalledYamlDataInspectionRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
        },
        isolated_cache_env(cache_root.path()),
    )
    .expect("valid previous candidate should be selected read-only");

    assert_eq!(
        inspection.main().provenance(),
        InstalledYamlDataProvenance::Previous
    );
    assert_eq!(
        inspection.main().identity().byte_len(),
        previous_main.len() as u64
    );
    assert!(
        previous.exists(),
        "inspection must preserve the previous sibling"
    );
    assert!(
        !cache.join("CLASSIC Main.yaml").exists(),
        "inspection must not promote the previous sibling"
    );
}

#[test]
fn present_invalid_canonical_never_selects_valid_previous() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install(installation.path());
    let cache = cache_dir(cache_root.path());
    std::fs::create_dir_all(&cache).expect("cache directory should be created");
    let canonical = cache.join("CLASSIC Main.yaml");
    let previous = cache.join("CLASSIC Main.yaml.prev");
    std::fs::write(&canonical, "schema_version: [invalid")
        .expect("invalid canonical should be written");
    std::fs::write(&previous, MAIN_YAML).expect("valid previous should be written");

    let inspection = inspect_installed_yaml_data_with_env(
        InstalledYamlDataInspectionRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
        },
        isolated_cache_env(cache_root.path()),
    )
    .expect("present invalid canonical should fall back to bundled data");

    assert_eq!(
        inspection.main().provenance(),
        InstalledYamlDataProvenance::Bundled
    );
    assert!(inspection.diagnostics().iter().any(|diagnostic| {
        diagnostic.candidate() == Some(InstalledYamlDataProvenance::Updated)
            && diagnostic.kind() == InstalledYamlDataDiagnosticKind::Parse
    }));
    assert!(
        !inspection.diagnostics().iter().any(|diagnostic| {
            diagnostic.candidate() == Some(InstalledYamlDataProvenance::Previous)
        }),
        "a previous sibling must not participate while canonical exists"
    );
    assert_eq!(
        std::fs::read(&previous).expect("previous sibling should remain readable"),
        MAIN_YAML.as_bytes()
    );
}

#[test]
fn unavailable_cache_uses_bundled_data_with_structured_diagnostic() {
    let installation = tempdir().expect("installation root should be created");
    write_bundled_install(installation.path());

    let inspection = inspect_installed_yaml_data_with_env(
        InstalledYamlDataInspectionRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
        },
        |_| None,
    )
    .expect("unavailable cache should leave bundled data eligible");

    assert_eq!(
        inspection.main().provenance(),
        InstalledYamlDataProvenance::Bundled
    );
    assert_eq!(
        inspection.game_file().provenance(),
        InstalledYamlDataProvenance::Bundled
    );
    assert!(inspection.diagnostics().iter().any(|diagnostic| {
        diagnostic.role().is_none()
            && diagnostic.kind() == InstalledYamlDataDiagnosticKind::CacheUnavailable
    }));
}

#[test]
fn fallout4_vr_maps_to_fallout4_and_unsupported_games_fail_before_file_io() {
    let installation = tempdir().expect("installation root should be created");
    write_bundled_install(installation.path());

    let vr = inspect_installed_yaml_data_with_env(
        InstalledYamlDataInspectionRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4VR,
        },
        |_| None,
    )
    .expect("Fallout 4 VR should inspect Fallout 4 YAML Data");
    assert_eq!(vr.game(), GameId::Fallout4VR);
    assert_eq!(vr.game_data_role(), crate::GameDataRole::Fallout4);

    let unsupported = inspect_installed_yaml_data_with_env(
        InstalledYamlDataInspectionRequest {
            installation_root: PathBuf::from("paths-must-not-be-read"),
            game: GameId::Skyrim,
        },
        |_| panic!("unsupported game must fail before cache resolution"),
    )
    .expect_err("unsupported game should return a typed error");
    assert!(matches!(
        unsupported,
        InstalledYamlDataInspectionError::UnsupportedGame {
            game: GameId::Skyrim
        }
    ));
}

#[test]
fn identity_is_derived_from_selected_bytes_and_local_ignore_is_untouched() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install(installation.path());
    let cache = cache_dir(cache_root.path());
    std::fs::create_dir_all(&cache).expect("cache directory should be created");
    let canonical = cache.join("CLASSIC Main.yaml");
    let updated_main = MAIN_YAML.replace("Bundled autoscan", "Exact owned bytes");
    std::fs::write(&canonical, &updated_main).expect("updated Main should be written");
    let local_ignore = installation
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");
    let malformed_ignore = b"CLASSIC_Ignore_Fallout4: [unterminated";
    std::fs::write(&local_ignore, malformed_ignore)
        .expect("Local Ignore sentinel should be written");

    let inspection = inspect_installed_yaml_data_with_env(
        InstalledYamlDataInspectionRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
        },
        isolated_cache_env(cache_root.path()),
    )
    .expect("Local Ignore must not participate in inspection");
    let expected_digest = Sha256::digest(updated_main.as_bytes())
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect::<String>();

    std::fs::write(&canonical, MAIN_YAML).expect("selected path should be replaceable afterward");

    assert_eq!(inspection.main().identity().sha256_hex(), expected_digest);
    assert_eq!(
        std::fs::read(&local_ignore).expect("Local Ignore should remain readable"),
        malformed_ignore
    );
}
