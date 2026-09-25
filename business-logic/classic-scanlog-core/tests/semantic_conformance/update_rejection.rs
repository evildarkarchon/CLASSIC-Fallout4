//! Negative runtime paths reject malformed input before an HTTP request can be sent.
#![allow(deprecated)] // The legacy latest-release entry point remains an explicit tracked obligation.

use super::{RunnerResult, invalid, text};
use classic_update_core::{GithubClient, UpdateError};
use serde_json::{Value, json};

/// Execute actual core entry points and distinguish builder rejection from transport failure.
pub(super) fn observe(fixture: &Value) -> RunnerResult<Value> {
    if fixture["token"] != "synthetic\ninvalid" {
        return Err(invalid("only synthetic malformed credentials are permitted").into());
    }
    let owner = text(&fixture["owner"])?;
    let repo = text(&fixture["repo"])?;
    let operation = text(&fixture["operation"])?;
    if operation == "metadata" {
        let client = GithubClient::with_token(&owner, &repo, Some(text(&fixture["token"])?))?;
        return Ok(json!({"repoUrl": client.repo_url()}));
    }
    let result = classic_shared_core::get_runtime().block_on(async {
        if operation == "notification" {
            classic_update_core::notification::check_app_notification(
                &owner,
                &repo,
                &text(&fixture["invalidVersion"]).expect("validated string"),
            )
            .await
            .map(|_| ())
        } else {
            let client = GithubClient::with_token(
                &owner,
                &repo,
                Some(text(&fixture["token"]).expect("validated string")),
            )?;
            if operation == "latest" {
                client.get_latest_release().await.map(|_| ())
            } else {
                client.get_all_releases(false, false).await.map(|_| ())
            }
        }
    });
    match result {
        Err(UpdateError::HttpError(error)) if operation != "notification" && error.is_builder() => {
            Ok(
                json!({"boundary": "request-builder", "error": "builder-error", "requestBuilt": false}),
            )
        }
        Err(UpdateError::NotificationInstalledVersionParse { .. })
            if operation == "notification" =>
        {
            Ok(
                json!({"boundary": "caller-validation", "error": "invalid-installed-version", "requestBuilt": false}),
            )
        }
        _ => Err(
            invalid("expected pre-transport rejection, not success or a network failure").into(),
        ),
    }
}
