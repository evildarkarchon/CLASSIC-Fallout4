#pragma once

#include <QHash>
#include <QObject>
#include <QString>

class QThread;

class ThreadManager : public QObject {
    Q_OBJECT

public:
    explicit ThreadManager(QObject* parent = nullptr);
    ~ThreadManager() override;

    void startWorker(const QString& name, QThread* thread, QObject* worker);
    void stopWorker(const QString& name);
    void stopAll();
    bool isRunning(const QString& name) const;

private:
    Q_DISABLE_COPY_MOVE(ThreadManager)

    struct WorkerEntry {
        QThread* thread = nullptr;
        QObject* worker = nullptr;
    };

    QHash<QString, WorkerEntry> m_workers;
};
