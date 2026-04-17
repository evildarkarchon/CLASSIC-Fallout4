#include "threadmanager.h"

#include <QDebug>
#include <QThread>

ThreadManager::ThreadManager(QObject* parent)
    : QObject(parent)
{
}

ThreadManager::~ThreadManager()
{
    stopAll();
}

void ThreadManager::startWorker(const QString& name, QThread* thread, QObject* worker)
{
    if (m_workers.contains(name)) {
        stopWorker(name);
    }
    worker->moveToThread(thread);
    m_workers.insert(name, {thread, worker});
    thread->start();
    qDebug() << "ThreadManager: started worker" << name;
}

void ThreadManager::stopWorker(const QString& name)
{
    auto it = m_workers.find(name);
    if (it == m_workers.end()) {
        return;
    }
    qDebug() << "ThreadManager: stopping worker" << name;
    if (it->thread && it->thread->isRunning()) {
        it->thread->quit();
        if (!it->thread->wait(5000)) {
            qWarning() << "ThreadManager: worker" << name << "did not stop within 5s, terminated";
            it->thread->terminate();
            it->thread->wait();
        }
    }
    delete it->worker;
    if (it->thread) {
        it->thread->deleteLater();
    }
    m_workers.erase(it);
}

void ThreadManager::stopAll()
{
    qDebug() << "ThreadManager: stopping all workers (" << m_workers.size() << "registered)";
    const auto names = m_workers.keys();
    for (const auto& name : names) {
        stopWorker(name);
    }
}

bool ThreadManager::isRunning(const QString& name) const
{
    auto it = m_workers.find(name);
    if (it == m_workers.end()) {
        return false;
    }
    return it->thread && it->thread->isRunning();
}
