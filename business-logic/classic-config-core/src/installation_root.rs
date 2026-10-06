//! Installation Root location: which folder is the one CLASSIC installation a process serves.
//!
//! An Installation Root is the directory that holds one installation's `CLASSIC Data`, User
//! Settings, and Local Ignore YAML Data. Config already owns the `CLASSIC Data` layout under that
//! root, so it also owns the single search every frontend uses to find it. Frontends supply the
//! two process facts (executable folder, working directory) and turn "nothing found" into their
//! own user-facing "CLASSIC Data not found" message; there is deliberately no fallback here.

use std::path::{Path, PathBuf};

/// The folder whose presence marks a directory as an Installation Root.
const CLASSIC_DATA_DIR: &str = "CLASSIC Data";

/// Locates the Installation Root from a process's executable folder and working directory.
///
/// The inputs are plain values rather than read from the current process, so callers (and tests)
/// decide where the search starts. Candidates are checked in this fixed order, and the first one
/// that contains a `CLASSIC Data` directory is returned:
///
/// 1. the executable folder (an installed or packaged build);
/// 2. the working directory (a launch from the installation folder);
/// 3. the executable folder's parent;
/// 4. the executable folder's grandparent (a development build output folder such as
///    `target/debug` or `classic-gui/build` below the repository root);
/// 5. the `install` folder beside the executable folder (a local `-Install` output);
/// 6. the working directory's `install` folder.
///
/// An absent or empty input skips only the candidates derived from it, as does a parent or
/// grandparent that does not exist because the folder is a filesystem root. Returns `None` when no candidate
/// holds `CLASSIC Data`; a `CLASSIC Data` *file* does not count. The search only inspects
/// metadata and never creates, writes, or canonicalizes anything, so a returned path is built
/// from the caller's input verbatim.
#[must_use]
pub fn locate_installation_root(
    executable_dir: Option<&Path>,
    working_dir: Option<&Path>,
) -> Option<PathBuf> {
    // An empty path (an empty input, or the parent of a one-component relative path such as
    // `bin`) would silently mean "relative to the working directory" once joined, so it is
    // dropped before anything is derived from it. Filtering only the finished candidates is not
    // enough: `"".join("install")` is the nonempty relative path `install`.
    let executable_dir = executable_dir.and_then(non_empty);
    let working_dir = working_dir.and_then(non_empty);
    let executable_parent = executable_dir.and_then(Path::parent).and_then(non_empty);
    let candidates = [
        executable_dir.map(Path::to_path_buf),
        working_dir.map(Path::to_path_buf),
        executable_parent.map(Path::to_path_buf),
        executable_parent
            .and_then(Path::parent)
            .and_then(non_empty)
            .map(Path::to_path_buf),
        executable_parent.map(|parent| parent.join("install")),
        working_dir.map(|directory| directory.join("install")),
    ];

    candidates
        .into_iter()
        .flatten()
        .find(|candidate| candidate.join(CLASSIC_DATA_DIR).is_dir())
}

/// Returns `path` unless it is empty, which is no usable base for a candidate.
fn non_empty(path: &Path) -> Option<&Path> {
    (!path.as_os_str().is_empty()).then_some(path)
}

#[cfg(test)]
#[path = "installation_root_tests.rs"]
mod tests;
