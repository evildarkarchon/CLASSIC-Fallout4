use super::*;
use std::fs;
use tempfile::TempDir;

fn create_test_ini(temp_dir: &Path, name: &str, content: &str) -> PathBuf {
    let ini_path = temp_dir.join(name);
    fs::write(&ini_path, content).unwrap();
    ini_path
}

#[test]
fn test_load_ini() {
    let temp_dir = TempDir::new().unwrap();
    let ini_content = "[Display]\niSize W=1920\niSize H=1080\n";
    let ini_path = create_test_ini(temp_dir.path(), "test.ini", ini_content);

    let ini = IniFile::load(&ini_path);
    assert!(ini.is_ok());
}

#[test]
fn test_load_nonexistent() {
    let result = IniFile::load(Path::new("nonexistent.ini"));
    assert!(result.is_err());
    match result {
        Err(DocsPathError::IniParseError { reason, .. }) => {
            assert!(reason.contains("does not exist"));
        }
        _ => panic!("Expected IniParseError"),
    }
}

#[test]
fn test_has_section() {
    let temp_dir = TempDir::new().unwrap();
    let ini_content = "[Display]\nkey=value\n[Archive]\nother=val\n";
    let ini_path = create_test_ini(temp_dir.path(), "test.ini", ini_content);

    let ini = IniFile::load(&ini_path).unwrap();
    assert!(ini.has_section("Display"));
    assert!(ini.has_section("display")); // Case-insensitive
    assert!(ini.has_section("Archive"));
    assert!(!ini.has_section("NonExistent"));
}

#[test]
fn test_has_key() {
    let temp_dir = TempDir::new().unwrap();
    let ini_content = "[Display]\niSize W=1920\niSize H=1080\n";
    let ini_path = create_test_ini(temp_dir.path(), "test.ini", ini_content);

    let ini = IniFile::load(&ini_path).unwrap();
    assert!(ini.has_key("Display", "iSize W"));
    assert!(ini.has_key("display", "iSize W")); // Case-insensitive section
    assert!(!ini.has_key("Display", "NonExistent"));
}

#[test]
fn test_get_value() {
    let temp_dir = TempDir::new().unwrap();
    let ini_content = "[Display]\niSize W=1920\niSize H=1080\n";
    let ini_path = create_test_ini(temp_dir.path(), "test.ini", ini_content);

    let ini = IniFile::load(&ini_path).unwrap();
    assert_eq!(ini.get("Display", "iSize W"), Some("1920".to_string()));
    assert_eq!(ini.get("display", "iSize W"), Some("1920".to_string())); // Case-insensitive
    assert_eq!(ini.get("Display", "NonExistent"), None);
}

#[test]
fn test_get_int() {
    let temp_dir = TempDir::new().unwrap();
    let ini_content = "[Display]\niSize W=1920\ninvalid=abc\n";
    let ini_path = create_test_ini(temp_dir.path(), "test.ini", ini_content);

    let ini = IniFile::load(&ini_path).unwrap();
    assert_eq!(ini.get_int("Display", "iSize W"), Some(1920));
    assert_eq!(ini.get_int("Display", "invalid"), None);
    assert_eq!(ini.get_int("Display", "NonExistent"), None);
}

#[test]
fn test_get_bool() {
    let temp_dir = TempDir::new().unwrap();
    let ini_content =
        "[Archive]\nbInvalidateOlderFiles=1\nbUseArchives=0\ntrue_val=true\nfalse_val=false\n";
    let ini_path = create_test_ini(temp_dir.path(), "test.ini", ini_content);

    let ini = IniFile::load(&ini_path).unwrap();
    assert_eq!(ini.get_bool("Archive", "bInvalidateOlderFiles"), Some(true));
    assert_eq!(ini.get_bool("Archive", "bUseArchives"), Some(false));
    assert_eq!(ini.get_bool("Archive", "true_val"), Some(true));
    assert_eq!(ini.get_bool("Archive", "false_val"), Some(false));
}

#[test]
fn test_sections() {
    let temp_dir = TempDir::new().unwrap();
    let ini_content = "[Display]\nkey=val\n[Archive]\nkey2=val2\n[General]\nkey3=val3\n";
    let ini_path = create_test_ini(temp_dir.path(), "test.ini", ini_content);

    let ini = IniFile::load(&ini_path).unwrap();
    let sections = ini.sections();

    // configparser normalizes section names to lowercase
    assert_eq!(sections.len(), 3);
    assert!(sections.contains(&"display".to_string()));
    assert!(sections.contains(&"archive".to_string()));
    assert!(sections.contains(&"general".to_string()));
}

#[test]
fn test_keys() {
    let temp_dir = TempDir::new().unwrap();
    let ini_content = "[Display]\niSize W=1920\niSize H=1080\nbFull Screen=0\n";
    let ini_path = create_test_ini(temp_dir.path(), "test.ini", ini_content);

    let ini = IniFile::load(&ini_path).unwrap();
    let keys = ini.keys("Display");

    // configparser normalizes both section and key names to lowercase
    assert_eq!(keys.len(), 3);
    assert!(keys.contains(&"isize w".to_string()));
    assert!(keys.contains(&"isize h".to_string()));
    assert!(keys.contains(&"bfull screen".to_string()));
}

#[test]
fn test_validate_sections() {
    let temp_dir = TempDir::new().unwrap();
    let ini_content = "[Display]\nkey=val\n[Archive]\nkey2=val2\n";
    let ini_path = create_test_ini(temp_dir.path(), "test.ini", ini_content);

    let ini = IniFile::load(&ini_path).unwrap();

    // Should succeed
    assert!(ini.validate_sections(&["Display", "Archive"]).is_ok());

    // Should fail
    let result = ini.validate_sections(&["Display", "NonExistent"]);
    assert!(result.is_err());
    match result {
        Err(DocsPathError::IniValidationFailed { reason, .. }) => {
            assert!(reason.contains("NonExistent"));
        }
        _ => panic!("Expected IniValidationFailed"),
    }
}

#[test]
fn test_validate_keys() {
    let temp_dir = TempDir::new().unwrap();
    let ini_content = "[Display]\niSize W=1920\niSize H=1080\n";
    let ini_path = create_test_ini(temp_dir.path(), "test.ini", ini_content);

    let ini = IniFile::load(&ini_path).unwrap();

    // Should succeed
    assert!(
        ini.validate_keys("Display", &["iSize W", "iSize H"])
            .is_ok()
    );

    // Should fail - missing key
    let result = ini.validate_keys("Display", &["iSize W", "NonExistent"]);
    assert!(result.is_err());

    // Should fail - missing section
    let result = ini.validate_keys("NonExistent", &["key"]);
    assert!(result.is_err());
}
