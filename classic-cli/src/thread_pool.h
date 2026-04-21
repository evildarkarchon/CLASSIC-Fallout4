#pragma once

#include <condition_variable>
#include <functional>
#include <mutex>
#include <queue>
#include <thread>
#include <vector>

/// Lightweight bounded thread pool for parallel crash log scanning.
///
/// Workers pull tasks from a shared queue protected by mutex + condvar.
/// RAII shutdown: destructor joins all threads after draining the queue.
class ThreadPool {
public:
    /// Create a pool with `num_threads` worker threads.
    explicit ThreadPool(uint32_t num_threads);

    /// RAII shutdown: signals stop, wakes all workers, joins threads.
    ~ThreadPool();

    ThreadPool(const ThreadPool&) = delete;
    ThreadPool& operator=(const ThreadPool&) = delete;

    /// Submit a task to the queue. Callable must be void().
    void submit(std::function<void()> task);

    /// Block until all submitted tasks have completed.
    void wait_all();

    /// Number of worker threads.
    uint32_t size() const { return static_cast<uint32_t>(workers_.size()); }

private:
    void worker_loop();

    std::vector<std::thread> workers_;
    std::queue<std::function<void()>> tasks_;
    std::mutex mutex_;
    std::condition_variable cv_task_;     // Workers wait for tasks
    std::condition_variable cv_finished_; // wait_all() waits here
    uint32_t active_tasks_ = 0;
    bool stop_ = false;
};
