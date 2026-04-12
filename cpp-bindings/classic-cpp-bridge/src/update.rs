//! GitHub update checking bridge for CXX FFI.
//!
//! Bridges `classic_update_core::GithubClient` for checking if updates are
//! available by comparing semver versions.

use classic_shared_core::get_runtime;
use classic_update_core::GithubClient;

fn github_has_update(current: &str, latest: &str) -> bool {
    let client = match GithubClient::new("evildarkarchon", "CLASSIC-Fallout4") {
        Ok(client) => client,
        Err(_) => return false,
    };
    client.has_update(current, latest).unwrap_or_default()
}

fn github_check_for_updates(
    owner: &str,
    repo: &str,
    current_version: &str,
) -> ffi::UpdateCheckResult {
    let client = match GithubClient::new(owner, repo) {
        Ok(client) => client,
        Err(e) => {
            return ffi::UpdateCheckResult {
                has_update: false,
                latest_version: String::new(),
                release_notes: String::new(),
                error_message: format!("{e}"),
            };
        }
    };
    match get_runtime().block_on(client.get_latest_release()) {
        Ok(release) => {
            let has_update = client
                .has_update(current_version, &release.tag_name)
                .unwrap_or(false);
            ffi::UpdateCheckResult {
                has_update,
                latest_version: release.tag_name,
                release_notes: release.body,
                error_message: String::new(),
            }
        }
        Err(e) => ffi::UpdateCheckResult {
            has_update: false,
            latest_version: String::new(),
            release_notes: String::new(),
            error_message: format!("{e}"),
        },
    }
}

#[cxx::bridge(namespace = "classic::update")]
mod ffi {
    struct UpdateCheckResult {
        has_update: bool,
        latest_version: String,
        release_notes: String,
        error_message: String,
    }

    extern "Rust" {
        fn github_has_update(current: &str, latest: &str) -> bool;
        fn github_check_for_updates(
            owner: &str,
            repo: &str,
            current_version: &str,
        ) -> UpdateCheckResult;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_has_update_older() {
        assert!(github_has_update("1.0.0", "2.0.0"));
    }

    #[test]
    fn test_has_update_same() {
        assert!(!github_has_update("1.0.0", "1.0.0"));
    }

    #[test]
    fn test_has_update_newer() {
        assert!(!github_has_update("2.0.0", "1.0.0"));
    }

    #[test]
    fn test_has_update_prerelease() {
        assert!(github_has_update("1.0.0-alpha", "1.0.0"));
    }

    #[test]
    fn test_has_update_invalid_version() {
        // Invalid versions should return false (no update)
        assert!(!github_has_update("not_a_version", "1.0.0"));
    }

    #[test]
    #[ignore] // Requires network access
    fn test_check_for_updates_network() {
        let result = github_check_for_updates("evildarkarchon", "CLASSIC-Fallout4", "0.0.1");
        assert!(result.error_message.is_empty());
        assert!(!result.latest_version.is_empty());
    }
}
