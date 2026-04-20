use super::*;
use std::time::Duration;

#[test]
fn test_github_error_display() {
    let err = UpdateError::GithubError("API rate limit".to_string());
    let display = format!("{}", err);
    assert!(display.contains("GitHub API error"));
    assert!(display.contains("API rate limit"));
}

#[test]
fn test_not_found_error_display() {
    let err = UpdateError::NotFound("Repository not found".to_string());
    let display = format!("{}", err);
    assert!(display.contains("Resource not found"));
    assert!(display.contains("Repository not found"));
}

#[test]
fn test_rate_limit_error_with_duration() {
    let err = UpdateError::RateLimitExceeded(Some(Duration::from_secs(60)));
    let display = format!("{}", err);
    assert!(display.contains("Rate limit exceeded"));
    assert!(display.contains("60"));
}

#[test]
fn test_rate_limit_error_without_duration() {
    let err = UpdateError::RateLimitExceeded(None);
    let display = format!("{}", err);
    assert!(display.contains("Rate limit exceeded"));
    assert!(display.contains("None"));
}

#[test]
fn test_timeout_error_display() {
    let err = UpdateError::Timeout;
    let display = format!("{}", err);
    assert_eq!(display, "Network timeout");
}

#[test]
fn test_generic_error_display() {
    let err = UpdateError::Generic("Something went wrong".to_string());
    let display = format!("{}", err);
    assert!(display.contains("Update error"));
    assert!(display.contains("Something went wrong"));
}

#[test]
fn test_version_error_from_semver() {
    // Parse an invalid version string to get a semver error
    let semver_err = semver::Version::parse("invalid").unwrap_err();
    let err: UpdateError = semver_err.into();

    let display = format!("{}", err);
    assert!(display.contains("Version error"));
}

#[test]
fn test_url_error_from_url() {
    let url_err = url::Url::parse("not a url").unwrap_err();
    let err: UpdateError = url_err.into();

    let display = format!("{}", err);
    assert!(display.contains("URL parsing error"));
}

#[test]
fn test_json_error_from_serde() {
    let json_err: serde_json::Error =
        serde_json::from_str::<String>("invalid json").unwrap_err();
    let err: UpdateError = json_err.into();

    let display = format!("{}", err);
    assert!(display.contains("JSON parsing error"));
}

#[test]
fn test_error_debug_impl() {
    let err = UpdateError::GithubError("Test".to_string());
    let debug = format!("{:?}", err);
    assert!(debug.contains("GithubError"));
    assert!(debug.contains("Test"));
}

#[test]
fn test_all_error_variants_are_send_sync() {
    fn assert_send_sync<T: Send + Sync>() {}

    // This will fail to compile if UpdateError is not Send + Sync
    assert_send_sync::<UpdateError>();
}

#[test]
fn test_result_type_alias() {
    fn returns_result() -> Result<i32> {
        Ok(42)
    }

    fn returns_error() -> Result<i32> {
        Err(UpdateError::Timeout)
    }

    assert_eq!(returns_result().unwrap(), 42);
    assert!(returns_error().is_err());
}

#[test]
fn test_error_source_chain() {
    use std::error::Error;

    // Version error should have a source
    let semver_err = semver::Version::parse("bad").unwrap_err();
    let err: UpdateError = semver_err.into();

    // The error should implement Error trait with source
    let _ = err.source();
}
