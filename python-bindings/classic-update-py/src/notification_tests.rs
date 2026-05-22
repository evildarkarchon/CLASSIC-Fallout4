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
fn manifest_invalid_maps_to_notification_base() {
    Python::initialize();
    Python::attach(|py| {
        let py_err = update_error_to_py(core::UpdateError::ManifestInvalid {
            reason: "min_supported_version must not exceed latest_version".to_string(),
        });

        assert!(
            py_err.is_instance_of::<ClassicNotificationError>(py),
            "invalid notification manifests must be catchable as ClassicNotificationError",
        );
        assert!(
            py_err.is_instance_of::<ClassicUpdateError>(py),
            "notification exceptions must still inherit from ClassicUpdateError",
        );
    });
}
