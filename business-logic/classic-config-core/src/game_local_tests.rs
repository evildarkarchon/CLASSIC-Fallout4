use super::persist_game_local_paths;
use classic_settings_core::load_yaml_merged_async;
use std::path::Path;
use tempfile::tempdir;

#[tokio::test]
async fn persist_game_local_paths_creates_missing_file_with_both_paths() {
    let temp_dir = tempdir().unwrap();
    let local_yaml_path = temp_dir
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Fallout4 Local.yaml");

    persist_game_local_paths(
        &local_yaml_path,
        Some(Path::new("C:/Games/Fallout4")),
        Some(Path::new("C:/Users/Test/Documents/My Games/Fallout4")),
    )
    .await
    .unwrap();

    let yaml = load_yaml_merged_async(&local_yaml_path).await.unwrap();
    assert_eq!(
        yaml["Game_Info"]["Root_Folder_Game"].as_str(),
        Some("C:/Games/Fallout4")
    );
    assert_eq!(
        yaml["Game_Info"]["Root_Folder_Docs"].as_str(),
        Some("C:/Users/Test/Documents/My Games/Fallout4")
    );
}

#[tokio::test]
async fn persist_game_local_paths_updates_supplied_path_and_preserves_other_documents() {
    let temp_dir = tempdir().unwrap();
    let local_yaml_path = temp_dir
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Fallout4 Local.yaml");
    let user_settings_path = temp_dir.path().join("CLASSIC Settings.yaml");
    let user_settings_sentinel = b"{ malformed user settings that must stay untouched";

    std::fs::create_dir_all(local_yaml_path.parent().unwrap()).unwrap();
    std::fs::write(
        &local_yaml_path,
        concat!(
            "Unrelated_Root:\n",
            "  Keep_Me: true\n",
            "Game_Info:\n",
            "  Root_Folder_Game: C:/Games/Old\n",
            "  Root_Folder_Docs: C:/Users/Test/Documents/Old\n",
            "  Docs_Folder_XSE: C:/Users/Test/Documents/Old/F4SE\n",
        ),
    )
    .unwrap();
    std::fs::write(&user_settings_path, user_settings_sentinel).unwrap();

    persist_game_local_paths(&local_yaml_path, Some(Path::new("D:/Games/Fallout4")), None)
        .await
        .unwrap();

    let yaml = load_yaml_merged_async(&local_yaml_path).await.unwrap();
    assert_eq!(
        yaml["Game_Info"]["Root_Folder_Game"].as_str(),
        Some("D:/Games/Fallout4")
    );
    assert_eq!(
        yaml["Game_Info"]["Root_Folder_Docs"].as_str(),
        Some("C:/Users/Test/Documents/Old")
    );
    assert_eq!(
        yaml["Game_Info"]["Docs_Folder_XSE"].as_str(),
        Some("C:/Users/Test/Documents/Old/F4SE")
    );
    assert_eq!(yaml["Unrelated_Root"]["Keep_Me"].as_bool(), Some(true));
    assert_eq!(
        std::fs::read(user_settings_path).unwrap(),
        user_settings_sentinel
    );
}

#[tokio::test]
async fn persist_game_local_paths_with_no_updates_does_not_create_file() {
    let temp_dir = tempdir().unwrap();
    let local_yaml_path = temp_dir
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Fallout4 Local.yaml");

    persist_game_local_paths(&local_yaml_path, None, None)
        .await
        .unwrap();

    assert!(!local_yaml_path.exists());
}
