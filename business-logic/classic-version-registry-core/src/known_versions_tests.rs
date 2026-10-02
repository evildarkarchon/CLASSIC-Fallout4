use super::*;
use crate::GameVersion;

fn shipped_registry() -> VersionRegistry {
    VersionRegistry::load_embedded_defaults().expect("embedded CLASSIC Main.yaml should load")
}

fn semver_of(version: &GameVersion) -> Version {
    Version::new(
        u64::from(version.major),
        u64::from(version.minor),
        u64::from(version.patch),
    )
}

#[test]
fn known_fallout4_versions_are_the_non_vr_entries() {
    let registry = shipped_registry();

    for id in ["FO4_OG", "FO4_NG", "FO4_AE"] {
        let info = registry.get_by_id(id).expect("shipped entry");
        assert!(
            registry.is_known_fallout4_version(&semver_of(&info.version)),
            "{id}"
        );
    }

    // VR is a separate mode; its game version is not a known Fallout 4 version.
    let vr = registry.get_by_id("FO4_VR").expect("shipped VR entry");
    assert!(!registry.is_known_fallout4_version(&semver_of(&vr.version)));
    assert!(!registry.is_known_fallout4_version(&Version::new(9, 9, 9)));
}

#[test]
fn known_f4se_versions_are_the_non_vr_compatible_versions() {
    let registry = shipped_registry();

    for id in ["FO4_OG", "FO4_NG"] {
        let compatible = &registry
            .get_by_id(id)
            .and_then(|info| info.xse.as_ref())
            .expect("shipped xse section")
            .compatible_version;
        let parsed = classic_shared_core::version::try_parse_version(compatible)
            .expect("shipped compatible version parses");
        assert!(registry.is_known_f4se_version(&parsed), "{id}");
    }

    assert!(!registry.is_known_f4se_version(&Version::new(9, 9, 9)));
}

#[test]
fn free_functions_answer_from_the_default_snapshot() {
    let og = Version::new(1, 10, 163);
    let f4se_og = Version::new(0, 6, 23);

    assert_eq!(
        is_known_fallout4_version(&og),
        get_version_registry().is_known_fallout4_version(&og)
    );
    assert_eq!(
        is_known_f4se_version(&f4se_og),
        get_version_registry().is_known_f4se_version(&f4se_og)
    );
    assert!(!is_known_fallout4_version(&Version::new(9, 9, 9)));
    assert!(!is_known_f4se_version(&Version::new(9, 9, 9)));
}
