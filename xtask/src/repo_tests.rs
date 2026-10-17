use super::*;

#[test]
fn discover_defaults_to_the_directory_holding_the_xtask_crate() {
    let root = RepoRoot::discover(None).expect("default root resolves");
    assert!(root.join("xtask/Cargo.toml").is_file());
    assert!(root.join("Cargo.toml").is_file());
}

#[test]
fn discover_honours_an_override_and_rejects_a_missing_directory() {
    let dir = tempfile::tempdir().unwrap();
    let root = RepoRoot::discover(Some(dir.path().to_path_buf())).unwrap();
    assert_eq!(root.path(), dir.path());

    let missing = dir.path().join("does-not-exist");
    assert!(RepoRoot::discover(Some(missing)).is_err());
}

#[test]
fn relative_paths_use_forward_slashes() {
    let dir = tempfile::tempdir().unwrap();
    let root = RepoRoot::new(dir.path());
    let nested = dir
        .path()
        .join("classic-gui")
        .join("src")
        .join("app")
        .join("main.cpp");
    assert_eq!(root.relative(&nested), "classic-gui/src/app/main.cpp");
}

#[test]
fn paths_outside_the_root_are_rendered_as_given_with_forward_slashes() {
    let dir = tempfile::tempdir().unwrap();
    let root = RepoRoot::new(dir.path());
    let (outside, expected) = if cfg!(windows) {
        (r"C:\elsewhere\db\a.yaml", "C:/elsewhere/db/a.yaml")
    } else {
        ("/elsewhere/db/a.yaml", "/elsewhere/db/a.yaml")
    };
    assert_eq!(root.relative(Path::new(outside)), expected);
    assert_eq!(root.relative(Path::new("db/a.yaml")), "db/a.yaml");
}

#[test]
fn walk_files_filters_by_extension_and_sorts() {
    let dir = tempfile::tempdir().unwrap();
    let src = dir.path().join("src");
    std::fs::create_dir_all(src.join("b")).unwrap();
    for name in ["src/b/z.cpp", "src/a.H", "src/notes.ui", "src/b/y.hpp"] {
        std::fs::write(dir.path().join(name), "").unwrap();
    }
    let root = RepoRoot::new(dir.path());
    let found: Vec<String> = root
        .walk_files("src", &["cpp", "h", "hpp"])
        .unwrap()
        .iter()
        .map(|path| root.relative(path))
        .collect();
    assert_eq!(found, ["src/a.H", "src/b/y.hpp", "src/b/z.cpp"]);
}

#[test]
fn walk_files_fails_on_a_missing_directory() {
    let dir = tempfile::tempdir().unwrap();
    assert!(
        RepoRoot::new(dir.path())
            .walk_files("nope", &["rs"])
            .is_err()
    );
}
