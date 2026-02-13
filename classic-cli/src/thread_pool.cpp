#include "thread_pool.h"

ThreadPool::ThreadPool(uint32_t num_threads) {
    workers_.reserve(num_threads);
    for (uint32_t i = 0; i < num_threads; ++i) {
        workers_.emplace_back([this] { worker_loop(); });
    }
}

ThreadPool::~ThreadPool() {
    {
        std::lock_guard lock(mutex_);
        stop_ = true;
    }
    cv_task_.notify_all();
    for (auto& w : workers_) {
        if (w.joinable()) {
            w.join();
        }
    }
}

void ThreadPool::submit(std::function<void()> task) {
    {
        std::lock_guard lock(mutex_);
        tasks_.push(std::move(task));
        ++active_tasks_;
    }
    cv_task_.notify_one();
}

void ThreadPool::wait_all() {
    std::unique_lock lock(mutex_);
    cv_finished_.wait(lock, [this] {
        return active_tasks_ == 0 && tasks_.empty();
    });
}

void ThreadPool::worker_loop() {
    while (true) {
        std::function<void()> task;
        {
            std::unique_lock lock(mutex_);
            cv_task_.wait(lock, [this] { return stop_ || !tasks_.empty(); });

            if (stop_ && tasks_.empty()) {
                return;
            }

            task = std::move(tasks_.front());
            tasks_.pop();
        }

        task();

        {
            std::lock_guard lock(mutex_);
            --active_tasks_;
        }
        cv_finished_.notify_one();
    }
}
