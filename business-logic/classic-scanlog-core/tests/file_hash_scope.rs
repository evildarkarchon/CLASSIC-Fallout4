//! Probes that a Crash Log Scan Run's FCX Game Setup Intake step hashes only
//! through the caller-selected `FileHashScope`.
//!
//! `contract::execute_in_scopes` carries an opaque hash scope chosen by the
//! caller (the Python `classic_scanlog` facade selects its own), while the
//! unscoped `contract::execute` keeps hashing through the process default
//! scope that Rust, CXX, and Node callers have always used. The default scope
//! is process-global, so these probes live in their own test binary and run
//! serially.

use std::path::{Path, PathBuf};

use classic_file_io_core::FileHashScope;
use classic_scanlog_core::CrashLogScanFacts;
use classic_scanlog_core::scan_run::contract;
use classic_scanlog_core::scan_run::{CrashLogScanSetupContext, TargetedCrashLogScanSource};
use classic_shared_core::{GameId, get_runtime};
use classic_version_registry_core::VersionRegistryScope;
use tempfile::{TempDir, tempdir};

const EMPTY_GOLDEN_INPUT: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../tests/fixtures/autoscan_report_goldens/cases/empty/input"
);

/// Copies one fixture directory tree into a scratch installation root.
fn copy_directory(source: &Path, destination: &Path) {
    std::fs::create_dir_all(destination).expect("fixture destination should be created");
    for entry in std::fs::read_dir(source).expect("fixture directory should be readable") {
        let entry = entry.expect("fixture directory entry should be readable");
        let source_path = entry.path();
        let destination_path = destination.join(entry.file_name());
        if source_path.is_dir() {
            copy_directory(&source_path, &destination_path);
        } else {
            std::fs::copy(&source_path, &destination_path).expect("fixture file should be copied");
        }
    }
}

/// One scratch FCX installation: a Crash Log plus a game root whose executable
/// the setup step hashes.
struct FcxInstallation {
    root: TempDir,
    crash_log: PathBuf,
    game_root: PathBuf,
    docs_root: PathBuf,
    executable: PathBuf,
}

impl FcxInstallation {
    fn new() -> Self {
        let root = tempdir().expect("installation root");
        copy_directory(Path::new(EMPTY_GOLDEN_INPUT), root.path());
        let game_root = root.path().join("Fallout4");
        let docs_root = root.path().join("Documents");
        std::fs::create_dir_all(&game_root).expect("game root");
        std::fs::create_dir_all(&docs_root).expect("documents root");
        let executable = game_root.join("Fallout4.exe");
        std::fs::write(&executable, b"not a real pe").expect("game executable");
        Self {
            crash_log: root.path().join("crash-empty.log"),
            root,
            game_root,
            docs_root,
            executable,
        }
    }

    /// Builds a Targeted FCX request for this installation's Crash Log.
    fn request(&self) -> contract::Request {
        let configuration = contract::Configuration {
            installation_root: self.root.path().to_path_buf(),
            game: GameId::Fallout4,
            game_version: "Original".to_string(),
            options: contract::Options::new(false, false),
            scan_facts: CrashLogScanFacts::default(),
            max_concurrent: Some(1),
        };
        contract::Request::targeted_with_fcx(
            configuration,
            TargetedCrashLogScanSource {
                inputs: vec![self.crash_log.clone()],
            },
            CrashLogScanSetupContext {
                game_root: Some(self.game_root.clone()),
                docs_root: Some(self.docs_root.clone()),
                game_exe_path: Some(self.executable.clone()),
                xse_log_path: None,
            },
        )
    }
}

/// `(hits, misses, entries)` for one hash scope.
fn counters(scope: &FileHashScope) -> (u64, u64, usize) {
    let stats = scope.cache_stats();
    (stats.hits, stats.misses, scope.cache_size())
}

/// Runs `body` with the per-user cache roots redirected, so the scan's report
/// and YAML caches never touch the developer's real profile.
fn with_isolated_cache<R>(body: impl FnOnce() -> R) -> R {
    let cache_root = tempdir().expect("isolated cache root");
    temp_env::with_vars(
        [
            ("LOCALAPPDATA", Some(cache_root.path())),
            ("XDG_CACHE_HOME", Some(cache_root.path())),
        ],
        body,
    )
}

#[test]
#[serial_test::serial]
fn scoped_fcx_setup_hashes_only_in_the_supplied_scope() {
    let installation = FcxInstallation::new();
    let facade_scope = FileHashScope::new_isolated();
    let default_before = counters(&FileHashScope::default_scope());

    let result = with_isolated_cache(|| {
        get_runtime().block_on(contract::execute_in_scopes(
            installation.request(),
            VersionRegistryScope::default_scope(),
            facade_scope.clone(),
            &contract::Cancellation::new(),
            None,
        ))
    })
    .expect("scoped FCX scan should execute");

    assert!(result.setup.is_some(), "FCX setup should have run");
    let (hits, misses, entries) = counters(&facade_scope);
    assert!(
        misses >= 1,
        "the setup step should hash into the supplied scope"
    );
    assert_eq!(hits, 0, "a fresh scope has nothing to hit");
    assert!(
        entries >= 1,
        "the executable hash should be cached in the scope"
    );
    assert_eq!(
        counters(&FileHashScope::default_scope()),
        default_before,
        "a scoped run must not read, fill, or count the default scope"
    );

    // A second scoped run re-hashes the same executable from the scope's cache.
    with_isolated_cache(|| {
        get_runtime().block_on(contract::execute_in_scopes(
            installation.request(),
            VersionRegistryScope::default_scope(),
            facade_scope.clone(),
            &contract::Cancellation::new(),
            None,
        ))
    })
    .expect("repeat scoped FCX scan should execute");
    assert!(
        counters(&facade_scope).0 >= 1,
        "repeat run should hit the scope"
    );
    assert_eq!(counters(&FileHashScope::default_scope()), default_before);
}

#[test]
#[serial_test::serial]
fn unscoped_fcx_setup_keeps_hashing_through_the_default_scope() {
    let installation = FcxInstallation::new();
    let bystander = FileHashScope::new_isolated();
    let default_scope = FileHashScope::default_scope();
    default_scope.clear_cache();
    default_scope.reset_cache_stats();

    let result = with_isolated_cache(|| {
        get_runtime().block_on(contract::execute(
            installation.request(),
            &contract::Cancellation::new(),
            None,
        ))
    })
    .expect("unscoped FCX scan should execute");

    assert!(result.setup.is_some(), "FCX setup should have run");
    let (_, misses, entries) = counters(&default_scope);
    assert!(misses >= 1, "unscoped runs hash through the default scope");
    assert!(entries >= 1);
    assert_eq!(counters(&bystander), (0, 0, 0));
}
