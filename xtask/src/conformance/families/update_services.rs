//! Input hook for `update-services`.
//!
//! Each fixture scripts the controlled update service the participant talks
//! to. The script must stay local and bounded: only the `pages` and `api`
//! routes, at most two queued responses each, a fixed status set, no headers
//! but `ETag` (so no redirect or injected header), and empty release lists so
//! no remote asset URL can reach the participant.

use serde_json::Value;

use super::{InputContext, has_exact_keys, issue};
use crate::conformance::Issue;

/// Checks every scenario's action and service script.
pub(super) fn validate(context: &InputContext<'_>) -> Vec<Issue> {
    let mut issues = Vec::new();
    for (index, scenario) in context.pack.scenarios.iter().enumerate() {
        if scenario.action != "update-services.notification" {
            issues.push(issue(
                index,
                "update-services scenarios must use the update-services.notification action",
            ));
        }
    }
    for (index, _, fixture) in context.sole_json_fixtures() {
        if let Err(message) = check(fixture) {
            issues.push(issue(index, message));
        }
    }
    issues
}

fn check(fixture: &Value) -> Result<(), String> {
    if !has_exact_keys(
        fixture,
        &["installedVersion", "timeoutMs", "checks", "service"],
    ) {
        return Err("an update service fixture must contain exactly installedVersion, timeoutMs, checks and service".into());
    }
    let bounded = fixture["installedVersion"].is_string()
        && fixture["timeoutMs"]
            .as_u64()
            .is_some_and(|ms| (1..=5000).contains(&ms))
        && fixture["checks"]
            .as_u64()
            .is_some_and(|checks| (1..=2).contains(&checks));
    if !bounded {
        return Err("update service inputs must be bounded: timeoutMs 1-5000, checks 1-2".into());
    }
    let service = &fixture["service"];
    if !has_exact_keys(service, &["pages", "api"]) {
        return Err("the update service permits only the local pages and api routes".into());
    }
    for route in ["pages", "api"] {
        let Some(responses) = service[route].as_array().filter(|items| items.len() <= 2) else {
            return Err(format!(
                "the {route} response sequence must be a list of at most two responses"
            ));
        };
        for response in responses {
            if response == &serde_json::json!({"stall": true}) {
                continue;
            }
            let keys_ok = response.as_object().is_some_and(|map| {
                ["status", "body", "headers"]
                    .iter()
                    .all(|key| map.contains_key(*key))
                    && map.keys().all(|key| {
                        matches!(key.as_str(), "status" | "body" | "headers" | "ifNoneMatch")
                    })
            });
            if !keys_ok {
                return Err(format!("an invalid controlled {route} response"));
            }
            let status = response["status"].as_u64();
            if !matches!(status, Some(200 | 304 | 404 | 503)) || !response["body"].is_string() {
                return Err(format!(
                    "a controlled {route} response needs status 200, 304, 404 or 503 and a string body"
                ));
            }
            if route == "api" && status == Some(200) && response["body"] != "[]" {
                return Err("release lists must be empty: remote asset URLs are forbidden".into());
            }
            let headers_ok = response["headers"].as_object().is_some_and(|headers| {
                headers.iter().all(|(name, value)| {
                    name == "ETag"
                        && value
                            .as_str()
                            .is_some_and(|text| !text.contains(['\r', '\n']))
                })
            });
            if !headers_ok {
                return Err(
                    "controlled responses cannot redirect or inject headers (ETag only)".into(),
                );
            }
            if response
                .get("ifNoneMatch")
                .is_some_and(|value| !value.is_string())
            {
                return Err("a conditional request (ifNoneMatch) must be a string".into());
            }
        }
    }
    Ok(())
}
