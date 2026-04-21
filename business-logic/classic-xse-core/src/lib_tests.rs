use super::*;

#[test]
fn test_xse_type_as_str() {
    assert_eq!(XseType::F4SE.as_str(), "F4SE");
    assert_eq!(XseType::SKSE64.as_str(), "SKSE64");
    assert_eq!(XseType::SFSE.as_str(), "SFSE");
}

#[test]
fn test_xse_type_from_str() {
    assert_eq!("f4se".parse::<XseType>().unwrap(), XseType::F4SE);
    assert_eq!("F4SE".parse::<XseType>().unwrap(), XseType::F4SE);
    assert_eq!("skse64".parse::<XseType>().unwrap(), XseType::SKSE64);
    assert!("unknown".parse::<XseType>().is_err());
}

#[test]
fn test_xse_type_from_game_id() {
    assert_eq!(XseType::from_game_id(GameId::Fallout4), XseType::F4SE);
    assert_eq!(XseType::from_game_id(GameId::Fallout4VR), XseType::F4SEVR);
    assert_eq!(XseType::from_game_id(GameId::Skyrim), XseType::SKSE64);
    assert_eq!(XseType::from_game_id(GameId::Starfield), XseType::SFSE);
}

#[test]
fn test_xse_type_loader_name() {
    assert_eq!(XseType::F4SE.loader_name(), "f4se_loader.exe");
    assert_eq!(XseType::SKSE64.loader_name(), "skse64_loader.exe");
    assert_eq!(XseType::SFSE.loader_name(), "sfse_loader.exe");
}

#[test]
fn test_xse_type_dll_prefix() {
    assert_eq!(XseType::F4SE.dll_prefix(), "f4se_");
    assert_eq!(XseType::SKSE64.dll_prefix(), "skse64_");
    assert_eq!(XseType::SFSE.dll_prefix(), "sfse_");
}

#[test]
fn test_xse_info_new() {
    let info = XseInfo::new(XseType::F4SE, PathBuf::from("C:\\Games\\Fallout4"));
    assert_eq!(info.xse_type, XseType::F4SE);
    assert_eq!(info.path, PathBuf::from("C:\\Games\\Fallout4"));
    assert_eq!(info.version, None);
    assert!(!info.installed);
}

#[test]
fn test_xse_info_with_version() {
    let info = XseInfo::with_version(
        XseType::F4SE,
        PathBuf::from("C:\\Games\\Fallout4"),
        Some(Version::new(0, 6, 23)),
        true,
    );
    assert_eq!(info.xse_type, XseType::F4SE);
    assert_eq!(info.version, Some(Version::new(0, 6, 23)));
    assert!(info.installed);
}

#[test]
fn test_xse_info_loader_path() {
    let info = XseInfo::new(XseType::F4SE, PathBuf::from("C:\\Games\\Fallout4"));
    let loader = info.loader_path();
    assert!(loader.ends_with("f4se_loader.exe"));
}
