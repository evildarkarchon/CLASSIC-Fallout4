use super::{
    GameLocalFacts, game_local_yaml_path, persist_game_local_paths, read_game_local_facts,
};
use classic_shared_core::yaml::load_yaml_merged_async;
use std::path::{Path, PathBuf};
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

fn write_game_local(game: &str, contents: &str) -> tempfile::TempDir {
    let temp_dir = tempdir().unwrap();
    let data = temp_dir.path().join("CLASSIC Data");
    std::fs::create_dir_all(&data).unwrap();
    std::fs::write(data.join(format!("CLASSIC {game} Local.yaml")), contents).unwrap();
    temp_dir
}

#[test]
fn game_local_yaml_path_names_the_per_game_document_in_the_data_dir() {
    assert_eq!(
        game_local_yaml_path(Path::new("CLASSIC Data"), "Fallout4"),
        PathBuf::from("CLASSIC Data/CLASSIC Fallout4 Local.yaml")
    );
    // Unlike the shared game database, Fallout 4 VR keeps its own Local file.
    assert_eq!(
        game_local_yaml_path(Path::new("CLASSIC Data"), "Fallout4VR"),
        PathBuf::from("CLASSIC Data/CLASSIC Fallout4VR Local.yaml")
    );
    assert_eq!(
        game_local_yaml_path(Path::new("CLASSIC Data"), "Fallout4"),
        crate::YamlSource::GameLocal.path("Fallout4")
    );
}

#[test]
fn read_game_local_facts_reports_recorded_folders() {
    let temp_dir = write_game_local(
        "Fallout4",
        r#"
Game_Info:
  Root_Folder_Game: C:\Games\Fallout4
  Root_Folder_Docs: C:\Users\Test\Documents\My Games\Fallout4
  Docs_Folder_XSE: C:\Users\Test\Documents\My Games\Fallout4\CustomXSE
"#,
    );

    let facts = read_game_local_facts(&temp_dir.path().join("CLASSIC Data"), "Fallout4");

    assert_eq!(
        facts,
        GameLocalFacts {
            root_folder_game: Some(PathBuf::from(r"C:\Games\Fallout4")),
            root_folder_docs: Some(PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4")),
            docs_folder_xse: Some(PathBuf::from(
                r"C:\Users\Test\Documents\My Games\Fallout4\CustomXSE"
            )),
        }
    );
}

#[test]
fn read_game_local_facts_trims_values_and_treats_blank_as_absent() {
    let temp_dir = write_game_local(
        "Fallout4",
        "Game_Info:\n  Root_Folder_Game: \"  C:/Games/Fallout4  \"\n  Root_Folder_Docs: \"   \"\n  Docs_Folder_XSE: \"\"\n",
    );

    let facts = read_game_local_facts(&temp_dir.path().join("CLASSIC Data"), "Fallout4");

    assert_eq!(
        facts,
        GameLocalFacts {
            root_folder_game: Some(PathBuf::from("C:/Games/Fallout4")),
            root_folder_docs: None,
            docs_folder_xse: None,
        }
    );
}

#[test]
fn read_game_local_facts_ignores_non_string_values() {
    let temp_dir = write_game_local(
        "Fallout4",
        "Game_Info:\n  Root_Folder_Game: 42\n  Root_Folder_Docs: [a, b]\n  Docs_Folder_XSE: true\n",
    );

    let facts = read_game_local_facts(&temp_dir.path().join("CLASSIC Data"), "Fallout4");

    assert_eq!(facts, GameLocalFacts::default());
}

#[test]
fn read_game_local_facts_is_fail_soft_for_missing_or_malformed_documents() {
    let missing = tempdir().unwrap();
    assert_eq!(
        read_game_local_facts(&missing.path().join("CLASSIC Data"), "Fallout4"),
        GameLocalFacts::default()
    );

    let malformed = write_game_local("Fallout4", "Game_Info: [unclosed\n");
    assert_eq!(
        read_game_local_facts(&malformed.path().join("CLASSIC Data"), "Fallout4"),
        GameLocalFacts::default()
    );
}

#[test]
fn read_game_local_facts_reads_only_the_named_game() {
    let temp_dir = write_game_local(
        "Fallout4",
        "Game_Info:\n  Root_Folder_Docs: C:/Docs/Fallout4\n",
    );

    let facts = read_game_local_facts(&temp_dir.path().join("CLASSIC Data"), "Fallout4VR");

    assert_eq!(facts, GameLocalFacts::default());
}

#[tokio::test]
async fn persisted_paths_read_back_as_game_local_facts() {
    let temp_dir = tempdir().unwrap();
    let data = temp_dir.path().join("CLASSIC Data");

    persist_game_local_paths(
        &game_local_yaml_path(&data, "Fallout4"),
        Some(Path::new("C:/Games/Fallout4")),
        Some(Path::new("C:/Users/Test/Documents/My Games/Fallout4")),
    )
    .await
    .unwrap();

    let facts = read_game_local_facts(&data, "Fallout4");
    assert_eq!(
        facts.root_folder_game.as_deref(),
        Some(Path::new("C:/Games/Fallout4"))
    );
    assert_eq!(
        facts.root_folder_docs.as_deref(),
        Some(Path::new("C:/Users/Test/Documents/My Games/Fallout4"))
    );
    assert_eq!(facts.docs_folder_xse, None);
}
