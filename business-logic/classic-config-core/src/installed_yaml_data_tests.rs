use crate::{
    InstalledYamlDataDiagnosticKind, InstalledYamlDataInspectionError,
    InstalledYamlDataInspectionRequest, InstalledYamlDataLoadError, InstalledYamlDataLoadOutcome,
    InstalledYamlDataLoadRequest, InstalledYamlDataProvenance, InstalledYamlDataRole,
    LocalIgnoreYamlDataState, inspect_installed_yaml_data_with_env,
    load_installed_yaml_data_with_env,
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

const IGNORE_YAML: &str = "CLASSIC_Ignore_Fallout4:\r\n  - ExistingUserEntry.dll\r\n";
const MAIN_SHA256: &str = "a1cc5332af4aeaaf0ddf8c8f4f151c5c445657ada5e2823b45ccf1a135c3bcde";
const GAME_SHA256: &str = "1bc32a693c96e4d51adce3d0f44f8ca02eac953dbcbb78f6898be56577aa7e08";
const IGNORE_SHA256: &str = "8876f72865dba00b7a7bf3dac0081d383a9b85053e5935d551e03b228d6e4743";
const UPDATED_MAIN_SHA256: &str =
    "e2cef80697286fa0e374b3f2eb1f10dd8f5fa5cf10d58ff3a94c0465a809da75";

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

fn write_existing_local_ignore(installation_root: &Path) -> PathBuf {
    let path = installation_root
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");
    std::fs::write(&path, IGNORE_YAML).expect("existing Local Ignore should be written");
    path
}

#[test]
fn installed_loading_returns_ready_snapshot_with_valid_existing_local_ignore() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install(installation.path());
    let ignore_path = write_existing_local_ignore(installation.path());

    let outcome = load_installed_yaml_data_with_env(
        InstalledYamlDataLoadRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        },
        isolated_cache_env(cache_root.path()),
    )
    .expect("a valid installation should load");
    let InstalledYamlDataLoadOutcome::Ready(snapshot) = outcome;

    assert_eq!(snapshot.game(), GameId::Fallout4);
    assert_eq!(snapshot.game_data_role(), crate::GameDataRole::Fallout4);
    assert_eq!(
        snapshot.local_ignore_state(),
        LocalIgnoreYamlDataState::Existing
    );
    assert_eq!(snapshot.yaml_data().ignore_list, ["ExistingUserEntry.dll"]);
    assert_eq!(
        snapshot.main().provenance(),
        InstalledYamlDataProvenance::Bundled
    );
    assert_eq!(
        snapshot.game_file().provenance(),
        InstalledYamlDataProvenance::Bundled
    );
    assert_eq!(snapshot.main().schema_version().to_string(), "2.0");
    assert_eq!(snapshot.game_file().schema_version().to_string(), "1.0");
    assert_eq!(
        snapshot.local_ignore_identity().byte_len(),
        IGNORE_YAML.len() as u64
    );
    assert!(snapshot.diagnostics().is_empty());
    assert_eq!(
        std::fs::read(ignore_path).expect("existing Local Ignore should remain readable"),
        IGNORE_YAML.as_bytes()
    );
}

#[test]
fn installed_snapshot_debug_does_not_expose_retained_content() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install(installation.path());
    write_existing_local_ignore(installation.path());

    let outcome = load_installed_yaml_data_with_env(
        InstalledYamlDataLoadRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        },
        isolated_cache_env(cache_root.path()),
    )
    .expect("a valid installation should load");
    let InstalledYamlDataLoadOutcome::Ready(snapshot) = outcome;
    let debug = format!("{snapshot:?}");

    assert!(!debug.contains("Bundled autoscan"));
    assert!(!debug.contains("ExistingUserEntry.dll"));
}

#[test]
fn installed_loading_selects_main_and_game_independently() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install(installation.path());
    write_existing_local_ignore(installation.path());
    let cache = cache_dir(cache_root.path());
    std::fs::create_dir_all(&cache).expect("cache directory should be created");
    let updated_main = MAIN_YAML.replace("Bundled autoscan", "Updated installed autoscan");
    std::fs::write(cache.join("CLASSIC Main.yaml"), updated_main)
        .expect("updated Main should be written");
    std::fs::write(
        cache.join("CLASSIC Fallout4.yaml"),
        GAME_YAML.replace(
            "Main_Root_Name: \"Fallout 4\"",
            "Main_Root_Name: \"Skyrim\"",
        ),
    )
    .expect("semantically invalid updated game should be written");

    let outcome = load_installed_yaml_data_with_env(
        InstalledYamlDataLoadRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        },
        isolated_cache_env(cache_root.path()),
    )
    .expect("independently selectable candidates should load");
    let InstalledYamlDataLoadOutcome::Ready(snapshot) = outcome;

    assert_eq!(
        snapshot.main().provenance(),
        InstalledYamlDataProvenance::Updated
    );
    assert_eq!(
        snapshot.game_file().provenance(),
        InstalledYamlDataProvenance::Bundled
    );
    assert_eq!(snapshot.main().identity().sha256_hex(), UPDATED_MAIN_SHA256);
    assert_eq!(snapshot.game_file().identity().sha256_hex(), GAME_SHA256);
    assert_eq!(
        snapshot.yaml_data().autoscan_text,
        "Updated installed autoscan"
    );
    assert!(snapshot.diagnostics().iter().any(|diagnostic| {
        diagnostic.role() == Some(InstalledYamlDataRole::Game)
            && diagnostic.candidate() == Some(InstalledYamlDataProvenance::Updated)
            && diagnostic.kind() == InstalledYamlDataDiagnosticKind::InvalidRoleData
    }));
}

#[test]
fn installed_snapshot_remains_stable_after_selected_files_change() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install(installation.path());
    let ignore_path = write_existing_local_ignore(installation.path());

    let outcome = load_installed_yaml_data_with_env(
        InstalledYamlDataLoadRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        },
        isolated_cache_env(cache_root.path()),
    )
    .expect("valid selected files should load");
    let InstalledYamlDataLoadOutcome::Ready(snapshot) = outcome;

    let databases = bundled_dir(installation.path());
    std::fs::write(databases.join("CLASSIC Main.yaml"), "changed after loading")
        .expect("selected Main path should be replaceable");
    std::fs::write(
        databases.join("CLASSIC Fallout4.yaml"),
        "changed after loading",
    )
    .expect("selected game path should be replaceable");
    std::fs::write(&ignore_path, "changed after loading")
        .expect("selected Local Ignore path should be replaceable");

    assert_eq!(snapshot.yaml_data().autoscan_text, "Bundled autoscan");
    assert_eq!(snapshot.yaml_data().game_root_name, "Fallout 4");
    assert_eq!(snapshot.yaml_data().ignore_list, ["ExistingUserEntry.dll"]);
    assert_eq!(snapshot.main().identity().sha256_hex(), MAIN_SHA256);
    assert_eq!(snapshot.game_file().identity().sha256_hex(), GAME_SHA256);
    assert_eq!(snapshot.local_ignore_identity().sha256_hex(), IGNORE_SHA256);
}

#[test]
fn installed_loading_rejects_unsupported_games_before_file_io() {
    let error = load_installed_yaml_data_with_env(
        InstalledYamlDataLoadRequest {
            installation_root: PathBuf::from("paths-must-not-be-read"),
            game: GameId::Skyrim,
            selected_game_version: "auto".to_string(),
        },
        |_| panic!("unsupported game must fail before cache resolution"),
    )
    .expect_err("unsupported game should return a typed fatal result");

    assert!(matches!(
        error,
        InstalledYamlDataLoadError::UnsupportedGame {
            game: GameId::Skyrim
        }
    ));
}

#[test]
fn installed_loading_reports_no_usable_required_source() {
    let installation = tempdir().expect("installation root should be created");

    let error = load_installed_yaml_data_with_env(
        InstalledYamlDataLoadRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        },
        |_| None,
    )
    .expect_err("missing required Main data should return a typed fatal result");

    let InstalledYamlDataLoadError::NoUsableSource { role, diagnostics } = error else {
        panic!("missing required Main should report no usable source");
    };
    assert_eq!(role, InstalledYamlDataRole::Main);
    assert!(diagnostics.iter().any(|diagnostic| {
        diagnostic.role() == Some(InstalledYamlDataRole::Main)
            && diagnostic.candidate() == Some(InstalledYamlDataProvenance::Bundled)
            && diagnostic.kind() == InstalledYamlDataDiagnosticKind::Missing
    }));
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
