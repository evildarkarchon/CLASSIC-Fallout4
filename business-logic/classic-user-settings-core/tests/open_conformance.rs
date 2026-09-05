//! Input-only receipt runner for the public read-only User Settings Rust seam.

use classic_user_settings_core::{Revision, UserSettings, WindowGeometry};
use classic_vocabulary::Vocabulary;
use serde_json::{Map, Value, json};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::error::Error;
use std::fs;
use std::io::{self, Write};
use std::path::{Component, Path, PathBuf};
use tempfile::{NamedTempFile, tempdir};

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

/// Materializes declared fixture bytes and observes one public read-only open call.
fn execute_scenario(plan: &Value, scenario: &Value) -> RunnerResult<Value> {
    if scenario.get("expected").is_some() || scenario["action"] != "user-settings.open" {
        return Err(invalid("scenario must be an input-only User Settings open action").into());
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
