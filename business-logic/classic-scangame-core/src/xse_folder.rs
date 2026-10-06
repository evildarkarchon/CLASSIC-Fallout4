//! XSE Folder and XSE log resolution from an installation's recorded Game
//! Local facts.
//!
//! `classic-xse-core` owns XSE Folder derivation but must not depend on
//! `classic-config-core`, which owns the Game Local document. This module is
//! the composing caller: it reads the facts through config and hands XSE the
//! plain paths. Setup (the GUI's setup-detection hint), Crash Log collection
//! (`classic-scanlog-core`), and the C++ bridge all resolve through here.

use classic_config_core::{GameLocalFacts, read_game_local_facts_in_yaml_file_cache_scope};
use classic_shared_core::yaml::YamlFileCacheScope;
use classic_version_registry_core::VersionRegistryScope;
use classic_xse_core::{
    XseGameLocalFacts, XseLogError,
    resolve_xse_folder_from_game_local_facts_in_version_registry_scope,
    resolve_xse_log_from_game_local_facts_in_version_registry_scope,
};
use std::path::{Path, PathBuf};

/// Resolve the XSE Folder for `game` from the Game Local document in
/// `yaml_dir_data` (the `CLASSIC Data` directory), reading Version Registry
/// metadata from the process default snapshot.
///
/// Precedence is the explicit `Game_Info.Docs_Folder_XSE`, then the folder
/// derived from `Game_Info.Root_Folder_Docs`, then the folder derived from
/// `configured_docs_root`, then platform documents discovery. Fail-soft: a
/// missing, malformed, or blank Game Local document only drops its facts, and
/// `None` means "no XSE Folder" rather than an error.
#[must_use]
pub fn resolve_xse_folder_for_scan(
    yaml_dir_data: impl AsRef<Path>,
    game: &str,
    selected_game_version: &str,
    configured_docs_root: Option<&Path>,
) -> Option<PathBuf> {
    resolve_xse_folder_for_scan_in_version_registry_scope(
        yaml_dir_data,
        game,
        selected_game_version,
        configured_docs_root,
        &VersionRegistryScope::default_scope(),
    )
}

/// Resolve the XSE Folder like [`resolve_xse_folder_for_scan`], reading
/// Version Registry metadata only from `version_registry`.
///
/// The scope's snapshot is taken lazily, and only for a Fallout 4 game; no
/// other snapshot, including the process default, is read.
#[must_use]
pub fn resolve_xse_folder_for_scan_in_version_registry_scope(
    yaml_dir_data: impl AsRef<Path>,
    game: &str,
    selected_game_version: &str,
    configured_docs_root: Option<&Path>,
    version_registry: &VersionRegistryScope,
) -> Option<PathBuf> {
    resolve_xse_folder_for_scan_in_scopes(
        yaml_dir_data,
        game,
        selected_game_version,
        configured_docs_root,
        version_registry,
        &YamlFileCacheScope::default_scope(),
    )
}

/// Resolve the XSE Folder like
/// [`resolve_xse_folder_for_scan_in_version_registry_scope`], and also read
/// the Game Local document only through `yaml_file_cache`.
///
/// The document read fills, hits, and counts only that path/mtime YAML-file
/// cache scope, so a binding facade that passes its own opaque scope keeps its
/// Game Local entries out of every other facade's cache (and out of reach of
/// their clears). Unscoped callers use the functions above, which pass the
/// process default scope.
#[must_use]
pub fn resolve_xse_folder_for_scan_in_scopes(
    yaml_dir_data: impl AsRef<Path>,
    game: &str,
    selected_game_version: &str,
    configured_docs_root: Option<&Path>,
    version_registry: &VersionRegistryScope,
    yaml_file_cache: &YamlFileCacheScope,
) -> Option<PathBuf> {
    let facts = read_game_local_facts_in_yaml_file_cache_scope(
        yaml_dir_data.as_ref(),
        game,
        yaml_file_cache,
    );
    resolve_xse_folder_from_game_local_facts_in_version_registry_scope(
        &xse_game_local_facts(facts),
        game,
        selected_game_version,
        configured_docs_root,
        version_registry,
    )
}

/// Locate the XSE log for `game` and `selected_game_version` from the Game
/// Local document in `yaml_dir_data` (the `CLASSIC Data` directory), reading
/// Version Registry metadata from the process default snapshot.
///
/// The log is looked for only in the XSE Folder [`resolve_xse_folder_for_scan`]
/// selects, under the selected version's Version Registry XSE log name, so
/// Fallout 4 VR gets its own `f4sevr.log`. See
/// [`classic_xse_core::resolve_xse_log_from_game_local_facts`] for the naming
/// and absence rules. Returns `Ok(None)` when no folder resolves or the folder
/// or log is missing; the Game Local document read stays fail-soft.
///
/// # Errors
///
/// Returns [`XseLogError::Inspect`] when the candidate log cannot be inspected
/// for a reason other than absence.
pub fn resolve_xse_log_for_scan(
    yaml_dir_data: impl AsRef<Path>,
    game: &str,
    selected_game_version: &str,
    configured_docs_root: Option<&Path>,
) -> Result<Option<PathBuf>, XseLogError> {
    resolve_xse_log_for_scan_in_scopes(
        yaml_dir_data,
        game,
        selected_game_version,
        configured_docs_root,
        &VersionRegistryScope::default_scope(),
        &YamlFileCacheScope::default_scope(),
    )
}

/// Locate the XSE log like [`resolve_xse_log_for_scan`], reading Version
/// Registry metadata only from `version_registry` and the Game Local document
/// only through `yaml_file_cache` (see [`resolve_xse_folder_for_scan_in_scopes`]).
///
/// # Errors
///
/// Returns [`XseLogError::Inspect`] when the candidate log cannot be inspected
/// for a reason other than absence.
pub fn resolve_xse_log_for_scan_in_scopes(
    yaml_dir_data: impl AsRef<Path>,
    game: &str,
    selected_game_version: &str,
    configured_docs_root: Option<&Path>,
    version_registry: &VersionRegistryScope,
    yaml_file_cache: &YamlFileCacheScope,
) -> Result<Option<PathBuf>, XseLogError> {
    let facts = read_game_local_facts_in_yaml_file_cache_scope(
        yaml_dir_data.as_ref(),
        game,
        yaml_file_cache,
    );
    resolve_xse_log_from_game_local_facts_in_version_registry_scope(
        &xse_game_local_facts(facts),
        game,
        selected_game_version,
        configured_docs_root,
        version_registry,
    )
}

/// Narrow config's Game Local facts to the two folders XSE consumes; the
/// game folder is irrelevant to XSE Folder resolution.
fn xse_game_local_facts(facts: GameLocalFacts) -> XseGameLocalFacts {
    XseGameLocalFacts {
        docs_folder_xse: facts.docs_folder_xse,
        root_folder_docs: facts.root_folder_docs,
    }
}

#[cfg(test)]
#[path = "xse_folder_tests.rs"]
mod tests;
