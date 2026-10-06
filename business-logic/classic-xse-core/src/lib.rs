//! Script Extender (XSE) utilities for CLASSIC.
//!
//! This crate provides comprehensive XSE handling for Bethesda games,
//! including version detection, file location, and status checking.
//!
//! # Features
//!
//! - **XSE Type Detection**: Identify F4SE, SKSE, SFSE, etc.
//! - **Version Detection**: Parse and validate XSE versions
//! - **File Location**: Find XSE executables and DLLs
//! - **Status Checking**: Verify installation and compatibility
//! - **Version Comparison**: Check if XSE version is compatible
//!
//! # Examples
//!
//! ```rust
//! use classic_xse_core::{XseType, detect_xse_version};
//! use std::path::Path;
//!
//! // Detect F4SE version from file path
//! if let Ok(version) = detect_xse_version(Path::new("f4se_loader.exe"), XseType::F4SE) {
//!     println!("F4SE version: {}", version);
//! }
//! ```

use classic_path_core::DocsPathFinder;
use classic_shared_core::GameId;
use classic_shared_core::version::parse_version;
use classic_version_registry_core::{Fallout4Version, VersionInfo, VersionRegistryScope};
use semver::Version;
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::str::FromStr;
use thiserror::Error;

/// XSE management errors.
#[derive(Error, Debug)]
pub enum XseError {
    /// XSE not found.
    #[error("XSE not found at: {0}")]
    NotFound(PathBuf),

    /// Invalid XSE type.
    #[error("Invalid XSE type: {0}")]
    InvalidType(String),

    /// Version detection failed.
    #[error("Failed to detect XSE version: {0}")]
    VersionDetectionFailed(String),

    /// Version incompatibility.
    #[error("XSE version {found} is incompatible with game version {expected}")]
    IncompatibleVersion {
        /// The found XSE version
        found: String,
        /// The expected/compatible game version
        expected: String,
    },

    /// I/O error.
    #[error("I/O error: {source}")]
    IoError {
        /// The underlying I/O error
        #[from]
        source: std::io::Error,
    },

    /// Path error.
    #[error("Path error: {0}")]
    PathError(#[from] classic_shared_core::path_core::PathError),
}

/// Result type for XSE operations.
pub type XseResult<T> = Result<T, XseError>;

/// Operational failure while locating an XSE log.
///
/// Absence is never an error: a missing XSE Folder or log is reported as
/// `Ok(None)` by the XSE log resolvers. This error means the candidate log
/// could not be inspected at all (for example, access was denied or the path
/// is not a valid file name), so the caller cannot tell whether it exists.
#[derive(Error, Debug)]
pub enum XseLogError {
    /// Inspecting the candidate log failed for a reason other than absence.
    #[error("cannot inspect XSE log {}: {source}", path.display())]
    Inspect {
        /// The candidate log path that could not be inspected.
        path: PathBuf,
        /// The underlying I/O error.
        #[source]
        source: std::io::Error,
    },
}

/// Script Extender type enumeration.
///
/// Represents the various script extenders for different Bethesda games.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum XseType {
    /// Fallout 4 Script Extender (F4SE)
    F4SE,
    /// Fallout 4 VR Script Extender (F4SEVR)
    F4SEVR,
    /// Skyrim Script Extender (SKSE)
    SKSE,
    /// Skyrim Special Edition Script Extender (SKSE64)
    SKSE64,
    /// Skyrim VR Script Extender (SKSEVR)
    SKSEVR,
    /// Starfield Script Extender (SFSE)
    SFSE,
}

impl XseType {
    /// Get the XSE type name as a string.
    ///
    /// # Returns
    ///
    /// A static string representing the XSE type.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_xse_core::XseType;
    ///
    /// assert_eq!(XseType::F4SE.as_str(), "F4SE");
    /// assert_eq!(XseType::SKSE64.as_str(), "SKSE64");
    /// ```
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Self::F4SE => "F4SE",
            Self::F4SEVR => "F4SEVR",
            Self::SKSE => "SKSE",
            Self::SKSE64 => "SKSE64",
            Self::SKSEVR => "SKSEVR",
            Self::SFSE => "SFSE",
        }
    }

    /// Get the XSE type for a game ID.
    ///
    /// # Arguments
    ///
    /// * `game_id` - The game identifier
    ///
    /// # Returns
    ///
    /// The corresponding `XseType`.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_xse_core::XseType;
    /// use classic_shared_core::GameId;
    ///
    /// assert_eq!(XseType::from_game_id(GameId::Fallout4), XseType::F4SE);
    /// assert_eq!(XseType::from_game_id(GameId::Fallout4VR), XseType::F4SEVR);
    /// assert_eq!(XseType::from_game_id(GameId::Skyrim), XseType::SKSE64);
    /// ```
    #[must_use]
    pub fn from_game_id(game_id: GameId) -> Self {
        match game_id {
            GameId::Fallout4 => Self::F4SE,
            GameId::Fallout4VR => Self::F4SEVR,
            GameId::Skyrim => Self::SKSE64,
            GameId::Starfield => Self::SFSE,
        }
    }

    /// Get the loader executable name for this XSE type.
    ///
    /// # Returns
    ///
    /// The executable filename (e.g., "f4se_loader.exe").
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_xse_core::XseType;
    ///
    /// assert_eq!(XseType::F4SE.loader_name(), "f4se_loader.exe");
    /// assert_eq!(XseType::SKSE64.loader_name(), "skse64_loader.exe");
    /// ```
    #[must_use]
    pub fn loader_name(self) -> &'static str {
        match self {
            Self::F4SE => "f4se_loader.exe",
            Self::F4SEVR => "f4sevr_loader.exe",
            Self::SKSE => "skse_loader.exe",
            Self::SKSE64 => "skse64_loader.exe",
            Self::SKSEVR => "sksevr_loader.exe",
            Self::SFSE => "sfse_loader.exe",
        }
    }

    /// Get the DLL name for this XSE type.
    ///
    /// # Returns
    ///
    /// The DLL filename (e.g., "f4se_1_10_163.dll").
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_xse_core::XseType;
    ///
    /// assert_eq!(XseType::F4SE.dll_prefix(), "f4se_");
    /// assert_eq!(XseType::SKSE64.dll_prefix(), "skse64_");
    /// ```
    #[must_use]
    pub fn dll_prefix(self) -> &'static str {
        match self {
            Self::F4SE => "f4se_",
            Self::F4SEVR => "f4sevr_",
            Self::SKSE => "skse_",
            Self::SKSE64 => "skse64_",
            Self::SKSEVR => "sksevr_",
            Self::SFSE => "sfse_",
        }
    }
}

impl FromStr for XseType {
    type Err = XseError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_uppercase().as_str() {
            "F4SE" => Ok(Self::F4SE),
            "F4SEVR" => Ok(Self::F4SEVR),
            "SKSE" => Ok(Self::SKSE),
            "SKSE64" => Ok(Self::SKSE64),
            "SKSEVR" => Ok(Self::SKSEVR),
            "SFSE" => Ok(Self::SFSE),
            _ => Err(XseError::InvalidType(s.to_string())),
        }
    }
}

// ============================================================================
// XSE Information
// ============================================================================

/// XSE installation information.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct XseInfo {
    /// XSE type
    pub xse_type: XseType,
    /// Installation path
    pub path: PathBuf,
    /// Detected version
    pub version: Option<Version>,
    /// Whether XSE is installed
    pub installed: bool,
}

impl XseInfo {
    /// Create a new XseInfo.
    ///
    /// # Arguments
    ///
    /// * `xse_type` - The XSE type
    /// * `path` - The installation path
    ///
    /// # Returns
    ///
    /// A new `XseInfo` instance.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_xse_core::{XseInfo, XseType};
    /// use std::path::PathBuf;
    ///
    /// let info = XseInfo::new(XseType::F4SE, PathBuf::from("C:\\Games\\Fallout4"));
    /// assert_eq!(info.xse_type, XseType::F4SE);
    /// ```
    #[must_use]
    pub fn new(xse_type: XseType, path: PathBuf) -> Self {
        Self {
            xse_type,
            path,
            version: None,
            installed: false,
        }
    }

    /// Create a new XseInfo with version.
    ///
    /// # Arguments
    ///
    /// * `xse_type` - The XSE type
    /// * `path` - The installation path
    /// * `version` - The detected version
    /// * `installed` - Whether XSE is installed
    ///
    /// # Returns
    ///
    /// A new `XseInfo` instance with version.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_xse_core::{XseInfo, XseType};
    /// use std::path::PathBuf;
    /// use semver::Version;
    ///
    /// let info = XseInfo::with_version(
    ///     XseType::F4SE,
    ///     PathBuf::from("C:\\Games\\Fallout4"),
    ///     Some(Version::new(0, 6, 23)),
    ///     true
    /// );
    /// assert!(info.installed);
    /// ```
    #[must_use]
    pub fn with_version(
        xse_type: XseType,
        path: PathBuf,
        version: Option<Version>,
        installed: bool,
    ) -> Self {
        Self {
            xse_type,
            path,
            version,
            installed,
        }
    }

    /// Check if the XSE is installed at the path.
    ///
    /// # Returns
    ///
    /// True if the XSE loader executable exists.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_xse_core::{XseInfo, XseType};
    /// use std::path::PathBuf;
    ///
    /// let info = XseInfo::new(XseType::F4SE, PathBuf::from("C:\\Games\\Fallout4"));
    /// if info.check_installed() {
    ///     println!("F4SE is installed");
    /// }
    /// ```
    pub fn check_installed(&self) -> bool {
        let loader_path = self.path.join(self.xse_type.loader_name());
        loader_path.exists() && loader_path.is_file()
    }

    /// Get the full path to the XSE loader executable.
    ///
    /// # Returns
    ///
    /// The full path to the loader executable.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_xse_core::{XseInfo, XseType};
    /// use std::path::PathBuf;
    ///
    /// let info = XseInfo::new(XseType::F4SE, PathBuf::from("C:\\Games\\Fallout4"));
    /// let loader = info.loader_path();
    /// assert!(loader.ends_with("f4se_loader.exe"));
    /// ```
    #[must_use]
    pub fn loader_path(&self) -> PathBuf {
        self.path.join(self.xse_type.loader_name())
    }
}

// ============================================================================
// Version Detection
// ============================================================================

/// Detect XSE version from a loader executable.
///
/// Attempts to extract version information from the XSE loader filename
/// or by checking for version-specific DLL files.
///
/// # Arguments
///
/// * `loader_path` - Path to the XSE loader executable
/// * `xse_type` - The XSE type to detect
///
/// # Returns
///
/// The detected version, or an error if detection fails.
///
/// # Errors
///
/// Returns `XseError::NotFound` if the loader doesn't exist,
/// or `XseError::VersionDetectionFailed` if version cannot be determined.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_xse_core::{detect_xse_version, XseType};
/// use std::path::Path;
///
/// match detect_xse_version(Path::new("f4se_loader.exe"), XseType::F4SE) {
///     Ok(version) => println!("F4SE version: {}", version),
///     Err(e) => eprintln!("Detection failed: {}", e),
/// }
/// ```
pub fn detect_xse_version(loader_path: &Path, xse_type: XseType) -> XseResult<Version> {
    if !loader_path.exists() {
        return Err(XseError::NotFound(loader_path.to_path_buf()));
    }

    // Try to find version-specific DLL in the same directory
    if let Some(parent) = loader_path.parent() {
        let dll_prefix = xse_type.dll_prefix();

        // Look for DLLs matching the pattern (e.g., f4se_1_10_163.dll)
        if let Ok(entries) = std::fs::read_dir(parent) {
            for entry in entries.flatten() {
                let path = entry.path();
                if let Some(filename) = path.file_name().and_then(|n| n.to_str())
                    && filename.starts_with(dll_prefix)
                    && filename.ends_with(".dll")
                {
                    // Extract version from filename
                    if let Some(version_str) = filename
                        .strip_prefix(dll_prefix)
                        .and_then(|s| s.strip_suffix(".dll"))
                    {
                        // Replace underscores with dots for version parsing
                        let version_dotted = version_str.replace('_', ".");
                        if let Ok(version) = parse_version(&version_dotted) {
                            return Ok(version);
                        }
                    }
                }
            }
        }
    }

    Err(XseError::VersionDetectionFailed(format!(
        "Could not detect version from {}",
        loader_path.display()
    )))
}

/// Check if XSE is installed in a directory.
///
/// # Arguments
///
/// * `game_path` - The game installation directory
/// * `xse_type` - The XSE type to check
///
/// # Returns
///
/// True if the XSE loader executable exists.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_xse_core::{is_xse_installed, XseType};
/// use std::path::Path;
///
/// if is_xse_installed(Path::new("C:\\Games\\Fallout4"), XseType::F4SE) {
///     println!("F4SE is installed");
/// }
/// ```
#[must_use]
pub fn is_xse_installed(game_path: &Path, xse_type: XseType) -> bool {
    let loader_path = game_path.join(xse_type.loader_name());
    loader_path.exists() && loader_path.is_file()
}

/// Get XSE information for a game directory.
///
/// # Arguments
///
/// * `game_path` - The game installation directory
/// * `xse_type` - The XSE type to check
///
/// # Returns
///
/// XseInfo with installation and version details.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_xse_core::{get_xse_info, XseType};
/// use std::path::Path;
///
/// let info = get_xse_info(Path::new("C:\\Games\\Fallout4"), XseType::F4SE);
/// if info.installed {
///     println!("F4SE version: {:?}", info.version);
/// }
/// ```
#[must_use]
pub fn get_xse_info(game_path: &Path, xse_type: XseType) -> XseInfo {
    let mut info = XseInfo::new(xse_type, game_path.to_path_buf());

    info.installed = info.check_installed();

    if info.installed
        && let Ok(version) = detect_xse_version(&info.loader_path(), xse_type)
    {
        info.version = Some(version);
    }

    info
}

/// The Game Local facts the XSE Folder resolver consumes.
///
/// This is XSE's narrow input for config-owned Game Local data: a composing
/// caller reads the facts through `classic-config-core` (its `GameLocalFacts`
/// carries the same two fields) and passes the plain paths here, so this crate
/// never depends on config or parses the Game Local YAML.
/// `classic_scangame_core::resolve_xse_folder_for_scan` is that composing
/// caller for setup, Crash Log collection, and the C++ bridge.
/// Empty paths are treated as absent.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct XseGameLocalFacts {
    /// `Game_Info.Docs_Folder_XSE`: an explicit XSE Folder, used as-is.
    pub docs_folder_xse: Option<PathBuf>,
    /// `Game_Info.Root_Folder_Docs`: the recorded documents folder the XSE
    /// Folder is derived from.
    pub root_folder_docs: Option<PathBuf>,
}

/// Resolve the XSE Folder from caller-supplied Game Local facts, reading
/// Version Registry metadata from the default snapshot.
///
/// Precedence is the explicit `docs_folder_xse`, then the folder derived from
/// `root_folder_docs`, then the folder derived from `configured_docs_root`,
/// then platform documents discovery. Fail-soft: absent or empty facts are
/// skipped, and `None` is returned rather than an error when nothing resolves.
/// Folders are derived from the Version Registry's XSE acronym, except that
/// Fallout 4 VR's F4SEVR writes crash logs under `F4SE`.
#[must_use]
pub fn resolve_xse_folder_from_game_local_facts(
    game_local: &XseGameLocalFacts,
    game: &str,
    selected_game_version: &str,
    configured_docs_root: Option<&Path>,
) -> Option<PathBuf> {
    resolve_xse_folder_from_game_local_facts_in_version_registry_scope(
        game_local,
        game,
        selected_game_version,
        configured_docs_root,
        &VersionRegistryScope::default_scope(),
    )
}

/// Resolve the XSE Folder like [`resolve_xse_folder_from_game_local_facts`],
/// reading Version Registry metadata only from `version_registry`.
///
/// The scope's snapshot is taken lazily, and only for a Fallout 4 game; no
/// other snapshot, including the process default, is read.
#[must_use]
pub fn resolve_xse_folder_from_game_local_facts_in_version_registry_scope(
    game_local: &XseGameLocalFacts,
    game: &str,
    selected_game_version: &str,
    configured_docs_root: Option<&Path>,
    version_registry: &VersionRegistryScope,
) -> Option<PathBuf> {
    // Resolve the registry entry before the explicit-folder check, as the
    // former Local.yaml-reading resolver always did, so a scope's lazy
    // first-use snapshot is taken at the same point it always was.
    let version_info = resolve_version_info(game, selected_game_version, version_registry);
    xse_folder_for_version(game_local, configured_docs_root, version_info)
}

/// Locate the XSE log for `game` and `selected_game_version` from
/// caller-supplied Game Local facts, reading Version Registry metadata from
/// the default snapshot.
///
/// The log is looked for only in the XSE Folder that
/// [`resolve_xse_folder_from_game_local_facts`] selects (same precedence; a
/// log in a lower-precedence folder is never used instead). Its file name is
/// the selected version's Version Registry XSE acronym, lower-cased, plus
/// `.log`, so Fallout 4 VR's F4SEVR has its own `f4sevr.log` inside the shared
/// `F4SE` folder and an edition never borrows the other edition's log.
///
/// Returns `Ok(Some(path))` for an existing log file and `Ok(None)` when no
/// XSE Folder resolves, the version has no XSE metadata, or the folder or log
/// does not exist (a directory named like the log is not a log).
///
/// # Errors
///
/// Returns [`XseLogError::Inspect`] when the candidate log cannot be
/// inspected for a reason other than absence.
pub fn resolve_xse_log_from_game_local_facts(
    game_local: &XseGameLocalFacts,
    game: &str,
    selected_game_version: &str,
    configured_docs_root: Option<&Path>,
) -> Result<Option<PathBuf>, XseLogError> {
    resolve_xse_log_from_game_local_facts_in_version_registry_scope(
        game_local,
        game,
        selected_game_version,
        configured_docs_root,
        &VersionRegistryScope::default_scope(),
    )
}

/// Locate the XSE log like [`resolve_xse_log_from_game_local_facts`], reading
/// Version Registry metadata only from `version_registry`.
///
/// # Errors
///
/// Returns [`XseLogError::Inspect`] when the candidate log cannot be
/// inspected for a reason other than absence.
pub fn resolve_xse_log_from_game_local_facts_in_version_registry_scope(
    game_local: &XseGameLocalFacts,
    game: &str,
    selected_game_version: &str,
    configured_docs_root: Option<&Path>,
    version_registry: &VersionRegistryScope,
) -> Result<Option<PathBuf>, XseLogError> {
    let version_info = resolve_version_info(game, selected_game_version, version_registry);
    let Some(folder) = xse_folder_for_version(game_local, configured_docs_root, version_info)
    else {
        return Ok(None);
    };
    let Some(log_name) = version_info
        .and_then(|info| info.xse.as_ref())
        .and_then(|xse| xse_log_file_name(&xse.acronym))
    else {
        return Ok(None);
    };
    probe_xse_log(folder.join(log_name))
}

/// The XSE log file name for a Version Registry XSE acronym: the trimmed
/// acronym lower-cased plus `.log` (`F4SE` -> `f4se.log`, `F4SEVR` ->
/// `f4sevr.log`), or `None` for an empty acronym.
fn xse_log_file_name(acronym: &str) -> Option<String> {
    let acronym = acronym.trim();
    (!acronym.is_empty()).then(|| format!("{}.log", acronym.to_ascii_lowercase()))
}

/// Report whether `path` is an existing log file, treating any kind of
/// absence as `None` and every other inspection failure as an error.
fn probe_xse_log(path: PathBuf) -> Result<Option<PathBuf>, XseLogError> {
    match std::fs::metadata(&path) {
        Ok(metadata) if metadata.is_file() => Ok(Some(path)),
        // A directory (or other non-file) named like the log is not a log.
        Ok(_) => Ok(None),
        // `NotADirectory` is how Unix reports a folder component that is a
        // file; it means the log cannot exist there, not that probing failed.
        Err(error)
            if matches!(
                error.kind(),
                std::io::ErrorKind::NotFound | std::io::ErrorKind::NotADirectory
            ) =>
        {
            Ok(None)
        }
        Err(source) => Err(XseLogError::Inspect { path, source }),
    }
}

/// Apply XSE Folder precedence for an already-resolved registry entry.
fn xse_folder_for_version(
    game_local: &XseGameLocalFacts,
    configured_docs_root: Option<&Path>,
    version_info: Option<&VersionInfo>,
) -> Option<PathBuf> {
    if let Some(path) = game_local
        .docs_folder_xse
        .as_deref()
        .and_then(non_empty_path)
    {
        return Some(path.to_path_buf());
    }

    if let Some(docs_root) = game_local
        .root_folder_docs
        .as_deref()
        .and_then(non_empty_path)
        && let Some(path) = xse_folder_from_docs_root(docs_root, version_info)
    {
        return Some(path);
    }

    if let Some(docs_root) = configured_docs_root.and_then(non_empty_path)
        && let Some(path) = xse_folder_from_docs_root(docs_root, version_info)
    {
        return Some(path);
    }

    discover_xse_folder(version_info)
}

fn resolve_version_info<'r>(
    game: &str,
    selected_game_version: &str,
    version_registry: &'r VersionRegistryScope,
) -> Option<&'r VersionInfo> {
    if !matches!(game, "Fallout4" | "Fallout4VR") {
        return None;
    }

    let normalized = selected_game_version.trim();
    let version_key = if normalized.is_empty() {
        "auto"
    } else {
        normalized
    };
    let selected = if game == "Fallout4VR" && version_key == "auto" {
        Fallout4Version::Vr
    } else {
        version_key.parse::<Fallout4Version>().ok()?
    };

    selected.version_info_in(version_registry.registry())
}

fn non_empty_path(path: &Path) -> Option<&Path> {
    if path.as_os_str().is_empty() {
        None
    } else {
        Some(path)
    }
}

fn xse_folder_from_docs_root(
    docs_root: &Path,
    version_info: Option<&VersionInfo>,
) -> Option<PathBuf> {
    let folder = version_info
        .and_then(|info| info.xse.as_ref())
        .map(|xse| xse_folder_name(&xse.acronym))
        .filter(|acronym| !acronym.is_empty())?;

    Some(docs_root.join(folder))
}

/// Return the on-disk folder name a Script Extender uses, given its Version
/// Registry XSE acronym.
///
/// The same name is used for the XSE Folder under the documents root (where
/// crash logs are written) and for the `Data/<folder>/Plugins` runtime plugin
/// folder under the game root. Fallout 4 VR's `F4SEVR` keeps its own loader
/// identity but uses the shared `F4SE` folder; every other acronym is its own
/// folder name. Surrounding whitespace is trimmed, and an empty acronym
/// yields an empty name for the caller to treat as "no folder".
#[must_use]
pub fn xse_folder_name(acronym: &str) -> &str {
    match acronym.trim() {
        // F4SEVR keeps the F4SEVR identity/loader, but writes crash logs and
        // installs runtime plugins under F4SE.
        "F4SEVR" => "F4SE",
        folder => folder,
    }
}

fn docs_relative_path(docs_name: &str) -> String {
    // DocsPathFinder joins this string on Unix/Proton too, where backslash is a literal.
    format!("My Games/{docs_name}")
}

fn discover_xse_folder(version_info: Option<&VersionInfo>) -> Option<PathBuf> {
    let info = version_info?;
    if info.docs_name.trim().is_empty() {
        return None;
    }

    let relative_docs = docs_relative_path(&info.docs_name);
    let mut finder = DocsPathFinder::new(relative_docs);
    if info.steam_id != 0 {
        finder = finder.with_steam_app_id(info.steam_id);
    }

    let docs_root = finder.find_docs_path(None).ok()?;
    xse_folder_from_docs_root(&docs_root, Some(info))
}

#[cfg(test)]
#[path = "lib_tests.rs"]
mod tests;
