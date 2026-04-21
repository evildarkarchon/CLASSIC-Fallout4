use super::*;

#[test]
fn test_game_id_as_str_fallout4() {
    assert_eq!(game_id_as_str(ffi::GameId::Fallout4), "Fallout4");
}

#[test]
fn test_game_id_as_str_all_variants_match_core() {
    let pairs = [
        (ffi::GameId::Fallout4, CoreGameId::Fallout4),
        (ffi::GameId::Fallout4VR, CoreGameId::Fallout4VR),
        (ffi::GameId::Skyrim, CoreGameId::Skyrim),
        (ffi::GameId::Starfield, CoreGameId::Starfield),
    ];
    for (bridge, core) in pairs {
        assert_eq!(game_id_as_str(bridge), core.as_str());
    }
}
