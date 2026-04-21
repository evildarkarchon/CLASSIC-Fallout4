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
fn test_get_documents_path() {
    // Documents path should always exist on Windows
    let result = get_documents_path();

    match result {
        Ok(path) => {
            assert!(path.is_absolute(), "Documents path should be absolute");
            // Documents path should exist
            assert!(
                path.exists(),
                "Documents path should exist: {}",
                path.display()
            );
        }
        Err(e) => {
            panic!("Failed to get documents path: {}", e);
        }
    }
}
