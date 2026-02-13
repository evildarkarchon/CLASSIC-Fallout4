#include "progress.h"
#include <fmt/core.h>
#include <algorithm>
#include <vector>

ProgressDisplay::ProgressDisplay(uint32_t total, const std::string& game)
    : total_(total)
    , game_(game)
    , start_time_(std::chrono::steady_clock::now())
{
}

void ProgressDisplay::report_started(std::thread::id tid, const std::string& log_name) {
    std::lock_guard lock(inflight_mutex_);
    inflight_[tid] = InFlightEntry{log_name, std::chrono::steady_clock::now()};
}

void ProgressDisplay::report_finished(std::thread::id tid) {
    completed_.fetch_add(1, std::memory_order_relaxed);
    std::lock_guard lock(inflight_mutex_);
    inflight_.erase(tid);
}

void ProgressDisplay::report_error(std::thread::id tid) {
    completed_.fetch_add(1, std::memory_order_relaxed);
    errors_.fetch_add(1, std::memory_order_relaxed);
    std::lock_guard lock(inflight_mutex_);
    inflight_.erase(tid);
}

void ProgressDisplay::render() {
    auto now = std::chrono::steady_clock::now();
    auto elapsed = std::chrono::duration<double>(now - start_time_).count();
    auto done = completed_.load(std::memory_order_relaxed);

    // Clear previously rendered lines
    for (int i = 0; i < last_rendered_lines_; ++i) {
        fmt::print("\x1b[A\x1b[2K");
    }

    int lines = 0;

    // Progress bar
    double pct = (total_ > 0) ? (static_cast<double>(done) / total_ * 100.0) : 0.0;
    int bar_width = 40;
    int filled = static_cast<int>(pct / 100.0 * bar_width);

    std::string bar(filled, '=');
    if (filled < bar_width) {
        bar += '>';
        bar += std::string(bar_width - filled - 1, ' ');
    }

    fmt::print("[{}] {:3.0f}% ({}/{}) | {:.1f}s elapsed\n",
        bar, pct, done, total_, elapsed);
    ++lines;

    // In-flight list (only show logs processing for >1 second)
    std::vector<std::pair<std::string, double>> active;
    {
        std::lock_guard lock(inflight_mutex_);
        for (const auto& [tid, entry] : inflight_) {
            double dur = std::chrono::duration<double>(now - entry.start_time).count();
            if (dur > 1.0) {
                active.emplace_back(entry.log_name, dur);
            }
        }
    }

    if (!active.empty()) {
        // Sort by duration descending (longest first)
        std::sort(active.begin(), active.end(),
            [](const auto& a, const auto& b) { return a.second > b.second; });

        fmt::print("  In-flight:\n");
        ++lines;
        for (const auto& [name, dur] : active) {
            fmt::print("    {} ({:.1f}s)\n", name, dur);
            ++lines;
        }
    }

    last_rendered_lines_ = lines;
    std::fflush(stdout);
}

void ProgressDisplay::finish() {
    // Clear progress lines
    for (int i = 0; i < last_rendered_lines_; ++i) {
        fmt::print("\x1b[A\x1b[2K");
    }
    last_rendered_lines_ = 0;
    std::fflush(stdout);
}
