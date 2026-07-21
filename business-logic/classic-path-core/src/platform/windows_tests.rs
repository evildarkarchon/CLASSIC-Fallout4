use super::*;

#[test]
fn test_query_game_registry() {
    // This test will fail if game is not installed, which is expected
    // In a real scenario, you'd mock the registry or skip if game not found
    let result = query_game_registry("Fallout4", "", true);

    // Test that we get either a valid path or RegistryNotFound error
    match result {
        Ok(path) => {
            assert!(path.is_absolute(), "Registry path should be absolute");
        }
        Err(GamePathError::RegistryNotFound) => {
            // Expected if game not installed
        }
        Err(e) => {
            panic!("Unexpected error: {}", e);
        }
    }
}

#[test]
/// Verifies Documents lookup reports the host registry outcome without assuming a user profile.
fn test_get_documents_path_reports_host_registry_outcome() {
    match get_documents_path() {
        Ok(path) => {
            assert!(path.is_absolute(), "Documents path should be absolute");
        }
        Err(DocsPathError::RegistryError(message)) => {
            // Service and sandbox accounts may not have a resolvable Personal registry value.
            assert!(!message.is_empty(), "registry errors should retain context");
        }
        Err(e) => {
            panic!("Unexpected documents path error: {e}");
        }
    }
}
