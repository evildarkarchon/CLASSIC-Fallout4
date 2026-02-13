#include <catch2/catch_test_macros.hpp>

#include "progress.h"

#include <thread>

TEST_CASE("ProgressDisplay construction", "[progress]") {
    ProgressDisplay progress(10, "Fallout4");
    REQUIRE(progress.completed() == 0);
    REQUIRE(progress.errors() == 0);
}

TEST_CASE("ProgressDisplay tracking", "[progress]") {
    ProgressDisplay progress(5, "Fallout4");
    auto tid = std::this_thread::get_id();

    SECTION("report_finished increments completed count") {
        progress.report_started(tid, "crash-01.log");
        progress.report_finished(tid);
        REQUIRE(progress.completed() == 1);
        REQUIRE(progress.errors() == 0);
    }

    SECTION("report_error increments both completed and error counts") {
        progress.report_started(tid, "crash-02.log");
        progress.report_error(tid);
        REQUIRE(progress.completed() == 1);
        REQUIRE(progress.errors() == 1);
    }

    SECTION("multiple completions accumulate") {
        for (int i = 0; i < 5; ++i) {
            progress.report_started(tid, "crash-0" + std::to_string(i) + ".log");
            progress.report_finished(tid);
        }
        REQUIRE(progress.completed() == 5);
        REQUIRE(progress.errors() == 0);
    }

    SECTION("mixed successes and errors") {
        progress.report_started(tid, "crash-01.log");
        progress.report_finished(tid);

        progress.report_started(tid, "crash-02.log");
        progress.report_error(tid);

        progress.report_started(tid, "crash-03.log");
        progress.report_finished(tid);

        REQUIRE(progress.completed() == 3);
        REQUIRE(progress.errors() == 1);
    }
}

TEST_CASE("ProgressDisplay thread safety", "[progress]") {
    constexpr uint32_t total = 100;
    ProgressDisplay progress(total, "Skyrim");

    // Simulate concurrent workers reporting from different threads
    std::vector<std::thread> workers;
    constexpr int num_workers = 4;
    constexpr int tasks_per_worker = total / num_workers;

    for (int w = 0; w < num_workers; ++w) {
        workers.emplace_back([&progress, w, tasks_per_worker] {
            auto tid = std::this_thread::get_id();
            for (int i = 0; i < tasks_per_worker; ++i) {
                std::string name = "crash-w" + std::to_string(w)
                                 + "-" + std::to_string(i) + ".log";
                progress.report_started(tid, name);
                // Simulate brief work
                std::this_thread::yield();
                if (i % 10 == 9) {
                    progress.report_error(tid);
                } else {
                    progress.report_finished(tid);
                }
            }
        });
    }

    for (auto& w : workers) {
        w.join();
    }

    REQUIRE(progress.completed() == total);
    // Each worker has tasks_per_worker/10 errors (indices 9, 19, 24)
    // tasks_per_worker = 25, error indices: 9, 19 => wait, 25 tasks per worker, i%10==9 means i=9,19 => 2 per worker
    // Actually: i goes 0..24, i%10==9 means i=9 and i=19 => 2 errors per worker => 8 total
    REQUIRE(progress.errors() == num_workers * 2);
}

TEST_CASE("ProgressDisplay render and finish", "[progress]") {
    // These methods write to stdout with ANSI escapes.
    // We just verify they don't crash -- output validation
    // is handled by the PowerShell integration tests.
    ProgressDisplay progress(3, "Fallout4");
    auto tid = std::this_thread::get_id();

    progress.report_started(tid, "crash-01.log");
    progress.render();
    progress.report_finished(tid);
    progress.render();
    progress.finish();

    REQUIRE(progress.completed() == 1);
}
