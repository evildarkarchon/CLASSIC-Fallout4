#pragma once

#include <atomic>
#include <chrono>
#include <map>
#include <mutex>
#include <string>
#include <thread>

/// ANSI-based progress display for concurrent crash log scanning.
///
/// Thread-safe: worker threads call report_started/report_finished/report_error,
/// while the main thread polls render() every 100ms.
class ProgressDisplay {
public:
    ProgressDisplay(uint32_t total, const std::string& game);

    /// Called by a worker thread when it begins scanning a log.
    void report_started(std::thread::id tid, const std::string& log_name);

    /// Called by a worker thread when it finishes scanning a log.
    void report_finished(std::thread::id tid);

    /// Called by a worker thread when a scan errors out.
    void report_error(std::thread::id tid);

    /// Render the progress bar + in-flight list to stdout (main thread).
    void render();

    /// Clear all rendered lines and print final summary.
    void finish();

    uint32_t completed() const { return completed_.load(std::memory_order_relaxed); }
    uint32_t errors() const { return errors_.load(std::memory_order_relaxed); }

private:
    struct InFlightEntry {
        std::string log_name;
        std::chrono::steady_clock::time_point start_time;
    };

    uint32_t total_;
    std::string game_;
    std::atomic<uint32_t> completed_{0};
    std::atomic<uint32_t> errors_{0};
    std::chrono::steady_clock::time_point start_time_;

    std::mutex inflight_mutex_;
    std::map<std::thread::id, InFlightEntry> inflight_;

    int last_rendered_lines_ = 0;
};
