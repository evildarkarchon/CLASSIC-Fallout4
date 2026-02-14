#pragma once

#include <QObject>
#include <QString>

class SignalHub : public QObject {
    Q_OBJECT

public:
    static SignalHub& instance();

signals:
    void scanStarted();
    void scanProgress(float percent, const QString& status);
    void scanCompleted();
    void scanError(const QString& message);
    void settingsChanged();
    void gameChanged(const QString& game);
    void fileWatchTriggered(const QString& path);

private:
    explicit SignalHub(QObject* parent = nullptr);
    Q_DISABLE_COPY_MOVE(SignalHub)
};
