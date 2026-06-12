use super::*;
use std::fs;
use tempfile::TempDir;

#[test]
fn test_validator_creation() {
    let validator = IniValidator::new("Fallout4");
    assert_eq!(validator.game_name, "Fallout4");
    assert_eq!(validator.vsync_settings.len(), 5);
}

#[test]
fn test_console_command_detection() {
    let temp_dir = TempDir::new().unwrap();
    let ini_file = temp_dir.path().join("fallout4.ini");

    fs::write(
        &ini_file,
        "[General]\nsStartingConsoleCommand=bat autoexec\n",
    )
    .unwrap();

    let mut validator = IniValidator::new("Fallout4");
    validator.load_ini(&ini_file).unwrap();

    let mut config_files = HashMap::new();
    config_files.insert("fallout4.ini".to_string(), ini_file.clone());

    let messages = validator.check_console_command(&config_files);
    assert!(!messages.is_empty());
    assert!(messages[0].contains("sStartingConsoleCommand"));
}

#[test]
fn test_vsync_detection() {
    let temp_dir = TempDir::new().unwrap();
    let ini_file = temp_dir.path().join("enblocal.ini");

    fs::write(&ini_file, "[ENGINE]\nForceVSync=true\n").unwrap();

    let mut validator = IniValidator::new("Fallout4");
    validator.load_ini(&ini_file).unwrap();

    let mut config_files = HashMap::new();
    config_files.insert("enblocal.ini".to_string(), ini_file.clone());

    let vsync_list = validator.check_vsync_settings(&config_files);
    assert!(!vsync_list.is_empty());
    assert!(vsync_list[0].contains("ForceVSync"));
}

#[test]
fn test_issue_detection_epo() {
    let temp_dir = TempDir::new().unwrap();
    let ini_file = temp_dir.path().join("epo.ini");

    fs::write(&ini_file, "[Particles]\niMaxDesired=10000\n").unwrap();

    let mut validator = IniValidator::new("Fallout4");
    validator.load_ini(&ini_file).unwrap();

    let mut config_files = HashMap::new();
    config_files.insert("epo.ini".to_string(), ini_file.clone());

    let issues = validator.detect_all_issues(&config_files);
    assert!(!issues.is_empty());
    assert_eq!(issues[0].setting, "iMaxDesired");
    assert_eq!(issues[0].recommended_value, "5000");
}

#[test]
fn test_issue_detection_f4ee() {
    let temp_dir = TempDir::new().unwrap();
    let ini_file = temp_dir.path().join("f4ee.ini");

    fs::write(&ini_file, "[CharGen]\nbUnlockHeadParts=0\nbUnlockTints=0\n").unwrap();

    let mut validator = IniValidator::new("Fallout4");
    validator.load_ini(&ini_file).unwrap();

    let mut config_files = HashMap::new();
    config_files.insert("f4ee.ini".to_string(), ini_file.clone());

    let issues = validator.detect_all_issues(&config_files);
    assert_eq!(issues.len(), 2);
    assert!(issues.iter().any(|i| i.setting == "bUnlockHeadParts"));
    assert!(issues.iter().any(|i| i.setting == "bUnlockTints"));
}
