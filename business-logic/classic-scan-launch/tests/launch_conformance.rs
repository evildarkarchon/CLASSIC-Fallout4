//! Input-only receipt runner for the `crash-log-scan-launch` conformance family (ADR-0008).
//!
//! The launcher materializes a run plan without expectations; this runner launches each
//! scenario through the public Rust interface in a fresh Installation Root and publishes
//! only what it observed. Comparison against the pack happens centrally.

use classic_scan_launch::{
    CrashLogScanIntent, CrashLogScanLaunchOverrides, CrashLogScanLaunchRequest,
    GameVersionSelection, MaxConcurrency, prepare_launch,
};
use classic_scanlog_core::StandardUnsolvedLogsIntent;
use classic_scanlog_core::scan_run::contract::Request;
use classic_shared_core::GameId;
use classic_vocabulary::Vocabulary;
use serde_json::{Value, json};
use std::error::Error;
use std::fs;
use std::io::{self, Write};
use std::path::{Component, Path, PathBuf};

type RunnerResult<T> = Result<T, Box<dyn Error + Send + Sync>>;

const RUN_PLAN_ENV: &str = "CLASSIC_CONFORMANCE_RUN_PLAN";
const OUTPUT_ENV: &str = "CLASSIC_CONFORMANCE_OUTPUT";
const FAMILY_ID: &str = "crash-log-scan-launch";
const SETTINGS_FILE: &str = "CLASSIC Settings.yaml";
const INSTALLATION_ROOT_PLACEHOLDER: &str = "{{installationRoot}}";

/// Publishes one receipt for the centrally materialized input-only run plan.
#[test]
fn writes_launch_conformance_receipt() {
    let plan = std::env::var_os(RUN_PLAN_ENV);
    let output = std::env::var_os(OUTPUT_ENV);
    let (plan, output) = match (plan, output) {
        (None, None) => {
            eprintln!("launch conformance launcher variables are absent; receipt run skipped");
            return;
        }
        (Some(plan), Some(output)) => (PathBuf::from(plan), PathBuf::from(output)),
        _ => panic!("{RUN_PLAN_ENV} and {OUTPUT_ENV} must be set together"),
    };
    execute_and_publish(&plan, &output)
        .expect("the Rust launch conformance receipt should be published");
}

/// Executes every scenario of a validated plan and atomically publishes the receipt.
fn execute_and_publish(plan_path: &Path, output_path: &Path) -> RunnerResult<()> {
    let plan: Value = serde_json::from_slice(&fs::read(plan_path)?)?;
    if plan["schemaVersion"] != 1 || plan["familyId"] != FAMILY_ID {
        return Err(invalid("run plan is not a crash-log-scan-launch v1 plan"));
    }
    if plan["participant"]
        != json!({"id": "rust", "role": "semantic-adapter", "executionInstanceId": "rust"})
    {
        return Err(invalid(
            "run plan is not the Rust semantic-adapter invocation",
        ));
    }
    if output_path.exists() || output_path.parent() != plan_path.parent() {
        return Err(invalid(
            "receipt must be a fresh sibling of its immutable run plan",
        ));
    }
    let scenarios = array(&plan["scenarios"], "scenarios")?
        .iter()
        .map(|scenario| {
            if scenario.get("expected").is_some() {
                return Err(invalid("input-only run plan must not contain expectations"));
            }
            let (status, observation, failure) = match observe(&plan["fixtures"], scenario) {
                Ok(observation) => ("completed", observation, Value::Null),
                Err(error) => (
                    "failed",
                    json!({}),
                    json!({"kind": "rust-runner-error", "message": error.to_string()}),
                ),
            };
            Ok(json!({
                "id": scenario["id"],
                "capabilityIds": scenario["capabilityIds"],
                "executionStatus": status,
                "observation": observation,
                "failure": failure,
            }))
        })
        .collect::<RunnerResult<Vec<_>>>()?;
    let receipt = json!({
        "schemaVersion": 1,
        "familyId": plan["familyId"],
        "familyVersion": plan["familyVersion"],
        "expectationDigest": plan["expectationDigest"],
        "invocation": plan["invocation"],
        "participant": plan["participant"],
        "runner": {
            "id": "classic-rust-scan-launch-conformance",
            "version": 1,
            "platform": std::env::consts::OS,
            "toolchain": "rust",
        },
        "scenarios": scenarios,
    });
    atomic_write_json(output_path, &receipt)
}

/// Launches one scenario in a fresh Installation Root and projects what the launch did.
fn observe(fixtures: &Value, scenario: &Value) -> RunnerResult<Value> {
    let input = &scenario["input"];
    let root = tempfile::tempdir()?;
    let root_path = root.path().to_path_buf();
    let reference = string(&input["settingsFixtureRef"], "settingsFixtureRef")?;
    let source = string(&fixtures[reference], "settings fixture path")?;
    let settings_path = root_path.join(SETTINGS_FILE);
    fs::write(
        &settings_path,
        installation_root_fixture(&fs::read_to_string(source)?, &root_path)?,
    )?;
    let before = fs::read(&settings_path)?;
    // Scenario files (game executables, XSE logs) are empty files beneath the root.
    if let Some(files) = input.get("files") {
        for file in array(files, "files")? {
            let path = root_path.join(relative(string(file, "file")?)?);
            fs::create_dir_all(path.parent().ok_or_else(|| invalid("file has no parent"))?)?;
            fs::write(path, b"")?;
        }
    }

    let intent = match string(&input["intent"], "intent")? {
        "standard" => CrashLogScanIntent::Standard,
        "targeted" => CrashLogScanIntent::Targeted(
            array(&input["targetedInputs"], "targetedInputs")?
                .iter()
                .map(|item| Ok(root_path.join(relative(string(item, "targeted input")?)?)))
                .collect::<RunnerResult<Vec<_>>>()?,
        ),
        other => return Err(invalid(format!("unsupported intent {other}"))),
    };
    let overrides = overrides(&input["overrides"], &root_path)?;

    let outcome = prepare_launch(&root_path, intent, &overrides);
    let settings_unchanged = fs::read(&settings_path)? == before;
    Ok(match outcome {
        Ok(launch) => json!({
            "outcome": "launched",
            "errorKind": null,
            "request": request_view(&launch, &root_path)?,
            "diagnostics": launch
                .diagnostics()
                .iter()
                .map(|diagnostic| json!({
                    "kind": diagnostic.kind().as_str(),
                    "code": diagnostic.code(),
                }))
                .collect::<Vec<_>>(),
            "settingsUnchanged": settings_unchanged,
        }),
        Err(error) => json!({
            "outcome": "error",
            "errorKind": error.kind().as_str(),
            "request": null,
            "diagnostics": [],
            "settingsUnchanged": settings_unchanged,
        }),
    })
}

/// Converts scenario overrides into the public builder; paths are Installation Root-relative.
fn overrides(value: &Value, root: &Path) -> RunnerResult<CrashLogScanLaunchOverrides> {
    let mut overrides = CrashLogScanLaunchOverrides::new();
    if let Some(game) = value.get("game") {
        let token = string(game, "game")?;
        let game = GameId::all()
            .into_iter()
            .find(|game| game.as_str() == token)
            .ok_or_else(|| invalid(format!("unsupported game {token}")))?;
        overrides = overrides.with_game(game);
    }
    if let Some(version) = value.get("gameVersion") {
        let token = string(version, "gameVersion")?;
        overrides = overrides.with_game_version(
            GameVersionSelection::parse(token)
                .ok_or_else(|| invalid(format!("unsupported gameVersion {token}")))?,
        );
    }
    if let Some(scan_path) = value.get("scanPath") {
        overrides = overrides.with_scan_path(root.join(relative(string(scan_path, "scanPath")?)?));
    }
    if value.get("noScanPath") == Some(&Value::Bool(true)) {
        overrides = overrides.with_no_scan_path();
    }
    if let Some(count) = value.get("maxConcurrent") {
        let count = count
            .as_u64()
            .and_then(|count| usize::try_from(count).ok())
            .ok_or_else(|| invalid("maxConcurrent must be a non-negative integer"))?;
        overrides = overrides.with_max_concurrency(MaxConcurrency::from_count(count));
    }
    if value.get("showFormidValues") == Some(&Value::Bool(true)) {
        overrides = overrides.with_show_formid_values();
    }
    if value.get("simplifyLogs") == Some(&Value::Bool(true)) {
        overrides = overrides.with_simplify_logs();
    }
    if value.get("fcxMode") == Some(&Value::Bool(true)) {
        overrides = overrides.with_fcx_mode();
    }
    Ok(overrides)
}

/// Replaces the fixture's `{{installationRoot}}` placeholder with this run's root.
///
/// The root is written with `/` separators so it reads the same inside any YAML quoting;
/// both separators name the same folders on Windows.
fn installation_root_fixture(fixture: &str, root: &Path) -> RunnerResult<String> {
    let root = root
        .to_str()
        .ok_or_else(|| invalid("Installation Root is not valid UTF-8"))?
        .replace('\\', "/");
    Ok(fixture.replace(INSTALLATION_ROOT_PLACEHOLDER, &root))
}

/// Projects the launched request; paths become Installation Root-relative.
fn request_view(launch: &CrashLogScanLaunchRequest, root: &Path) -> RunnerResult<Value> {
    let request = launch.request();
    let configuration = request.configuration();
    let optional = |path: Option<&Path>| -> RunnerResult<Value> {
        path.map(|path| root_relative(root, path).map(Value::String))
            .transpose()
            .map(|value| value.unwrap_or(Value::Null))
    };
    let (base, custom, documents, unsolved, targeted, fcx) = match request {
        Request::Standard(standard) => (
            optional(Some(&standard.source().base_directory))?,
            optional(standard.source().custom_scan_directory.as_deref())?,
            optional(standard.source().configured_documents_root.as_deref())?,
            json!(match standard.unsolved_logs() {
                StandardUnsolvedLogsIntent::LeaveInPlace => "leave_in_place",
                StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault =>
                    "move_to_configured_or_default",
                StandardUnsolvedLogsIntent::MoveToCustom(_) => "move_to_custom",
            }),
            Value::Null,
            standard.fcx_enabled(),
        ),
        Request::Targeted(targeted) => (
            Value::Null,
            Value::Null,
            Value::Null,
            Value::Null,
            Value::Array(
                targeted
                    .source()
                    .inputs
                    .iter()
                    .map(|path| root_relative(root, path).map(Value::String))
                    .collect::<RunnerResult<Vec<_>>>()?,
            ),
            targeted.fcx_enabled(),
        ),
    };
    Ok(json!({
        "intent": match request {
            Request::Standard(_) => "standard",
            Request::Targeted(_) => "targeted",
        },
        "game": configuration.game.as_str(),
        "gameVersion": configuration.game_version,
        "showFormidValues": configuration.options.show_formid_values,
        "simplifyLogs": configuration.options.simplify_logs,
        "formidDatabasePaths": configuration
            .scan_facts
            .formid_database_paths
            .iter()
            .map(|path| path.to_string_lossy().replace('\\', "/"))
            .collect::<Vec<_>>(),
        "unsolvedLogsDestination": optional(
            configuration.scan_facts.unsolved_logs_destination.as_deref()
        )?,
        "maxConcurrent": configuration.max_concurrent,
        "baseDirectory": base,
        "customScanDirectory": custom,
        "configuredDocumentsRoot": documents,
        "unsolvedLogs": unsolved,
        "targetedInputs": targeted,
        "fcxEnabled": fcx,
        "setupContext": launch
            .setup_context()
            .map(|context| -> RunnerResult<Value> {
                Ok(json!({
                    "gameRoot": optional(context.game_root.as_deref())?,
                    "docsRoot": optional(context.docs_root.as_deref())?,
                    "gameExePath": optional(context.game_exe_path.as_deref())?,
                    "xseLogPath": optional(context.xse_log_path.as_deref())?,
                }))
            })
            .transpose()?,
    }))
}

/// Renders `path` relative to the Installation Root with `/` separators; the root is `.`.
fn root_relative(root: &Path, path: &Path) -> RunnerResult<String> {
    let relative = path
        .strip_prefix(root)
        .map_err(|_| invalid(format!("{} escapes the Installation Root", path.display())))?;
    let parts = relative
        .components()
        .map(|part| match part {
            Component::Normal(part) => part
                .to_str()
                .map(str::to_string)
                .ok_or_else(|| invalid("observed path is not valid UTF-8")),
            _ => Err(invalid("observed path is not normalized")),
        })
        .collect::<Result<Vec<_>, _>>()?;
    Ok(if parts.is_empty() {
        ".".to_string()
    } else {
        parts.join("/")
    })
}

/// Validates a scenario-supplied relative path that must stay beneath the root.
fn relative(text: &str) -> RunnerResult<PathBuf> {
    if text.contains(['\\', ':'])
        || text
            .split('/')
            .any(|part| part.is_empty() || part == "." || part == "..")
    {
        return Err(invalid(format!(
            "{text} must stay beneath the Installation Root"
        )));
    }
    Ok(text.split('/').collect())
}

/// Reads one required non-empty string from the plan.
fn string<'a>(value: &'a Value, label: &str) -> RunnerResult<&'a str> {
    value
        .as_str()
        .filter(|text| !text.is_empty())
        .ok_or_else(|| invalid(format!("{label} must be a non-empty string")))
}

/// Reads one required array from the plan.
fn array<'a>(value: &'a Value, label: &str) -> RunnerResult<&'a Vec<Value>> {
    value
        .as_array()
        .ok_or_else(|| invalid(format!("{label} must be an array")))
}

/// Publishes a complete JSON receipt without exposing partial bytes at its final path.
fn atomic_write_json(output_path: &Path, receipt: &Value) -> RunnerResult<()> {
    let parent = output_path
        .parent()
        .ok_or_else(|| invalid("receipt output path has no parent"))?;
    let mut temporary = tempfile::NamedTempFile::new_in(parent)?;
    serde_json::to_writer_pretty(temporary.as_file_mut(), receipt)?;
    temporary.as_file_mut().write_all(b"\n")?;
    temporary.as_file_mut().sync_all()?;
    // The launcher reserves an absent destination, so a same-directory persist is one
    // atomic visibility boundary.
    temporary
        .persist(output_path)
        .map_err(|error| error.error)?;
    Ok(())
}

/// Builds an attributable runner error.
fn invalid(message: impl Into<String>) -> Box<dyn Error + Send + Sync> {
    Box::new(io::Error::new(io::ErrorKind::InvalidData, message.into()))
}
