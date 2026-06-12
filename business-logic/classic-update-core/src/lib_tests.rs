use super::*;

#[test]
fn test_version_constant() {
    // VERSION is a const str, so it's always non-empty at compile time
    #[allow(clippy::len_zero)]
    {
        assert!(VERSION.len() > 0);
    }
    assert!(VERSION.contains('.'));
}

#[test]
fn test_version_is_semver() {
    // VERSION should be a valid semver version
    let result = semver::Version::parse(VERSION);
    assert!(
        result.is_ok(),
        "VERSION '{}' should be valid semver",
        VERSION
    );
}

#[test]
fn test_re_exports_github_client() {
    // Test that GithubClient is re-exported
    let client = GithubClient::new("owner", "repo").expect("client creation should succeed");
    assert_eq!(client.owner(), "owner");
    assert_eq!(client.repo(), "repo");
}

#[test]
fn test_re_exports_github_release() {
    // Test that GithubRelease is re-exported and usable
    let release = GithubRelease {
        tag_name: "v1.0.0".to_string(),
        name: "Test Release".to_string(),
        body: "Release notes".to_string(),
        prerelease: false,
        draft: false,
        html_url: "https://github.com/test/repo".to_string(),
        assets: vec![],
        created_at: "2024-01-01T00:00:00Z".to_string(),
        published_at: Some("2024-01-01T12:00:00Z".to_string()),
    };

    assert_eq!(release.tag_name, "v1.0.0");
}

#[test]
fn test_re_exports_github_asset() {
    // Test that GithubAsset is re-exported and usable
    let asset = GithubAsset {
        name: "release.zip".to_string(),
        size: 1024,
        browser_download_url: "https://example.com/release.zip".to_string(),
        content_type: "application/zip".to_string(),
        download_count: 100,
    };

    assert_eq!(asset.name, "release.zip");
    assert_eq!(asset.size, 1024);
}

#[test]
fn test_re_exports_update_error() {
    // Test that UpdateError is re-exported
    let err = UpdateError::NotFound("test".to_string());
    let display = format!("{}", err);
    assert!(display.contains("not found"));
}

#[test]
fn test_re_exports_result_type() {
    // Test that Result type alias works
    fn returns_result() -> Result<String> {
        Ok("success".to_string())
    }

    fn returns_error() -> Result<String> {
        Err(UpdateError::Timeout)
    }

    assert!(returns_result().is_ok());
    assert!(returns_error().is_err());
}

#[test]
fn test_module_exports_are_accessible() {
    // Verify that the error module is accessible
    let _: error::Result<()> = Ok(());

    // Verify github module is accessible
    let _client = github::GithubClient::new("a", "b").expect("client creation should succeed");
}
