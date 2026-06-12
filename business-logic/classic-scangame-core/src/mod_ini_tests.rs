use super::*;
use std::fs;
use tempfile::TempDir;

/// Helper: create a game root with files
fn setup_game_root(files: &[(&str, &str)]) -> TempDir {
    let temp = TempDir::new().unwrap();
    for (name, content) in files {
        fs::write(temp.path().join(name), content).unwrap();
    }
    temp
}

#[test]
fn test_scan_empty_directory() {
    let root = setup_game_root(&[]);
    let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();

    assert!(result.message.is_empty());
    assert!(result.issues.is_empty());
    assert!(result.vsync_files.is_empty());
    assert!(result.duplicates.is_empty());
}

#[test]
fn test_console_command_detection() {
    let root = setup_game_root(&[(
        "fallout4.ini",
        "[General]\nsStartingConsoleCommand=bat autoexec\n",
    )]);

    let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();
    assert!(result.message.contains("sStartingConsoleCommand"));
}

#[test]
fn test_vsync_detection() {
    let root = setup_game_root(&[("enblocal.ini", "[ENGINE]\nForceVSync=true\n")]);

    let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();
    assert_eq!(result.vsync_files.len(), 1);
    assert_eq!(result.vsync_files[0].setting, "ForceVSync");
    assert!(result.message.contains("VSYNC"));
}

#[test]
fn test_vsync_highfps_separate() {
    let root = setup_game_root(&[(
        "highfpsphysicsfix.ini",
        "[Main]\nEnableVSync=true\n[Limiter]\nLoadingScreenFPS=600.0\n",
    )]);

    let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();
    assert_eq!(result.vsync_files.len(), 1);
    assert_eq!(result.vsync_files[0].setting, "EnableVSync");
}

#[test]
fn test_epo_particle_issue() {
    let root = setup_game_root(&[("epo.ini", "[Particles]\niMaxDesired=10000\n")]);

    let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();
    assert_eq!(result.issues.len(), 1);
    assert_eq!(result.issues[0].setting, "iMaxDesired");
    assert_eq!(result.issues[0].recommended_value, "5000");
}

#[test]
fn test_epo_particle_ok() {
    let root = setup_game_root(&[("epo.ini", "[Particles]\niMaxDesired=3000\n")]);

    let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();
    assert!(result.issues.is_empty());
}

#[test]
fn test_f4ee_issues() {
    let root = setup_game_root(&[(
        "f4ee.ini",
        "[CharGen]\nbUnlockHeadParts=0\nbUnlockTints=0\n",
    )]);

    let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();
    assert_eq!(result.issues.len(), 2);
    assert!(
        result
            .issues
            .iter()
            .any(|i| i.setting == "bUnlockHeadParts")
    );
    assert!(result.issues.iter().any(|i| i.setting == "bUnlockTints"));
}

#[test]
fn test_f4ee_no_issues_when_unlocked() {
    let root = setup_game_root(&[(
        "f4ee.ini",
        "[CharGen]\nbUnlockHeadParts=1\nbUnlockTints=1\n",
    )]);

    let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();
    assert!(result.issues.is_empty());
}

#[test]
fn test_highfps_loading_fps_issue() {
    let root = setup_game_root(&[(
        "highfpsphysicsfix.ini",
        "[Limiter]\nLoadingScreenFPS=120.0\n",
    )]);

    let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();
    assert_eq!(result.issues.len(), 1);
    assert_eq!(result.issues[0].setting, "LoadingScreenFPS");
}

#[test]
fn test_espexplorer_hotkey_issue() {
    let root = setup_game_root(&[("espexplorer.ini", "[General]\nHotKey=; F10\n")]);

    let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();
    assert_eq!(result.issues.len(), 1);
    assert_eq!(result.issues[0].setting, "HotKey");
    assert_eq!(result.issues[0].recommended_value, "0x79");
}

#[test]
fn test_multiple_issues_combined() {
    let root = setup_game_root(&[
        ("epo.ini", "[Particles]\niMaxDesired=10000\n"),
        ("f4ee.ini", "[CharGen]\nbUnlockHeadParts=0\n"),
        ("enblocal.ini", "[ENGINE]\nForceVSync=true\n"),
        (
            "fallout4.ini",
            "[General]\nsStartingConsoleCommand=bat autoexec\n",
        ),
    ]);

    let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();

    // 2 issues: EPO particle + F4EE head parts
    assert_eq!(result.issues.len(), 2);
    // 1 VSync entry
    assert_eq!(result.vsync_files.len(), 1);
    // Console command in message
    assert!(result.message.contains("sStartingConsoleCommand"));
    assert!(result.message.contains("VSYNC"));
}

#[test]
fn test_nonexistent_game_root() {
    let result = ModIniScanner::scan(Path::new("/nonexistent"), "Fallout4");
    assert!(result.is_err());
}

#[test]
fn test_duplicate_files() {
    // The ModIniScanner uses "F4EE" whitelist for duplicate detection,
    // so we need directories/files that match this pattern
    let root = TempDir::new().unwrap();
    let sub1 = root.path().join("F4EE");
    let sub2 = root.path().join("other_F4EE");
    fs::create_dir(&sub1).unwrap();
    fs::create_dir(&sub2).unwrap();

    let content = "[Section]\nkey=value\n";
    fs::write(sub1.join("test.ini"), content).unwrap();
    fs::write(sub2.join("test.ini"), content).unwrap();

    let result = ModIniScanner::scan(root.path(), "Fallout4").unwrap();
    assert!(!result.duplicates.is_empty());
    assert!(result.message.contains("DUPLICATES"));
}
