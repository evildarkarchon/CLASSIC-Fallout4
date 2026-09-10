//! Supported endpoint and credential configuration for hosted update mirrors.

use crate::{GithubClient, NotificationStatus, Result, UpdateError};
use serde::{Deserialize, Serialize};
use std::path::Path;

/// Endpoint overrides shared by native and language binding callers.
/// Omitted fields use production endpoints and a 30-second request timeout.
/// Credentials are explicit: `None` never reads the environment or dotenv.
#[derive(Clone, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct UpdateEndpointConfig {
    /// GitHub-compatible API root, without the repository path.
    pub github_api_base_url: String,
    /// Full notification manifest URL; omitted uses the repository's GitHub Pages URL.
    pub notification_pages_url: Option<String>,
    /// Request timeout in milliseconds, from 1 through 300000; Pages also caps at 5000.
    pub timeout_ms: u64,
    /// Optional explicit API credential. Never inferred from process state.
    pub token: Option<String>,
}

impl Default for UpdateEndpointConfig {
    fn default() -> Self {
        Self {
            github_api_base_url: "https://api.github.com".into(),
            notification_pages_url: None,
            timeout_ms: 30_000,
            token: None,
        }
    }
}

impl UpdateEndpointConfig {
    /// Reject unsupported URLs and unbounded request timeouts before any I/O.
    pub(crate) fn validate(&self) -> Result<()> {
        if !(1..=300_000).contains(&self.timeout_ms) {
            return Err(UpdateError::Generic(
                "timeout_ms must be between 1 and 300000".into(),
            ));
        }
        for value in
            std::iter::once(&self.github_api_base_url).chain(self.notification_pages_url.iter())
        {
            let url = url::Url::parse(value)?;
            if !matches!(url.scheme(), "http" | "https")
                || url.host_str().is_none()
                || !url.username().is_empty()
                || url.password().is_some()
                || url.fragment().is_some()
            {
                return Err(UpdateError::Generic("update endpoints require an HTTP(S) URL without embedded credentials or fragment".into()));
            }
        }
        Ok(())
    }
}

/// Check a repository notification using explicit endpoint configuration and cache ownership.
/// `config_json` follows `UpdateEndpointConfig`; `{}` selects production defaults without
/// ambient credentials. An empty `cache_dir` disables caching; otherwise the caller owns
/// that directory. Returns the same classification and typed errors as the default check.
pub async fn check_app_notification_configured(
    owner: &str,
    repo: &str,
    installed_version: &str,
    config_json: &str,
    cache_dir: &str,
) -> Result<NotificationStatus> {
    let config: UpdateEndpointConfig = serde_json::from_str(config_json)?;
    let client = GithubClient::with_endpoint_config(owner, repo, &config)?;
    let pages_url = config
        .notification_pages_url
        .unwrap_or_else(|| crate::build_app_notification_pages_url(&client));
    let cache_dir = (!cache_dir.is_empty()).then(|| Path::new(cache_dir));
    crate::check_app_notification_with(&client, &pages_url, cache_dir, installed_version).await
}

#[cfg(test)]
#[path = "endpoints_tests.rs"]
mod tests;
