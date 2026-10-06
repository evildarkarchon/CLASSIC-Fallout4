use super::*;
use pyo3::Python;
use std::sync::mpsc;
use std::time::Duration;

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
                .is(py.get_type::<ClassicNotificationError>()),
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

#[test]
fn not_published_status_maps_to_python_success_classification() {
    let py_status = core_status_to_py(core::NotificationStatus {
        classification: core::Classification::NotPublished,
        latest_version: String::new(),
        published_at: String::new(),
        min_supported_version: None,
        display: None,
        parse_error: None,
    });

    assert_eq!(py_status.classification, "notPublished");
    assert!(py_status.latest_version.is_empty());
    assert!(py_status.published_at.is_empty());
    assert!(py_status.min_supported_version.is_none());
    assert!(py_status.display.is_none());
    assert!(py_status.parse_error.is_none());
}

#[test]
fn notification_block_on_releases_gil_while_waiting() {
    Python::initialize();
    Python::attach(|py| {
        let other_thread_obtained_gil = super::block_on_notification_future(py, || async {
            let (tx, rx) = mpsc::channel();

            std::thread::spawn(move || {
                Python::attach(|_| {
                    let _ = tx.send(());
                });
            });

            tokio::task::spawn_blocking(move || rx.recv_timeout(Duration::from_millis(500)).is_ok())
                .await
                .expect("GIL observer task should run to completion")
        });

        assert!(
            other_thread_obtained_gil,
            "notification block_on must release the GIL so other Python threads can run during network waits",
        );
    });
}
