use super::*;

#[test]
fn defaults_use_production_without_ambient_credentials() {
    let config: UpdateEndpointConfig = serde_json::from_str("{}").unwrap();
    assert_eq!(config.github_api_base_url, "https://api.github.com");
    assert_eq!(config.timeout_ms, 30_000);
    assert!(config.token.is_none());
    config.validate().unwrap();
}

#[test]
fn rejects_unbounded_timeout_and_credential_urls() {
    for json in [
        r#"{"timeout_ms":0}"#,
        r#"{"timeout_ms":300001}"#,
        r#"{"github_api_base_url":"file:///tmp/manifest"}"#,
        r#"{"notification_pages_url":"http://user:secret@localhost/pages"}"#,
    ] {
        let config: UpdateEndpointConfig = serde_json::from_str(json).unwrap();
        assert!(config.validate().is_err());
    }
}

#[test]
fn pages_timeout_honors_shorter_caller_budget() {
    let config = UpdateEndpointConfig {
        timeout_ms: 25,
        ..Default::default()
    };
    let client = GithubClient::with_endpoint_config("owner", "repo", &config).unwrap();
    assert_eq!(
        client.capped_timeout(std::time::Duration::from_secs(5)),
        std::time::Duration::from_millis(25)
    );
}
