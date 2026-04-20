use super::*;
use serial_test::serial;
use tempfile::TempDir;

#[tokio::test]
#[serial]
async fn test_generate_ignore_file() {
    let temp_dir = TempDir::new().unwrap();
    let original_dir = std::env::current_dir().unwrap();

    // Change to temp directory for test
    std::env::set_current_dir(&temp_dir).unwrap();

    let config = FileGeneratorConfig::new(
        "# Test ignore file\n*.tmp".to_string(),
        "# Test local yaml".to_string(),
        "TestGame".to_string(),
    );

    let generator = FileGenerator::new(config);

    // First generation should succeed
    let result = generator.generate_ignore_file_async().await.unwrap();
    assert!(result, "File should be generated on first call");

    // Verify file exists and has correct content
    let ignore_path = PathBuf::from("CLASSIC Ignore.yaml");
    assert!(ignore_path.exists());
    let content = fs::read_to_string(&ignore_path).await.unwrap();
    assert_eq!(content, "# Test ignore file\n*.tmp");

    // Second generation should return false (file already exists)
    let result = generator.generate_ignore_file_async().await.unwrap();
    assert!(!result, "File should not be regenerated");

    // Restore original directory
    std::env::set_current_dir(original_dir).unwrap();
}

#[tokio::test]
#[serial]
async fn test_generate_local_yaml() {
    let temp_dir = TempDir::new().unwrap();
    let original_dir = std::env::current_dir().unwrap();

    // Change to temp directory for test
    std::env::set_current_dir(&temp_dir).unwrap();

    let config = FileGeneratorConfig::new(
        "# Test ignore".to_string(),
        "# Test local yaml\ngame: TestGame".to_string(),
        "TestGame".to_string(),
    );

    let generator = FileGenerator::new(config);

    // First generation should succeed
    let result = generator.generate_local_yaml_async().await.unwrap();
    assert!(result, "File should be generated on first call");

    // Verify file exists and has correct content
    let local_path = PathBuf::from("CLASSIC Data/CLASSIC TestGame Local.yaml");
    assert!(local_path.exists());
    let content = fs::read_to_string(&local_path).await.unwrap();
    assert_eq!(content, "# Test local yaml\ngame: TestGame");

    // Verify parent directory was created
    assert!(local_path.parent().unwrap().exists());

    // Second generation should return false (file already exists)
    let result = generator.generate_local_yaml_async().await.unwrap();
    assert!(!result, "File should not be regenerated");

    // Restore original directory
    std::env::set_current_dir(original_dir).unwrap();
}

#[tokio::test]
#[serial]
async fn test_generate_all_files() {
    let temp_dir = TempDir::new().unwrap();
    let original_dir = std::env::current_dir().unwrap();

    // Change to temp directory for test
    std::env::set_current_dir(&temp_dir).unwrap();

    let config = FileGeneratorConfig::new(
        "# Test ignore file".to_string(),
        "# Test local yaml".to_string(),
        "TestGame".to_string(),
    );

    let generator = FileGenerator::new(config);

    // Generate all files
    let (ignore_generated, local_generated) = generator.generate_all_files_async().await.unwrap();

    assert!(ignore_generated, "Ignore file should be generated");
    assert!(local_generated, "Local YAML should be generated");

    // Verify both files exist
    assert!(PathBuf::from("CLASSIC Ignore.yaml").exists());
    assert!(PathBuf::from("CLASSIC Data/CLASSIC TestGame Local.yaml").exists());

    // Second generation should return false for both
    let (ignore_generated, local_generated) = generator.generate_all_files_async().await.unwrap();

    assert!(!ignore_generated, "Ignore file should not be regenerated");
    assert!(!local_generated, "Local YAML should not be regenerated");

    // Restore original directory
    std::env::set_current_dir(original_dir).unwrap();
}

#[tokio::test]
#[serial]
async fn test_standalone_functions() {
    let temp_dir = TempDir::new().unwrap();
    let original_dir = std::env::current_dir().unwrap();

    // Change to temp directory for test
    std::env::set_current_dir(&temp_dir).unwrap();

    // Test standalone generate_ignore_file
    let result = generate_ignore_file("# Standalone test").await.unwrap();
    assert!(result);
    assert!(PathBuf::from("CLASSIC Ignore.yaml").exists());

    // Test standalone generate_local_yaml
    let result = generate_local_yaml("# Local test", "StandaloneGame")
        .await
        .unwrap();
    assert!(result);
    assert!(PathBuf::from("CLASSIC Data/CLASSIC StandaloneGame Local.yaml").exists());

    // Restore original directory
    std::env::set_current_dir(original_dir).unwrap();
}

#[tokio::test]
async fn test_file_paths() {
    let config = FileGeneratorConfig::new(
        "content".to_string(),
        "content".to_string(),
        "TestGame".to_string(),
    );

    let generator = FileGenerator::new(config);

    assert_eq!(
        generator.ignore_file_path(),
        PathBuf::from("CLASSIC Ignore.yaml")
    );
    assert_eq!(
        generator.local_yaml_path(),
        PathBuf::from("CLASSIC Data/CLASSIC TestGame Local.yaml")
    );
}
