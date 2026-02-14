#include "updateworker.h"
#include "core/rust_qt_bridge.h"

#include "rust/cxx.h"
#include "classic_cxx_bridge/update.h"

UpdateWorker::UpdateWorker(QObject* parent)
    : QObject(parent)
{
}

void UpdateWorker::checkForUpdates(const QString& currentVersion)
{
    try {
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
