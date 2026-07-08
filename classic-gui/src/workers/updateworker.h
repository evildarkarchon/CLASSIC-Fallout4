#pragma once

#include <QObject>
#include <QString>
#include <QVariantMap>

/// Background worker for the CLASSIC app-update notification check via the
/// CXX bridge entry point `classic::update::check_app_notification`.
///
/// Runs a single blocking call on a QThread and emits the result as a
/// `QVariantMap` so the full `NotificationStatusDto` surface (classification,
/// latest_version, published_at, min_supported_version, optional display
/// payload, parse_error, error_message) can reach the UI in one signal.
/// The thread can be cleaned up after the signal fires.
class UpdateWorker : public QObject {
    Q_OBJECT

public:
    explicit UpdateWorker(QObject* parent = nullptr);

    /// Payload-map keys emitted in `updateCheckCompleted`.
    /// Defined as constants so callers can consume the map without literal
    /// duplication. Values mirror the fields on
    /// `classic::update::NotificationStatusDto`.
    static constexpr const char* kKeyClassification = "classification";
    static constexpr const char* kKeyLatestVersion = "latestVersion";
    static constexpr const char* kKeyPublishedAt = "publishedAt";
    static constexpr const char* kKeyMinSupportedVersion = "minSupportedVersion";
    static constexpr const char* kKeyDisplayTitle = "displayTitle";
    static constexpr const char* kKeyDisplayBody = "displayBody";
    static constexpr const char* kKeyDisplayCtaUrl = "displayCtaUrl";
    static constexpr const char* kKeyParseError = "parseError";
    static constexpr const char* kKeyErrorMessage = "errorMessage";

    /// Classification string values; mirror `CLASSIFICATION_*` in
    /// `cpp-bindings/classic-cpp-bridge/src/update.rs`.
    static constexpr const char* kClassificationUpToDate = "up_to_date";
    static constexpr const char* kClassificationUpdateAvailable = "update_available";
    static constexpr const char* kClassificationDeprecated = "deprecated_client";
    static constexpr const char* kClassificationUnknown = "unknown";
    static constexpr const char* kClassificationNotPublished = "not_published";
    static constexpr const char* kClassificationError = "error";

public slots:
    /// Perform the notification check. Called after `moveToThread()`.
    void checkForUpdates(const QString& currentVersion);

signals:
    /// Emitted when the notification check completes (success or failure).
    /// The map is guaranteed to contain `kKeyClassification`; every other
    /// key holds a `QString` (possibly empty) mirroring the corresponding
    /// `NotificationStatusDto` field.
    void updateCheckCompleted(const QVariantMap& result);
};
