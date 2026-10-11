//! Repository root discovery and tree walking shared by every subcommand.

use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use walkdir::WalkDir;

/// The root of the CLASSIC repository a subcommand inspects.
///
/// Every path a subcommand reports is relative to this root.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RepoRoot {
    path: PathBuf,
}

impl RepoRoot {
    /// Wraps `path` as the repository root without validating it.
    ///
    /// Tests use this to aim a subcommand at a temporary fixture tree.
    pub fn new(path: impl Into<PathBuf>) -> Self {
        Self { path: path.into() }
    }

    /// Resolves the root for a real run: `override_root` when given (the
    /// `--repo-root` flag), otherwise the parent of this crate's manifest
    /// directory, since `xtask/` sits at the repository root.
    ///
    /// # Errors
    ///
    /// Fails when the chosen path is not an existing directory.
    pub fn discover(override_root: Option<PathBuf>) -> Result<Self> {
        let path = match override_root {
            Some(path) => path,
            None => Path::new(env!("CARGO_MANIFEST_DIR"))
                .parent()
                .context("xtask manifest directory has no parent")?
                .to_path_buf(),
        };
        if !path.is_dir() {
            bail!("repository root {} is not a directory", path.display());
        }
        Ok(Self::new(path))
    }

    /// The absolute (or as-given) root path.
    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Joins a repo-relative path (forward slashes are fine on Windows).
    pub fn join(&self, relative: &str) -> PathBuf {
        self.path.join(relative)
    }

    /// Renders `path` relative to the root with forward slashes, the form every
    /// finding uses. Paths outside the root are rendered as given.
    pub fn relative(&self, path: &Path) -> String {
        let relative = path.strip_prefix(&self.path).unwrap_or(path);
        relative
            .components()
            .map(|component| component.as_os_str().to_string_lossy())
            .collect::<Vec<_>>()
            .join("/")
    }

    /// Lists every file under the repo-relative directory `relative_dir` whose
    /// extension is one of `extensions` (compared case-insensitively, without
    /// the dot), sorted so output is deterministic across platforms.
    ///
    /// # Errors
    ///
    /// Fails when the directory is missing or cannot be walked; a gate must not
    /// silently pass over a tree it could not read.
    pub(crate) fn walk_files(
        &self,
        relative_dir: &str,
        extensions: &[&str],
    ) -> Result<Vec<PathBuf>> {
        let dir = self.join(relative_dir);
        if !dir.is_dir() {
            bail!(
                "expected directory {relative_dir} under {}",
                self.path.display()
            );
        }
        let mut files = Vec::new();
        for entry in WalkDir::new(&dir) {
            let entry = entry.with_context(|| format!("walking {relative_dir}"))?;
            if !entry.file_type().is_file() {
                continue;
            }
            let matches = entry
                .path()
                .extension()
                .and_then(|ext| ext.to_str())
                .is_some_and(|ext| extensions.iter().any(|want| ext.eq_ignore_ascii_case(want)));
            if matches {
                files.push(entry.into_path());
            }
        }
        files.sort();
        Ok(files)
    }
}

#[cfg(test)]
#[path = "repo_tests.rs"]
mod tests;
