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
