use super::*;

#[test]
fn test_xse_type_as_str() {
    assert_eq!(XseType::F4SE.as_str(), "F4SE");
    assert_eq!(XseType::SKSE64.as_str(), "SKSE64");
    assert_eq!(XseType::SFSE.as_str(), "SFSE");
}

#[test]
fn test_xse_type_from_str() {
    assert_eq!("f4se".parse::<XseType>().unwrap(), XseType::F4SE);
    assert_eq!("F4SE".parse::<XseType>().unwrap(), XseType::F4SE);
    assert_eq!("skse64".parse::<XseType>().unwrap(), XseType::SKSE64);
    assert!("unknown".parse::<XseType>().is_err());
}

#[test]
fn test_xse_type_from_game_id() {
    assert_eq!(XseType::from_game_id(GameId::Fallout4), XseType::F4SE);
    assert_eq!(XseType::from_game_id(GameId::Fallout4VR), XseType::F4SEVR);
    assert_eq!(XseType::from_game_id(GameId::Skyrim), XseType::SKSE64);
    assert_eq!(XseType::from_game_id(GameId::Starfield), XseType::SFSE);
}

#[test]
fn xse_folder_name_maps_f4sevr_to_the_shared_f4se_folder() {
    assert_eq!(xse_folder_name("F4SEVR"), "F4SE");
    assert_eq!(xse_folder_name(" F4SEVR "), "F4SE");
    assert_eq!(xse_folder_name("F4SE"), "F4SE");
    assert_eq!(xse_folder_name("SKSE64"), "SKSE64");
    assert_eq!(xse_folder_name(" SFSE "), "SFSE");
    assert_eq!(xse_folder_name(""), "");
}

#[test]
fn test_xse_type_loader_name() {
    assert_eq!(XseType::F4SE.loader_name(), "f4se_loader.exe");
    assert_eq!(XseType::SKSE64.loader_name(), "skse64_loader.exe");
    assert_eq!(XseType::SFSE.loader_name(), "sfse_loader.exe");
}

#[test]
fn test_xse_type_dll_prefix() {
    assert_eq!(XseType::F4SE.dll_prefix(), "f4se_");
    assert_eq!(XseType::SKSE64.dll_prefix(), "skse64_");
    assert_eq!(XseType::SFSE.dll_prefix(), "sfse_");
}

#[test]
fn test_xse_info_new() {
    let info = XseInfo::new(XseType::F4SE, PathBuf::from("C:\\Games\\Fallout4"));
    assert_eq!(info.xse_type, XseType::F4SE);
    assert_eq!(info.path, PathBuf::from("C:\\Games\\Fallout4"));
    assert_eq!(info.version, None);
    assert!(!info.installed);
}

#[test]
fn test_xse_info_with_version() {
    let info = XseInfo::with_version(
        XseType::F4SE,
        PathBuf::from("C:\\Games\\Fallout4"),
        Some(Version::new(0, 6, 23)),
        true,
    );
    assert_eq!(info.xse_type, XseType::F4SE);
    assert_eq!(info.version, Some(Version::new(0, 6, 23)));
    assert!(info.installed);
}

#[test]
fn test_xse_info_loader_path() {
    let info = XseInfo::new(XseType::F4SE, PathBuf::from("C:\\Games\\Fallout4"));
    let loader = info.loader_path();
    assert!(loader.ends_with("f4se_loader.exe"));
}

#[test]
fn docs_relative_path_uses_proton_safe_separator() {
    assert_eq!(docs_relative_path("Fallout4"), "My Games/Fallout4");
    assert_eq!(docs_relative_path("Fallout4VR"), "My Games/Fallout4VR");
}

// ---------------------------------------------------------------------------
// XSE Folder from caller-supplied Game Local facts
// ---------------------------------------------------------------------------

#[test]
fn xse_folder_from_facts_prefers_the_explicit_xse_folder() {
    let facts = XseGameLocalFacts {
        docs_folder_xse: Some(PathBuf::from(r"D:\Custom\XSE")),
        root_folder_docs: Some(PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4")),
    };
    let configured_docs_root = PathBuf::from(r"C:\Elsewhere");

    let folder = resolve_xse_folder_from_game_local_facts(
        &facts,
        "Fallout4",
        "auto",
        Some(configured_docs_root.as_path()),
    );

    assert_eq!(folder, Some(PathBuf::from(r"D:\Custom\XSE")));
}

#[test]
fn xse_folder_from_facts_derives_from_the_recorded_docs_root() {
    let facts = XseGameLocalFacts {
        docs_folder_xse: None,
        root_folder_docs: Some(PathBuf::from(
            r"C:\Users\Test\Documents\My Games\Fallout4VR",
        )),
    };

    let folder = resolve_xse_folder_from_game_local_facts(&facts, "Fallout4", "VR", None);

    // F4SEVR writes crash logs under F4SE.
    assert_eq!(
        folder,
        Some(PathBuf::from(
            r"C:\Users\Test\Documents\My Games\Fallout4VR\F4SE"
        ))
    );
}

#[test]
fn xse_folder_from_facts_treats_empty_paths_as_absent() {
    let facts = XseGameLocalFacts {
        docs_folder_xse: Some(PathBuf::new()),
        root_folder_docs: Some(PathBuf::new()),
    };
    let configured_docs_root = PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4");

    let folder = resolve_xse_folder_from_game_local_facts(
        &facts,
        "Fallout4",
        "Original",
        Some(configured_docs_root.as_path()),
    );

    assert_eq!(
        folder,
        Some(PathBuf::from(
            r"C:\Users\Test\Documents\My Games\Fallout4\F4SE"
        ))
    );
}

#[test]
fn xse_folder_from_facts_prefers_the_recorded_docs_root_over_the_configured_one() {
    let facts = XseGameLocalFacts {
        docs_folder_xse: None,
        root_folder_docs: Some(PathBuf::from(r"C:\Recorded\Fallout4")),
    };
    let configured_docs_root = PathBuf::from(r"C:\Configured\Fallout4");

    let folder = resolve_xse_folder_from_game_local_facts(
        &facts,
        "Fallout4",
        "Original",
        Some(configured_docs_root.as_path()),
    );

    assert_eq!(folder, Some(PathBuf::from(r"C:\Recorded\Fallout4\F4SE")));
}

#[test]
fn xse_folder_from_facts_still_honors_an_explicit_folder_for_unknown_games() {
    // The explicit folder needs no registry metadata, so it is returned even
    // when the game has no Version Registry entry.
    let facts = XseGameLocalFacts {
        docs_folder_xse: Some(PathBuf::from(r"D:\Custom\XSE")),
        root_folder_docs: Some(PathBuf::from(r"C:\Recorded\Docs")),
    };

    assert_eq!(
        resolve_xse_folder_from_game_local_facts(&facts, "Unknown", "auto", None),
        Some(PathBuf::from(r"D:\Custom\XSE"))
    );
    assert_eq!(
        resolve_xse_folder_from_game_local_facts(
            &XseGameLocalFacts {
                docs_folder_xse: None,
                ..facts
            },
            "Unknown",
            "auto",
            None,
        ),
        None
    );
}

#[test]
fn xse_folder_from_facts_falls_back_to_the_configured_docs_root() {
    let configured_docs_root = PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4VR");

    let folder = resolve_xse_folder_from_game_local_facts(
        &XseGameLocalFacts::default(),
        "Fallout4VR",
        "auto",
        Some(configured_docs_root.as_path()),
    );

    assert_eq!(
        folder,
        Some(PathBuf::from(
            r"C:\Users\Test\Documents\My Games\Fallout4VR\F4SE"
        ))
    );
}

// ---------------------------------------------------------------------------
// XSE log from caller-supplied Game Local facts
// ---------------------------------------------------------------------------

/// Creates `<root>/<relative>` as an empty file, creating its parent folders.
fn touch(root: &Path, relative: &str) -> PathBuf {
    let path = root.join(relative);
    std::fs::create_dir_all(path.parent().expect("log has a parent")).expect("create folder");
    std::fs::write(&path, b"").expect("write log");
    path
}

#[test]
fn xse_log_from_facts_locates_the_fallout4_log() {
    let docs = tempfile::tempdir().expect("tempdir");
    let log = touch(docs.path(), "F4SE/f4se.log");

    let located = resolve_xse_log_from_game_local_facts(
        &XseGameLocalFacts::default(),
        "Fallout4",
        "Original",
        Some(docs.path()),
    )
    .expect("probe succeeds");

    assert_eq!(located, Some(log));
}

#[test]
fn xse_log_from_facts_gives_fallout4_vr_its_own_log_in_the_shared_folder() {
    let docs = tempfile::tempdir().expect("tempdir");
    touch(docs.path(), "F4SE/f4se.log");
    let vr_log = touch(docs.path(), "F4SE/f4sevr.log");

    for (game, version) in [("Fallout4VR", "auto"), ("Fallout4", "VR")] {
        let located = resolve_xse_log_from_game_local_facts(
            &XseGameLocalFacts::default(),
            game,
            version,
            Some(docs.path()),
        )
        .expect("probe succeeds");

        assert_eq!(located, Some(vr_log.clone()), "{game} {version}");
    }
}

#[test]
fn xse_log_from_facts_never_borrows_the_other_editions_log() {
    let docs = tempfile::tempdir().expect("tempdir");
    touch(docs.path(), "F4SE/f4sevr.log");

    let located = resolve_xse_log_from_game_local_facts(
        &XseGameLocalFacts::default(),
        "Fallout4",
        "Original",
        Some(docs.path()),
    )
    .expect("probe succeeds");

    assert_eq!(located, None);
}

#[test]
fn xse_log_from_facts_keeps_xse_folder_precedence() {
    let root = tempfile::tempdir().expect("tempdir");
    let explicit_log = touch(root.path(), "explicit/f4se.log");
    touch(root.path(), "recorded/F4SE/f4se.log");
    touch(root.path(), "configured/F4SE/f4se.log");
    let facts = XseGameLocalFacts {
        docs_folder_xse: Some(root.path().join("explicit")),
        root_folder_docs: Some(root.path().join("recorded")),
    };
    let configured = root.path().join("configured");

    let located =
        resolve_xse_log_from_game_local_facts(&facts, "Fallout4", "Original", Some(&configured))
            .expect("probe succeeds");
    assert_eq!(located, Some(explicit_log));

    // The log is looked for only in the XSE Folder precedence selects; a
    // log in a lower-precedence folder is never used instead.
    std::fs::remove_file(root.path().join("explicit/f4se.log")).expect("remove log");
    let located =
        resolve_xse_log_from_game_local_facts(&facts, "Fallout4", "Original", Some(&configured))
            .expect("probe succeeds");
    assert_eq!(located, None);

    let located = resolve_xse_log_from_game_local_facts(
        &XseGameLocalFacts {
            docs_folder_xse: None,
            ..facts
        },
        "Fallout4",
        "Original",
        Some(&configured),
    )
    .expect("probe succeeds");
    assert_eq!(located, Some(root.path().join("recorded/F4SE/f4se.log")));
}

#[test]
fn xse_log_from_facts_returns_nothing_for_a_missing_folder_or_log() {
    let root = tempfile::tempdir().expect("tempdir");
    std::fs::create_dir_all(root.path().join("present/F4SE")).expect("create folder");
    // A directory named like the log is not a log.
    std::fs::create_dir_all(root.path().join("dir-log/F4SE/f4se.log")).expect("create folder");

    for docs in ["missing", "present", "dir-log"] {
        let located = resolve_xse_log_from_game_local_facts(
            &XseGameLocalFacts::default(),
            "Fallout4",
            "Original",
            Some(&root.path().join(docs)),
        )
        .expect("absence is not a failure");

        assert_eq!(located, None, "{docs}");
    }
}

#[test]
fn xse_log_from_facts_returns_nothing_without_xse_metadata() {
    // An explicit folder resolves for an unknown game, but without Version
    // Registry XSE metadata there is no log name to look for.
    let root = tempfile::tempdir().expect("tempdir");
    touch(root.path(), "explicit/f4se.log");
    let facts = XseGameLocalFacts {
        docs_folder_xse: Some(root.path().join("explicit")),
        root_folder_docs: None,
    };

    let located = resolve_xse_log_from_game_local_facts(&facts, "Unknown", "auto", None)
        .expect("probe succeeds");

    assert_eq!(located, None);
}

#[test]
fn xse_log_from_facts_reports_an_uninspectable_log_as_a_typed_error() {
    // A NUL byte makes every platform's metadata probe fail with an error
    // other than "not found", standing in for any operational I/O failure.
    let facts = XseGameLocalFacts {
        docs_folder_xse: Some(PathBuf::from("bad\0xse")),
        root_folder_docs: None,
    };

    let error = resolve_xse_log_from_game_local_facts(&facts, "Fallout4", "Original", None)
        .expect_err("an uninspectable log is an operational failure");

    let XseLogError::Inspect { path, .. } = &error;
    assert_eq!(path, &PathBuf::from("bad\0xse").join("f4se.log"));
    assert!(
        error.to_string().starts_with("cannot inspect XSE log "),
        "{error}"
    );
}
