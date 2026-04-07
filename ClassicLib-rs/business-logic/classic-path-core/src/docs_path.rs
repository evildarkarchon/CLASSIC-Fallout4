//! Documents path detection and validation.
//!
//! This module provides functionality for detecting and validating the game's documents folder,
//! which contains configuration files (INI files), save games, and logs.
//!
//! # Detection Strategies
//!
//! The module uses multiple strategies to find the documents path:
//! 1. **Cached Path**: Use previously saved path from settings if valid
//! 2. **Windows Registry**: Query "Personal" folder from Windows registry
//! 3. **Home Directory**: Use standard home directory on Linux
//! 4. **Manual Selection**: Prompt user to manually select the path (handled by caller)
//!
//! # Platform Support
//!
//! - **Windows**: Uses Windows registry to find "My Documents" folder
//! - **Linux**: Uses home directory + ".local/share" for compatibility layers
//!
//! # Examples
//!
//! ```rust,no_run
//! use classic_path_core::DocsPathFinder;
//! use std::path::Path;
//!
//! // Create finder for Fallout 4
//! let finder = DocsPathFinder::new("My Games\\Fallout4");
//!
//! // Find documents path (tries cache, registry, etc.)
//! let docs_path = finder.find_docs_path(None)?;
//! println!("Documents folder: {}", docs_path.display());
//!
//! // Validate required INI files exist
//! finder.validate_ini_files(&docs_path, &["Fallout4.ini", "Fallout4Prefs.ini"])?;
//! # Ok::<(), Box<dyn std::error::Error>>(())
//! ```

use crate::IniFile;
use crate::error::{DocsPathError, DocsPathResult};
use std::path::{Path, PathBuf};

const FALLOUT_4_STEAM_APP_ID: u32 = 377160;

/// Documents path finder with multi-strategy detection.
///
/// This struct provides game-agnostic documents path detection using multiple
/// fallback strategies. It builds on the platform-specific abstractions for
/// registry queries and home directory detection.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::DocsPathFinder;
///
/// let finder = DocsPathFinder::new("My Games\\Fallout4");
/// let docs_path = finder.find_docs_path(None)?;
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
#[derive(Debug, Clone)]
pub struct DocsPathFinder {
    /// Relative path within documents folder (e.g., "My Games\\Fallout4")
    relative_path: String,
}

impl DocsPathFinder {
    /// Create a new DocsPathFinder.
    ///
    /// # Arguments
    ///
    /// * `relative_path` - Path relative to documents folder (e.g., "My Games\\Fallout4")
    ///
    /// # Returns
    ///
    /// A new DocsPathFinder instance.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_path_core::DocsPathFinder;
    ///
    /// // For Fallout 4
    /// let finder = DocsPathFinder::new("My Games\\Fallout4");
    ///
    /// // For Skyrim
    /// let finder_skyrim = DocsPathFinder::new("My Games\\Skyrim");
    /// ```
    pub fn new(relative_path: impl Into<String>) -> Self {
        Self {
            relative_path: relative_path.into(),
        }
    }

    /// Find the documents folder path using multiple strategies.
    ///
    /// Attempts to find the documents path in this order:
    /// 1. Use cached path if provided and valid
    /// 2. Query Windows registry (Windows only)
    /// 3. Use the shared Linux workflow (Proton first, then local share)
    /// 4. Return error if all strategies fail
    ///
    /// # Arguments
    ///
    /// * `cached_path` - Optional cached path from settings (None if not cached)
    ///
    /// # Returns
    ///
    /// The validated documents folder path.
    ///
    /// # Errors
    ///
    /// Returns [`DocsPathError::NotFound`] if documents folder cannot be found by any method.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_path_core::DocsPathFinder;
    ///
    /// let finder = DocsPathFinder::new("My Games\\Fallout4");
    ///
    /// // Try with cached path
    /// match finder.find_docs_path(Some("C:\\Users\\Name\\Documents\\My Games\\Fallout4")) {
    ///     Ok(path) => println!("Found: {}", path.display()),
    ///     Err(e) => println!("Not found: {}", e),
    /// }
    /// ```
    pub fn find_docs_path(&self, cached_path: Option<&str>) -> DocsPathResult<PathBuf> {
        // Strategy 1: Use cached path if provided
        if let Some(cached) = cached_path {
            let cached_path = PathBuf::from(cached);
            if self.validate_docs_path(&cached_path).is_ok() {
                return Ok(cached_path);
            }
        }

        // Strategy 2: Try platform-specific detection
        #[cfg(target_os = "windows")]
        {
            if let Ok(docs_path) = self.find_docs_path_windows() {
                return Ok(docs_path);
            }
        }

        #[cfg(not(target_os = "windows"))]
        {
            if let Ok(docs_path) = self.find_docs_path_linux() {
                return Ok(docs_path);
            }
        }

        // All strategies failed
        Err(DocsPathError::NotFound)
    }

    /// Find documents path on Windows using registry.
    ///
    /// Queries the Windows registry for the "Personal" (My Documents) folder,
    /// then appends the relative path.
    ///
    /// # Returns
    ///
    /// The documents folder path if found and valid.
    ///
    /// # Errors
    ///
    /// Returns error if registry query fails or path doesn't exist.
    #[cfg(target_os = "windows")]
    fn find_docs_path_windows(&self) -> DocsPathResult<PathBuf> {
        use crate::platform::windows::get_documents_path;

        let docs_base =
            get_documents_path().map_err(|e| DocsPathError::RegistryError(e.to_string()))?;

        let docs_path = docs_base.join(&self.relative_path);
        self.validate_docs_path(&docs_path)?;

        Ok(docs_path)
    }

    /// Find documents path on Linux using Proton-first selection plus local-share fallback.
    ///
    /// Uses the home directory to prefer a valid Proton documents path for Fallout 4,
    /// then falls back to the legacy `.local/share` location.
    ///
    /// # Returns
    ///
    /// The documents folder path if found and valid.
    ///
    /// # Errors
    ///
    /// Returns error if home directory cannot be determined or path doesn't exist.
    #[cfg(not(target_os = "windows"))]
    fn find_docs_path_linux(&self) -> DocsPathResult<PathBuf> {
        use crate::platform::linux::{get_home_directory, parse_steam_library_vdf};

        let home = get_home_directory()?;

        self.find_docs_path_linux_with(&home, parse_steam_library_vdf(FALLOUT_4_STEAM_APP_ID))
    }

    /// Resolve the Linux documents path from injected home and Steam-library inputs.
    ///
    /// This helper keeps the shared Linux selection logic testable on non-Linux hosts.
    #[doc(hidden)]
    pub fn find_docs_path_linux_with(
        &self,
        home: &Path,
        steam_library: DocsPathResult<PathBuf>,
    ) -> DocsPathResult<PathBuf> {
        use crate::platform::linux::construct_proton_docs_path;

        if let Ok(steam_library) = steam_library {
            let proton_docs_path = construct_proton_docs_path(
                &steam_library,
                FALLOUT_4_STEAM_APP_ID,
                &self.relative_path,
            );

            if self.validate_docs_path(&proton_docs_path).is_ok() {
                return Ok(proton_docs_path);
            }
        }

        let local_share_path = home.join(".local/share").join(&self.relative_path);
        self.validate_docs_path(&local_share_path)?;

        Ok(local_share_path)
    }

    /// Validate that a documents path exists and is a directory.
    ///
    /// # Arguments
    ///
    /// * `path` - The path to validate
    ///
    /// # Returns
    ///
    /// `Ok(())` if the path is valid, error otherwise.
    ///
    /// # Errors
    ///
    /// Returns error if the path doesn't exist or isn't a directory.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_path_core::DocsPathFinder;
    /// use std::path::PathBuf;
    ///
    /// let finder = DocsPathFinder::new("My Games\\Fallout4");
    /// let path = PathBuf::from("C:\\Users\\Name\\Documents\\My Games\\Fallout4");
    ///
    /// finder.validate_docs_path(&path)?;
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn validate_docs_path(&self, path: &Path) -> DocsPathResult<()> {
        if !path.exists() {
            return Err(DocsPathError::PathError(crate::error::PathError::NotFound(
                path.to_path_buf(),
            )));
        }

        if !path.is_dir() {
            return Err(DocsPathError::PathError(
                crate::error::PathError::NotADirectory(path.to_path_buf()),
            ));
        }

        Ok(())
    }

    /// Validate that required INI files exist in the documents path.
    ///
    /// # Arguments
    ///
    /// * `docs_path` - The documents folder path
    /// * `required_inis` - List of INI file names that must exist
    ///
    /// # Returns
    ///
    /// `Ok(())` if all INI files exist and are valid, error otherwise.
    ///
    /// # Errors
    ///
    /// Returns error if any required INI file is missing or cannot be parsed.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_path_core::DocsPathFinder;
    /// use std::path::PathBuf;
    ///
    /// let finder = DocsPathFinder::new("My Games\\Fallout4");
    /// let docs_path = PathBuf::from("C:\\Users\\Name\\Documents\\My Games\\Fallout4");
    ///
    /// finder.validate_ini_files(&docs_path, &["Fallout4.ini", "Fallout4Prefs.ini"])?;
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn validate_ini_files(
        &self,
        docs_path: &Path,
        required_inis: &[&str],
    ) -> DocsPathResult<()> {
        for ini_name in required_inis {
            let ini_path = docs_path.join(ini_name);

            if !ini_path.exists() {
                return Err(DocsPathError::IniValidationFailed {
                    ini: ini_name.to_string(),
                    reason: "INI file does not exist".to_string(),
                });
            }

            // Try to load the INI file to ensure it's valid
            IniFile::load(&ini_path)?;
        }

        Ok(())
    }

    /// Get the relative path within documents folder.
    ///
    /// # Returns
    ///
    /// The relative path (e.g., "My Games\\Fallout4").
    pub fn relative_path(&self) -> &str {
        &self.relative_path
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    fn create_test_docs_structure(temp_dir: &Path, relative_path: &str) -> PathBuf {
        let docs_path = temp_dir.join(relative_path);
        fs::create_dir_all(&docs_path).unwrap();
        docs_path
    }

    fn create_test_ini(docs_path: &Path, ini_name: &str) {
        let ini_path = docs_path.join(ini_name);
        fs::write(&ini_path, "[General]\nkey=value\n").unwrap();
    }

    #[test]
    fn test_new() {
        let finder = DocsPathFinder::new("My Games\\Fallout4");
        assert_eq!(finder.relative_path(), "My Games\\Fallout4");
    }

    #[test]
    fn test_validate_docs_path_success() {
        let temp_dir = TempDir::new().unwrap();
        let docs_path = create_test_docs_structure(temp_dir.path(), "My Games/Fallout4");

        let finder = DocsPathFinder::new("My Games/Fallout4");
        assert!(finder.validate_docs_path(&docs_path).is_ok());
    }

    #[test]
    fn test_validate_docs_path_not_found() {
        let finder = DocsPathFinder::new("My Games/Fallout4");
        let result = finder.validate_docs_path(Path::new("/nonexistent/path"));

        assert!(result.is_err());
        assert!(matches!(
            result,
            Err(DocsPathError::PathError(crate::error::PathError::NotFound(
                _
            )))
        ));
    }

    #[test]
    fn test_validate_ini_files_success() {
        let temp_dir = TempDir::new().unwrap();
        let docs_path = create_test_docs_structure(temp_dir.path(), "My Games/Fallout4");

        create_test_ini(&docs_path, "Fallout4.ini");
        create_test_ini(&docs_path, "Fallout4Prefs.ini");

        let finder = DocsPathFinder::new("My Games/Fallout4");
        assert!(
            finder
                .validate_ini_files(&docs_path, &["Fallout4.ini", "Fallout4Prefs.ini"])
                .is_ok()
        );
    }

    #[test]
    fn test_validate_ini_files_missing() {
        let temp_dir = TempDir::new().unwrap();
        let docs_path = create_test_docs_structure(temp_dir.path(), "My Games/Fallout4");

        create_test_ini(&docs_path, "Fallout4.ini");
        // Missing Fallout4Prefs.ini

        let finder = DocsPathFinder::new("My Games/Fallout4");
        let result = finder.validate_ini_files(&docs_path, &["Fallout4.ini", "Fallout4Prefs.ini"]);

        assert!(result.is_err());
        assert!(matches!(
            result,
            Err(DocsPathError::IniValidationFailed { .. })
        ));
    }

    #[test]
    fn test_find_docs_path_with_valid_cache() {
        let temp_dir = TempDir::new().unwrap();
        let docs_path = create_test_docs_structure(temp_dir.path(), "My Games/Fallout4");

        let finder = DocsPathFinder::new("My Games/Fallout4");
        let result = finder.find_docs_path(Some(docs_path.to_str().unwrap()));

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), docs_path);
    }

    #[test]
    fn test_find_docs_path_fallback_to_platform_detection() {
        // Use a relative path that's very unlikely to exist
        let finder = DocsPathFinder::new("NonExistentGame/VeryUnlikelyTestPath");
        let result = finder.find_docs_path(Some("/invalid/cache/path"));

        // The cache is invalid, so it should fall back to platform detection
        // On Windows: might find Documents via registry, but path won't exist
        // On Linux: might find home directory, but path won't exist
        // Either way, this specific path is very unlikely to exist

        // We accept both outcomes:
        // - Error if the path doesn't exist (expected)
        // - Ok if someone actually created this exact path (very unlikely but valid)
        match result {
            Ok(path) => {
                // If found, verify it's a directory
                assert!(path.is_dir());
            }
            Err(e) => {
                // Expected error: NotFound or PathError::NotFound
                assert!(
                    matches!(e, DocsPathError::NotFound)
                        || matches!(
                            e,
                            DocsPathError::PathError(crate::error::PathError::NotFound(_))
                        )
                );
            }
        }
    }
}
