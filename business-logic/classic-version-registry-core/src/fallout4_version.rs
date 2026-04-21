use semver::Version;
use serde::{Deserialize, Serialize};

use crate::{AddressLibraryConfig, GameVersion, VersionInfo, XseConfig, get_version_registry};

/// Null/invalid version identifier (0.0.0).
pub const NULL_VERSION: Version = Version::new(0, 0, 0);

/// Fallout 4-specific version variants.
///
/// This enum represents the four main version variants of Fallout 4:
/// - Original (OG): Pre-Next-Gen update version (1.10.163)
/// - NextGen (NG): Next-Gen update version (1.10.984)
/// - AnniversaryEdition (AE): Anniversary Edition version (1.11.137+)
/// - Vr: Virtual Reality version (1.2.72)
///
/// Unlike `GameId` which treats VR as a separate game, this enum treats
/// VR as a version variant of Fallout 4, allowing unified handling of
/// game-specific logic with version-aware configuration.
///
/// **MANDATORY**: All version metadata is sourced from the [`crate::VersionRegistry`].
/// Methods like [`exe_name()`](Self::exe_name), [`docs_folder_name()`](Self::docs_folder_name),
/// etc. delegate to the VersionRegistry for their data. Use [`get_version_info()`](Self::get_version_info)
/// for direct access to the full [`VersionInfo`] from the registry.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_version_registry_core::Fallout4Version;
///
/// let version = Fallout4Version::Vr;
/// assert!(version.is_vr());
///
/// // Get full VersionInfo from the registry (RECOMMENDED)
/// if let Some(info) = version.get_version_info() {
///     println!("Display name: {}", info.display_name);
///     if let Some(addr_lib) = &info.address_library {
///         println!("Address Library: {}", addr_lib.filename);
///     }
/// }
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
pub enum Fallout4Version {
    /// Original pre-Next-Gen version (1.10.163).
    #[default]
    Original,
    /// Next-Gen update version (1.10.984).
    NextGen,
    /// Anniversary Edition version (1.11.137+).
    AnniversaryEdition,
    /// Virtual Reality version (1.2.72).
    Vr,
}

impl Fallout4Version {
    /// Return the canonical registry key for this Fallout 4 version variant.
    #[must_use]
    pub const fn registry_id(&self) -> &'static str {
        match self {
            Self::Original => "FO4_OG",
            Self::NextGen => "FO4_NG",
            Self::AnniversaryEdition => "FO4_AE",
            Self::Vr => "FO4_VR",
        }
    }

    /// Get the full [`VersionInfo`] from the version registry.
    #[must_use]
    pub fn get_version_info(&self) -> Option<&'static VersionInfo> {
        get_version_registry().get_by_id(self.registry_id())
    }

    /// Report whether this variant represents Fallout 4 VR.
    #[must_use]
    pub const fn is_vr(&self) -> bool {
        matches!(self, Self::Vr)
    }

    /// Report whether this variant is a non-VR Fallout 4 build.
    #[must_use]
    pub const fn is_standard(&self) -> bool {
        !self.is_vr()
    }

    /// Return the default executable name for this version family.
    #[must_use]
    pub const fn exe_name(&self) -> &'static str {
        if self.is_vr() {
            "Fallout4VR.exe"
        } else {
            "Fallout4.exe"
        }
    }

    /// Return the My Games documents folder name for this version family.
    #[must_use]
    pub const fn docs_folder_name(&self) -> &'static str {
        if self.is_vr() {
            "Fallout4VR"
        } else {
            "Fallout4"
        }
    }

    /// Return the Steam app ID associated with this version family.
    #[must_use]
    pub const fn steam_app_id(&self) -> u32 {
        if self.is_vr() { 611660 } else { 377160 }
    }

    /// Get the game version from the version registry.
    #[must_use]
    pub fn game_version(&self) -> GameVersion {
        self.get_version_info()
            .map(|info| info.version)
            .unwrap_or_else(|| GameVersion::new(0, 0, 0, 0))
    }

    /// Convert the registry-backed game version into semantic-version form.
    #[must_use]
    pub fn version_semver(&self) -> Version {
        let gv = self.game_version();
        Version::new(
            u64::from(gv.major),
            u64::from(gv.minor),
            u64::from(gv.patch),
        )
    }

    /// Return the canonical script extender acronym for this variant.
    #[must_use]
    pub fn xse_acronym(&self) -> &'static str {
        self.get_version_info()
            .and_then(|info| info.xse.as_ref())
            .map(|xse| match xse.acronym.as_str() {
                "F4SEVR" => "F4SEVR",
                _ => "F4SE",
            })
            .unwrap_or(if self.is_vr() { "F4SEVR" } else { "F4SE" })
    }

    /// Return the script extender acronym as an owned string.
    #[must_use]
    pub fn xse_acronym_string(&self) -> String {
        self.get_version_info()
            .and_then(|info| info.xse.as_ref())
            .map(|xse| xse.acronym.clone())
            .unwrap_or_else(|| {
                if self.is_vr() {
                    "F4SEVR".to_string()
                } else {
                    "F4SE".to_string()
                }
            })
    }

    /// Return a human-readable display name for this version variant.
    #[must_use]
    pub fn display_name(&self) -> &'static str {
        self.get_version_info()
            .map(|info| match info.short_name.as_str() {
                "OG" => "Fallout 4 Original",
                "NG" => "Fallout 4 Next-Gen",
                "AE" => "Fallout 4 Anniversary Edition",
                "VR" => "Fallout 4 VR",
                _ => "Unknown",
            })
            .unwrap_or("Unknown")
    }

    /// Return the registry-provided display name as an owned string.
    #[must_use]
    pub fn display_name_string(&self) -> String {
        self.get_version_info()
            .map(|info| info.display_name.clone())
            .unwrap_or_else(|| "Unknown".to_string())
    }

    /// Return the short registry-style code for this version variant.
    #[must_use]
    pub fn short_name(&self) -> &'static str {
        match self {
            Self::Original => "OG",
            Self::NextGen => "NG",
            Self::AnniversaryEdition => "AE",
            Self::Vr => "VR",
        }
    }

    /// Return the stable enum identifier for serialization and CLI usage.
    #[must_use]
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::Original => "Original",
            Self::NextGen => "NextGen",
            Self::AnniversaryEdition => "AnniversaryEdition",
            Self::Vr => "VR",
        }
    }

    /// Return all supported Fallout 4 version variants in a stable order.
    #[must_use]
    pub const fn all() -> [Self; 4] {
        [
            Self::Original,
            Self::NextGen,
            Self::AnniversaryEdition,
            Self::Vr,
        ]
    }

    /// Return the address-library configuration for this version, if any.
    #[must_use]
    pub fn address_library(&self) -> Option<&'static AddressLibraryConfig> {
        self.get_version_info()
            .and_then(|info| info.address_library.as_ref())
    }

    /// Return the script-extender configuration for this version, if any.
    #[must_use]
    pub fn xse_config(&self) -> Option<&'static XseConfig> {
        self.get_version_info().and_then(|info| info.xse.as_ref())
    }
}

impl std::fmt::Display for Fallout4Version {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.display_name())
    }
}

impl std::str::FromStr for Fallout4Version {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let lower = s.to_lowercase();
        match lower.as_str() {
            "original" | "og" | "1.10.163" => Ok(Self::Original),
            "nextgen" | "next-gen" | "ng" | "1.10.984" => Ok(Self::NextGen),
            "anniversaryedition" | "anniversary-edition" | "anniversary" | "ae" => {
                Ok(Self::AnniversaryEdition)
            }
            "vr" | "1.2.72" => Ok(Self::Vr),
            "auto" => Ok(Self::default()),
            _ if lower.starts_with("1.11.") => Ok(Self::AnniversaryEdition),
            _ => Err(format!("Unknown Fallout 4 version: {s}")),
        }
    }
}

#[cfg(test)]
#[path = "fallout4_version_tests.rs"]
mod tests;
