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
