use super::*;

#[test]
fn canonical_registry_paths_are_unique() {
    let mut paths = MIRROR_SETTINGS
        .iter()
        .filter(|setting| setting.canonical)
        .map(|setting| setting.path.join("."))
        .collect::<Vec<_>>();
    let count = paths.len();
    paths.sort();
    paths.dedup();
    assert_eq!(paths.len(), count, "canonical setting paths must be unique");
}
