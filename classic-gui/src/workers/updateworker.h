#pragma once

#include <QObject>
#include <QString>

/// Background worker for checking GitHub releases via the CXX update bridge.
///
/// Runs a single blocking call on a QThread, then emits the result.
/// The thread can be cleaned up after the signal fires.
class UpdateWorker : public QObject {
    Q_OBJECT

public:
    explicit UpdateWorker(QObject* parent = nullptr);

public slots:
    /// Perform the update check. Called after moveToThread().
    void checkForUpdates(const QString& currentVersion);

signals:
    /// Emitted when the update check completes (success or failure).
    void updateCheckCompleted(bool hasUpdate,
                              QString latestVersion,
                              QString errorMessage);
};
