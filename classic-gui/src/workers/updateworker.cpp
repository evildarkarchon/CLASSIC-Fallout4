#include "updateworker.h"
#include "core/rust_qt_bridge.h"

#include <QDebug>

#include "rust/cxx.h"
#include "classic_cxx_bridge/update.h"
#include "classic_cxx_bridge/web.h"

UpdateWorker::UpdateWorker(QObject* parent)
    : QObject(parent)
{
}

void UpdateWorker::checkForUpdates(const QString& currentVersion)
{
    try {
        // D-11 / CXXS-02 consumer migration: obtain the CLASSIC user-agent string
        // via the bridged classic::web helper so the CXX web surface is exercised
        // from production C++ code.  The actual HTTP user-agent is set inside the
        // Rust runtime; this provides a diagnostic label for the update check call.
        auto userAgent = classic::web::web_get_user_agent();
        qDebug() << "UpdateWorker: checking for updates with user-agent"
                 << QString::fromUtf8(userAgent.data(), static_cast<int>(userAgent.size()));

        auto result = classic::update::github_check_for_updates(
            "evildarkarchon",
            "CLASSIC-Fallout4",
            classic::toRustString(currentVersion));

        if (!result.error_message.empty()) {
            emit updateCheckCompleted(
                false, QString(), classic::toQString(result.error_message));
        } else {
            emit updateCheckCompleted(
                result.has_update,
                classic::toQString(result.latest_version),
                QString());
        }
    } catch (const rust::Error& e) {
        emit updateCheckCompleted(false, QString(), QString::fromUtf8(e.what()));
    } catch (const std::exception& e) {
        emit updateCheckCompleted(false, QString(), QString::fromUtf8(e.what()));
    }
}
