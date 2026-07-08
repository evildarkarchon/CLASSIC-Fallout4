use super::*;
use crate::scan_intake::CrashLogScanIntakePaths;
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
    std::fs::write(
        temp.path().join("CLASSIC Settings.yaml"),
        format!(
            "CLASSIC_Settings:\n  Unsolved Logs Destination: '{}'\n  FormID Databases:\n    Fallout4:\n      - databases/FOLON FormIDs.db\n      - databases/custom.db\n",
            destination.display()
        ),
    )
    .expect("settings YAML should be written");

    let sidecars = ScanSidecarSettings::load(&paths, "Fallout4").expect("sidecars should load");

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
fn empty_has_no_sidecar_values() {
    assert_eq!(ScanSidecarSettings::empty(), ScanSidecarSettings::default());
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
    std::fs::write(
        temp.path().join("CLASSIC Settings.yaml"),
        "CLASSIC_Settings: [\n",
    )
    .expect("settings YAML should be written");

    let sidecars =
        ScanSidecarSettings::load(&paths, "Fallout4").expect("sidecars should load fail-soft");

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
    std::fs::write(
        temp.path().join("CLASSIC Settings.yaml"),
        "CLASSIC_Settings:\n  Unsolved Logs Destination: relative/path\n",
    )
    .expect("settings YAML should be written");

    let error = ScanSidecarSettings::load(&paths, "Fallout4")
        .expect_err("relative destination should fail setup");

    assert!(matches!(error, ScanLogError::InvalidInput(_)));
}
