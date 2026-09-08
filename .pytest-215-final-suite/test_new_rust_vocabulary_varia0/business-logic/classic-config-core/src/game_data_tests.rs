use super::canonical_game_data_name;

#[test]
fn fallout4_variants_share_the_fallout4_data_identity() {
    assert_eq!(canonical_game_data_name("Fallout4"), "Fallout4");
    assert_eq!(canonical_game_data_name("Fallout4VR"), "Fallout4");
}

#[test]
fn unrelated_game_data_identities_are_unchanged() {
    assert_eq!(canonical_game_data_name("Skyrim"), "Skyrim");
    assert_eq!(canonical_game_data_name("Starfield"), "Starfield");
    assert_eq!(canonical_game_data_name("TestGame"), "TestGame");
}
