use super::*;
use crate::scan_intake::{CrashLogScanFacts, CrashLogScanIntakePaths};
use tempfile::tempdir;

fn make_paths(root: &std::path::Path) -> CrashLogScanIntakePaths {
    CrashLogScanIntakePaths::new(root, root.join("CLASSIC Data"))
}

fn create_database_dir(paths: &CrashLogScanIntakePaths) {
    std::fs::create_dir_all(paths.yaml_dir_data.join("databases"))
        .expect("database dir should be created");
}

#[test]
fn load_collects_typed_sidecar_settings() {
    let temp = tempdir().expect("tempdir should be created");
    let paths = make_paths(temp.path());
    let custom_db = paths.yaml_dir_data.join("databases").join("custom.db");
    let destination = temp.path().join("custom unsolved logs");
    create_database_dir(&paths);

    std::fs::write(
        paths
            .yaml_dir_data
            .join("databases")
            .join("CLASSIC Main.yaml"),
        "exclude_log_records:\n  - '(void*)'\n  - 'Basic Render Driver'\n",
    )
    .expect("main YAML should be written");
    let scan_facts = CrashLogScanFacts {
        formid_database_paths: vec![
            "databases/FOLON FormIDs.db".into(),
            "databases/custom.db".into(),
        ],
        unsolved_logs_destination: Some(destination.clone()),
    };

    let sidecars =
        ScanSidecarSettings::load(&paths, "Fallout4", &scan_facts).expect("sidecars should load");

    assert_eq!(
        sidecars.remove_list,
        vec!["(void*)".to_string(), "Basic Render Driver".to_string()]
    );
    assert_eq!(
        sidecars.formid_database_paths,
        vec![
            paths
                .yaml_dir_data
                .join("databases")
                .join("Fallout4 FormIDs Main.db"),
            paths
                .yaml_dir_data
                .join("databases")
                .join("FOLON FormIDs.db"),
            custom_db,
        ]
    );
    assert_eq!(sidecars.unsolved_logs_destination, Some(destination));
}

#[test]
fn fallout4_vr_uses_the_shared_fallout4_formid_databases() {
    let data_dir = PathBuf::from("C:/CLASSIC/CLASSIC Data");

    assert_eq!(
        resolve_formid_database_paths(&data_dir, "Fallout4VR", &[]),
        vec![
            data_dir.join("databases").join("Fallout4 FormIDs Main.db"),
            data_dir.join("databases").join("FOLON FormIDs.db"),
        ]
    );
}

#[test]
fn empty_has_no_sidecar_values() {
    assert_eq!(
        ScanSidecarSettings::from_scan_facts(&CrashLogScanFacts::default())
            .expect("empty facts should be valid"),
        ScanSidecarSettings::default()
    );
}

#[test]
fn malformed_sidecar_yaml_preserves_fail_soft_settings() {
    let temp = tempdir().expect("tempdir should be created");
    let paths = make_paths(temp.path());
    create_database_dir(&paths);

    std::fs::write(
        paths
            .yaml_dir_data
            .join("databases")
            .join("CLASSIC Main.yaml"),
        "exclude_log_records: [\n",
    )
    .expect("main YAML should be written");
    let sidecars = ScanSidecarSettings::load(&paths, "Fallout4", &CrashLogScanFacts::default())
        .expect("sidecars should load fail-soft");

    assert!(sidecars.remove_list.is_empty());
    assert_eq!(
        sidecars.formid_database_paths,
        vec![
            paths
                .yaml_dir_data
                .join("databases")
                .join("Fallout4 FormIDs Main.db"),
            paths
                .yaml_dir_data
                .join("databases")
                .join("FOLON FormIDs.db"),
        ]
    );
    assert!(sidecars.unsolved_logs_destination.is_none());
}

#[test]
fn relative_unsolved_logs_destination_is_rejected() {
    let temp = tempdir().expect("tempdir should be created");
    let paths = make_paths(temp.path());
    create_database_dir(&paths);
    let error = ScanSidecarSettings::load(
        &paths,
        "Fallout4",
        &CrashLogScanFacts {
            formid_database_paths: Vec::new(),
            unsolved_logs_destination: Some("relative/path".into()),
        },
    )
    .expect_err("relative destination should fail setup");

    assert!(matches!(error, ScanLogError::InvalidInput(_)));
}
