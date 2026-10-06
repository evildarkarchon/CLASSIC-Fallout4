//! Probes that a Standard Crash Log Scan Run reads its Game Local document
//! only through the caller-selected path/mtime YAML-file cache scope.
//!
//! Standard discovery reads `CLASSIC <game> Local.yaml` to find the XSE
//! Folder. `contract::execute_in_scopes` carries an opaque YAML-file cache
//! scope chosen by the caller (the Python `classic_scanlog` facade selects its
//! own), while the unscoped `contract::execute` keeps reading through the
//! process default scope that Rust, CXX, and Node callers have always used.
//! The default scope is process-global, so these probes live in their own test
//! binary and run serially.

use std::path::{Path, PathBuf};

use classic_file_io_core::FileHashScope;
use classic_scanlog_core::scan_run::contract;
use classic_scanlog_core::{
    CrashLogScanFacts, StandardCrashLogScanSource, StandardUnsolvedLogsIntent,
};
use classic_shared_core::yaml::YamlFileCacheScope;
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

/// One scratch Standard installation whose Game Local document names an
/// explicit XSE Folder holding one Crash Log.
struct StandardInstallation {
    root: TempDir,
    base: PathBuf,
    xse_log_name: &'static str,
}

impl StandardInstallation {
    fn new() -> Self {
        let root = tempdir().expect("installation root");
        copy_directory(Path::new(EMPTY_GOLDEN_INPUT), root.path());
        let base = root.path().join("base");
        let xse = root.path().join("xse");
        std::fs::create_dir_all(&base).expect("base directory");
        std::fs::create_dir_all(&xse).expect("XSE Folder");
        let xse_log_name = "crash-xse-probe.log";
        std::fs::copy(root.path().join("crash-empty.log"), xse.join(xse_log_name))
            .expect("XSE Crash Log");
        std::fs::write(
            root.path()
                .join("CLASSIC Data")
                .join("CLASSIC Fallout4 Local.yaml"),
            format!(
                "Game_Info:\n  Docs_Folder_XSE: '{}'\n",
                xse.display().to_string().replace('\'', "''")
            ),
        )
        .expect("Game Local document");
        Self {
            root,
            base,
            xse_log_name,
        }
    }

    /// Builds a Standard request that leaves unsolved logs in place.
    fn request(&self) -> contract::Request {
        contract::Request::standard(
            contract::Configuration {
                installation_root: self.root.path().to_path_buf(),
                game: GameId::Fallout4,
                game_version: "Original".to_string(),
                options: contract::Options::new(false, false),
                scan_facts: CrashLogScanFacts::default(),
                max_concurrent: Some(1),
            },
            StandardCrashLogScanSource {
                base_directory: self.base.clone(),
                custom_scan_directory: None,
                configured_documents_root: None,
            },
            StandardUnsolvedLogsIntent::LeaveInPlace,
        )
    }

    /// Whether discovery accepted the Crash Log copied from the XSE Folder.
    fn accepted_xse_log(&self, result: &contract::RunResult) -> bool {
        result.discovery.as_ref().is_some_and(|discovery| {
            discovery.accepted_logs.iter().any(|log| {
                log.file_name()
                    .is_some_and(|name| name == self.xse_log_name)
            })
        })
    }
}

/// `(hits, misses, entries)` for one YAML-file cache scope.
fn counters(scope: &YamlFileCacheScope) -> (u64, u64, usize) {
    let stats = scope.stats();
    (stats.hits, stats.misses, stats.size)
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
fn scoped_standard_discovery_reads_game_local_only_through_the_supplied_scope() {
    let installation = StandardInstallation::new();
    let facade_scope = YamlFileCacheScope::new_isolated();
    let default_before = counters(&YamlFileCacheScope::default_scope());

    let result = with_isolated_cache(|| {
        get_runtime().block_on(contract::execute_in_scopes(
            installation.request(),
            VersionRegistryScope::default_scope(),
            FileHashScope::default_scope(),
            facade_scope.clone(),
            &contract::Cancellation::new(),
            None,
            contract::ObserverFailurePolicy::ContinueRun,
        ))
    })
    .expect("scoped Standard scan should execute");

    assert!(
        installation.accepted_xse_log(&result),
        "discovery should collect from the Game Local XSE Folder"
    );
    assert_eq!(
        counters(&facade_scope),
        (0, 1, 1),
        "the Game Local read should miss and fill the supplied scope"
    );
    assert_eq!(
        counters(&YamlFileCacheScope::default_scope()),
        default_before,
        "a scoped run must not read, fill, or count the default scope"
    );
}

#[test]
#[serial_test::serial]
fn unscoped_standard_discovery_keeps_reading_through_the_default_scope() {
    let installation = StandardInstallation::new();
    let bystander = YamlFileCacheScope::new_isolated();
    let default_scope = YamlFileCacheScope::default_scope();
    let (_, misses_before, _) = counters(&default_scope);

    let result = with_isolated_cache(|| {
        get_runtime().block_on(contract::execute(
            installation.request(),
            &contract::Cancellation::new(),
            None,
            contract::ObserverFailurePolicy::ContinueRun,
        ))
    })
    .expect("unscoped Standard scan should execute");

    assert!(installation.accepted_xse_log(&result));
    assert!(
        counters(&default_scope).1 > misses_before,
        "unscoped runs read Game Local through the default scope"
    );
    assert_eq!(counters(&bystander), (0, 0, 0));
}
