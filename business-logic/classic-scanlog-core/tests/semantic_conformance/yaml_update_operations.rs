//! YAML update operations with local manifest transport and owned cache generations.
use super::{RunnerResult, invalid, text};
use classic_settings_core::SchemaCompat;
use classic_shared_core::get_runtime;
use classic_update_core::yaml_update::{
    apply_yaml_data_update_with_decision, check_yaml_data_update, rollback_yaml_data_update,
};
use classic_update_core::{
    ApprovedUpdate, ClientSchemaSet, GithubClient, RollbackOutcome, UpdateCheckConfig, UpdateError,
    YamlUpdateReport, YamlUpdateStatus, apply_yaml_update_with_decision, check_yaml_update,
    rollback_yaml_update,
};
use serde_json::{Value, json};
use std::{
    fs,
    path::{Component, Path, PathBuf},
};

/// Restore cwd before the temporary installation is removed.
struct CwdGuard(PathBuf);
impl Drop for CwdGuard {
    /// Cleanup must not replace the primary conformance failure.
    fn drop(&mut self) {
        let _ = std::env::set_current_dir(&self.0);
    }
}

/// Preserve exact files, normalizing only the parsed cache manifest's JSON ordering.
fn files(root: &Path, directory: &Path, out: &mut Vec<Value>) -> RunnerResult<()> {
    for entry in fs::read_dir(directory)? {
        let entry = entry?;
        if entry.file_type()?.is_symlink() {
            return Err(invalid("unexpected YAML update link").into());
        }
        let path = entry.path();
        if path.is_dir() {
            files(root, &path, out)?;
        } else {
            let relative = path
                .strip_prefix(root)?
                .to_string_lossy()
                .replace('\\', "/");
            let bytes = fs::read(&path)?;
            out.push(if path.file_name().is_some_and(|name| name == "manifest-latest.json") { json!({"path":relative,"json":serde_json::from_slice::<Value>(&bytes)?}) } else { json!({"path":relative,"hex":bytes.iter().map(|byte|format!("{byte:02x}")).collect::<String>()}) });
        }
    }
    out.sort_by(|a, b| a["path"].as_str().cmp(&b["path"].as_str()));
    Ok(())
}

/// Recognize typed refusals; unexpected transport or filesystem failures fail the runner.
fn error_kind(error: UpdateError) -> RunnerResult<&'static str> {
    match error {
        UpdateError::UpdateCheckDisabled => Ok("disabled"),
        UpdateError::DecisionStale { .. } => Ok("stale_decision"),
        UpdateError::Generic(message) if message.starts_with("approved decision malformed:") => {
            Ok("malformed_approval")
        }
        UpdateError::ManifestInvalid { reason }
            if reason.contains("not a valid plain cache-dir basename") =>
        {
            Ok("invalid_name")
        }
        UpdateError::Generic(message)
            if message == "rollback refused: Local Ignore YAML Data is user-owned" =>
        {
            Ok("local_ignore_refused")
        }
        other => Err(other.into()),
    }
}

/// Read the native disabled/available status envelope and all exposed file metadata.
fn status(api: &str, result: Result<YamlUpdateStatus, UpdateError>) -> RunnerResult<Value> {
    let mut value = json!({"api":api,"tag":0,"releaseTag":"","publishedAt":"","compatible":[],"incompatible":[],"incompatibleReasons":[],"unknownReason":"","error":null});
    match result? {
        YamlUpdateStatus::Disabled => {}
        YamlUpdateStatus::UpdateAvailable {
            manifest,
            compatible_files,
            incompatible_files,
        } => {
            if !incompatible_files.is_empty() {
                return Err(invalid("unexpected incompatible fixture file").into());
            }
            value["tag"] = json!(1);
            value["releaseTag"] = json!(manifest.release_tag);
            value["publishedAt"] = json!(manifest.published_at);
            value["compatible"] = json!(compatible_files.iter().map(|file|json!({"name":file.name,"schemaVersion":file.schema_version,"sha256":file.sha256,"sizeBytes":file.size_bytes,"downloadUrl":file.download_url})).collect::<Vec<_>>());
        }
        other => return Err(invalid(&format!("unexpected YAML check status {other:?}")).into()),
    }
    Ok(value)
}

/// Empty reviewed selections install nothing; explicit native errors remain separately tagged.
fn report(api: &str, result: Result<YamlUpdateReport, UpdateError>) -> RunnerResult<Value> {
    match result {
        Ok(value) => {
            if !value.installed.is_empty() || !value.failed.is_empty() {
                return Err(invalid("empty consent unexpectedly selected payloads").into());
            }
            Ok(json!({"api":api,"installed":[],"failed":[],"error":null}))
        }
        Err(error) => Ok(json!({"api":api,"installed":[],"failed":[],"error":error_kind(error)?})),
    }
}

/// Execute core operations with all cache fallbacks and network proxy routes owned by the scenario.
pub(super) fn execute(fixture: &Value, scenario: &Value) -> RunnerResult<Value> {
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    let service = std::env::var("CLASSIC_CONFORMANCE_SERVICE")?;
    let port = service
        .strip_prefix("http://127.0.0.1:")
        .ok_or_else(|| invalid("service must be loopback"))?
        .parse::<u16>()?;
    if port == 0 {
        return Err(invalid("service port is zero").into());
    }
    fs::create_dir_all(root.join("cache"))?;
    fs::create_dir_all(root.join("bundled"))?;
    fs::write(root.join(".env"), b"")?;
    for (name, content) in fixture["files"]
        .as_object()
        .ok_or_else(|| invalid("files must be object"))?
    {
        if !name.starts_with("cache/")
            || name.contains('\\')
            || Path::new(name)
                .components()
                .any(|part| !matches!(part, Component::Normal(_)))
        {
            return Err(invalid("YAML update fixture escaped owned cache").into());
        }
        let path = root.join(name);
        fs::create_dir_all(
            path.parent()
                .ok_or_else(|| invalid("missing file parent"))?,
        )?;
        fs::write(path, text(content)?)?;
    }
    let cache = root.join("cache").to_string_lossy().into_owned();
    temp_env::with_vars(
        [
            ("LOCALAPPDATA", Some(cache.clone())),
            ("APPDATA", Some(cache.clone())),
            ("XDG_CACHE_HOME", Some(cache.clone())),
            ("HOME", Some(cache)),
            ("GITHUB_TOKEN", Some(String::new())),
            ("HTTP_PROXY", Some(service.clone())),
            ("HTTPS_PROXY", Some(service.clone())),
            ("ALL_PROXY", Some(service.clone())),
            ("NO_PROXY", Some("127.0.0.1,localhost".into())),
            ("http_proxy", Some(service.clone())),
            ("https_proxy", Some(service.clone())),
            ("all_proxy", Some(service.clone())),
            ("no_proxy", Some("127.0.0.1,localhost".into())),
        ],
        || -> RunnerResult<Value> {
            let _cwd = CwdGuard(std::env::current_dir()?);
            std::env::set_current_dir(root)?;
            // Empty owned .env plus a non-forwarding loopback proxy prevents production fallback traffic.
            let client = GithubClient::new("evildarkarchon", "CLASSIC-Fallout4")?;
            let pages = format!("{}/{}/pages", service, text(&scenario["id"])?);
            let mut current = ClientSchemaSet::new();
            current.insert("CLASSIC Main.yaml", SchemaCompat::new(2, 0), None);
            let config = |enabled| {
                (if enabled {
                    UpdateCheckConfig::enabled()
                } else {
                    UpdateCheckConfig::disabled()
                })
                .with_bundled_yaml_dir(root.join("bundled"))
            };
            let approved = if let Some(value) = fixture.get("approved") {
                ApprovedUpdate {
                    release_tag: text(&value["releaseTag"])?,
                    file_names: value["names"]
                        .as_array()
                        .ok_or_else(|| invalid("approved names must be array"))?
                        .iter()
                        .map(text)
                        .collect::<Result<Vec<_>, _>>()?,
                    file_sha256: value["digests"]
                        .as_array()
                        .ok_or_else(|| invalid("approved digests must be array"))?
                        .iter()
                        .map(text)
                        .collect::<Result<Vec<_>, _>>()?,
                }
            } else {
                ApprovedUpdate {
                    release_tag: String::new(),
                    file_names: Vec::new(),
                    file_sha256: Vec::new(),
                }
            };
            let mut before = Vec::new();
            files(root, root, &mut before)?;
            let mut results = Vec::new();
            match fixture["operation"]
                .as_str()
                .ok_or_else(|| invalid("operation missing"))?
            {
                "disabled" => {
                    results.push(status(
                        "yaml_check_update",
                        get_runtime().block_on(check_yaml_update(
                            &client,
                            &pages,
                            "yaml-data-v",
                            &current,
                            config(false),
                        )),
                    )?);
                    results.push(status(
                        "yaml_data_check_update",
                        get_runtime().block_on(check_yaml_data_update(&client, config(false))),
                    )?);
                    results.push(report(
                        "yaml_apply_update",
                        get_runtime().block_on(apply_yaml_update_with_decision(
                            &client,
                            &pages,
                            "yaml-data-v",
                            &current,
                            config(false),
                            &approved,
                        )),
                    )?);
                    results.push(report(
                        "yaml_data_apply_update",
                        get_runtime().block_on(apply_yaml_data_update_with_decision(
                            &client,
                            config(false),
                            &approved,
                        )),
                    )?);
                }
                "controlled-consent" => {
                    results.push(status(
                        "yaml_check_update",
                        get_runtime().block_on(check_yaml_update(
                            &client,
                            &pages,
                            "yaml-data-v",
                            &current,
                            config(true),
                        )),
                    )?);
                    results.push(report(
                        "yaml_apply_update",
                        get_runtime().block_on(apply_yaml_update_with_decision(
                            &client,
                            &pages,
                            "yaml-data-v",
                            &current,
                            config(true),
                            &approved,
                        )),
                    )?);
                }
                "malformed-approval" | "stale-decision" => results.push(report(
                    "yaml_apply_update",
                    get_runtime().block_on(apply_yaml_update_with_decision(
                        &client,
                        &pages,
                        "yaml-data-v",
                        &current,
                        config(true),
                        &approved,
                    )),
                )?),
                "rollback" => {
                    let name = text(&fixture["fileName"])?;
                    results.push(match rollback_yaml_update(&name) {
                        Ok(RollbackOutcome::RolledBack { file_name }) => json!({"api":"yaml_rollback_update","fileName":file_name,"rolledBack":true,"error":null}),
                        Ok(RollbackOutcome::NoPreviousVersion { file_name }) => json!({"api":"yaml_rollback_update","fileName":file_name,"rolledBack":false,"error":null}),
                        Err(error) => json!({"api":"yaml_rollback_update","fileName":name,"rolledBack":false,"error":error_kind(error)?})
                    });
                }
                "rollback-bulk" => {
                    let mut rolled = Vec::new();
                    let mut absent = Vec::new();
                    for (_, outcome) in get_runtime().block_on(rollback_yaml_data_update()) {
                        match outcome? {
                            RollbackOutcome::RolledBack { file_name } => rolled.push(file_name),
                            RollbackOutcome::NoPreviousVersion { file_name } => {
                                absent.push(file_name)
                            }
                        }
                    }
                    results.push(json!({"api":"yaml_data_rollback_update","rolledBack":rolled,"noPrevious":absent,"failedFiles":[],"failureReasons":[]}));
                }
                _ => return Err(invalid("unsupported YAML update operation").into()),
            }
            let mut after = Vec::new();
            files(root, root, &mut after)?;
            Ok(json!({"results":results,"beforeFiles":before,"files":after}))
        },
    )
}
