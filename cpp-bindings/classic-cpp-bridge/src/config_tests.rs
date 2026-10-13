use super::*;
use tempfile::tempdir;

#[test]
fn test_save_local_yaml_paths_creates_file() {
    let temp = tempdir().expect("failed to create temp dir");
    let local_yaml_path = temp
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Fallout4 Local.yaml");

    save_local_yaml_paths(
        &local_yaml_path.to_string_lossy(),
        "C:/Games/Fallout4",
        "C:/Users/Test/Documents/My Games/Fallout4",
    )
    .expect("save_local_yaml_paths should succeed");

    let yaml = classic_shared_core::yaml::YamlOperations::new()
        .load_yaml_file(&local_yaml_path)
        .expect("load local yaml");
    assert_eq!(
        yaml["Game_Info"]["Root_Folder_Game"].as_str(),
        Some("C:/Games/Fallout4")
    );
    assert_eq!(
        yaml["Game_Info"]["Root_Folder_Docs"].as_str(),
        Some("C:/Users/Test/Documents/My Games/Fallout4")
    );
}

#[test]
fn test_save_local_yaml_paths_preserves_empty_adapter_field() {
    let temp = tempdir().expect("failed to create temp dir");
    let local_yaml_path = temp
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Fallout4 Local.yaml");

    std::fs::create_dir_all(local_yaml_path.parent().expect("local YAML parent"))
        .expect("create local YAML parent");
    std::fs::write(
        &local_yaml_path,
        concat!(
            "Game_Info:\n",
            "  Root_Folder_Docs: C:/Users/Test/Documents/Existing\n",
            "  Docs_Folder_XSE: C:/Users/Test/Documents/Existing/F4SE\n",
        ),
    )
    .expect("seed local YAML");

    save_local_yaml_paths(&local_yaml_path.to_string_lossy(), "D:/Games/Fallout4", "")
        .expect("save_local_yaml_paths should preserve an unset docs path");

    let yaml = classic_shared_core::yaml::YamlOperations::new()
        .load_yaml_file(&local_yaml_path)
        .expect("load local YAML");
    assert_eq!(
        yaml["Game_Info"]["Root_Folder_Game"].as_str(),
        Some("D:/Games/Fallout4")
    );
    assert_eq!(
        yaml["Game_Info"]["Root_Folder_Docs"].as_str(),
        Some("C:/Users/Test/Documents/Existing")
    );
    assert_eq!(
        yaml["Game_Info"]["Docs_Folder_XSE"].as_str(),
        Some("C:/Users/Test/Documents/Existing/F4SE")
    );
}

#[test]
/// Empty strings stand for an absent input and for "no Installation Root" at the CXX boundary.
fn installation_root_bridge_uses_empty_strings_for_absent_inputs_and_no_match() {
    let layout = tempdir().unwrap();
    let executable_dir = layout.path().join("build").join("bin");
    let working_dir = layout.path().join("work");
    std::fs::create_dir_all(&executable_dir).unwrap();
    std::fs::create_dir_all(&working_dir).unwrap();
    let executable = executable_dir.to_str().unwrap();
    let working = working_dir.to_str().unwrap();

    assert_eq!(locate_installation_root(executable, working), "");

    // The grandparent (a development build output folder's repository root) is candidate 4.
    std::fs::create_dir(layout.path().join("CLASSIC Data")).unwrap();
    assert_eq!(
        locate_installation_root(executable, working),
        layout.path().to_str().unwrap()
    );

    // An empty executable folder skips every executable-derived candidate.
    assert_eq!(locate_installation_root("", working), "");

    std::fs::create_dir(working_dir.join("CLASSIC Data")).unwrap();
    assert_eq!(locate_installation_root("", working), working);
}
