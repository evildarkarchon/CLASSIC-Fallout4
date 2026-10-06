//! Probes that scanlog's registry-backed analysis reads only a caller-selected
//! Version Registry scope.
//!
//! A scope's snapshot is taken from the process working directory on first
//! use. These probes change the working directory, so they live in their own
//! test binary (process) and run serially.

use std::path::{Path, PathBuf};

use classic_scanlog_core::scan_run::TargetedCrashLogScanSource;
use classic_scanlog_core::scan_run::contract;
use classic_scanlog_core::{CrashLogScanFacts, PluginAnalyzer};
use classic_shared_core::{GameId, get_runtime};
use classic_version_registry_core::{VersionRegistryScope, get_version_registry};
use tempfile::tempdir;

const EMPTY_GOLDEN_INPUT: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../tests/fixtures/autoscan_report_goldens/cases/empty/input"
);

/// The golden case's Buffout 4 v1.37.0 is below the shipped OG floor, so its
/// default-scope report carries this verdict.
const OUTDATED_VERDICT: &str = "YOUR Buffout 4 IS OUTDATED";

/// Restores the original working directory on drop, even if the probe panics.
struct RestoreCwd(PathBuf);

impl RestoreCwd {
    fn capture() -> Self {
        Self(std::env::current_dir().expect("current dir"))
    }
}

impl Drop for RestoreCwd {
    fn drop(&mut self) {
        // Best effort: a failed restore must not mask the probe's own panic.
        let _ = std::env::set_current_dir(&self.0);
    }
}

/// Write a Version Registry root whose `FO4_OG` entry is classified `NG` and
/// accepts Buffout 4 from 1.30.0, unlike the shipped registry.
fn write_custom_root(root: &Path) {
    let yaml = r#"Version_Registry:
  versions:
    - id: FO4_OG
      game: Fallout4
      is_vr: false
      version: "1.10.163.0"
      display_name: Custom Original
      short_name: NG
      docs_name: Fallout4
      crashgen_versions:
        - version: "1.30.0"
          name: "Buffout 4"
"#;
    std::fs::write(root.join("CLASSIC Main.yaml"), yaml).expect("write yaml root");
}

/// Enter a fresh custom registry root and return an isolated scope whose
/// first use happens inside it. The default snapshot is taken first, so these
/// probes can never be the ones that initialize it from a custom root.
fn custom_scope(root: &Path) -> VersionRegistryScope {
    let _ = get_version_registry();
    write_custom_root(root);
    let scope = VersionRegistryScope::new_isolated();
    std::env::set_current_dir(root).expect("enter registry root");
    let _ = scope.registry();
    scope
}

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

/// Run the empty golden case once and return its persisted Autoscan Report.
async fn run_empty_case(version_registry: Option<VersionRegistryScope>) -> String {
    let installation = tempdir().expect("installation root");
    copy_directory(Path::new(EMPTY_GOLDEN_INPUT), installation.path());
    let crash_log = installation.path().join("crash-empty.log");
    let configuration = contract::Configuration {
        installation_root: installation.path().to_path_buf(),
        game: GameId::Fallout4,
        game_version: "Original".to_string(),
        options: contract::Options::new(false, false),
        scan_facts: CrashLogScanFacts::default(),
        max_concurrent: Some(1),
    };
    let request = contract::Request::targeted(
        configuration,
        TargetedCrashLogScanSource {
            inputs: vec![crash_log],
        },
    );
    let cancellation = contract::Cancellation::new();
    let result = match version_registry {
        Some(scope) => {
            contract::execute_in_version_registry_scope(
                request,
                scope,
                &cancellation,
                None,
                contract::ObserverFailurePolicy::ContinueRun,
            )
            .await
        }
        None => {
            contract::execute(
                request,
                &cancellation,
                None,
                contract::ObserverFailurePolicy::ContinueRun,
            )
            .await
        }
    }
    .expect("scan should execute");

    assert_eq!(result.status, contract::RunStatus::Completed);
    let report = result.logs[0]
        .autoscan_report
        .as_ref()
        .expect("persisted report path");
    std::fs::read_to_string(report).expect("read report")
}

#[test]
#[serial_test::serial]
fn plugin_limit_classification_reads_the_analyzer_scope() {
    let _restore = RestoreCwd::capture();
    let root = tempdir().expect("registry root");
    let scope = custom_scope(root.path());
    let analyzer = || {
        PluginAnalyzer::new(
            vec![],
            vec![],
            "Buffout 4".to_string(),
            "1.10.163".to_string(),
            "1.2.72".to_string(),
        )
        .expect("analyzer")
    };
    let segment = vec!["[FF] PluginLimit.esp".to_string()];

    // The shipped registry classifies 1.10.163 as OG, which triggers the limit.
    let unscoped = analyzer()
        .check_plugin_limit(&segment, "1.10.163", "1.36.0")
        .expect("unscoped check");
    // The custom snapshot classifies it as NG, where a pre-1.37 crash
    // generator disables the check instead.
    let scoped = analyzer()
        .with_version_registry_scope(scope)
        .check_plugin_limit(&segment, "1.10.163", "1.36.0")
        .expect("scoped check");

    assert_eq!(unscoped, (true, false));
    assert_eq!(scoped, (false, true));
}

#[test]
#[serial_test::serial]
fn scan_run_analysis_reads_only_the_supplied_scope() {
    let _restore = RestoreCwd::capture();
    let root = tempdir().expect("registry root");
    let scope = custom_scope(root.path());
    let cache_root = tempdir().expect("isolated cache root");

    let (scoped, unscoped) = temp_env::with_vars(
        [
            ("LOCALAPPDATA", Some(cache_root.path())),
            ("XDG_CACHE_HOME", Some(cache_root.path())),
        ],
        || {
            get_runtime().block_on(async {
                (
                    run_empty_case(Some(scope)).await,
                    run_empty_case(None).await,
                )
            })
        },
    );

    assert!(unscoped.contains(OUTDATED_VERDICT), "{unscoped}");
    assert!(!scoped.contains(OUTDATED_VERDICT), "{scoped}");
}
