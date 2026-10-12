//! Shared fixture-tree builder for xtask integration tests.
//!
//! Each test assembles a throwaway repository under a temp directory with only
//! the files the subcommand under test reads, then aims the subcommand at it
//! through `RepoRoot::new`.

#![allow(dead_code)] // Each integration test binary uses a different subset.

use std::fs;
use std::path::Path;

use tempfile::TempDir;
use xtask::RepoRoot;

/// Repo-relative directory holding the CXX bridge crate's sources.
pub const BRIDGE_SRC: &str = "cpp-bindings/classic-cpp-bridge/src";
/// Repo-relative CLI production source tree.
pub const CLI_SRC: &str = "classic-cli/src";
/// Repo-relative GUI production source tree.
pub const GUI_SRC: &str = "classic-gui/src";

/// A temporary repository tree; deleted when dropped.
pub struct FixtureRepo {
    dir: TempDir,
}

impl FixtureRepo {
    /// An empty repository tree.
    pub fn empty() -> Self {
        Self {
            dir: tempfile::tempdir().expect("create fixture temp dir"),
        }
    }

    /// A tree with the bridge, CLI and GUI source directories in place, so
    /// `cxx-bridge-gate` has everything it requires.
    pub fn cxx() -> Self {
        let repo = Self::empty();
        for dir in [BRIDGE_SRC, CLI_SRC, GUI_SRC] {
            fs::create_dir_all(repo.path().join(dir)).expect("create fixture dir");
        }
        repo
    }

    /// Writes `contents` to the repo-relative `path`, creating parents.
    pub fn file(self, path: &str, contents: &str) -> Self {
        let full = self.path().join(path);
        fs::create_dir_all(full.parent().expect("fixture path has a parent"))
            .expect("create fixture parent");
        fs::write(&full, contents).expect("write fixture file");
        self
    }

    /// Writes a bridge crate source file under `BRIDGE_SRC`.
    pub fn bridge(self, name: &str, contents: &str) -> Self {
        self.file(&format!("{BRIDGE_SRC}/{name}"), contents)
    }

    /// Writes a CLI production source file under `CLI_SRC`.
    pub fn cli(self, name: &str, contents: &str) -> Self {
        self.file(&format!("{CLI_SRC}/{name}"), contents)
    }

    /// Writes a GUI production source file under `GUI_SRC`.
    pub fn gui(self, name: &str, contents: &str) -> Self {
        self.file(&format!("{GUI_SRC}/{name}"), contents)
    }

    /// The fixture's root directory.
    pub fn path(&self) -> &Path {
        self.dir.path()
    }

    /// The fixture as a `RepoRoot` for calling a subcommand's `run`.
    pub fn root(&self) -> RepoRoot {
        RepoRoot::new(self.path())
    }
}

pub mod http;
