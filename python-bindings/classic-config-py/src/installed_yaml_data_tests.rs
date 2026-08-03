use super::*;
use classic_config_core::LocalIgnoreResetDurabilityReceipt;
use pyo3::types::PyString;

#[test]
/// Durability uncertainty preserves the config exception's string-path contract.
fn replacement_durability_unknown_projects_string_paths_and_receipt() {
    Python::initialize();
    let malformed_identity = CoreYamlDataContentIdentity::from_bytes(b"malformed");
    let backup_identity = malformed_identity.clone();
    let replacement_identity = CoreYamlDataContentIdentity::from_bytes(b"defaults");
    let error = CoreResetError::ReplacementDurabilityUnknown {
        receipt: Box::new(LocalIgnoreResetDurabilityReceipt {
            path: PathBuf::from("isolated/CLASSIC Ignore.yaml"),
            backup_path: PathBuf::from("isolated/backup.bak"),
            malformed_identity: malformed_identity.clone(),
            backup_identity: backup_identity.clone(),
            replacement_identity: replacement_identity.clone(),
        }),
        source: std::io::Error::other("directory sync failed"),
    };

    let py_error = local_ignore_reset_error_to_py(error);
    Python::attach(|py| {
        let value = py_error.value(py);
        let path = value.getattr("path").expect("path should be projected");
        let backup_path = value
            .getattr("backup_path")
            .expect("backup path should be projected");

        assert!(py_error.is_instance_of::<LocalIgnoreResetReplacementDurabilityUnknownError>(py));
        assert!(path.is_instance_of::<PyString>());
        assert!(backup_path.is_instance_of::<PyString>());
        assert_eq!(
            path.extract::<String>().expect("path should be a string"),
            "isolated/CLASSIC Ignore.yaml"
        );
        assert_eq!(
            backup_path
                .extract::<String>()
                .expect("backup path should be a string"),
            "isolated/backup.bak"
        );
        assert_eq!(
            value
                .getattr("malformed_identity")
                .expect("malformed identity should be projected")
                .getattr("byte_len")
                .expect("malformed identity length should exist")
                .extract::<u64>()
                .expect("malformed identity length should be numeric"),
            malformed_identity.byte_len()
        );
        assert_eq!(
            value
                .getattr("backup_identity")
                .expect("backup identity should be projected")
                .getattr("byte_len")
                .expect("backup identity length should exist")
                .extract::<u64>()
                .expect("backup identity length should be numeric"),
            backup_identity.byte_len()
        );
        assert_eq!(
            value
                .getattr("replacement_identity")
                .expect("replacement identity should be projected")
                .getattr("byte_len")
                .expect("replacement identity length should exist")
                .extract::<u64>()
                .expect("replacement identity length should be numeric"),
            replacement_identity.byte_len()
        );
    });
}
