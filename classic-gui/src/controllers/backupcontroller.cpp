#include "backupcontroller.h"
#include "core/rust_qt_bridge.h"
#include "core/signalhub.h"

#include "classic_cxx_bridge/files.h"
#include "rust/cxx.h"

BackupController::BackupController(const QString& gameRoot, SignalHub* signalHub, QObject* parent)
    : QObject(parent)
    , m_gameRoot(gameRoot)
    , m_signalHub(signalHub)
{
}

bool BackupController::backupExists(const QString& backupType) const
{
    if (m_gameRoot.isEmpty()) {
        return false;
    }
    try {
        auto mgr = classic::files::backup_manager_new(classic::toRustString(m_gameRoot));
        return classic::files::backup_manager_exists(*mgr, classic::toRustString(backupType));
    } catch (const rust::Error&) {
        return false;
    }
}

QString BackupController::gameRoot() const
{
    return m_gameRoot;
}

void BackupController::setGameRoot(const QString& gameRoot)
{
    m_gameRoot = gameRoot;
}

void BackupController::backup(const QString& backupType)
{
    if (m_gameRoot.isEmpty()) {
        emit operationError(QStringLiteral("Game root path is not set"));
        return;
    }

    try {
        auto mgr = classic::files::backup_manager_new(classic::toRustString(m_gameRoot));
        auto result = classic::files::backup_manager_create(*mgr, classic::toRustString(backupType));
        QString msg = backupType.toUpper() + QStringLiteral(" backup created: ") + classic::toQString(result);
        emit operationCompleted(msg);
    } catch (const rust::Error& e) {
        emit operationError(backupType.toUpper() + QStringLiteral(" backup failed: ") + QString::fromUtf8(e.what()));
    }
}

void BackupController::restore(const QString& backupType)
{
    if (m_gameRoot.isEmpty()) {
        emit operationError(QStringLiteral("Game root path is not set"));
        return;
    }

    try {
        auto mgr = classic::files::backup_manager_new(classic::toRustString(m_gameRoot));
        auto count = classic::files::backup_manager_restore(*mgr, classic::toRustString(backupType));
        QString msg =
            backupType.toUpper() + QStringLiteral(" restored: ") + QString::number(count) + QStringLiteral(" files");
        emit operationCompleted(msg);
    } catch (const rust::Error& e) {
        emit operationError(backupType.toUpper() + QStringLiteral(" restore failed: ") + QString::fromUtf8(e.what()));
    }
}

void BackupController::remove(const QString& backupType)
{
    if (m_gameRoot.isEmpty()) {
        emit operationError(QStringLiteral("Game root path is not set"));
        return;
    }

    try {
        auto mgr = classic::files::backup_manager_new(classic::toRustString(m_gameRoot));
        classic::files::backup_manager_remove(*mgr, classic::toRustString(backupType));
        QString msg = backupType.toUpper() + QStringLiteral(" backup removed");
        emit operationCompleted(msg);
    } catch (const rust::Error& e) {
        emit operationError(backupType.toUpper() + QStringLiteral(" remove failed: ") + QString::fromUtf8(e.what()));
    }
}
