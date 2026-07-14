use super::select_classic_root;

#[test]
fn root_selection_uses_the_first_candidate_with_classic_data() {
    let root = tempfile::tempdir().unwrap();
    let first = root.path().join("first");
    let second = root.path().join("second");
    std::fs::create_dir_all(first.join("CLASSIC Data")).unwrap();
    std::fs::create_dir_all(second.join("CLASSIC Data")).unwrap();

    let selected = select_classic_root(vec![first.clone(), second], root.path().join("fallback"));

    assert_eq!(selected, first);
}

#[test]
fn root_selection_retains_the_application_fallback_when_data_is_missing() {
    let root = tempfile::tempdir().unwrap();
    let fallback = root.path().join("application");

    let selected = select_classic_root(vec![root.path().join("working")], fallback.clone());

    assert_eq!(selected, fallback);
}
