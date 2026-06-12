#pragma once

#include <QObject>
#include <QString>

class SignalHub;

/// Controller for file backup, restore, and remove operations.
///
/// Manages the CxxBackupManager for the 4 backup categories (XSE,
/// ReShade, Vulkan, ENB). Operations are performed synchronously
/// on the calling thread since they are typically fast; wrap in
/// QThread if needed for very large backup sets.
///
/// Backup type strings recognized by the CXX bridge: "xse",
/// "reshade", "vulkan", "enb".
class BackupController : public QObject {
    Q_OBJECT

public:
    /// Create a backup controller for the given game root directory.
    /// @param gameRoot Root directory of the game installation.
    /// @param signalHub Optional SignalHub for global event routing.
    /// @param parent Qt parent object.
    explicit BackupController(const QString& gameRoot, SignalHub* signalHub = nullptr, QObject* parent = nullptr);

    /// Check whether a backup of the given type exists.
    /// @param backupType One of: "xse", "reshade", "vulkan", "enb".
    bool backupExists(const QString& backupType) const;

    /// @return The game root path this controller was initialized with.
    QString gameRoot() const;

    /// Update the game root path (e.g. after settings change).
    void setGameRoot(const QString& gameRoot);

public slots:
    /// Create a backup of the specified type.
    void backup(const QString& backupType);

    /// Restore a backup of the specified type.
    void restore(const QString& backupType);

    /// Remove a backup of the specified type.
    void remove(const QString& backupType);

signals:
    /// Emitted after a successful backup/restore/remove operation.
    void operationCompleted(const QString& message);

    /// Emitted when an operation fails with an error.
    void operationError(const QString& error);

private:
    QString m_gameRoot;
    SignalHub* m_signalHub = nullptr;
};
