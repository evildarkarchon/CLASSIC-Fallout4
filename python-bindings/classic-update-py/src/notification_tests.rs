use super::*;
use pyo3::Python;

#[test]
fn manifest_unsupported_version_maps_to_notification_base() {
    Python::initialize();
    Python::attach(|py| {
        let py_err = update_error_to_py(core::UpdateError::ManifestUnsupportedVersion {
            found: 99,
            max_supported: 1,
        });

        assert!(
            py_err.is_instance_of::<ClassicNotificationError>(py),
            "unsupported notification manifest versions must be catchable as ClassicNotificationError",
        );
        assert!(
            py_err.is_instance_of::<ClassicUpdateError>(py),
            "notification exceptions must still inherit from ClassicUpdateError",
        );
    });
}

#[test]
fn manifest_invalid_maps_directly_to_notification_base_with_reason() {
    Python::initialize();
    Python::attach(|py| {
        let reason = "min_supported_version must not exceed latest_version";
        let py_err = update_error_to_py(core::UpdateError::ManifestInvalid {
            reason: reason.to_string(),
        });

        assert!(
            py_err
                .get_type(py)
                .is(&py.get_type::<ClassicNotificationError>()),
            "invalid notification manifests must map directly to ClassicNotificationError",
        );
        assert!(
            py_err.is_instance_of::<ClassicUpdateError>(py),
            "notification exceptions must still inherit from ClassicUpdateError",
        );
        let message = py_err
            .value(py)
            .str()
            .expect("notification exception should stringify")
            .to_string_lossy()
            .into_owned();
        assert!(
            message.contains(reason),
            "invalid notification manifest reason must survive in the Python exception message: {message}",
        );
    });
}
