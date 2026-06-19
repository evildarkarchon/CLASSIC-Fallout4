use super::*;

#[test]
fn not_published_status_maps_to_js_success_classification() {
    let js_status = core_notification_status_to_js(core::NotificationStatus {
        classification: core::Classification::NotPublished,
        latest_version: String::new(),
        published_at: String::new(),
        min_supported_version: None,
        display: None,
        parse_error: None,
    });

    assert_eq!(js_status.classification, "notPublished");
    assert!(js_status.latest_version.is_empty());
    assert!(js_status.published_at.is_empty());
    assert!(js_status.min_supported_version.is_none());
    assert!(js_status.display.is_none());
    assert!(js_status.parse_error.is_none());
}
