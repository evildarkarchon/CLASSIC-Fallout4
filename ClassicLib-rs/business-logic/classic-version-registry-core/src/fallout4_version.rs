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

    #[must_use]
    pub const fn is_vr(&self) -> bool {
        matches!(self, Self::Vr)
    }

    #[must_use]
    pub const fn is_standard(&self) -> bool {
        !self.is_vr()
    }

    #[must_use]
    pub const fn exe_name(&self) -> &'static str {
        if self.is_vr() {
            "Fallout4VR.exe"
        } else {
            "Fallout4.exe"
        }
    }

    #[must_use]
    pub const fn docs_folder_name(&self) -> &'static str {
        if self.is_vr() {
            "Fallout4VR"
        } else {
            "Fallout4"
        }
    }

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

    #[must_use]
    pub fn version_semver(&self) -> Version {
        let gv = self.game_version();
        Version::new(
            u64::from(gv.major),
            u64::from(gv.minor),
            u64::from(gv.patch),
        )
    }

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

    #[must_use]
    pub fn display_name_string(&self) -> String {
        self.get_version_info()
            .map(|info| info.display_name.clone())
            .unwrap_or_else(|| "Unknown".to_string())
    }

    #[must_use]
    pub fn short_name(&self) -> &'static str {
        match self {
            Self::Original => "OG",
            Self::NextGen => "NG",
            Self::AnniversaryEdition => "AE",
            Self::Vr => "VR",
        }
    }

    #[must_use]
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::Original => "Original",
            Self::NextGen => "NextGen",
            Self::AnniversaryEdition => "AnniversaryEdition",
            Self::Vr => "VR",
        }
    }

    #[must_use]
    pub const fn all() -> [Self; 4] {
        [
            Self::Original,
            Self::NextGen,
            Self::AnniversaryEdition,
            Self::Vr,
        ]
    }

    #[must_use]
    pub fn address_library(&self) -> Option<&'static AddressLibraryConfig> {
        self.get_version_info()
            .and_then(|info| info.address_library.as_ref())
    }

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
mod tests {
    use super::*;

    #[test]
    fn test_null_version() {
        assert_eq!(NULL_VERSION, Version::new(0, 0, 0));
    }

    #[test]
    fn test_fallout4_version_is_vr() {
        assert!(!Fallout4Version::Original.is_vr());
        assert!(!Fallout4Version::NextGen.is_vr());
        assert!(Fallout4Version::Vr.is_vr());
    }

    #[test]
    fn test_fallout4_version_is_standard() {
        assert!(Fallout4Version::Original.is_standard());
        assert!(Fallout4Version::NextGen.is_standard());
        assert!(!Fallout4Version::Vr.is_standard());
    }

    #[test]
    fn test_fallout4_version_exe_name() {
        assert_eq!(Fallout4Version::Original.exe_name(), "Fallout4.exe");
        assert_eq!(Fallout4Version::NextGen.exe_name(), "Fallout4.exe");
        assert_eq!(Fallout4Version::Vr.exe_name(), "Fallout4VR.exe");
    }

    #[test]
    fn test_fallout4_version_docs_folder_name() {
        assert_eq!(Fallout4Version::Original.docs_folder_name(), "Fallout4");
        assert_eq!(Fallout4Version::NextGen.docs_folder_name(), "Fallout4");
        assert_eq!(Fallout4Version::Vr.docs_folder_name(), "Fallout4VR");
    }

    #[test]
    fn test_fallout4_version_steam_app_id() {
        assert_eq!(Fallout4Version::Original.steam_app_id(), 377160);
        assert_eq!(Fallout4Version::NextGen.steam_app_id(), 377160);
        assert_eq!(Fallout4Version::Vr.steam_app_id(), 611660);
    }

    #[test]
    fn test_fallout4_version_version_semver() {
        let og_version = Fallout4Version::Original.version_semver();
        let ng_version = Fallout4Version::NextGen.version_semver();
        let vr_version = Fallout4Version::Vr.version_semver();

        assert_eq!(og_version.major, 1);
        assert_eq!(ng_version.major, 1);
        assert_eq!(vr_version.major, 1);
    }

    #[test]
    fn test_fallout4_version_xse_acronym() {
        assert_eq!(Fallout4Version::Original.xse_acronym(), "F4SE");
        assert_eq!(Fallout4Version::NextGen.xse_acronym(), "F4SE");
        assert_eq!(Fallout4Version::Vr.xse_acronym(), "F4SEVR");
    }

    #[test]
    fn test_fallout4_version_display_name() {
        assert_eq!(
            Fallout4Version::Original.display_name(),
            "Fallout 4 Original"
        );
        assert_eq!(
            Fallout4Version::NextGen.display_name(),
            "Fallout 4 Next-Gen"
        );
        assert_eq!(Fallout4Version::Vr.display_name(), "Fallout 4 VR");
    }

    #[test]
    fn test_fallout4_version_as_str() {
        assert_eq!(Fallout4Version::Original.as_str(), "Original");
        assert_eq!(Fallout4Version::NextGen.as_str(), "NextGen");
        assert_eq!(Fallout4Version::Vr.as_str(), "VR");
    }

    #[test]
    fn test_fallout4_version_all() {
        let all = Fallout4Version::all();
        assert_eq!(all.len(), 4);
        assert!(all.contains(&Fallout4Version::Original));
        assert!(all.contains(&Fallout4Version::NextGen));
        assert!(all.contains(&Fallout4Version::AnniversaryEdition));
        assert!(all.contains(&Fallout4Version::Vr));
    }

    #[test]
    fn test_fallout4_version_default() {
        let default: Fallout4Version = Default::default();
        assert_eq!(default, Fallout4Version::Original);
    }

    #[test]
    fn test_fallout4_version_display() {
        assert_eq!(
            format!("{}", Fallout4Version::Original),
            "Fallout 4 Original"
        );
        assert_eq!(
            format!("{}", Fallout4Version::NextGen),
            "Fallout 4 Next-Gen"
        );
        assert_eq!(format!("{}", Fallout4Version::Vr), "Fallout 4 VR");
    }

    #[test]
    fn test_fallout4_version_from_str() {
        assert_eq!(
            "Original".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::Original
        );
        assert_eq!(
            "NextGen".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::NextGen
        );
        assert_eq!(
            "AnniversaryEdition".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::AnniversaryEdition
        );
        assert_eq!(
            "VR".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::Vr
        );
        assert_eq!(
            "og".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::Original
        );
        assert_eq!(
            "NG".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::NextGen
        );
        assert_eq!(
            "next-gen".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::NextGen
        );
        assert_eq!(
            "ae".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::AnniversaryEdition
        );
        assert_eq!(
            "anniversary".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::AnniversaryEdition
        );
        assert_eq!(
            "anniversary-edition".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::AnniversaryEdition
        );
        assert_eq!(
            "vr".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::Vr
        );
        assert_eq!(
            "1.10.163".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::Original
        );
        assert_eq!(
            "1.10.984".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::NextGen
        );
        assert_eq!(
            "1.11.137".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::AnniversaryEdition
        );
        assert_eq!(
            "1.11.191".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::AnniversaryEdition
        );
        assert_eq!(
            "1.11.999".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::AnniversaryEdition
        );
        assert_eq!(
            "1.2.72".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::Vr
        );
        assert_eq!(
            "auto".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::Original
        );
        assert!("unknown".parse::<Fallout4Version>().is_err());
    }

    #[test]
    fn test_fallout4_version_serialization() {
        let version = Fallout4Version::Vr;
        let json = serde_json::to_string(&version).unwrap();
        let deserialized: Fallout4Version = serde_json::from_str(&json).unwrap();
        assert_eq!(version, deserialized);
    }
}
