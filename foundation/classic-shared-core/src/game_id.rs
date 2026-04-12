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
mod tests {
    use super::*;

    #[test]
    fn test_game_id_as_str() {
        assert_eq!(GameId::Fallout4.as_str(), "Fallout4");
        assert_eq!(GameId::Fallout4VR.as_str(), "Fallout4VR");
        assert_eq!(GameId::Skyrim.as_str(), "Skyrim");
        assert_eq!(GameId::Starfield.as_str(), "Starfield");
    }

    #[test]
    fn test_game_id_exe_name() {
        assert_eq!(GameId::Fallout4.exe_name(), "Fallout4.exe");
        assert_eq!(GameId::Fallout4VR.exe_name(), "Fallout4VR.exe");
        assert_eq!(GameId::Skyrim.exe_name(), "SkyrimSE.exe");
        assert_eq!(GameId::Starfield.exe_name(), "Starfield.exe");
    }

    #[test]
    fn test_game_id_is_vr() {
        assert!(!GameId::Fallout4.is_vr());
        assert!(GameId::Fallout4VR.is_vr());
        assert!(!GameId::Skyrim.is_vr());
        assert!(!GameId::Starfield.is_vr());
    }

    #[test]
    fn test_game_id_all() {
        let all = GameId::all();
        assert_eq!(all.len(), 4);
        assert!(all.contains(&GameId::Fallout4));
        assert!(all.contains(&GameId::Fallout4VR));
    }

    #[test]
    fn test_game_id_from_str() {
        assert_eq!("Fallout4".parse::<GameId>().unwrap(), GameId::Fallout4);
        assert_eq!("Fallout4VR".parse::<GameId>().unwrap(), GameId::Fallout4VR);
        assert_eq!("Skyrim".parse::<GameId>().unwrap(), GameId::Skyrim);
        assert_eq!("Starfield".parse::<GameId>().unwrap(), GameId::Starfield);
        assert!("UnknownGame".parse::<GameId>().is_err());
    }

    #[test]
    fn test_game_id_display() {
        assert_eq!(format!("{}", GameId::Fallout4), "Fallout4");
        assert_eq!(format!("{}", GameId::Fallout4VR), "Fallout4VR");
    }

    #[test]
    fn test_game_id_serialization() {
        let game = GameId::Fallout4;
        let json = serde_json::to_string(&game).unwrap();
        let deserialized: GameId = serde_json::from_str(&json).unwrap();
        assert_eq!(game, deserialized);
    }
}
