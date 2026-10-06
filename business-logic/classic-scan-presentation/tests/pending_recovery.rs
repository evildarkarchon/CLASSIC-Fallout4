//! The pending recovery a frontend receives carries the prompt this crate renders.
//!
//! A pending recovery holds a live continuation, which only a real paused run can produce, so
//! these tests execute the public scan-run contract over a malformed Local Ignore rather than
//! assembling one by hand.

use classic_scan_presentation::{
    DisplaySeverity, PendingRecoveryWithPrompt, render_local_ignore_recovery, take_pending_recovery,
};
use classic_scanlog_core::CrashLogScanFacts;
use classic_scanlog_core::scan_run::TargetedCrashLogScanSource;
use classic_scanlog_core::scan_run::contract;
use classic_shared_core::{GameId, get_runtime};
use std::fs;
use std::path::{Path, PathBuf};
use tempfile::{TempDir, tempdir};

const FIXTURE_ROOT: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../tests/fixtures/crash_log_scan_run"
);

/// Selected Main YAML Data with no `default_ignorefile`, so Reset To Default cannot succeed.
const MAIN_WITHOUT_DEFAULT_IGNORE: &str = "schema_version: \"2.0\"\nCLASSIC_Info:\n  version: \"9.1.0\"\n  version_date: \"2026-07-15\"\nCLASSIC_Interface:\n  autoscan_text_Fallout4: \"Autoscan Fallout 4\"\ncatch_log_records:\n  - LAND\nexclude_log_records:\n  - \"(void*)\"\n";

/// One paused run, the control it was started with, and the root keeping its files alive.
struct PausedRun {
    _root: TempDir,
    _cache: TempDir,
    cancellation: contract::Cancellation,
    result: contract::RunResult,
}

/// Executes a targeted run over a malformed Local Ignore until it pauses for recovery.
///
/// `main_yaml` replaces the fixture Main YAML Data when given, which is how a run without
/// retained defaults is produced.
fn paused_run(main_yaml: Option<&str>) -> PausedRun {
    let root = tempdir().expect("scenario root should be created");
    let cache = tempdir().expect("isolated YAML cache root should be created");
    let fixtures = Path::new(FIXTURE_ROOT);
    let databases = root.path().join("CLASSIC Data/databases");
    fs::create_dir_all(&databases).expect("YAML Data directory should be created");
    for name in ["CLASSIC Main.yaml", "CLASSIC Fallout4.yaml"] {
        fs::copy(
            fixtures.join("CLASSIC Data/databases").join(name),
            databases.join(name),
        )
        .expect("installation YAML Data fixture should be copied");
    }
    if let Some(main_yaml) = main_yaml {
        fs::write(databases.join("CLASSIC Main.yaml"), main_yaml)
            .expect("replacement Main YAML Data should be written");
    }
    fs::copy(
        fixtures.join("malformed-local-ignore.yaml"),
        root.path().join("CLASSIC Data/CLASSIC Ignore.yaml"),
    )
    .expect("malformed Local Ignore fixture should be copied");
    let log: PathBuf = root.path().join("crash-pending-recovery.log");
    fs::copy(fixtures.join("valid-crash.log"), &log).expect("Crash Log fixture should be copied");

    let request = contract::Request::targeted(
        contract::Configuration {
            installation_root: root.path().to_path_buf(),
            game: GameId::Fallout4,
            game_version: "Original".to_string(),
            options: contract::Options::new(false, false),
            scan_facts: CrashLogScanFacts::default(),
            max_concurrent: Some(1),
        },
        TargetedCrashLogScanSource { inputs: vec![log] },
    );
    let cancellation = contract::Cancellation::new();
    // The per-user YAML Data update cache is resolved from LOCALAPPDATA; isolating it keeps a
    // developer's real cache from changing which Main YAML Data the run selects.
    let result = temp_env::with_var("LOCALAPPDATA", Some(cache.path()), || {
        get_runtime().block_on(contract::execute(
            request,
            &cancellation,
            None,
            contract::ObserverFailurePolicy::ContinueRun,
        ))
    })
    .expect("a malformed Local Ignore should pause as expected result data");
    assert_eq!(
        result.status,
        contract::RunStatus::LocalIgnoreRecoveryRequired
    );
    PausedRun {
        _root: root,
        _cache: cache,
        cancellation,
        result,
    }
}

/// Takes the pending recovery a paused run offers.
fn take(paused: &mut PausedRun) -> PendingRecoveryWithPrompt {
    take_pending_recovery(&mut paused.result).expect("a paused run should offer a pending recovery")
}

#[test]
fn the_pending_recovery_prompt_is_the_rendered_recovery_prompt() {
    let mut paused = paused_run(None);
    let expected = render_local_ignore_recovery(paused.result.installed_yaml_data.as_ref());

    let pending = take(&mut paused);

    assert_eq!(pending.prompt(), &expected);
    assert!(
        pending
            .prompt()
            .decisions
            .iter()
            .all(|decision| decision.available),
        "a run with retained defaults offers both decisions"
    );
    assert!(!pending.cancellation_requested());
}

#[test]
fn the_pending_recovery_prompt_withholds_reset_when_classic_cannot_safely_reset() {
    let mut paused = paused_run(Some(MAIN_WITHOUT_DEFAULT_IGNORE));
    let expected = render_local_ignore_recovery(paused.result.installed_yaml_data.as_ref());

    let pending = take(&mut paused);

    assert_eq!(pending.prompt(), &expected);
    let reset = pending
        .prompt()
        .decisions
        .iter()
        .find(|description| {
            description.decision == contract::LocalIgnoreRecoveryDecision::ResetToDefault
        })
        .expect("Reset To Default is always described");
    assert!(!reset.available);
    assert!(
        pending
            .prompt()
            .lines
            .iter()
            .any(|line| line.severity == DisplaySeverity::Notice),
        "an unavailable reset is explained"
    );
}

#[test]
fn the_pending_recovery_reports_cancellation_requested_on_the_runs_own_control() {
    let mut paused = paused_run(None);
    let pending = take(&mut paused);

    paused.cancellation.cancel();

    assert!(pending.cancellation_requested());
    let settled = get_runtime()
        .block_on(pending.settle(None, None, contract::ObserverFailurePolicy::ContinueRun))
        .expect("settling a cancelled run should remain expected result data");
    assert_eq!(settled.status, contract::RunStatus::Cancelled);
}

#[test]
fn a_paused_run_offers_its_pending_recovery_only_once() {
    let mut paused = paused_run(None);
    let _pending = take(&mut paused);

    assert!(take_pending_recovery(&mut paused.result).is_none());
}
