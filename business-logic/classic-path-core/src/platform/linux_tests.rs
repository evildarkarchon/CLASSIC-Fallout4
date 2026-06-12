use super::*;

#[test]
fn test_parse_vdf_content() {
    let vdf_content = r#"
"libraryfolders"
{
    "0"
    {
        "path"    "/home/user/.local/share/Steam"
        "label"   ""
        "apps"
        {
            "377160"    "12345"
            "489830"    "67890"
        }
    }
    "1"
    {
        "path"    "/mnt/games/SteamLibrary"
        "label"   "Games"
        "apps"
        {
            "22380"     "111111"
        }
    }
}
"#;

    // Test finding Fallout 4 (377160)
    let result = parse_vdf_content(vdf_content, 377160);
    assert!(result.is_ok());
    assert_eq!(
        result.unwrap(),
        PathBuf::from("/home/user/.local/share/Steam")
    );

    // Test finding Skyrim SE (489830)
    let result = parse_vdf_content(vdf_content, 489830);
    assert!(result.is_ok());
    assert_eq!(
        result.unwrap(),
        PathBuf::from("/home/user/.local/share/Steam")
    );

    // Test finding Fallout 3 (22380) in second library
    let result = parse_vdf_content(vdf_content, 22380);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), PathBuf::from("/mnt/games/SteamLibrary"));

    // Test game not in library
    let result = parse_vdf_content(vdf_content, 999999);
    assert!(result.is_err());
    match result {
        Err(DocsPathError::GameNotInSteamLibrary(id)) => assert_eq!(id, 999999),
        _ => panic!("Expected GameNotInSteamLibrary error"),
    }
}

#[test]
fn test_extract_vdf_value() {
    assert_eq!(
        extract_vdf_value(r#""path"    "/home/user/Steam""#),
        Some("/home/user/Steam".to_string())
    );

    assert_eq!(
        extract_vdf_value(r#""label"   "Games Drive""#),
        Some("Games Drive".to_string())
    );

    assert_eq!(
        extract_vdf_value(r#""377160"    "12345""#),
        Some("12345".to_string())
    );

    // Invalid format
    assert_eq!(extract_vdf_value("invalid"), None);
}

#[test]
fn test_construct_proton_docs_path() {
    let library = PathBuf::from("/home/user/.local/share/Steam");
    let docs_path = construct_proton_docs_path(&library, 377160, "My Games/Fallout4");

    let expected = PathBuf::from(
        "/home/user/.local/share/Steam/steamapps/compatdata/377160/pfx/drive_c/users/steamuser/My Documents/My Games/Fallout4",
    );

    assert_eq!(docs_path, expected);
}

#[test]
fn test_get_home_directory() {
    // Home directory should exist on Linux
    let result = get_home_directory();
    assert!(result.is_ok());

    let home = result.unwrap();
    assert!(home.is_absolute());
}
