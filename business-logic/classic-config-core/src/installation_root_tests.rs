use super::*;
use std::fs;

/// A temporary tree holding one executable folder and one working directory.
///
/// Every candidate the locator derives from the two inputs (parent, grandparent, and both
/// `install` folders) stays inside the temporary tree, so no host directory can satisfy a lookup.
struct Layout {
    _root: tempfile::TempDir,
    /// `<tree>/build/bin`: the executable's folder.
    executable_dir: PathBuf,
    /// `<tree>/work`: the process working directory.
    working_dir: PathBuf,
}

impl Layout {
    fn new() -> Self {
        let root = tempfile::tempdir().expect("temporary layout should be created");
        let tree = root.path().join("tree");
        let executable_dir = tree.join("build").join("bin");
        let working_dir = tree.join("work");
        fs::create_dir_all(&executable_dir).expect("executable folder should be created");
        fs::create_dir_all(&working_dir).expect("working directory should be created");
        Self {
            _root: root,
            executable_dir,
            working_dir,
        }
    }

    /// The six candidates in the documented search order.
    fn candidates(&self) -> [PathBuf; 6] {
        let parent = self.executable_dir.parent().unwrap().to_path_buf();
        let grandparent = parent.parent().unwrap().to_path_buf();
        [
            self.executable_dir.clone(),
            self.working_dir.clone(),
            parent.clone(),
            grandparent,
            parent.join("install"),
            self.working_dir.join("install"),
        ]
    }

    /// Marks `directory` as an Installation Root by creating its `CLASSIC Data` folder.
    fn add_classic_data(&self, directory: &Path) {
        fs::create_dir_all(directory.join("CLASSIC Data")).expect("CLASSIC Data should be created");
    }

    fn locate(&self) -> Option<PathBuf> {
        locate_installation_root(Some(&self.executable_dir), Some(&self.working_dir))
    }
}

#[test]
fn each_candidate_position_is_found_when_it_alone_holds_classic_data() {
    for position in 0..6 {
        let layout = Layout::new();
        let expected = layout.candidates()[position].clone();
        layout.add_classic_data(&expected);

        assert_eq!(
            layout.locate(),
            Some(expected),
            "candidate {} should be the Installation Root",
            position + 1
        );
    }
}

#[test]
fn executable_folder_wins_over_the_working_directory() {
    let layout = Layout::new();
    layout.add_classic_data(&layout.executable_dir);
    layout.add_classic_data(&layout.working_dir);

    assert_eq!(layout.locate(), Some(layout.executable_dir.clone()));
}

#[test]
fn the_first_matching_candidate_wins_over_every_later_one() {
    for position in 0..5 {
        let layout = Layout::new();
        let candidates = layout.candidates();
        // Every candidate from `position` onwards holds CLASSIC Data; only the earliest counts.
        for candidate in &candidates[position..] {
            layout.add_classic_data(candidate);
        }

        assert_eq!(
            layout.locate(),
            Some(candidates[position].clone()),
            "candidate {} should win over every later candidate",
            position + 1
        );
    }
}

#[test]
fn development_build_output_folder_finds_the_repository_root() {
    // `target/debug/classic-tui.exe` and `classic-gui/build/classic-gui.exe` both sit two levels
    // below the folder that holds CLASSIC Data, and are often launched from an unrelated directory.
    let layout = Layout::new();
    let repository_root = layout.executable_dir.parent().unwrap().parent().unwrap();
    layout.add_classic_data(repository_root);

    assert_eq!(layout.locate().as_deref(), Some(repository_root));
}

#[test]
fn no_candidate_with_classic_data_returns_nothing() {
    let layout = Layout::new();

    assert_eq!(layout.locate(), None);
}

#[test]
fn a_classic_data_file_does_not_mark_an_installation_root() {
    let layout = Layout::new();
    fs::write(layout.executable_dir.join("CLASSIC Data"), "not a folder")
        .expect("CLASSIC Data file should be written");

    assert_eq!(layout.locate(), None);
}

#[test]
fn a_missing_executable_folder_still_searches_the_working_directory_candidates() {
    let layout = Layout::new();
    let working_install = layout.working_dir.join("install");
    layout.add_classic_data(&working_install);
    // The executable-derived candidates would win if they were searched.
    layout.add_classic_data(&layout.executable_dir);

    assert_eq!(
        locate_installation_root(None, Some(&layout.working_dir)),
        Some(working_install)
    );
}

#[test]
fn a_missing_working_directory_still_searches_the_executable_candidates() {
    let layout = Layout::new();
    let parent_install = layout.executable_dir.parent().unwrap().join("install");
    layout.add_classic_data(&parent_install);
    // The working-directory candidates would win if they were searched.
    layout.add_classic_data(&layout.working_dir);

    assert_eq!(
        locate_installation_root(Some(&layout.executable_dir), None),
        Some(parent_install)
    );
}

#[test]
fn no_inputs_return_nothing() {
    assert_eq!(locate_installation_root(None, None), None);
}

/// Restores the process working directory when dropped, even if the test panics.
struct WorkingDirectory(PathBuf);

impl WorkingDirectory {
    fn enter(directory: &Path) -> Self {
        let previous = std::env::current_dir().expect("working directory should be readable");
        std::env::set_current_dir(directory).expect("working directory should be changed");
        Self(previous)
    }
}

impl Drop for WorkingDirectory {
    fn drop(&mut self) {
        // Best effort: a failed restore must not mask the test's own assertion failure.
        let _ = std::env::set_current_dir(&self.0);
    }
}

#[test]
#[serial_test::serial]
fn an_empty_input_is_no_candidate_rather_than_the_working_directory() {
    // An empty path joined with `CLASSIC Data` would resolve against whatever working directory
    // the process happens to have, so this test runs from a folder that holds CLASSIC Data.
    let layout = Layout::new();
    layout.add_classic_data(&layout.working_dir);
    let _cwd = WorkingDirectory::enter(&layout.working_dir);

    assert_eq!(
        locate_installation_root(Some(Path::new("")), Some(Path::new(""))),
        None
    );
}
