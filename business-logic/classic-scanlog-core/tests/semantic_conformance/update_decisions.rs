//! Observe deterministic strict version comparisons without release fetching.
use super::{RunnerResult, invalid, text};
use classic_update_core::{GithubClient, UpdateError};
use serde_json::{Value, json};

/// Compare explicit versions and preserve only typed version errors as domain results.
pub(super) fn execute(fixture: &Value) -> RunnerResult<Value> {
    if fixture.as_object().is_none_or(|object| object.len() != 2) {
        return Err(invalid("unsupported update decision fixture").into());
    }
    let client = GithubClient::new("conformance", "unused")?;
    match client.has_update(&text(&fixture["current"])?, &text(&fixture["latest"])?) {
        Ok(result) => Ok(json!({"hasUpdate": result, "error": null})),
        Err(UpdateError::VersionError(_)) => {
            Ok(json!({"hasUpdate": null, "error": {"code": "invalid_version"}}))
        }
        Err(error) => Err(error.into()),
    }
}
