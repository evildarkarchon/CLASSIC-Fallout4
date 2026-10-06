//! Config-produced Game Local facts feed the XSE Folder resolver.
//!
//! `classic-xse-core` must not depend on `classic-config-core`, so a composing
//! crate (scangame, here) reads the facts through config and hands XSE the
//! plain paths. This probe pins that seam: the composed result equals what
//! XSE's own Local.yaml-reading resolver produces for the same document.

use classic_config_core::{GameLocalFacts, read_game_local_facts};
use classic_xse_core::{
    XseGameLocalFacts, resolve_xse_folder_for_scan, resolve_xse_folder_from_game_local_facts,
};
use std::path::{Path, PathBuf};

/// Map config's Game Local facts onto XSE's narrow input.
fn xse_input(facts: &GameLocalFacts) -> XseGameLocalFacts {
    XseGameLocalFacts {
        docs_folder_xse: facts.docs_folder_xse.clone(),
        root_folder_docs: facts.root_folder_docs.clone(),
    }
}

fn write_local(data: &Path, game: &str, contents: &str) {
    std::fs::create_dir_all(data).expect("create CLASSIC Data");
    std::fs::write(data.join(format!("CLASSIC {game} Local.yaml")), contents)
        .expect("write Local.yaml");
}

#[test]
fn explicit_xse_folder_from_config_reaches_xse() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    write_local(
        &data,
        "Fallout4",
        "Game_Info:\n  Docs_Folder_XSE: \"  D:/Custom/XSE  \"\n  Root_Folder_Docs: C:/Docs/Fallout4\n",
    );

    let facts = read_game_local_facts(&data, "Fallout4");
    let composed =
        resolve_xse_folder_from_game_local_facts(&xse_input(&facts), "Fallout4", "auto", None);

    assert_eq!(composed, Some(PathBuf::from("D:/Custom/XSE")));
    assert_eq!(
        composed,
        resolve_xse_folder_for_scan(&data, "Fallout4", "auto", None)
    );
}

#[test]
fn recorded_docs_root_from_config_derives_the_vr_xse_folder() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    write_local(
        &data,
        "Fallout4",
        "Game_Info:\n  Root_Folder_Docs: C:/Docs/Fallout4VR\n",
    );

    let facts = read_game_local_facts(&data, "Fallout4");
    let composed =
        resolve_xse_folder_from_game_local_facts(&xse_input(&facts), "Fallout4", "VR", None);

    // F4SEVR keeps the F4SE crash-log folder name.
    assert_eq!(composed, Some(Path::new("C:/Docs/Fallout4VR").join("F4SE")));
    assert_eq!(
        composed,
        resolve_xse_folder_for_scan(&data, "Fallout4", "VR", None)
    );
}

#[test]
fn missing_game_local_document_falls_back_to_configured_docs_root() {
    let temp = tempfile::tempdir().expect("tempdir");
    let data = temp.path().join("CLASSIC Data");
    let configured = PathBuf::from("C:/Docs/Fallout4");

    let facts = read_game_local_facts(&data, "Fallout4");
    let composed = resolve_xse_folder_from_game_local_facts(
        &xse_input(&facts),
        "Fallout4",
        "Original",
        Some(configured.as_path()),
    );

    assert_eq!(facts, GameLocalFacts::default());
    assert_eq!(composed, Some(configured.join("F4SE")));
    assert_eq!(
        composed,
        resolve_xse_folder_for_scan(&data, "Fallout4", "Original", Some(configured.as_path()))
    );
}
