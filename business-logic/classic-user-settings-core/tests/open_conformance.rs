//! Input-only receipt runner for public User Settings opening, updates, and migrations.

use classic_user_settings_core::{
    GuiWindow, MigrationEndpoint, MigrationPlanningOutcome, Revision, UserSettings,
    UserSettingsCommitOutcome, UserSettingsMigrationApplyOutcome, UserSettingsMigrationPlan,
    UserSettingsMigrationReceipt, UserSettingsMigrationRestoreOutcome, UserSettingsUpdate,
    UserSettingsUpdateField, UserSettingsUpdatePreview, WindowGeometry,
};
use classic_vocabulary::Vocabulary;
use serde_json::{Map, Value, json};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::error::Error;
use std::fs;
use std::io::{self, Write};
use std::path::{Component, Path, PathBuf};
use tempfile::{NamedTempFile, tempdir};

#[path = "open_conformance/defaults.rs"]
mod defaults_conformance;

type RunnerResult<T> = Result<T, Box<dyn Error + Send + Sync>>;

/// Rejects malformed private invocation data with an attributable error.
fn invalid(message: impl Into<String>) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message.into())
}

/// Reads one required non-empty string without coercing plan values.
fn string<'a>(value: &'a Value, label: &str) -> RunnerResult<&'a str> {
    value
        .as_str()
        .filter(|text| !text.is_empty())
        .ok_or_else(|| invalid(format!("{label} must be a non-empty string")).into())
}

/// Reads one required array from the authenticated input-only plan.
fn array<'a>(value: &'a Value, label: &str) -> RunnerResult<&'a Vec<Value>> {
    value
        .as_array()
        .ok_or_else(|| invalid(format!("{label} must be an array")).into())
}

/// Resolves a canonical relative placement beneath a fresh temporary root.
fn runtime_path(root: &Path, value: &Value) -> RunnerResult<PathBuf> {
    let text = string(value, "runtime path")?;
    if text.contains(['\\', ':'])
        || text
            .split('/')
            .any(|part| part.is_empty() || part == "." || part == "..")
        || Path::new(text)
            .components()
            .any(|part| !matches!(part, Component::Normal(_)))
    {
        return Err(invalid("runtime path must stay beneath its temporary root").into());
    }
    Ok(root.join(text))
}

/// Snapshots directories and exact file bytes, detecting any ordinary-open disk mutation.
fn tree(root: &Path) -> RunnerResult<BTreeMap<PathBuf, Option<Vec<u8>>>> {
    /// Visits one directory while retaining empty directories and rejecting symlinks.
    fn visit(
        root: &Path,
        directory: &Path,
        result: &mut BTreeMap<PathBuf, Option<Vec<u8>>>,
    ) -> RunnerResult<()> {
        for entry in fs::read_dir(directory)? {
            let entry = entry?;
            let path = entry.path();
            let kind = entry.file_type()?;
            let relative = path.strip_prefix(root)?.to_path_buf();
            if kind.is_dir() {
                result.insert(relative, None);
                visit(root, &path, result)?;
            } else if kind.is_file() {
                result.insert(relative, Some(fs::read(&path)?));
            } else {
                return Err(invalid("runtime tree contains an unsupported file kind").into());
            }
        }
        Ok(())
    }
    let mut result = BTreeMap::new();
    visit(root, root, &mut result)?;
    Ok(result)
}

/// Projects public geometry values without reproducing their fallback policy.
fn geometry(value: &WindowGeometry) -> Value {
    json!({"maximized": value.maximized(), "width": value.width(), "height": value.height()})
}

/// Projects only fields selected by the central input contract, never expected values.
fn view(settings: &UserSettings, fields: &[Value]) -> RunnerResult<Value> {
    let scan = settings.crash_log_scan_settings();
    let windows = settings.frontend_state().window_geometry();
    let mut values = Map::new();
    for field in fields {
        let name = string(field, "observation field")?;
        let value = match name {
            "update_check" => json!(settings.update_preferences().update_check()),
            "game_version" => json!(scan.game_version_selection().as_str()),
            "move_unsolved_logs" => json!(scan.move_unsolved_logs()),
            "max_concurrent_scans" => json!(scan.max_concurrent_scans()),
            "formid_databases" => json!(scan.formid_databases()),
            "main_tab_width" => json!(windows.main_tab().width()),
            "main_tab_maximized" => json!(windows.main_tab().maximized()),
            "custom_scan_folder" => json!(scan.custom_scan_input()),
            "mods_folder" => json!(settings.game_setup_settings().mods_root()),
            "main_tab" => geometry(windows.main_tab()),
            "backups_tab" => geometry(windows.backups_tab()),
            "articles_tab" => geometry(windows.articles_tab()),
            "results_tab" => geometry(windows.results_tab()),
            "fcx_mode" => json!(scan.fcx_mode()),
            "simplify_logs" => json!(scan.simplify_logs()),
            "show_formid_values" => json!(scan.formid_value_lookup()),
            _ => return Err(invalid(format!("unsupported observation field {name}")).into()),
        };
        if values.insert(name.into(), value).is_some() {
            return Err(invalid(format!("duplicate observation field {name}")).into());
        }
    }
    Ok(Value::Object(values))
}

/// Installs a declared input fixture beneath the isolated operation root.
fn install_fixture(
    plan: &Value,
    scenario: &Value,
    root: &Path,
    placement: &Value,
) -> RunnerResult<()> {
    let reference = string(&placement["fixtureRef"], "fixtureRef")?;
    if !array(&scenario["fixtureRefs"], "fixtureRefs")?.contains(&json!(reference)) {
        return Err(invalid("fixtureRef is not declared by the scenario").into());
    }
    let source = Path::new(string(&plan["fixtures"][reference], "fixture source")?);
    let destination = runtime_path(root, &placement["path"])?;
    fs::create_dir_all(
        destination
            .parent()
            .ok_or_else(|| invalid("placement has no parent"))?,
    )?;
    fs::copy(source, destination)?;
    Ok(())
}

/// Captures every operation artifact as exact bytes, including the root and empty directories.
fn operation_tree(root: &Path) -> RunnerResult<Value> {
    match fs::symlink_metadata(root) {
        Ok(metadata) if metadata.is_dir() && !metadata.is_symlink() => {}
        Ok(_) => return Err(invalid("operation root must be a directory, not a link").into()),
        Err(error) if error.kind() == io::ErrorKind::NotFound => return Ok(json!([])),
        Err(error) => return Err(error.into()),
    }
    let mut entries = vec![json!({"path": {"path": "."}, "kind": "directory"})];
    for (path, content) in tree(root)? {
        let mut entry = json!({"path": {"path": path.to_string_lossy().replace('\\', "/")},
            "kind": if content.is_some() { "file" } else { "directory" }});
        if let Some(bytes) = content {
            entry["bytesHex"] = json!(
                bytes
                    .iter()
                    .map(|byte| format!("{byte:02x}"))
                    .collect::<String>()
            );
        }
        entries.push(entry);
    }
    entries.sort_by(|left, right| {
        left["path"]["path"]
            .as_str()
            .cmp(&right["path"]["path"].as_str())
    });
    Ok(json!(entries))
}

/// Transports the scenario's typed requests into public builders without validating settings policy.
fn operation_update(input: &Value) -> RunnerResult<UserSettingsUpdate> {
    let requested = input["requestedUpdate"]
        .as_object()
        .ok_or_else(|| invalid("requestedUpdate must be an object"))?;
    let mut update = UserSettingsUpdate::new();
    if let Some(maximized) = requested.get("/UI/window_geometry/main_tab/maximized") {
        update = update.with_window_geometry(
            GuiWindow::Main,
            maximized
                .as_bool()
                .ok_or_else(|| invalid("maximized must be bool"))?,
            requested["/UI/window_geometry/main_tab/width"]
                .as_i64()
                .ok_or_else(|| invalid("width must be integer"))?,
            requested["/UI/window_geometry/main_tab/height"]
                .as_i64()
                .ok_or_else(|| invalid("height must be integer"))?,
        );
    }
    if let Some(active) = requested.get("/UI/tui/active_tab") {
        update = update.with_tui_remembered_state(
            active
                .as_i64()
                .ok_or_else(|| invalid("active tab must be integer"))?,
            requested["/UI/tui/results_panel_width"]
                .as_i64()
                .ok_or_else(|| invalid("panel width must be integer"))?,
            requested["/UI/tui/sort_ascending"]
                .as_bool()
                .ok_or_else(|| invalid("sort must be bool"))?,
        );
    }
    for (path, value) in requested {
        if matches!(
            path.as_str(),
            "/UI/window_geometry/main_tab/maximized"
                | "/UI/window_geometry/main_tab/width"
                | "/UI/window_geometry/main_tab/height"
                | "/UI/tui/active_tab"
                | "/UI/tui/results_panel_width"
                | "/UI/tui/sort_ascending"
        ) {
            continue;
        }
        update = match path.as_str() {
            "/CLASSIC_Settings/Update Check" => {
                update.with_update_check(value.as_bool().ok_or_else(|| invalid("expected bool"))?)
            }
            "/CLASSIC_Settings/Update Source" => {
                update.with_update_source(value.as_str().ok_or_else(|| invalid("expected string"))?)
            }
            "/UI/preferences/auto_switch_after_scan" => update.with_auto_switch_after_scan(
                value.as_bool().ok_or_else(|| invalid("expected bool"))?,
            ),
            "/CLASSIC_Settings/Managed Game" => {
                update.with_managed_game(value.as_str().ok_or_else(|| invalid("expected string"))?)
            }
            "/CLASSIC_Settings/Game Version" => update.with_game_version_selection(
                value.as_str().ok_or_else(|| invalid("expected string"))?,
            ),
            "/CLASSIC_Settings/Game Folder Path" => {
                update.with_game_root(serde_json::from_value::<Option<String>>(value.clone())?)
            }
            "/CLASSIC_Settings/Game EXE Path" => update
                .with_game_executable(serde_json::from_value::<Option<String>>(value.clone())?),
            "/CLASSIC_Settings/Documents Folder Path" => {
                update.with_documents_root(serde_json::from_value::<Option<String>>(value.clone())?)
            }
            "/CLASSIC_Settings/INI Folder Path" => {
                update.with_ini_folder(serde_json::from_value::<Option<String>>(value.clone())?)
            }
            "/CLASSIC_Settings/MODS Folder Path" => {
                update.with_mods_folder(serde_json::from_value::<Option<String>>(value.clone())?)
            }
            "/CLASSIC_Settings/FCX Mode" => {
                update.with_fcx_mode(value.as_bool().ok_or_else(|| invalid("expected bool"))?)
            }
            "/CLASSIC_Settings/Simplify Logs" => {
                update.with_simplify_logs(value.as_bool().ok_or_else(|| invalid("expected bool"))?)
            }
            "/CLASSIC_Settings/Show Statistics" => update
                .with_show_statistics(value.as_bool().ok_or_else(|| invalid("expected bool"))?),
            "/CLASSIC_Settings/Show FormID Values" => update
                .with_formid_value_lookup(value.as_bool().ok_or_else(|| invalid("expected bool"))?),
            "/CLASSIC_Settings/FormID Databases" => {
                update.with_formid_databases(serde_json::from_value(value.clone())?)
            }
            "/CLASSIC_Settings/Move Unsolved Logs" => update
                .with_move_unsolved_logs(value.as_bool().ok_or_else(|| invalid("expected bool"))?),
            "/CLASSIC_Settings/Unsolved Logs Destination" => update.with_unsolved_logs_destination(
                serde_json::from_value::<Option<String>>(value.clone())?,
            ),
            "/CLASSIC_Settings/SCAN Custom Path" => update
                .with_custom_scan_input(serde_json::from_value::<Option<String>>(value.clone())?),
            "/CLASSIC_Settings/Papyrus Log Path" => update
                .with_papyrus_log_path(serde_json::from_value::<Option<String>>(value.clone())?),
            "/CLASSIC_Settings/Max Concurrent Scans" => update.with_max_concurrent_scans(
                value.as_i64().ok_or_else(|| invalid("expected integer"))?,
            ),
            _ => {
                return Err(
                    invalid(format!("unsupported operation request selector {path}")).into(),
                );
            }
        };
    }
    Ok(update)
}

/// Projects every actual accepted value through an exhaustive public field match.
fn accepted_field(field: &UserSettingsUpdateField) -> RunnerResult<Value> {
    let value = match field {
        UserSettingsUpdateField::WindowMaximized(_, value) => json!(value),
        UserSettingsUpdateField::WindowWidth(_, value)
        | UserSettingsUpdateField::WindowHeight(_, value) => json!(value),
        UserSettingsUpdateField::TuiActiveTab(value) => json!(value),
        UserSettingsUpdateField::TuiResultsPanelWidth(value) => json!(value),
        UserSettingsUpdateField::TuiSortAscending(value) => json!(value),
        UserSettingsUpdateField::UpdateCheck(value) => json!(value),
        UserSettingsUpdateField::UpdateSource(value) => json!(value.as_str()),
        UserSettingsUpdateField::AutoSwitchAfterScan(value) => json!(value),
        UserSettingsUpdateField::ManagedGame(value) => json!(value.as_str()),
        UserSettingsUpdateField::GameVersionSelection(value) => json!(value.as_str()),
        UserSettingsUpdateField::GameRoot(value) => json!(value),
        UserSettingsUpdateField::GameExecutable(value) => json!(value),
        UserSettingsUpdateField::DocumentsRoot(value) => json!(value),
        UserSettingsUpdateField::IniFolder(value) => json!(value),
        UserSettingsUpdateField::ModsFolder(value) => json!(value),
        UserSettingsUpdateField::FcxMode(value) => json!(value),
        UserSettingsUpdateField::SimplifyLogs(value) => json!(value),
        UserSettingsUpdateField::ShowStatistics(value) => json!(value),
        UserSettingsUpdateField::FormIdValueLookup(value) => json!(value),
        UserSettingsUpdateField::FormIdDatabases(value) => json!(value),
        UserSettingsUpdateField::MoveUnsolvedLogs(value) => json!(value),
        UserSettingsUpdateField::UnsolvedLogsDestination(value) => json!(value),
        UserSettingsUpdateField::CustomScanInput(value) => json!(value),
        UserSettingsUpdateField::PapyrusLogPath(value) => json!(value),
        UserSettingsUpdateField::MaxConcurrentScans(value) => json!(value),
    };
    Ok(json!({"fieldPath": field.canonical_path(), "value": value}))
}

/// Observes preview before caller consent or an external edit, then optionally commits its artifact.
fn execute_operation(plan: &Value, scenario: &Value) -> RunnerResult<Value> {
    let temporary = tempdir()?;
    // A missing installation root makes even incidental preview directory creation observable.
    let root = temporary.path().join("installation");
    let input = &scenario["input"];
    if input["installationRootExists"]
        .as_bool()
        .ok_or_else(|| invalid("installationRootExists must be boolean"))?
    {
        fs::create_dir(&root)?;
    }
    for placement in array(&input["installationData"], "installationData")? {
        install_fixture(plan, scenario, &root, placement)?;
    }
    let settings = UserSettings::open(&root);
    let update = operation_update(input)?;
    let preview = match string(&input["previewMode"], "previewMode")? {
        "bootstrap" => settings.preview_bootstrap(update),
        "update" => settings.preview_update(update),
        _ => return Err(invalid("unsupported User Settings preview mode").into()),
    };
    let preview_observation = match &preview {
        UserSettingsUpdatePreview::Accepted(accepted) => json!({
            "status": "accepted", "baseRevision": accepted.base_revision().token(),
            "acceptedFields": accepted.fields().iter().map(accepted_field).collect::<RunnerResult<Vec<_>>>()?,
            "diagnostics": [],
        }),
        UserSettingsUpdatePreview::Rejected(diagnostics) => json!({
            "status": "rejected", "baseRevision": null, "acceptedFields": [],
            "diagnostics": diagnostics.iter().map(|diagnostic| json!({
                "fieldPath": diagnostic.field_path(), "code": diagnostic.code(), "message": diagnostic.message()
            })).collect::<Vec<_>>(),
        }),
    };
    let after_preview = operation_tree(&root)?;
    if !input["externalEdit"].is_null() {
        install_fixture(plan, scenario, &root, &input["externalEdit"])?;
    }
    let mut commit = json!({"status": "not-attempted", "revision": null,
        "expectedRevision": null, "actualRevision": null});
    if input["commit"]
        .as_bool()
        .ok_or_else(|| invalid("commit must be boolean"))?
        && let UserSettingsUpdatePreview::Accepted(accepted) = preview
    {
        match accepted.commit(&root)? {
            UserSettingsCommitOutcome::Committed { revision } => {
                commit["status"] = json!("committed");
                commit["revision"] = json!(revision.token());
            }
            UserSettingsCommitOutcome::Conflict {
                expected_revision,
                actual_revision,
            } => {
                commit["status"] = json!("conflict");
                commit["expectedRevision"] = json!(expected_revision.token());
                commit["actualRevision"] = json!(actual_revision.token());
            }
        }
    }
    Ok(
        json!({"preview": preview_observation, "afterPreviewTree": after_preview,
        "commit": commit, "finalTree": operation_tree(&root)?}),
    )
}

/// Preserves every byte of a public migration artifact in the private receipt transport.
fn migration_hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

/// Projects the public location and optional schema version without deriving compatibility.
fn migration_endpoint(endpoint: &MigrationEndpoint) -> Value {
    json!({
        "location": endpoint.location().as_str(),
        "schemaVersion": endpoint.schema_version().map(|version| json!({
            "major": version.major(), "minor": version.minor(),
        })),
    })
}

/// Projects the exact public plan and ordered review rows without interpreting their values.
fn migration_plan(plan: &UserSettingsMigrationPlan) -> Value {
    json!({
        "required": plan.required(), "baseRevision": plan.base_revision().token(),
        "source": migration_endpoint(plan.source()), "target": migration_endpoint(plan.target()),
        "changes": plan.changes().iter().map(|change| json!({
            "kind": change.kind().as_str(), "sourcePath": change.source_path(),
            "targetPath": change.target_path(), "before": change.before(), "after": change.after(),
        })).collect::<Vec<_>>(),
        "originalHex": migration_hex(plan.original_bytes()),
        "proposedHex": migration_hex(plan.proposed_bytes()),
    })
}

/// Projects a planner result while retaining all unsupported diagnostic codes.
fn migration_planning(outcome: &MigrationPlanningOutcome) -> Value {
    match outcome {
        MigrationPlanningOutcome::NotRequired => {
            json!({"status": "not-required", "diagnostics": [], "plan": null})
        }
        MigrationPlanningOutcome::Planned(plan) => {
            json!({"status": "planned", "diagnostics": [], "plan": migration_plan(plan)})
        }
        MigrationPlanningOutcome::Unsupported(diagnostics) => json!({
            "status": "unsupported", "plan": null,
            "diagnostics": diagnostics.iter().map(|diagnostic| diagnostic.code()).collect::<Vec<_>>(),
        }),
    }
}

/// Makes a returned artifact path portable while rejecting paths outside the isolated root.
fn migration_path(root: &Path, path: &Path) -> RunnerResult<Value> {
    Ok(json!({"path": path.strip_prefix(root)?.to_string_lossy().replace('\\', "/")}))
}

/// Copies only the public receipt's verified paths, endpoints, and revision attestations.
fn migration_receipt(root: &Path, receipt: &UserSettingsMigrationReceipt) -> RunnerResult<Value> {
    Ok(json!({
        "sourcePath": migration_path(root, receipt.source_path())?,
        "destinationPath": migration_path(root, receipt.destination_path())?,
        "backupPath": migration_path(root, receipt.backup_path())?,
        "source": migration_endpoint(receipt.source()), "target": migration_endpoint(receipt.target()),
        "backupRevision": receipt.backup_revision().token(),
        "publishedRevision": receipt.published_revision().token(),
    }))
}

/// Applies an input-declared filesystem edit at the selected public operation boundary.
fn migration_interference(
    plan: &Value,
    scenario: &Value,
    root: &Path,
    interference: &Value,
    receipt: Option<&UserSettingsMigrationReceipt>,
) -> RunnerResult<()> {
    if interference.is_null() {
        return Ok(());
    }
    match string(&interference["kind"], "interference kind")? {
        "external-edit" => install_fixture(plan, scenario, root, interference)?,
        "block-backup-directory" if receipt.is_none() => {
            fs::write(root.join("CLASSIC Backup"), b"blocked")?;
        }
        "tamper-backup" | "remove-backup" if receipt.is_some() => {
            let backup = receipt
                .expect("the match guard requires a real receipt")
                .backup_path();
            // Only the real core receipt chooses the backup; input cannot target an arbitrary file.
            let path = migration_path(root, backup)?;
            if interference["kind"] == "tamper-backup" {
                install_fixture(
                    plan,
                    scenario,
                    root,
                    &json!({
                        "fixtureRef": interference["fixtureRef"], "path": path["path"],
                    }),
                )?;
            } else {
                fs::remove_file(backup)?;
            }
        }
        _ => return Err(invalid("unsupported migration interference at this boundary").into()),
    }
    Ok(())
}

/// Observes pure planning and reversal, then runs consented public apply and receipt restoration.
fn execute_migration(plan: &Value, scenario: &Value) -> RunnerResult<Value> {
    let temporary = tempdir()?;
    let root = temporary.path();
    let input = &scenario["input"];
    for placement in array(&input["installationData"], "installationData")? {
        install_fixture(plan, scenario, root, placement)?;
    }
    let settings = UserSettings::open(root);
    let planning = settings.plan_migration();
    let repeated_planning = settings.plan_migration();
    let (reversed, round_trip) = match &planning {
        MigrationPlanningOutcome::Planned(plan) => {
            let reversed = plan.reverse_in_memory();
            let round_trip = reversed.reverse_in_memory();
            (migration_plan(&reversed), migration_plan(&round_trip))
        }
        _ => (Value::Null, Value::Null),
    };
    let after_planning = operation_tree(root)?;
    let mut apply = json!({"status": "not-attempted", "expectedRevision": null,
        "actualRevision": null, "errorCode": null, "receipt": null});
    let mut applied_receipt = None;
    if input["apply"]
        .as_bool()
        .ok_or_else(|| invalid("apply must be boolean"))?
        && let MigrationPlanningOutcome::Planned(migration) = &planning
    {
        migration_interference(plan, scenario, root, &input["beforeApply"], None)?;
        match migration.apply(root) {
            Ok(UserSettingsMigrationApplyOutcome::Applied(receipt)) => {
                apply["status"] = json!("applied");
                apply["receipt"] = migration_receipt(root, &receipt)?;
                applied_receipt = Some(receipt);
            }
            Ok(UserSettingsMigrationApplyOutcome::Conflict {
                expected_revision,
                actual_revision,
            }) => {
                apply["status"] = json!("conflict");
                apply["expectedRevision"] = json!(expected_revision.token());
                apply["actualRevision"] = json!(actual_revision.token());
            }
            Err(error) => {
                apply["status"] = json!("error");
                apply["errorCode"] = json!(error.code());
            }
        }
    }
    let after_apply = operation_tree(root)?;
    let mut restore = json!({"status": "not-attempted", "revision": null,
        "expectedRevision": null, "actualRevision": null, "errorCode": null});
    if input["restore"]
        .as_bool()
        .ok_or_else(|| invalid("restore must be boolean"))?
        && let Some(receipt) = applied_receipt
    {
        migration_interference(
            plan,
            scenario,
            root,
            &input["beforeRestore"],
            Some(&receipt),
        )?;
        match receipt.restore(root) {
            Ok(UserSettingsMigrationRestoreOutcome::Restored { revision }) => {
                restore["status"] = json!("restored");
                restore["revision"] = json!(revision.token());
            }
            Ok(UserSettingsMigrationRestoreOutcome::Conflict {
                expected_revision,
                actual_revision,
            }) => {
                restore["status"] = json!("conflict");
                restore["expectedRevision"] = json!(expected_revision.token());
                restore["actualRevision"] = json!(actual_revision.token());
            }
            Err(error) => {
                restore["status"] = json!("error");
                restore["errorCode"] = json!(error.code());
            }
        }
    }
    Ok(json!({
        "planning": migration_planning(&planning), "repeatedPlanning": migration_planning(&repeated_planning),
        "reversedPlan": reversed, "roundTripPlan": round_trip, "afterPlanningTree": after_planning,
        "apply": apply, "afterApplyTree": after_apply, "restore": restore, "finalTree": operation_tree(root)?,
    }))
}

/// Dispatches an input-only action through the corresponding public Rust operation.
fn execute_scenario(plan: &Value, scenario: &Value) -> RunnerResult<Value> {
    if scenario.get("expected").is_some() {
        return Err(invalid("scenario must be an input-only User Settings action").into());
    }
    if scenario["action"] == "user-settings.defaults" {
        return Ok(defaults_conformance::observe());
    }
    if scenario["action"] == "user-settings.legacy-import" {
        return execute_legacy_import(plan, scenario);
    }
    if scenario["action"] == "user-settings.geometry" {
        return execute_geometry(plan, scenario);
    }
    if scenario["action"] == "user-settings.update" {
        return execute_operation(plan, scenario);
    }
    if scenario["action"] == "user-settings.migrate" {
        return execute_migration(plan, scenario);
    }
    if scenario["action"] != "user-settings.open" {
        return Err(invalid("unsupported User Settings action").into());
    }
    let root = tempdir()?;
    let input = &scenario["input"];
    for placement in array(&input["installationData"], "installationData")? {
        let reference = string(&placement["fixtureRef"], "fixtureRef")?;
        if !array(&scenario["fixtureRefs"], "fixtureRefs")?.contains(&json!(reference)) {
            return Err(invalid("fixtureRef is not declared by the scenario").into());
        }
        let source = Path::new(string(&plan["fixtures"][reference], "fixture source")?);
        let destination = runtime_path(root.path(), &placement["path"])?;
        fs::create_dir_all(
            destination
                .parent()
                .ok_or_else(|| invalid("placement has no parent"))?,
        )?;
        fs::copy(source, destination)?;
    }
    let before = tree(root.path())?;
    let settings = UserSettings::open(root.path());
    // Compare retained bytes and revision with the pre-open tree so a rewrite cannot mask itself.
    let source_path = settings
        .source()
        .path()
        .map(|path| path.strip_prefix(root.path()))
        .transpose()?;
    let source_bytes = source_path
        .and_then(|path| before.get(path))
        .and_then(Option::as_deref);
    let revision_matches = match (settings.revision(), source_bytes) {
        (Revision::Missing, None) => true,
        (Revision::ContentSha256(digest), Some(bytes)) => {
            digest.as_slice() == Sha256::digest(bytes).as_slice()
        }
        _ => false,
    };
    let revision_kind = match settings.revision() {
        Revision::Missing => "missing",
        Revision::Unavailable => "unavailable",
        Revision::ContentSha256(_) => "sha256",
    };
    Ok(json!({
        "source": {
            "location": settings.source().location().as_str(),
            "path": source_path.map(|path| json!({"path": path.to_string_lossy().replace('\\', "/")})),
            "classification": settings.classification().as_str(),
        },
        "commitEligibility": settings.commit_eligibility().as_str(),
        "diagnostics": settings.diagnostics().iter().map(|diagnostic| diagnostic.code()).collect::<Vec<_>>(),
        "view": view(&settings, array(&input["observationFields"], "observationFields")?)?,
        "durableEffects": {"treeUnchanged": before == tree(root.path())?},
        "revision": {"kind": revision_kind, "matchesSourceBytes": revision_matches},
        "originalContent": {
            "present": settings.original_bytes().is_some(),
            "matchesSourceBytes": settings.original_bytes() == source_bytes,
        },
    }))
}

/// Runs the supplied family plan and publishes a fresh receipt with copied central identities.
fn execute_and_publish(plan_path: &Path, output_path: &Path) -> RunnerResult<()> {
    let plan: Value = serde_json::from_slice(&fs::read(plan_path)?)?;
    if plan["schemaVersion"] != 1
        || plan["familyVersion"] != 1
        || plan["familyId"] != "user-settings"
        || plan["participant"]
            != json!({"id": "rust", "role": "semantic-adapter", "executionInstanceId": "rust"})
    {
        return Err(invalid("run plan is not the Rust User Settings v1 invocation").into());
    }
    if output_path.exists() || plan_path.parent() != output_path.parent() {
        return Err(invalid("receipt must be a fresh sibling of its immutable plan").into());
    }
    let scenarios = array(&plan["scenarios"], "scenarios")?;
    if scenarios.is_empty() {
        return Err(invalid("run plan must contain scenarios").into());
    }
    let receipts = scenarios
        .iter()
        .map(|scenario| {
            let mut receipt =
                json!({"id": scenario["id"], "capabilityIds": scenario["capabilityIds"]});
            match execute_scenario(&plan, scenario) {
                Ok(observation) => {
                    receipt["executionStatus"] = json!("completed");
                    receipt["observation"] = observation;
                    receipt["failure"] = Value::Null;
                }
                Err(error) => {
                    receipt["executionStatus"] = json!("failed");
                    receipt["observation"] = json!({});
                    receipt["failure"] =
                        json!({"kind": "rust-runner-error", "message": error.to_string()});
                }
            }
            receipt
        })
        .collect::<Vec<_>>();
    let receipt = json!({
        "schemaVersion": plan["schemaVersion"], "familyId": plan["familyId"],
        "familyVersion": plan["familyVersion"], "expectationDigest": plan["expectationDigest"],
        "invocation": plan["invocation"], "participant": plan["participant"],
        "runner": {"id": "classic-rust-user-settings-conformance", "version": 1,
            "platform": std::env::consts::OS, "toolchain": "rust"},
        "scenarios": receipts,
    });
    let mut temporary = NamedTempFile::new_in(
        output_path
            .parent()
            .ok_or_else(|| invalid("receipt has no parent"))?,
    )?;
    temporary.write_all(&serde_json::to_vec(&receipt)?)?;
    temporary.as_file().sync_all()?;
    temporary.persist_noclobber(output_path)?;
    Ok(())
}

/// Executes only when the central launcher supplies both environment paths.
#[test]
fn writes_user_settings_conformance_receipt() {
    match (
        std::env::var_os("CLASSIC_CONFORMANCE_RUN_PLAN"),
        std::env::var_os("CLASSIC_CONFORMANCE_OUTPUT"),
    ) {
        (None, None) => eprintln!(
            "User Settings conformance launcher variables are absent; receipt run skipped"
        ),
        (Some(plan), Some(output)) => execute_and_publish(Path::new(&plan), Path::new(&output))
            .expect("the Rust User Settings conformance receipt should be published"),
        _ => panic!("both conformance launcher environment paths are required"),
    }
}

/// Commit public geometry and bind the returned revision to the actual final source bytes.
fn execute_geometry(plan: &Value, scenario: &Value) -> RunnerResult<Value> {
    let root = tempdir()?;
    for item in array(&scenario["input"]["installationData"], "installationData")? {
        install_fixture(plan, scenario, root.path(), item)?;
    }
    let initial = UserSettings::open(root.path());
    if scenario["input"]["blockLock"] == true {
        fs::create_dir(root.path().join("CLASSIC Settings.yaml.commit.lock"))?;
    }
    let transition = match UserSettings::commit_frontend_geometry_transition(
        root.path(),
        initial.revision(),
        GuiWindow::Main,
        false,
        900,
        650,
    ) {
        Ok(classic_user_settings_core::UserSettingsFrontendTransitionOutcome::Committed {
            revision,
        }) => {
            let content = fs::read(root.path().join("CLASSIC Settings.yaml"))?;
            json!({"status":"committed","code":null,"hasMessage":null,"revisionMatches":revision.token()==format!("sha256:{}",migration_hex(Sha256::digest(content).as_slice()))})
        }
        Err(error) => {
            json!({"status":"error","code":error.code(),"hasMessage":!error.message().trim().is_empty(),"revisionMatches":null})
        }
        _ => return Err(invalid("unexpected geometry outcome").into()),
    };
    let current = UserSettings::open(root.path());
    let geometry = current.frontend_state().window_geometry().main_tab();
    let files=tree(root.path())?.into_iter().map(|(path,content)|json!({"path":path.to_string_lossy().replace('\\',"/"),"kind":if content.is_some(){"file"}else{"directory"}})).collect::<Vec<_>>();
    Ok(
        json!({"transition":transition,"geometry":{"maximized":geometry.maximized(),"width":geometry.width(),"height":geometry.height()},"files":files}),
    )
}

/// Import exact retired state bytes and restore the authenticated original settings base.
fn execute_legacy_import(plan: &Value, scenario: &Value) -> RunnerResult<Value> {
    let root = tempdir()?;
    for item in array(&scenario["input"]["installationData"], "installationData")? {
        install_fixture(plan, scenario, root.path(), item)?;
    }
    let original = fs::read(root.path().join("CLASSIC Settings.yaml"))?;
    let legacy = fs::read(root.path().join("state.json"))?;
    let outcome = classic_user_settings_core::import_legacy_tui_state(
        root.path(),
        root.path().join("state.json"),
    )?;
    let classic_user_settings_core::LegacyTuiStateImportOutcome::Applied(receipt) = outcome else {
        return Err(invalid("legacy import has no applied receipt").into());
    };
    let published = fs::read(root.path().join("CLASSIC Settings.yaml"))?;
    let backup = fs::read(receipt.backup_path())?;
    let revision =
        |bytes: &[u8]| format!("sha256:{}", migration_hex(Sha256::digest(bytes).as_slice()));
    let relative = |path: &Path| -> RunnerResult<String> {
        Ok(path
            .strip_prefix(root.path())?
            .to_string_lossy()
            .replace('\\', "/"))
    };
    let current = UserSettings::open(root.path());
    let tui = current.frontend_state().tui();
    let observed = json!({"status":"applied","sourcePath":relative(receipt.source_path())?,"backupPath":relative(receipt.backup_path())?,"settingsPath":relative(receipt.settings_path())?,"settingsBackupPath":receipt.settings_backup_path().map(relative).transpose()?,"sourceRevisionMatches":receipt.source_revision().token()==revision(&legacy),"backupRevisionMatches":receipt.backup_revision().token()==revision(&backup)&&backup==legacy,"baseRevisionMatches":receipt.base_settings_revision().token()==revision(&original),"publishedRevisionMatches":receipt.published_settings_revision().token()==revision(&published),"inapplicable":{"classification":null,"revision":null,"expectedRevision":null,"actualRevision":null},"tui":{"activeTab":tui.active_tab(),"resultsPanelWidth":tui.results_panel_width(),"sortAscending":tui.sort_ascending(),"origins":[tui.active_tab_origin().as_str(),tui.results_panel_width_origin().as_str(),tui.sort_ascending_origin().as_str()]}});
    let restored = match receipt.restore(root.path())? {
        classic_user_settings_core::LegacyTuiStateImportRestoreOutcome::Restored {
            revision: current,
        } => {
            json!({"status":"restored","revisionMatches":current.token()==revision(&original)&&fs::read(root.path().join("CLASSIC Settings.yaml"))?==original,"expectedRevision":null,"actualRevision":null})
        }
        _ => return Err(invalid("legacy restore did not restore").into()),
    };
    let files=tree(root.path())?.into_iter().filter_map(|(path,bytes)|bytes.map(|bytes|json!({"path":path.to_string_lossy().replace('\\',"/"),"bytesHex":migration_hex(&bytes)}))).collect::<Vec<_>>();
    Ok(json!({"import":observed,"restore":restored,"files":files}))
}
