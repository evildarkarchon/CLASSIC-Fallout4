#include "updateworker.h"
#include "core/rust_qt_bridge.h"

#include <QDebug>

#include "classic_cxx_bridge/update.h"
#include "classic_cxx_bridge/web.h"
#include "rust/cxx.h"

UpdateWorker::UpdateWorker(QObject* parent)
    : QObject(parent)
{
}

void UpdateWorker::checkForUpdates(const QString& currentVersion)
{
    QVariantMap payload;

    try {
        // D-11 / CXXS-02 consumer migration: obtain the CLASSIC user-agent string
        // via the bridged classic::web helper so the CXX web surface is exercised
        // from production C++ code.  The actual HTTP user-agent is set inside the
        // Rust runtime; this provides a diagnostic label for the update check call.
        auto userAgent = classic::web::web_get_user_agent();
        qDebug() << "UpdateWorker: checking for updates with user-agent"
                 << QString::fromUtf8(userAgent.data(), static_cast<int>(userAgent.size()));

        auto status = classic::update::check_app_notification(
            rust::Str("evildarkarchon"), rust::Str("CLASSIC-Fallout4"), classic::toRustString(currentVersion));

        payload.insert(kKeyClassification, classic::toQString(status.classification));
        payload.insert(kKeyLatestVersion, classic::toQString(status.latest_version));
        payload.insert(kKeyPublishedAt, classic::toQString(status.published_at));
        payload.insert(kKeyMinSupportedVersion, classic::toQString(status.min_supported_version));
        payload.insert(kKeyDisplayTitle, classic::toQString(status.display_title));
        payload.insert(kKeyDisplayBody, classic::toQString(status.display_body));
        payload.insert(kKeyDisplayCtaUrl, classic::toQString(status.display_cta_url));
        payload.insert(kKeyParseError, classic::toQString(status.parse_error));
        payload.insert(kKeyErrorMessage, classic::toQString(status.error_message));
    } catch (const rust::Error& e) {
        payload.insert(kKeyClassification, QString::fromUtf8(kClassificationError));
        payload.insert(kKeyErrorMessage, QString::fromUtf8(e.what()));
    } catch (const std::exception& e) {
        payload.insert(kKeyClassification, QString::fromUtf8(kClassificationError));
        payload.insert(kKeyErrorMessage, QString::fromUtf8(e.what()));
    }

    emit updateCheckCompleted(payload);
}
