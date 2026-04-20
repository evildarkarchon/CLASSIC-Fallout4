use serde::{Deserialize, Serialize};

/// Enumeration of supported game identifiers.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum GameId {
    /// Fallout 4.
    Fallout4,
    /// Fallout 4 VR.
    Fallout4VR,
    /// Skyrim Special Edition.
    Skyrim,
    /// Starfield.
    Starfield,
}

impl GameId {
    /// Return the stable string identifier used across CLASSIC surfaces.
    #[must_use]
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::Fallout4 => "Fallout4",
            Self::Fallout4VR => "Fallout4VR",
            Self::Skyrim => "Skyrim",
            Self::Starfield => "Starfield",
        }
    }

    /// Return the default executable name for this game.
    #[must_use]
    pub const fn exe_name(&self) -> &'static str {
        match self {
            Self::Fallout4 => "Fallout4.exe",
            Self::Fallout4VR => "Fallout4VR.exe",
            Self::Skyrim => "SkyrimSE.exe",
            Self::Starfield => "Starfield.exe",
        }
    }

    /// Report whether this game identifier represents a VR build.
    #[must_use]
    pub const fn is_vr(&self) -> bool {
        matches!(self, Self::Fallout4VR)
    }

    /// Return all supported game identifiers in a stable order.
    #[must_use]
    pub const fn all() -> [Self; 4] {
        [
            Self::Fallout4,
            Self::Fallout4VR,
            Self::Skyrim,
            Self::Starfield,
        ]
    }
}

impl std::fmt::Display for GameId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

impl std::str::FromStr for GameId {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "Fallout4" => Ok(Self::Fallout4),
            "Fallout4VR" => Ok(Self::Fallout4VR),
            "Skyrim" => Ok(Self::Skyrim),
            "Starfield" => Ok(Self::Starfield),
            _ => Err(format!("Unknown game identifier: {s}")),
        }
    }
}

#[cfg(test)]
#[path = "game_id_tests.rs"]
mod tests;
