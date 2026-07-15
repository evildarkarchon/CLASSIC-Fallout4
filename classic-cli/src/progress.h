#pragma once

#include <atomic>
#include <chrono>
#include <map>
#include <mutex>
#include <string>
#include <thread>

/// ANSI-based progress display for concurrent crash log scanning.
///
/// Thread-safe: workers or scan-run callbacks call report_started/report_finished/report_error.
/// A frontend may render synchronously after events or poll render() from a dedicated renderer.
class ProgressDisplay {
public:
    ProgressDisplay(uint32_t total, const std::string& game);

    /// Called by a worker thread when it begins scanning a log.
    void report_started(std::thread::id tid, const std::string& log_name);

    /// Called when a logical scan-run entry begins scanning a log.
    void report_started(const std::string& key, const std::string& log_name);

    /// Called by a worker thread when it finishes scanning a log.
    void report_finished(std::thread::id tid);

    /// Called when a logical scan-run entry finishes scanning a log.
    void report_finished(const std::string& key);

    /// Called by a worker thread when a scan errors out.
    void report_error(std::thread::id tid);

    /// Called when a logical scan-run entry errors out.
    void report_error(const std::string& key);

    /// Render the progress bar + in-flight list to stdout (main thread).
    void render();

    /// Clears the current dynamic progress frame; callers own durable messages and summaries.
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
    std::map<std::string, InFlightEntry> inflight_;

    int last_rendered_lines_ = 0;
};
