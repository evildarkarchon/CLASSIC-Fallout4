//! Observe notification transport and cache effects through the supported core API.
use super::{RunnerResult, invalid, text};
use classic_update_core::{UpdateError, check_app_notification_configured};
use serde_json::{Value, json};
use std::fs;

/// Run each check against the scenario service and retain the cache's exact bytes.
pub(super) fn execute(fixture: &Value, scenario: &Value) -> RunnerResult<Value> {
    let root = tempfile::tempdir()?;
    let cache = root.path().join("cache");
    fs::create_dir(&cache)?;
    let service = std::env::var("CLASSIC_CONFORMANCE_SERVICE")?;
    let base = format!(
        "{}/{}",
        service.trim_end_matches('/'),
        text(&scenario["id"])?
    );
    let config = json!({"github_api_base_url": format!("{base}/api"), "notification_pages_url": format!("{base}/pages"), "timeout_ms": fixture["timeoutMs"]}).to_string();
    let mut results = Vec::new();
    for _ in 0..fixture["checks"]
        .as_u64()
        .ok_or_else(|| invalid("checks must be an integer"))?
    {
        match classic_shared_core::get_runtime().block_on(check_app_notification_configured("conformance", "updates", &text(&fixture["installedVersion"])?, &config, &cache.to_string_lossy())) {
            Ok(status) => results.push(json!({"status": {
                "classification": status.classification, "latestVersion": status.latest_version,
                "publishedAt": status.published_at, "minSupportedVersion": status.min_supported_version,
                "display": status.display.map(|d| json!({"title":d.title,"body":d.body,"ctaUrl":d.cta_url})),
                "parseError": status.parse_error}, "error": null})),
            Err(error) => {
                let code = match error {
                    UpdateError::NotificationFetchFailed { .. } => "fetch_failed",
                    UpdateError::NotificationDecode { .. } => "decode",
                    UpdateError::ManifestUnsupportedVersion { .. } => "unsupported_version",
                    UpdateError::NotificationInstalledVersionParse { .. } => "installed_version",
                    other => return Err(other.into()),
                };
                results.push(json!({"status":null,"error":{"code":code}}));
            }
        }
    }
    let mut files = Vec::new();
    for entry in fs::read_dir(&cache)? {
        let path = entry?.path();
        if path.is_file() {
            let hex: String = fs::read(&path)?
                .iter()
                .map(|byte| format!("{byte:02x}"))
                .collect();
            files.push(json!({"path":format!("cache/{}", path.file_name().unwrap().to_string_lossy()),"hex":hex}));
        }
    }
    files.sort_by_key(|file| file["path"].as_str().unwrap().to_owned());
    Ok(json!({"results":results,"files":files}))
}
