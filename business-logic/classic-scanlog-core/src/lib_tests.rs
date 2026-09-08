use super::*;

#[test]
fn vr_detection_preserves_both_games_and_case_variants() {
    for marker in [
        "Fallout4VR.exe",
        "FALLOUT4VR.ESM",
        "SkyrimVR.exe",
        "SKYRIMVR.ESM",
    ] {
        assert!(
            detect_vr_log(&format!("module or plugin: {marker}")),
            "{marker}"
        );
    }
}

#[test]
fn vr_detection_rejects_non_vr_and_similar_names() {
    for content in [
        "",
        "Fallout4.exe",
        "SkyrimSE.exe",
        "Skyrim.esm",
        "SkyrimVRplugin",
        "Fallout4VResm",
    ] {
        assert!(!detect_vr_log(content), "{content}");
    }
}
