use super::{
    LocalIgnoreFileSystem, LocalIgnoreResetPublicationKind, LocalIgnoreResetPublisher,
    SystemLocalIgnoreFileSystem, SystemLocalIgnoreResetPublisher,
    load_installed_yaml_data_with_env_and_io,
};
use crate::{
    InstalledYamlDataDiagnosticKind, InstalledYamlDataInspectionError,
    InstalledYamlDataInspectionRequest, InstalledYamlDataLoadError, InstalledYamlDataLoadOutcome,
    InstalledYamlDataLoadRequest, InstalledYamlDataProvenance, InstalledYamlDataRole,
    LocalIgnoreResetError, LocalIgnoreResetOutcome, LocalIgnoreResetPublicationStage,
    LocalIgnoreYamlDataState, inspect_installed_yaml_data_with_env,
    load_installed_yaml_data_with_env,
};
use classic_shared_core::GameId;
use sha2::{Digest, Sha256};
use std::io;
use std::path::{Path, PathBuf};
use std::sync::{
    Arc, Barrier,
    atomic::{AtomicBool, AtomicUsize, Ordering},
};
use tempfile::tempdir;

const MAIN_YAML: &str = r#"schema_version: "2.0"
CLASSIC_Info:
  version: "9.1.0"
  version_date: "2026-07-17"
CLASSIC_Interface:
  autoscan_text_Fallout4: "Bundled autoscan"
catch_log_records: []
"#;

const DEFAULT_IGNORE_YAML: &str = "CLASSIC_Ignore_Fallout4:\n  - SelectedMainDefault.dll\n";

const MAIN_WITH_DEFAULT_YAML: &str = r#"schema_version: "2.0"
CLASSIC_Info:
  version: "9.1.0"
  version_date: "2026-07-17"
  default_ignorefile: |
    CLASSIC_Ignore_Fallout4:
      - SelectedMainDefault.dll
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
    write_bundled_install_with_main(installation_root, MAIN_YAML);
}

/// Write one isolated bundled installation using the caller-selected Main fixture.
fn write_bundled_install_with_main(installation_root: &Path, main_yaml: &str) {
    let databases = bundled_dir(installation_root);
    std::fs::create_dir_all(&databases).expect("bundled YAML Data directory should be created");
    std::fs::write(databases.join("CLASSIC Main.yaml"), main_yaml)
        .expect("bundled Main should be written");
    std::fs::write(databases.join("CLASSIC Fallout4.yaml"), GAME_YAML)
        .expect("bundled game should be written");
}

/// Build valid Main YAML whose retained Local Ignore default identifies one entry.
fn main_with_default(entry: &str, autoscan_text: &str) -> String {
    format!(
        r#"schema_version: "2.0"
CLASSIC_Info:
  version: "9.1.0"
  version_date: "2026-07-17"
  default_ignorefile: |
    CLASSIC_Ignore_Fallout4:
      - {entry}
CLASSIC_Interface:
  autoscan_text_Fallout4: "{autoscan_text}"
catch_log_records: []
"#
    )
}

/// Filesystem seam that makes concurrent publishers rendezvous after validation and staging.
struct BarrierLocalIgnoreFileSystem {
    publish_barrier: Arc<Barrier>,
}

impl LocalIgnoreFileSystem for BarrierLocalIgnoreFileSystem {
    fn read(&self, path: &Path) -> io::Result<Vec<u8>> {
        std::fs::read(path)
    }

    fn publish_staged_noclobber(&self, staged_path: &Path, path: &Path) -> io::Result<bool> {
        self.publish_barrier.wait();
        SystemLocalIgnoreFileSystem.publish_staged_noclobber(staged_path, path)
    }
}

/// Filesystem seam that rejects the final publication operation.
struct PublicationFailureLocalIgnoreFileSystem;

impl LocalIgnoreFileSystem for PublicationFailureLocalIgnoreFileSystem {
    fn read(&self, path: &Path) -> io::Result<Vec<u8>> {
        std::fs::read(path)
    }

    fn publish_staged_noclobber(&self, _staged_path: &Path, _path: &Path) -> io::Result<bool> {
        Err(io::Error::new(
            io::ErrorKind::PermissionDenied,
            "injected Local Ignore publication failure",
        ))
    }
}

/// Filesystem seam that permits the initial missing read but rejects the authoritative reread.
struct RereadFailureLocalIgnoreFileSystem {
    read_count: AtomicUsize,
}

impl LocalIgnoreFileSystem for RereadFailureLocalIgnoreFileSystem {
    fn read(&self, path: &Path) -> io::Result<Vec<u8>> {
        if self.read_count.fetch_add(1, Ordering::SeqCst) == 0 {
            std::fs::read(path)
        } else {
            Err(io::Error::new(
                io::ErrorKind::PermissionDenied,
                "injected Local Ignore authoritative reread failure",
            ))
        }
    }

    fn publish_staged_noclobber(&self, staged_path: &Path, path: &Path) -> io::Result<bool> {
        SystemLocalIgnoreFileSystem.publish_staged_noclobber(staged_path, path)
    }
}

/// Filesystem seam that replaces selected Main after defaults are staged but before publication.
struct MainReplacingLocalIgnoreFileSystem {
    main_path: PathBuf,
    replacement_main: Vec<u8>,
}

impl LocalIgnoreFileSystem for MainReplacingLocalIgnoreFileSystem {
    fn read(&self, path: &Path) -> io::Result<Vec<u8>> {
        std::fs::read(path)
    }

    fn publish_staged_noclobber(&self, staged_path: &Path, path: &Path) -> io::Result<bool> {
        std::fs::write(&self.main_path, &self.replacement_main)?;
        SystemLocalIgnoreFileSystem.publish_staged_noclobber(staged_path, path)
    }
}

fn write_existing_local_ignore(installation_root: &Path) -> PathBuf {
    let path = installation_root
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");
    std::fs::write(&path, IGNORE_YAML).expect("existing Local Ignore should be written");
    path
}

#[test]
/// Production publication moves staged bytes into place without retaining a hard-linked source.
fn system_local_ignore_publication_uses_a_noclobber_move() {
    let directory = tempdir().expect("publication directory should be created");
    let staged_path = directory.path().join("staged-ignore.yaml");
    let ignore_path = directory.path().join("CLASSIC Ignore.yaml");
    std::fs::write(&staged_path, DEFAULT_IGNORE_YAML).expect("staged defaults should be written");

    assert!(
        SystemLocalIgnoreFileSystem
            .publish_staged_noclobber(&staged_path, &ignore_path)
            .expect("no-clobber move should publish into an absent path")
    );
    assert_eq!(
        std::fs::read(&ignore_path).expect("published Local Ignore should be readable"),
        DEFAULT_IGNORE_YAML.as_bytes()
    );
    assert!(
        !staged_path.exists(),
        "publication must move the staging name instead of retaining it as a hard-link source"
    );
}

#[test]
/// Production publication preserves an existing canonical winner and the losing staged bytes.
fn system_local_ignore_publication_does_not_clobber_an_existing_path() {
    let directory = tempdir().expect("publication directory should be created");
    let staged_path = directory.path().join("staged-ignore.yaml");
    let ignore_path = directory.path().join("CLASSIC Ignore.yaml");
    std::fs::write(&staged_path, DEFAULT_IGNORE_YAML).expect("staged defaults should be written");
    std::fs::write(&ignore_path, IGNORE_YAML).expect("canonical winner should be written");

    assert!(
        !SystemLocalIgnoreFileSystem
            .publish_staged_noclobber(&staged_path, &ignore_path)
            .expect("an existing canonical path should be reported as a lost race")
    );
    assert_eq!(
        std::fs::read(&ignore_path).expect("canonical winner should remain readable"),
        IGNORE_YAML.as_bytes()
    );
    assert_eq!(
        std::fs::read(&staged_path).expect("losing staged bytes should remain caller-owned"),
        DEFAULT_IGNORE_YAML.as_bytes()
    );
}

#[test]
/// Missing Local Ignore is initialized from the exact selected Main defaults.
fn missing_local_ignore_is_generated_from_the_selected_main_snapshot() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install_with_main(installation.path(), MAIN_WITH_DEFAULT_YAML);
    let ignore_path = installation
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");

    let outcome = load_installed_yaml_data_with_env(
        InstalledYamlDataLoadRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        },
        isolated_cache_env(cache_root.path()),
    )
    .expect("a missing Local Ignore should be generated from selected Main defaults");
    let InstalledYamlDataLoadOutcome::Ready(snapshot) = outcome else {
        panic!("generated Local Ignore should return a Ready snapshot");
    };

    assert_eq!(
        snapshot.local_ignore_state(),
        LocalIgnoreYamlDataState::Generated
    );
    assert_eq!(
        snapshot.yaml_data().ignore_list,
        ["SelectedMainDefault.dll"]
    );
    assert_eq!(
        std::fs::read(&ignore_path).expect("generated Local Ignore should be readable"),
        DEFAULT_IGNORE_YAML.as_bytes()
    );
    assert!(snapshot.diagnostics().iter().any(|diagnostic| {
        diagnostic.role().is_none()
            && diagnostic.candidate().is_none()
            && diagnostic.path() == Some(ignore_path.as_path())
            && diagnostic.kind() == InstalledYamlDataDiagnosticKind::LocalIgnoreGenerated
    }));
}

#[test]
/// Invalid selected Main defaults fail before staging or publishing any filesystem content.
fn invalid_selected_main_defaults_fail_before_any_generation_attempt() {
    let invalid_mains = [
        ("missing", MAIN_YAML.to_string()),
        (
            "non-string",
            MAIN_WITH_DEFAULT_YAML.replace(
                "default_ignorefile: |\n    CLASSIC_Ignore_Fallout4:\n      - SelectedMainDefault.dll",
                "default_ignorefile: [not, a, string]",
            ),
        ),
        (
            "empty",
            MAIN_WITH_DEFAULT_YAML.replace(
                "default_ignorefile: |\n    CLASSIC_Ignore_Fallout4:\n      - SelectedMainDefault.dll",
                "default_ignorefile: \"\"",
            ),
        ),
        (
            "malformed-role",
            MAIN_WITH_DEFAULT_YAML.replace(
                "CLASSIC_Ignore_Fallout4:\n      - SelectedMainDefault.dll",
                "CLASSIC_Ignore_Fallout4: not-a-sequence",
            ),
        ),
        (
            "malformed-yaml",
            MAIN_WITH_DEFAULT_YAML.replace(
                "CLASSIC_Ignore_Fallout4:\n      - SelectedMainDefault.dll",
                "CLASSIC_Ignore_Fallout4: [unterminated",
            ),
        ),
    ];

    for (case, main_yaml) in invalid_mains {
        let installation = tempdir().expect("installation root should be created");
        let cache_root = tempdir().expect("cache root should be created");
        write_bundled_install_with_main(installation.path(), &main_yaml);
        let ignore_path = installation
            .path()
            .join("CLASSIC Data")
            .join("CLASSIC Ignore.yaml");

        let error = load_installed_yaml_data_with_env(
            InstalledYamlDataLoadRequest {
                installation_root: installation.path().to_path_buf(),
                game: GameId::Fallout4,
                selected_game_version: "Original".to_string(),
            },
            isolated_cache_env(cache_root.path()),
        )
        .expect_err("invalid defaults must prevent Local Ignore generation");

        assert!(
            matches!(
                error,
                InstalledYamlDataLoadError::LocalIgnoreDefaultInvalid { path, .. }
                    if path == ignore_path
            ),
            "case `{case}` should return the typed default-validation failure"
        );
        assert!(
            !ignore_path.exists(),
            "case `{case}` must not publish partial Local Ignore content"
        );
        let data_entries = std::fs::read_dir(installation.path().join("CLASSIC Data"))
            .expect("CLASSIC Data should remain readable")
            .map(|entry| {
                entry
                    .expect("directory entry should be readable")
                    .file_name()
            })
            .collect::<Vec<_>>();
        assert_eq!(
            data_entries,
            [std::ffi::OsString::from("databases")],
            "case `{case}` must fail before creating a staging file"
        );
    }
}

#[test]
/// Accidental deletion follows the same successful generation path on the next load.
fn deleting_local_ignore_regenerates_it_from_the_new_selected_snapshot() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    let main_path = bundled_dir(installation.path()).join("CLASSIC Main.yaml");
    write_bundled_install_with_main(
        installation.path(),
        &main_with_default("FirstDefault.dll", "First snapshot"),
    );
    let request = InstalledYamlDataLoadRequest {
        installation_root: installation.path().to_path_buf(),
        game: GameId::Fallout4,
        selected_game_version: "Original".to_string(),
    };
    let ignore_path = installation
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");

    let first =
        load_installed_yaml_data_with_env(request.clone(), isolated_cache_env(cache_root.path()))
            .expect("first run should generate Local Ignore");
    let InstalledYamlDataLoadOutcome::Ready(first) = first else {
        panic!("the initial generated Local Ignore should return Ready");
    };
    assert_eq!(first.yaml_data().ignore_list, ["FirstDefault.dll"]);

    std::fs::remove_file(&ignore_path).expect("generated Local Ignore should be deletable");
    std::fs::write(
        &main_path,
        main_with_default("RegeneratedDefault.dll", "Second snapshot"),
    )
    .expect("selected Main should be replaceable before the next load");

    let second = load_installed_yaml_data_with_env(request, isolated_cache_env(cache_root.path()))
        .expect("accidental deletion should use the successful generation path");
    let InstalledYamlDataLoadOutcome::Ready(second) = second else {
        panic!("the valid generated Local Ignore should return Ready on reload");
    };

    assert_eq!(
        second.local_ignore_state(),
        LocalIgnoreYamlDataState::Generated
    );
    assert_eq!(second.yaml_data().ignore_list, ["RegeneratedDefault.dll"]);
    assert_eq!(second.yaml_data().autoscan_text, "Second snapshot");
}

#[test]
/// Concurrent loaders preserve one complete winner and all snapshots reread its bytes.
fn concurrent_generation_preserves_one_winner_and_every_loader_rereads_it() {
    let installation = tempdir().expect("installation root should be created");
    let cache_a = tempdir().expect("first cache root should be created");
    let cache_b = tempdir().expect("second cache root should be created");
    write_bundled_install_with_main(installation.path(), MAIN_WITH_DEFAULT_YAML);
    for (cache_root, entry, autoscan) in [
        (cache_a.path(), "ConcurrentA.dll", "Selected A"),
        (cache_b.path(), "ConcurrentB.dll", "Selected B"),
    ] {
        let cache = cache_dir(cache_root);
        std::fs::create_dir_all(&cache).expect("updated cache should be created");
        std::fs::write(
            cache.join("CLASSIC Main.yaml"),
            main_with_default(entry, autoscan),
        )
        .expect("updated Main should be written");
    }
    let installation_root = installation.path().to_path_buf();
    let start_barrier = Arc::new(Barrier::new(3));
    let publish_barrier = Arc::new(Barrier::new(2));
    let spawn_loader = |cache_root: PathBuf, expected_default: &'static str| {
        let installation_root = installation_root.clone();
        let start_barrier = Arc::clone(&start_barrier);
        let local_ignore_io = BarrierLocalIgnoreFileSystem {
            publish_barrier: Arc::clone(&publish_barrier),
        };
        std::thread::spawn(move || {
            start_barrier.wait();
            let outcome = load_installed_yaml_data_with_env_and_io(
                InstalledYamlDataLoadRequest {
                    installation_root,
                    game: GameId::Fallout4,
                    selected_game_version: "Original".to_string(),
                },
                isolated_cache_env(&cache_root),
                &local_ignore_io,
            )
            .expect("each concurrent loader should become Ready");
            let InstalledYamlDataLoadOutcome::Ready(snapshot) = outcome else {
                panic!("a valid concurrent Local Ignore winner should return Ready");
            };
            (expected_default, snapshot)
        })
    };
    let loader_a = spawn_loader(cache_a.path().to_path_buf(), "ConcurrentA.dll");
    let loader_b = spawn_loader(cache_b.path().to_path_buf(), "ConcurrentB.dll");

    start_barrier.wait();
    let results = [
        loader_a.join().expect("first loader should not panic"),
        loader_b.join().expect("second loader should not panic"),
    ];
    let ignore_path = installation_root
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");
    let winning_bytes = std::fs::read(&ignore_path).expect("winning Local Ignore should exist");
    let winning_default =
        if winning_bytes == b"CLASSIC_Ignore_Fallout4:\n  - ConcurrentA.dll\n".as_slice() {
            "ConcurrentA.dll"
        } else {
            assert_eq!(
                winning_bytes, b"CLASSIC_Ignore_Fallout4:\n  - ConcurrentB.dll\n",
                "the canonical file must be one complete selected-Main default"
            );
            "ConcurrentB.dll"
        };
    let winning_digest = Sha256::digest(&winning_bytes)
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect::<String>();

    assert_eq!(
        results
            .iter()
            .filter(|(_, snapshot)| {
                snapshot.local_ignore_state() == LocalIgnoreYamlDataState::Generated
            })
            .count(),
        1,
        "exactly one no-clobber publisher should win"
    );
    for (selected_default, snapshot) in results {
        assert_eq!(
            snapshot.yaml_data().ignore_list,
            [winning_default],
            "every caller must reread the authoritative winner"
        );
        assert_eq!(
            snapshot.local_ignore_identity().sha256_hex(),
            winning_digest,
            "snapshot identity must derive from the reread winner bytes"
        );
        assert_eq!(
            snapshot.local_ignore_identity().byte_len(),
            winning_bytes.len() as u64
        );
        if snapshot.local_ignore_state() == LocalIgnoreYamlDataState::Generated {
            assert_eq!(
                selected_default, winning_default,
                "published content must come from the winner's retained Main snapshot"
            );
            assert!(snapshot.diagnostics().iter().any(|diagnostic| {
                diagnostic.kind() == InstalledYamlDataDiagnosticKind::LocalIgnoreGenerated
                    && diagnostic.path() == Some(ignore_path.as_path())
            }));
        }
    }
    let data_entries = std::fs::read_dir(installation_root.join("CLASSIC Data"))
        .expect("CLASSIC Data should remain readable")
        .map(|entry| {
            entry
                .expect("directory entry should be readable")
                .file_name()
        })
        .collect::<Vec<_>>();
    assert_eq!(
        data_entries.len(),
        2,
        "the losing publisher must clean its caller-owned staging file"
    );
    assert!(data_entries.contains(&std::ffi::OsString::from("databases")));
    assert!(data_entries.contains(&std::ffi::OsString::from("CLASSIC Ignore.yaml")));
}

#[test]
/// Publication failures return the typed creation error and remove the complete staging file.
fn publication_failure_leaves_no_local_ignore_or_staging_content() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install_with_main(installation.path(), MAIN_WITH_DEFAULT_YAML);
    let ignore_path = installation
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");

    let error = load_installed_yaml_data_with_env_and_io(
        InstalledYamlDataLoadRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        },
        isolated_cache_env(cache_root.path()),
        &PublicationFailureLocalIgnoreFileSystem,
    )
    .expect_err("an injected publication failure should abort the load");

    match error {
        InstalledYamlDataLoadError::LocalIgnoreCreate { path, source } => {
            assert_eq!(path, ignore_path);
            assert_eq!(source.kind(), io::ErrorKind::PermissionDenied);
        }
        other => panic!("publication should return LocalIgnoreCreate, got {other:?}"),
    }
    assert!(
        !ignore_path.exists(),
        "failed publication must not expose partial canonical content"
    );
    let data_entries = std::fs::read_dir(installation.path().join("CLASSIC Data"))
        .expect("CLASSIC Data should remain readable")
        .map(|entry| {
            entry
                .expect("directory entry should be readable")
                .file_name()
        })
        .collect::<Vec<_>>();
    assert_eq!(
        data_entries,
        [std::ffi::OsString::from("databases")],
        "the dropped staging file must be cleaned up"
    );
}

#[test]
/// Authoritative reread failures return a typed read error without exposing partial content.
fn authoritative_reread_failure_returns_error_after_complete_publication() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install_with_main(installation.path(), MAIN_WITH_DEFAULT_YAML);
    let ignore_path = installation
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");
    let local_ignore_io = RereadFailureLocalIgnoreFileSystem {
        read_count: AtomicUsize::new(0),
    };

    let error = load_installed_yaml_data_with_env_and_io(
        InstalledYamlDataLoadRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        },
        isolated_cache_env(cache_root.path()),
        &local_ignore_io,
    )
    .expect_err("an injected authoritative reread failure should abort the load");

    match error {
        InstalledYamlDataLoadError::LocalIgnoreRead { path, source } => {
            assert_eq!(path, ignore_path);
            assert_eq!(source.kind(), io::ErrorKind::PermissionDenied);
        }
        other => panic!("reread should return LocalIgnoreRead, got {other:?}"),
    }
    assert_eq!(
        std::fs::read(&ignore_path).expect("published canonical bytes should remain complete"),
        DEFAULT_IGNORE_YAML.as_bytes()
    );
    let mut data_entries = std::fs::read_dir(installation.path().join("CLASSIC Data"))
        .expect("CLASSIC Data should remain readable")
        .map(|entry| {
            entry
                .expect("directory entry should be readable")
                .file_name()
        })
        .collect::<Vec<_>>();
    data_entries.sort();
    assert_eq!(
        data_entries,
        [
            std::ffi::OsString::from("CLASSIC Ignore.yaml"),
            std::ffi::OsString::from("databases"),
        ],
        "publication must leave no temporary or partial artifact"
    );
}

#[test]
/// Main replacement during generation cannot change retained defaults or snapshot identity.
fn generation_uses_retained_main_when_selected_path_changes_before_publication() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    let selected_main = main_with_default("RetainedDefault.dll", "Retained snapshot");
    let replacement_main = main_with_default("ReplacementDefault.dll", "Replacement snapshot");
    write_bundled_install_with_main(installation.path(), &selected_main);
    let main_path = bundled_dir(installation.path()).join("CLASSIC Main.yaml");
    let ignore_path = installation
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");
    let expected_main_digest = Sha256::digest(selected_main.as_bytes())
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect::<String>();
    let local_ignore_io = MainReplacingLocalIgnoreFileSystem {
        main_path: main_path.clone(),
        replacement_main: replacement_main.as_bytes().to_vec(),
    };

    let outcome = load_installed_yaml_data_with_env_and_io(
        InstalledYamlDataLoadRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        },
        isolated_cache_env(cache_root.path()),
        &local_ignore_io,
    )
    .expect("generation should remain bound to the retained selected Main bytes");
    let InstalledYamlDataLoadOutcome::Ready(snapshot) = outcome else {
        panic!("a generated Local Ignore from retained Main should return Ready");
    };

    assert_eq!(
        std::fs::read(&main_path).expect("replacement Main should be readable"),
        replacement_main.as_bytes(),
        "the test seam must replace Main during generation"
    );
    assert_eq!(snapshot.yaml_data().autoscan_text, "Retained snapshot");
    assert_eq!(snapshot.yaml_data().ignore_list, ["RetainedDefault.dll"]);
    assert_eq!(
        snapshot.main().identity().sha256_hex(),
        expected_main_digest
    );
    assert_eq!(
        std::fs::read(ignore_path).expect("generated Local Ignore should be readable"),
        b"CLASSIC_Ignore_Fallout4:\n  - RetainedDefault.dll\n"
    );
    assert_eq!(
        snapshot.local_ignore_state(),
        LocalIgnoreYamlDataState::Generated
    );
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
    let InstalledYamlDataLoadOutcome::Ready(snapshot) = outcome else {
        panic!("valid existing Local Ignore should return Ready");
    };

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
    let InstalledYamlDataLoadOutcome::Ready(snapshot) = outcome else {
        panic!("valid existing Local Ignore should return Ready");
    };
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
    let InstalledYamlDataLoadOutcome::Ready(snapshot) = outcome else {
        panic!("independently selected valid data should return Ready");
    };

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
    let InstalledYamlDataLoadOutcome::Ready(snapshot) = outcome else {
        panic!("valid selected files should return Ready");
    };

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
/// Proceed Without Ignore uses retained data and leaves every installation file untouched.
fn malformed_local_ignore_can_proceed_without_ignore_from_retained_snapshot_without_writes() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install_with_main(installation.path(), MAIN_WITH_DEFAULT_YAML);
    let ignore_path = installation
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");
    let malformed_ignore = b"CLASSIC_Ignore_Fallout4: [unterminated";
    std::fs::write(&ignore_path, malformed_ignore)
        .expect("malformed Local Ignore should be written");

    let outcome = load_installed_yaml_data_with_env(
        InstalledYamlDataLoadRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        },
        isolated_cache_env(cache_root.path()),
    )
    .expect("malformed Local Ignore should require an expected recovery decision");
    let InstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired(plan) = outcome else {
        panic!("malformed Local Ignore should return a recovery plan");
    };

    assert_eq!(plan.local_ignore_path(), ignore_path);
    assert_eq!(
        plan.malformed_local_ignore_identity().sha256_hex(),
        Sha256::digest(malformed_ignore)
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    );
    assert_eq!(
        plan.default_local_ignore_identity()
            .expect("valid selected-Main defaults should retain an identity")
            .sha256_hex(),
        Sha256::digest(DEFAULT_IGNORE_YAML.as_bytes())
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    );
    assert!(plan.diagnostics().iter().any(|diagnostic| {
        diagnostic.role().is_none()
            && diagnostic.candidate().is_none()
            && diagnostic.path() == Some(ignore_path.as_path())
            && diagnostic.kind() == InstalledYamlDataDiagnosticKind::Parse
    }));

    let databases = bundled_dir(installation.path());
    let main_path = databases.join("CLASSIC Main.yaml");
    let game_path = databases.join("CLASSIC Fallout4.yaml");
    std::fs::write(&main_path, "changed after recovery was requested")
        .expect("selected Main path should be replaceable");
    std::fs::write(&game_path, "changed after recovery was requested")
        .expect("selected game path should be replaceable");
    let before_proceed = [
        std::fs::read(&main_path).expect("changed Main should remain readable"),
        std::fs::read(&game_path).expect("changed game should remain readable"),
        std::fs::read(&ignore_path).expect("malformed Local Ignore should remain readable"),
    ];

    let snapshot = plan.proceed_without_ignore();

    assert_eq!(snapshot.yaml_data().autoscan_text, "Bundled autoscan");
    assert_eq!(snapshot.yaml_data().game_root_name, "Fallout 4");
    assert!(snapshot.yaml_data().ignore_list.is_empty());
    assert_eq!(
        snapshot.local_ignore_state(),
        LocalIgnoreYamlDataState::ProceedWithoutIgnore
    );
    assert_eq!(
        snapshot.local_ignore_identity().sha256_hex(),
        Sha256::digest(malformed_ignore)
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    );
    assert_eq!(
        [
            std::fs::read(&main_path).expect("Main should remain readable after proceeding"),
            std::fs::read(&game_path).expect("game should remain readable after proceeding"),
            std::fs::read(&ignore_path)
                .expect("Local Ignore should remain readable after proceeding"),
        ],
        before_proceed
    );
}

#[test]
/// Reset retains an exact durable backup and publishes the already selected Main defaults.
fn malformed_local_ignore_can_reset_to_retained_defaults_with_verified_backup_metadata() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install_with_main(installation.path(), MAIN_WITH_DEFAULT_YAML);
    let databases = bundled_dir(installation.path());
    let main_path = databases.join("CLASSIC Main.yaml");
    let game_path = databases.join("CLASSIC Fallout4.yaml");
    let ignore_path = installation
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");
    let malformed_ignore = b"\xffuser-edit\0\r\nCLASSIC_Ignore_Fallout4: [unterminated";
    std::fs::write(&ignore_path, malformed_ignore)
        .expect("malformed Local Ignore should be written");

    let outcome = load_installed_yaml_data_with_env(
        InstalledYamlDataLoadRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        },
        isolated_cache_env(cache_root.path()),
    )
    .expect("malformed Local Ignore should require recovery");
    let InstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired(plan) = outcome else {
        panic!("malformed Local Ignore should return a recovery plan");
    };
    let malformed_sha256 = Sha256::digest(malformed_ignore)
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect::<String>();
    let backup_directory = installation
        .path()
        .join("CLASSIC Backup")
        .join("YAML Data")
        .join("Local Ignore");
    std::fs::create_dir_all(&backup_directory)
        .expect("legacy backup directory should be creatable");
    let legacy_content_path =
        backup_directory.join(format!("CLASSIC Ignore.yaml.{malformed_sha256}.bak"));
    std::fs::write(&legacy_content_path, b"untrusted prior backup")
        .expect("legacy content-addressed path should be writable");

    std::fs::write(
        &main_path,
        main_with_default("ChangedAfterDecision.dll", "Changed autoscan"),
    )
    .expect("selected Main path should be replaceable after planning");
    std::fs::write(&game_path, "changed after recovery decision")
        .expect("selected game path should be replaceable after planning");

    let reset = plan
        .reset_to_default()
        .expect("retained defaults should reset Local Ignore");
    let LocalIgnoreResetOutcome::Reset(result) = reset else {
        panic!("unchanged malformed Local Ignore should reset successfully");
    };

    assert_eq!(result.local_ignore_path(), ignore_path);
    assert_ne!(result.backup_path(), legacy_content_path);
    assert_eq!(
        std::fs::read(&legacy_content_path)
            .expect("untrusted prior backup should remain untouched"),
        b"untrusted prior backup"
    );
    let backup_name = result
        .backup_path()
        .file_name()
        .expect("owned backup should have a filename")
        .to_string_lossy();
    assert!(backup_name.starts_with(&format!("CLASSIC Ignore.yaml.{malformed_sha256}.")));
    assert!(backup_name.ends_with(".bak"));
    assert_eq!(
        std::fs::read(result.backup_path()).expect("verified backup should remain readable"),
        malformed_ignore
    );
    assert_eq!(
        result.backup_identity(),
        result.malformed_local_ignore_identity()
    );
    assert_eq!(result.backup_identity().sha256_hex(), malformed_sha256);
    assert_eq!(
        std::fs::read(&ignore_path).expect("reset Local Ignore should remain readable"),
        DEFAULT_IGNORE_YAML.as_bytes()
    );
    assert_eq!(
        result.replacement_identity().sha256_hex(),
        Sha256::digest(DEFAULT_IGNORE_YAML.as_bytes())
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    );
    assert_eq!(
        result.snapshot().local_ignore_state(),
        LocalIgnoreYamlDataState::ResetToDefault
    );
    assert_eq!(
        result.snapshot().yaml_data().ignore_list,
        ["SelectedMainDefault.dll"]
    );
    assert_eq!(
        result.snapshot().yaml_data().autoscan_text,
        "Bundled autoscan"
    );
    assert_eq!(result.snapshot().yaml_data().game_root_name, "Fallout 4");
    assert!(result.snapshot().diagnostics().iter().any(|diagnostic| {
        diagnostic.kind() == InstalledYamlDataDiagnosticKind::LocalIgnoreReset
            && diagnostic.path() == Some(ignore_path.as_path())
    }));
    assert!(
        !PathBuf::from(format!("{}.prev", ignore_path.display())).exists(),
        "Local Ignore reset must not publish update-channel rollback state"
    );

    std::fs::write(&main_path, MAIN_WITH_DEFAULT_YAML)
        .expect("bundled Main should be restored for durable reload");
    std::fs::write(&game_path, GAME_YAML)
        .expect("bundled game should be restored for durable reload");
    let reloaded = load_installed_yaml_data_with_env(
        InstalledYamlDataLoadRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        },
        isolated_cache_env(cache_root.path()),
    )
    .expect("durably reset Local Ignore should load normally");
    let InstalledYamlDataLoadOutcome::Ready(reloaded) = reloaded else {
        panic!("durably reset Local Ignore should no longer require recovery");
    };
    assert_eq!(
        reloaded.local_ignore_state(),
        LocalIgnoreYamlDataState::Existing
    );
    assert_eq!(
        reloaded.yaml_data().ignore_list,
        ["SelectedMainDefault.dll"]
    );
}

#[cfg(unix)]
#[test]
/// A legacy content-addressed symlink can never become the verified reset backup.
fn local_ignore_reset_owns_a_unique_backup_instead_of_following_a_legacy_symlink() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install_with_main(installation.path(), MAIN_WITH_DEFAULT_YAML);
    let ignore_path = installation
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");
    let malformed_ignore = b"CLASSIC_Ignore_Fallout4: [unterminated";
    std::fs::write(&ignore_path, malformed_ignore)
        .expect("malformed Local Ignore should be written");
    let outcome = load_installed_yaml_data_with_env(
        InstalledYamlDataLoadRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        },
        isolated_cache_env(cache_root.path()),
    )
    .expect("malformed Local Ignore should require recovery");
    let InstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired(plan) = outcome else {
        panic!("malformed Local Ignore should return a recovery plan");
    };
    let malformed_sha256 = Sha256::digest(malformed_ignore)
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect::<String>();
    let backup_directory = installation
        .path()
        .join("CLASSIC Backup")
        .join("YAML Data")
        .join("Local Ignore");
    std::fs::create_dir_all(&backup_directory).expect("backup directory should be creatable");
    let legacy_symlink =
        backup_directory.join(format!("CLASSIC Ignore.yaml.{malformed_sha256}.bak"));
    std::os::unix::fs::symlink(&ignore_path, &legacy_symlink)
        .expect("legacy backup symlink should be creatable");

    let reset = plan
        .reset_to_default()
        .expect("untrusted legacy symlink should not block an owned backup");
    let LocalIgnoreResetOutcome::Reset(result) = reset else {
        panic!("unchanged Local Ignore should reset successfully");
    };

    assert_ne!(result.backup_path(), legacy_symlink);
    assert_eq!(
        std::fs::read(result.backup_path()).expect("owned backup should remain readable"),
        malformed_ignore
    );
    assert_eq!(
        std::fs::read(&legacy_symlink).expect("legacy symlink should still follow canonical state"),
        DEFAULT_IGNORE_YAML.as_bytes()
    );
}

#[test]
/// Changed or removed malformed bytes conflict before backup or replacement publication.
fn stale_local_ignore_reset_plan_returns_typed_conflict_without_overwriting_current_state() {
    for (defaults_case, main_yaml) in [
        ("valid", MAIN_WITH_DEFAULT_YAML),
        ("unavailable", MAIN_YAML),
    ] {
        for (mutation_case, replacement, remove_parent) in [
            ("changed", Some(b"newer user edit".as_slice()), false),
            ("removed", None, false),
            ("parent-removed", None, true),
        ] {
            let installation = tempdir().expect("installation root should be created");
            let cache_root = tempdir().expect("cache root should be created");
            write_bundled_install_with_main(installation.path(), main_yaml);
            let ignore_path = installation
                .path()
                .join("CLASSIC Data")
                .join("CLASSIC Ignore.yaml");
            let malformed_ignore = b"CLASSIC_Ignore_Fallout4: [unterminated";
            std::fs::write(&ignore_path, malformed_ignore)
                .expect("malformed Local Ignore should be written");
            let outcome = load_installed_yaml_data_with_env(
                InstalledYamlDataLoadRequest {
                    installation_root: installation.path().to_path_buf(),
                    game: GameId::Fallout4,
                    selected_game_version: "Original".to_string(),
                },
                isolated_cache_env(cache_root.path()),
            )
            .expect("malformed Local Ignore should require recovery");
            let InstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired(plan) = outcome else {
                panic!("malformed Local Ignore should return a recovery plan");
            };

            if remove_parent {
                std::fs::remove_dir_all(
                    ignore_path
                        .parent()
                        .expect("Local Ignore should have a containing directory"),
                )
                .expect("Local Ignore containing directory should be removable");
            } else if let Some(bytes) = replacement {
                std::fs::write(&ignore_path, bytes).expect("newer Local Ignore should be written");
            } else {
                std::fs::remove_file(&ignore_path).expect("Local Ignore should be removable");
            }

            let reset = plan.reset_to_default().unwrap_or_else(|error| {
                panic!(
                    "{defaults_case} defaults with {mutation_case} file should be typed conflict, got {error}"
                )
            });
            let LocalIgnoreResetOutcome::Conflict(conflict) = reset else {
                panic!(
                    "{defaults_case} defaults with {mutation_case} file should not reset stale Local Ignore bytes"
                );
            };

            assert_eq!(
                conflict.expected_identity().sha256_hex(),
                Sha256::digest(malformed_ignore)
                    .iter()
                    .map(|byte| format!("{byte:02x}"))
                    .collect::<String>(),
                "{defaults_case} defaults with {mutation_case} file"
            );
            assert_eq!(
                conflict.actual_identity().is_some(),
                replacement.is_some(),
                "{defaults_case} defaults with {mutation_case} file"
            );
            assert!(
                conflict.backup_path().is_none(),
                "{defaults_case} defaults with {mutation_case} file"
            );
            assert_eq!(
                std::fs::read(&ignore_path).ok().as_deref(),
                replacement,
                "{defaults_case} defaults with {mutation_case} file"
            );
            assert!(
                !installation.path().join("CLASSIC Backup").exists(),
                "{defaults_case} defaults with {mutation_case} file must conflict before backup publication"
            );
        }
    }
}

#[test]
/// Every durable publication boundary fails before a partial replacement can become visible.
fn local_ignore_reset_is_failure_atomic_at_every_backup_and_replacement_boundary() {
    let stages = [
        LocalIgnoreResetPublicationStage::Create,
        LocalIgnoreResetPublicationStage::Write,
        LocalIgnoreResetPublicationStage::Flush,
        LocalIgnoreResetPublicationStage::Sync,
        LocalIgnoreResetPublicationStage::Publish,
    ];

    for kind in [
        LocalIgnoreResetPublicationKind::Backup,
        LocalIgnoreResetPublicationKind::Replacement,
    ] {
        for stage in stages {
            let installation = tempdir().expect("installation root should be created");
            let cache_root = tempdir().expect("cache root should be created");
            write_bundled_install_with_main(installation.path(), MAIN_WITH_DEFAULT_YAML);
            let ignore_path = installation
                .path()
                .join("CLASSIC Data")
                .join("CLASSIC Ignore.yaml");
            let malformed_ignore = b"CLASSIC_Ignore_Fallout4: [unterminated";
            std::fs::write(&ignore_path, malformed_ignore)
                .expect("malformed Local Ignore should be written");
            let outcome = load_installed_yaml_data_with_env(
                InstalledYamlDataLoadRequest {
                    installation_root: installation.path().to_path_buf(),
                    game: GameId::Fallout4,
                    selected_game_version: "Original".to_string(),
                },
                isolated_cache_env(cache_root.path()),
            )
            .expect("malformed Local Ignore should require recovery");
            let InstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired(plan) = outcome else {
                panic!("malformed Local Ignore should return a recovery plan");
            };
            let publisher = SystemLocalIgnoreResetPublisher::failing_at(kind, stage);

            let error = plan
                .reset_to_default_with_publisher(&publisher)
                .expect_err("injected publication failure should abort reset");

            match (kind, error) {
                (
                    LocalIgnoreResetPublicationKind::Backup,
                    LocalIgnoreResetError::BackupPublication { stage: actual, .. },
                ) => assert_eq!(actual, stage),
                (
                    LocalIgnoreResetPublicationKind::Replacement,
                    LocalIgnoreResetError::ReplacementPublication { stage: actual, .. },
                ) => assert_eq!(actual, stage),
                (_, other) => panic!("unexpected {kind:?} {stage:?} failure: {other}"),
            }
            assert_eq!(
                std::fs::read(&ignore_path).expect("original Local Ignore should remain readable"),
                malformed_ignore,
                "{kind:?} {stage:?}"
            );
            let backup_directory = installation
                .path()
                .join("CLASSIC Backup")
                .join("YAML Data")
                .join("Local Ignore");
            let backup_files = std::fs::read_dir(&backup_directory)
                .map(|entries| {
                    entries
                        .map(|entry| entry.expect("backup entry should be readable").path())
                        .collect::<Vec<_>>()
                })
                .unwrap_or_default();
            assert!(
                backup_files.iter().all(|path| {
                    !path.file_name().is_some_and(|name| {
                        name.to_string_lossy()
                            .starts_with(".classic-local-ignore-reset-")
                    })
                }),
                "{kind:?} {stage:?} must clean staging artifacts"
            );
            let canonical_staging_files = std::fs::read_dir(
                ignore_path
                    .parent()
                    .expect("canonical Local Ignore should have a parent"),
            )
            .expect("canonical directory should remain readable")
            .filter_map(Result::ok)
            .filter(|entry| {
                entry
                    .file_name()
                    .to_string_lossy()
                    .starts_with(".classic-local-ignore-reset-")
            })
            .count();
            assert_eq!(
                canonical_staging_files, 0,
                "{kind:?} {stage:?} must clean canonical staging artifacts"
            );
            if kind == LocalIgnoreResetPublicationKind::Backup {
                assert!(backup_files.is_empty(), "{kind:?} {stage:?}");
            } else {
                assert_eq!(backup_files.len(), 1, "{kind:?} {stage:?}");
                assert_eq!(
                    std::fs::read(&backup_files[0])
                        .expect("replacement failure should retain verified backup"),
                    malformed_ignore,
                    "{kind:?} {stage:?}"
                );
            }
        }
    }
}

/// Publisher that corrupts a completed backup before the reset can verify it.
struct CorruptingBackupPublisher;

impl LocalIgnoreResetPublisher for CorruptingBackupPublisher {
    fn publish_backup(&self, path: &Path, bytes: &[u8]) -> Result<(), LocalIgnoreResetError> {
        SystemLocalIgnoreResetPublisher::system().publish_backup(path, bytes)?;
        std::fs::write(path, b"corrupted after publication").map_err(|source| {
            LocalIgnoreResetError::BackupVerification {
                path: path.to_path_buf(),
                reason: source.to_string(),
            }
        })
    }

    fn replace_if_unchanged(
        &self,
        path: &Path,
        expected: &[u8],
        replacement: &[u8],
    ) -> Result<super::ConditionalReplacement, LocalIgnoreResetError> {
        SystemLocalIgnoreResetPublisher::system().replace_if_unchanged(path, expected, replacement)
    }
}

#[test]
/// Backup reread verification blocks replacement when durable bytes do not match the original.
fn local_ignore_reset_verifies_backup_bytes_before_replacement() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install_with_main(installation.path(), MAIN_WITH_DEFAULT_YAML);
    let ignore_path = installation
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");
    let malformed_ignore = b"CLASSIC_Ignore_Fallout4: [unterminated";
    std::fs::write(&ignore_path, malformed_ignore)
        .expect("malformed Local Ignore should be written");
    let outcome = load_installed_yaml_data_with_env(
        InstalledYamlDataLoadRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        },
        isolated_cache_env(cache_root.path()),
    )
    .expect("malformed Local Ignore should require recovery");
    let InstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired(plan) = outcome else {
        panic!("malformed Local Ignore should return a recovery plan");
    };

    let error = plan
        .reset_to_default_with_publisher(&CorruptingBackupPublisher)
        .expect_err("corrupted backup must abort reset");

    assert!(matches!(
        error,
        LocalIgnoreResetError::BackupVerification { .. }
    ));
    assert_eq!(
        std::fs::read(&ignore_path).expect("original Local Ignore should remain readable"),
        malformed_ignore
    );
}

#[test]
/// Unavailable retained defaults reject reset before backup while Proceed Without Ignore remains valid.
fn local_ignore_reset_reports_unavailable_defaults_without_mutation() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install_with_main(installation.path(), MAIN_YAML);
    let ignore_path = installation
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");
    let malformed_ignore = b"CLASSIC_Ignore_Fallout4: [unterminated";
    std::fs::write(&ignore_path, malformed_ignore)
        .expect("malformed Local Ignore should be written");
    let outcome = load_installed_yaml_data_with_env(
        InstalledYamlDataLoadRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        },
        isolated_cache_env(cache_root.path()),
    )
    .expect("malformed Local Ignore should require recovery");
    let InstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired(plan) = outcome else {
        panic!("malformed Local Ignore should return a recovery plan");
    };

    let error = plan
        .reset_to_default()
        .expect_err("unavailable retained defaults should reject reset");

    assert!(matches!(
        error,
        LocalIgnoreResetError::DefaultsUnavailable { .. }
    ));
    assert_eq!(
        std::fs::read(&ignore_path).expect("original Local Ignore should remain readable"),
        malformed_ignore
    );
    assert!(!installation.path().join("CLASSIC Backup").exists());
}

/// Publisher that replaces the canonical file after backup but before the adjacent recheck.
struct RacingReplacementPublisher {
    path: PathBuf,
    newer_bytes: Vec<u8>,
}

impl LocalIgnoreResetPublisher for RacingReplacementPublisher {
    fn publish_backup(&self, path: &Path, bytes: &[u8]) -> Result<(), LocalIgnoreResetError> {
        SystemLocalIgnoreResetPublisher::system().publish_backup(path, bytes)
    }

    fn replace_if_unchanged(
        &self,
        path: &Path,
        expected: &[u8],
        replacement: &[u8],
    ) -> Result<super::ConditionalReplacement, LocalIgnoreResetError> {
        std::fs::write(&self.path, &self.newer_bytes).map_err(|source| {
            LocalIgnoreResetError::Read {
                path: self.path.clone(),
                source,
            }
        })?;
        SystemLocalIgnoreResetPublisher::system().replace_if_unchanged(path, expected, replacement)
    }
}

#[test]
/// A change during durable backup is preserved and reported with the verified backup location.
fn local_ignore_reset_rechecks_conflict_immediately_before_atomic_replacement() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install_with_main(installation.path(), MAIN_WITH_DEFAULT_YAML);
    let ignore_path = installation
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");
    let malformed_ignore = b"CLASSIC_Ignore_Fallout4: [unterminated";
    let newer_bytes = b"newer edit made while backup was publishing".to_vec();
    std::fs::write(&ignore_path, malformed_ignore)
        .expect("malformed Local Ignore should be written");
    let outcome = load_installed_yaml_data_with_env(
        InstalledYamlDataLoadRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        },
        isolated_cache_env(cache_root.path()),
    )
    .expect("malformed Local Ignore should require recovery");
    let InstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired(plan) = outcome else {
        panic!("malformed Local Ignore should return a recovery plan");
    };
    let publisher = RacingReplacementPublisher {
        path: ignore_path.clone(),
        newer_bytes: newer_bytes.clone(),
    };

    let reset = plan
        .reset_to_default_with_publisher(&publisher)
        .expect("late file change should be a typed conflict");
    let LocalIgnoreResetOutcome::Conflict(conflict) = reset else {
        panic!("late file change must not be overwritten");
    };

    assert_eq!(
        conflict
            .actual_identity()
            .expect("changed file should expose its identity")
            .sha256_hex(),
        Sha256::digest(&newer_bytes)
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    );
    let backup_path = conflict
        .backup_path()
        .expect("late conflict should expose the already verified backup");
    assert_eq!(
        std::fs::read(backup_path).expect("verified backup should remain readable"),
        malformed_ignore
    );
    assert_eq!(
        std::fs::read(&ignore_path).expect("newer Local Ignore should remain authoritative"),
        newer_bytes
    );
}

/// Publisher that exposes a barrier after critical-section entry and before replacement.
struct BlockingReplacementPublisher {
    entered: Arc<Barrier>,
    release: Arc<Barrier>,
}

impl LocalIgnoreResetPublisher for BlockingReplacementPublisher {
    fn publish_backup(&self, path: &Path, bytes: &[u8]) -> Result<(), LocalIgnoreResetError> {
        SystemLocalIgnoreResetPublisher::system().publish_backup(path, bytes)
    }

    fn replace_if_unchanged(
        &self,
        path: &Path,
        expected: &[u8],
        replacement: &[u8],
    ) -> Result<super::ConditionalReplacement, LocalIgnoreResetError> {
        self.entered.wait();
        self.release.wait();
        SystemLocalIgnoreResetPublisher::system().replace_if_unchanged(path, expected, replacement)
    }
}

#[test]
/// Once entered, reset reaches a complete durable result without observing cancellation state.
fn local_ignore_reset_critical_section_is_explicitly_non_interruptible() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install_with_main(installation.path(), MAIN_WITH_DEFAULT_YAML);
    let ignore_path = installation
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");
    std::fs::write(&ignore_path, b"CLASSIC_Ignore_Fallout4: [unterminated")
        .expect("malformed Local Ignore should be written");
    let outcome = load_installed_yaml_data_with_env(
        InstalledYamlDataLoadRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        },
        isolated_cache_env(cache_root.path()),
    )
    .expect("malformed Local Ignore should require recovery");
    let InstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired(plan) = outcome else {
        panic!("malformed Local Ignore should return a recovery plan");
    };
    let entered = Arc::new(Barrier::new(2));
    let release = Arc::new(Barrier::new(2));
    let cancellation = Arc::new(AtomicBool::new(false));
    let publisher = BlockingReplacementPublisher {
        entered: Arc::clone(&entered),
        release: Arc::clone(&release),
    };

    let resetter = std::thread::spawn(move || plan.reset_to_default_with_publisher(&publisher));
    entered.wait();
    cancellation.store(true, Ordering::Release);
    release.wait();
    let reset = resetter
        .join()
        .expect("reset worker should not panic")
        .expect("critical section should finish successfully");

    assert!(cancellation.load(Ordering::Acquire));
    assert!(matches!(reset, LocalIgnoreResetOutcome::Reset(_)));
    assert_eq!(
        std::fs::read(&ignore_path).expect("reset Local Ignore should remain readable"),
        DEFAULT_IGNORE_YAML.as_bytes()
    );
}

#[test]
/// Invalid selected-Main defaults do not block the non-mutating proceed recovery decision.
fn malformed_local_ignore_can_proceed_when_selected_main_defaults_are_unavailable() {
    let installation = tempdir().expect("installation root should be created");
    let cache_root = tempdir().expect("cache root should be created");
    write_bundled_install_with_main(installation.path(), MAIN_YAML);
    let databases = bundled_dir(installation.path());
    let main_path = databases.join("CLASSIC Main.yaml");
    let game_path = databases.join("CLASSIC Fallout4.yaml");
    let ignore_path = installation
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");
    let malformed_ignore = b"CLASSIC_Ignore_Fallout4: [unterminated";
    std::fs::write(&ignore_path, malformed_ignore)
        .expect("malformed Local Ignore should be written");
    let original_files = [
        std::fs::read(&main_path).expect("Main should remain readable"),
        std::fs::read(&game_path).expect("game should remain readable"),
        std::fs::read(&ignore_path).expect("Local Ignore should remain readable"),
    ];

    let outcome = load_installed_yaml_data_with_env(
        InstalledYamlDataLoadRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        },
        isolated_cache_env(cache_root.path()),
    )
    .expect("malformed Local Ignore should remain recoverable without usable defaults");
    let InstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired(plan) = outcome else {
        panic!("malformed Local Ignore should return a recovery plan");
    };
    assert!(plan.default_local_ignore_identity().is_none());

    let snapshot = plan.proceed_without_ignore();

    assert!(snapshot.yaml_data().ignore_list.is_empty());
    assert_eq!(
        [
            std::fs::read(&main_path).expect("Main should remain readable after proceed"),
            std::fs::read(&game_path).expect("game should remain readable after proceed"),
            std::fs::read(&ignore_path).expect("Local Ignore should remain readable after proceed"),
        ],
        original_files
    );
}

#[test]
/// Every malformed Local Ignore shape requires recovery again after operation-scoped proceed.
fn malformed_local_ignore_recovery_is_operation_scoped_and_never_mutates_files() {
    let cases = [
        (
            "invalid-utf8",
            vec![0xff],
            InstalledYamlDataDiagnosticKind::InvalidUtf8,
        ),
        (
            "malformed-yaml",
            b"CLASSIC_Ignore_Fallout4: [unterminated".to_vec(),
            InstalledYamlDataDiagnosticKind::Parse,
        ),
        (
            "invalid-role-data",
            b"CLASSIC_Ignore_Fallout4: not-a-sequence\n".to_vec(),
            InstalledYamlDataDiagnosticKind::InvalidRoleData,
        ),
    ];

    for (case, malformed_ignore, expected_kind) in cases {
        let installation = tempdir().expect("installation root should be created");
        let cache_root = tempdir().expect("cache root should be created");
        write_bundled_install_with_main(installation.path(), MAIN_WITH_DEFAULT_YAML);
        let databases = bundled_dir(installation.path());
        let main_path = databases.join("CLASSIC Main.yaml");
        let game_path = databases.join("CLASSIC Fallout4.yaml");
        let ignore_path = installation
            .path()
            .join("CLASSIC Data")
            .join("CLASSIC Ignore.yaml");
        std::fs::write(&ignore_path, &malformed_ignore)
            .expect("malformed Local Ignore should be written");
        let original_files = [
            std::fs::read(&main_path).expect("Main should remain readable"),
            std::fs::read(&game_path).expect("game should remain readable"),
            std::fs::read(&ignore_path).expect("Local Ignore should remain readable"),
        ];
        let request = InstalledYamlDataLoadRequest {
            installation_root: installation.path().to_path_buf(),
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        };

        let first = load_installed_yaml_data_with_env(
            request.clone(),
            isolated_cache_env(cache_root.path()),
        )
        .unwrap_or_else(|error| panic!("{case} should require recovery, got {error}"));
        let InstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired(plan) = first else {
            panic!("{case} should return Local Ignore recovery required");
        };
        assert_eq!(
            plan.malformed_local_ignore_identity().byte_len(),
            malformed_ignore.len() as u64,
            "{case}"
        );
        assert!(
            plan.diagnostics()
                .iter()
                .any(|diagnostic| diagnostic.kind() == expected_kind),
            "{case}"
        );

        let snapshot = plan.proceed_without_ignore();
        assert!(snapshot.yaml_data().ignore_list.is_empty(), "{case}");
        assert_eq!(
            [
                std::fs::read(&main_path).expect("Main should remain readable after proceed"),
                std::fs::read(&game_path).expect("game should remain readable after proceed"),
                std::fs::read(&ignore_path)
                    .expect("Local Ignore should remain readable after proceed"),
            ],
            original_files,
            "{case}"
        );

        let second =
            load_installed_yaml_data_with_env(request, isolated_cache_env(cache_root.path()))
                .unwrap_or_else(|error| {
                    panic!("{case} should require recovery again, got {error}")
                });
        let InstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired(second_plan) = second else {
            panic!("{case} should require a new recovery decision on the next operation");
        };
        assert_eq!(
            second_plan.malformed_local_ignore_identity(),
            snapshot.local_ignore_identity(),
            "{case}"
        );
        assert_eq!(
            std::fs::read(&ignore_path)
                .expect("malformed Local Ignore should remain readable after reload"),
            malformed_ignore,
            "{case}"
        );
    }
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
