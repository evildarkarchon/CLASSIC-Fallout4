//! Byte-exact Autoscan Report characterization at the complete Crash Log Scan Run seam.

use classic_scanlog_core::CrashLogScanFacts;
use classic_scanlog_core::scan_run::contract;
use classic_scanlog_core::scan_run::{CrashLogScanSetupContext, TargetedCrashLogScanSource};
use classic_shared_core::{GameId, get_runtime};
use serde::Deserialize;
use sqlx::sqlite::SqlitePoolOptions;
use std::path::{Path, PathBuf};
use tempfile::tempdir;

const FIXTURE_ROOT: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../tests/fixtures/autoscan_report_goldens"
);
const MANIFEST_JSON: &str = include_str!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../tests/fixtures/autoscan_report_goldens/manifest.json"
));

#[derive(Debug, Deserialize)]
struct Manifest {
    cases: Vec<GoldenCase>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct GoldenCase {
    name: String,
    fixture_directory: String,
    crash_log: String,
    expected_report: String,
    game_version: String,
    show_formid_values: bool,
    fcx_mode: bool,
    #[serde(default)]
    formid_database_entries: Vec<FormIdDatabaseEntry>,
    expected: ExpectedOutcome,
}

#[derive(Debug, Deserialize)]
struct FormIdDatabaseEntry {
    formid: String,
    plugin: String,
    entry: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ExpectedOutcome {
    formid_count: usize,
    plugin_count: usize,
    suspect_count: usize,
}

/// Loads the immutable scenario inventory that owns all public outcome expectations.
fn manifest() -> Manifest {
    serde_json::from_str(MANIFEST_JSON).expect("Autoscan Report golden manifest should be valid")
}

/// Recursively copies one scenario's path-backed scan inputs into an isolated run root.
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

/// Creates the scan-run-owned main FormID database used to characterize lookup hits and misses.
async fn create_formid_database(root: &Path, entries: &[FormIdDatabaseEntry]) {
    if entries.is_empty() {
        return;
    }

    let database_path = root
        .join("CLASSIC Data")
        .join("databases")
        .join("Fallout4 FormIDs Main.db");
    let connection = format!("sqlite://{}?mode=rwc", database_path.display());
    let pool = SqlitePoolOptions::new()
        .max_connections(1)
        .connect(&connection)
        .await
        .expect("golden FormID database should open");
    sqlx::query(
        "CREATE TABLE Fallout4 (\
            formid TEXT NOT NULL, \
            plugin TEXT NOT NULL, \
            entry TEXT NOT NULL, \
            PRIMARY KEY (formid, plugin)\
        )",
    )
    .execute(&pool)
    .await
    .expect("golden FormID table should be created");

    for entry in entries {
        sqlx::query("INSERT INTO Fallout4 (formid, plugin, entry) VALUES (?, ?, ?)")
            .bind(&entry.formid)
            .bind(&entry.plugin)
            .bind(&entry.entry)
            .execute(&pool)
            .await
            .expect("golden FormID row should be inserted");
    }
    pool.close().await;
}

/// Returns absolute fixture paths used by FCX while keeping their report bytes template-driven.
fn fcx_fixture_paths() -> (PathBuf, PathBuf, PathBuf) {
    let root = Path::new(FIXTURE_ROOT);
    let game_root = root.join("fcx-game");
    let documents_root = root.join("fcx-documents");
    let executable = game_root.join("Fallout4.exe");
    assert!(game_root.is_dir(), "FCX game root fixture should exist");
    assert!(
        documents_root.is_dir(),
        "FCX documents fixture should exist"
    );
    assert!(executable.is_file(), "FCX executable fixture should exist");
    (game_root, documents_root, executable)
}

/// Expands only environment-dependent FCX path tokens before the exact byte comparison.
fn expected_report_bytes(case_root: &Path, case: &GoldenCase) -> Vec<u8> {
    let template_path = case_root.join(&case.expected_report);
    let mut expected = std::fs::read_to_string(&template_path)
        .unwrap_or_else(|error| panic!("failed to read {}: {error}", template_path.display()));
    if case.fcx_mode {
        let (game_root, documents_root, _) = fcx_fixture_paths();
        expected = expected
            .replace("{{FCX_GAME_ROOT}}", &game_root.to_string_lossy())
            .replace("{{FCX_DOCUMENTS_ROOT}}", &documents_root.to_string_lossy())
            .replace("{{PATH_SEPARATOR}}", std::path::MAIN_SEPARATOR_STR);
    }
    expected.into_bytes()
}

/// Emits useful mismatch artifacts under `target/` without mutating the immutable corpus.
fn assert_report_bytes(case_name: &str, actual: &[u8], expected: &[u8]) {
    if actual != expected {
        let output =
            Path::new(env!("CARGO_MANIFEST_DIR")).join("../../target/autoscan-report-goldens");
        std::fs::create_dir_all(&output).expect("golden mismatch directory should be created");
        std::fs::write(output.join(format!("{case_name}-actual.md")), actual)
            .expect("actual golden mismatch should be written");
        std::fs::write(output.join(format!("{case_name}-expected.md")), expected)
            .expect("expected golden mismatch should be written");
        panic!(
            "Autoscan Report bytes changed for {case_name}; inspect {}",
            output.display()
        );
    }
}

/// Executes one fixture through the public complete Crash Log Scan Run contract.
async fn assert_golden_case(case: &GoldenCase) {
    let temp = tempdir().expect("golden tempdir should be created");
    let case_root = Path::new(FIXTURE_ROOT).join(&case.fixture_directory);
    copy_directory(&case_root.join("input"), temp.path());
    create_formid_database(temp.path(), &case.formid_database_entries).await;

    let crash_log = temp.path().join(&case.crash_log);
    let configuration = contract::Configuration {
        yaml_dir_root: temp.path().to_path_buf(),
        yaml_dir_data: temp.path().join("CLASSIC Data"),
        game: GameId::Fallout4,
        game_version: case.game_version.clone(),
        options: contract::Options::new(case.show_formid_values, false),
        scan_facts: CrashLogScanFacts::default(),
        max_concurrent: Some(1),
    };
    let source = TargetedCrashLogScanSource {
        inputs: vec![crash_log.clone()],
    };
    let request = if case.fcx_mode {
        let (game_root, documents_root, executable) = fcx_fixture_paths();
        contract::Request::targeted_with_fcx(
            configuration,
            source,
            CrashLogScanSetupContext {
                game_root: Some(game_root),
                docs_root: Some(documents_root),
                game_exe_path: Some(executable),
                xse_log_path: None,
            },
        )
    } else {
        contract::Request::targeted(configuration, source)
    };

    let result = contract::execute(request, &contract::Cancellation::new(), None)
        .await
        .unwrap_or_else(|error| panic!("{} scan should execute: {error}", case.name));

    assert_eq!(
        result.status,
        contract::RunStatus::Completed,
        "{}",
        case.name
    );
    assert_eq!((result.total, result.succeeded), (1, 1), "{}", case.name);
    assert_eq!((result.failed, result.cancelled), (0, 0), "{}", case.name);
    assert_eq!(result.setup.is_some(), case.fcx_mode, "{}", case.name);
    assert_eq!(result.logs.len(), 1, "{}", case.name);

    let log = &result.logs[0];
    assert_eq!(log.discovery_index, 0, "{}", case.name);
    assert_eq!(log.crash_log, crash_log, "{}", case.name);
    assert_eq!(
        log.disposition,
        contract::LogDisposition::Succeeded,
        "{}",
        case.name
    );
    assert!(log.failures.is_empty(), "{}", case.name);
    assert!(log.message.is_none(), "{}", case.name);
    assert_eq!(
        log.formid_count, case.expected.formid_count,
        "{}",
        case.name
    );
    assert_eq!(
        log.plugin_count, case.expected.plugin_count,
        "{}",
        case.name
    );
    assert_eq!(
        log.suspect_count, case.expected.suspect_count,
        "{}",
        case.name
    );

    let report_path = log
        .autoscan_report
        .as_ref()
        .unwrap_or_else(|| panic!("{} should retain its persisted report path", case.name));
    assert!(report_path.is_file(), "{}", case.name);
    let actual = std::fs::read(report_path)
        .unwrap_or_else(|error| panic!("failed to read {}: {error}", report_path.display()));
    let expected = expected_report_bytes(&case_root, case);
    assert_report_bytes(&case.name, &actual, &expected);
}

#[test]
fn complete_scan_runs_persist_byte_exact_autoscan_report_goldens() {
    get_runtime().block_on(async {
        for case in manifest().cases {
            assert_golden_case(&case).await;
        }
    });
}
