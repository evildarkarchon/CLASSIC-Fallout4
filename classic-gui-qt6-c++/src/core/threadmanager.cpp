#include "threadmanager.h"

#include <QThread>

ThreadManager::ThreadManager(QObject* parent)
    : QObject(parent) {}

ThreadManager::~ThreadManager() {
    stopAll();
}

void ThreadManager::startWorker(const QString& name, QThread* thread, QObject* worker) {
    if (m_workers.contains(name)) {
        stopWorker(name);
    }
    worker->moveToThread(thread);
    m_workers.insert(name, {thread, worker});
    thread->start();
}

void ThreadManager::stopWorker(const QString& name) {
    auto it = m_workers.find(name);
    if (it == m_workers.end()) {
        return;
    }
    if (it->thread && it->thread->isRunning()) {
        it->thread->quit();
        if (!it->thread->wait(5000)) {
            it->thread->terminate();
            it->thread->wait();
        }
    }
    delete it->worker;
    delete it->thread;
    m_workers.erase(it);
}

void ThreadManager::stopAll() {
    const auto names = m_workers.keys();
    for (const auto& name : names) {
        stopWorker(name);
    }
}

bool ThreadManager::isRunning(const QString& name) const {
    auto it = m_workers.find(name);
    if (it == m_workers.end()) {
        return false;
    }
    return it->thread && it->thread->isRunning();
}
