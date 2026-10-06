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

// --- Vocabulary projection ------------------------------------------------
//
// Expectations are derived from `classic-config-core`, never restated. A
// hand-written array here would be a fourth copy of the vocabulary: it would
// pass against a surface that had already drifted, because it would only be
// comparing this file's copy against itself. Iterating `VARIANTS` also means a
// new variant is covered without anyone remembering to extend these tests.

#[test]
/// Every Display Label this surface resolves is the core label for that token.
fn every_config_vocabulary_token_resolves_to_the_core_display_label() {
    for variant in CoreProvenance::VARIANTS.iter().copied() {
        assert_eq!(
            installed_yaml_data_provenance_label(variant.as_str())
                .expect("a published token must resolve"),
            variant.label(),
        );
    }
    for variant in classic_config_core::InstalledYamlDataDiagnosticKind::VARIANTS
        .iter()
        .copied()
    {
        assert_eq!(
            installed_yaml_data_diagnostic_kind_label(variant.as_str())
                .expect("a published token must resolve"),
            variant.label(),
        );
    }
    for variant in classic_config_core::LocalIgnoreYamlDataState::VARIANTS
        .iter()
        .copied()
    {
        assert_eq!(
            local_ignore_yaml_data_state_label(variant.as_str())
                .expect("a published token must resolve"),
            variant.label(),
        );
    }
}

#[test]
/// An unrecognized token is rejected rather than resolved to a default label.
fn an_unknown_token_raises_rather_than_returning_a_placeholder_label() {
    Python::initialize();
    Python::attach(|py| {
        for error in [
            installed_yaml_data_provenance_label("not_a_provenance").unwrap_err(),
            installed_yaml_data_diagnostic_kind_label("not_a_kind").unwrap_err(),
            local_ignore_yaml_data_state_label("not_a_state").unwrap_err(),
        ] {
            assert!(error.is_instance_of::<pyo3::exceptions::PyValueError>(py));
        }
    });
}

#[test]
/// The durable publication stage token comes from the vocabulary that owns it.
fn reset_publication_stage_tokens_delegate_to_the_shared_stage_vocabulary() {
    // Not a restatement of the five strings: the assertion is that this surface
    // and the durable-publication crate produce the same bytes, which is the
    // property the deleted copy could violate.
    for stage in [
        CoreResetPublicationStage::Create,
        CoreResetPublicationStage::Write,
        CoreResetPublicationStage::Flush,
        CoreResetPublicationStage::Sync,
        CoreResetPublicationStage::Publish,
    ] {
        assert_eq!(reset_publication_stage_token(stage), stage.as_str());
    }
}
