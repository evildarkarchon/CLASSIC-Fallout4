//! Integration proof for Linux Proton documents-path selection.

use classic_path_core::{DocsPathError, DocsPathFinder};
use std::fs;
use std::path::{Path, PathBuf};
use tempfile::TempDir;

fn create_directory(path: &Path) {
    fs::create_dir_all(path).unwrap();
}

fn local_share(home: &Path, relative_path: &str) -> PathBuf {
    home.join(".local/share").join(relative_path)
}

fn proton_docs_root(steam_library: &Path, relative_path: &str) -> PathBuf {
    steam_library
        .join("steamapps/compatdata/377160/pfx/drive_c/users/steamuser/My Documents")
        .join(relative_path)
}

#[test]
fn proton_docs_path_wins_over_valid_local_share() {
    let temp_dir = TempDir::new().unwrap();
    let home = temp_dir.path();
    let relative_path = "My Games/Fallout4";
    let steam_library = home.join("steam-library");
    let proton_path = proton_docs_root(&steam_library, relative_path);
    let local_share_path = local_share(home, relative_path);

    create_directory(&proton_path);
    create_directory(&local_share_path);

    let finder = DocsPathFinder::new(relative_path).with_steam_app_id(377160);
    let result = finder.find_docs_path_linux_with(home, Ok(steam_library));

    assert_eq!(result.unwrap(), proton_path);
}

#[test]
fn steam_lookup_failure_proton_falls_back_to_local_share() {
    let temp_dir = TempDir::new().unwrap();
    let home = temp_dir.path();
    let relative_path = "My Games/Fallout4";
    let local_share_path = local_share(home, relative_path);

    create_directory(&local_share_path);

    let finder = DocsPathFinder::new(relative_path).with_steam_app_id(377160);
    let result = finder.find_docs_path_linux_with(home, Err(DocsPathError::NotFound));

    assert_eq!(result.unwrap(), local_share_path);
}

#[test]
fn invalid_proton_docs_path_falls_back_to_local_share() {
    let temp_dir = TempDir::new().unwrap();
    let home = temp_dir.path();
    let relative_path = "My Games/Fallout4";
    let steam_library = home.join("steam-library");
    let local_share_path = local_share(home, relative_path);

    create_directory(&steam_library);
    create_directory(&local_share_path);

    let finder = DocsPathFinder::new(relative_path).with_steam_app_id(377160);
    let result = finder.find_docs_path_linux_with(home, Ok(steam_library));

    assert_eq!(result.unwrap(), local_share_path);
}

#[test]
fn legacy_local_share_regression_still_works_without_proton() {
    let temp_dir = TempDir::new().unwrap();
    let home = temp_dir.path();
    let relative_path = "My Games/Fallout4";
    let local_share_path = local_share(home, relative_path);

    create_directory(&local_share_path);

    let finder = DocsPathFinder::new(relative_path).with_steam_app_id(377160);
    let result = finder.find_docs_path_linux_with(
        home,
        Err(DocsPathError::SteamLibraryNotFound(
            home.join(".local/share/Steam/steamapps/libraryfolders.vdf"),
        )),
    );

    assert_eq!(result.unwrap(), local_share_path);
}

#[test]
fn proton_path_ignored_when_steam_app_id_unset() {
    // When the caller does NOT opt in via with_steam_app_id, the Proton
    // compatdata lookup must be skipped entirely, even if a valid Proton
    // FO4 docs dir is present on disk. The finder must return the
    // local-share path instead.
    let temp_dir = TempDir::new().unwrap();
    let home = temp_dir.path();
    let relative_path = "My Games/Fallout4";
    let steam_library = home.join("steam-library");
    let proton_path = proton_docs_root(&steam_library, relative_path);
    let local_share_path = local_share(home, relative_path);

    // Create BOTH paths on disk. Before the fix, the Proton path would
    // win. After the fix, with no Steam app ID opt-in, the local-share
    // path must win.
    create_directory(&proton_path);
    create_directory(&local_share_path);

    // NO .with_steam_app_id call -- default-constructed finder.
    let finder = DocsPathFinder::new(relative_path);
    let result = finder.find_docs_path_linux_with(home, Ok(steam_library));

    assert_eq!(result.unwrap(), local_share_path);
}
