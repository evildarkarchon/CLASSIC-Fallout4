#include <catch2/catch_test_macros.hpp>

#include "thread_pool.h"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <thread>
#include <vector>

TEST_CASE("ThreadPool construction", "[thread_pool]") {
    SECTION("creates requested number of threads") {
        ThreadPool pool(4);
        REQUIRE(pool.size() == 4);
    }

    SECTION("single thread pool") {
        ThreadPool pool(1);
        REQUIRE(pool.size() == 1);
    }
}

TEST_CASE("ThreadPool submit and wait", "[thread_pool]") {
    ThreadPool pool(2);

    SECTION("single task executes") {
        std::atomic<int> counter{0};
        pool.submit([&] { counter.fetch_add(1); });
        pool.wait_all();
        REQUIRE(counter.load() == 1);
    }

    SECTION("multiple tasks all execute") {
        std::atomic<int> counter{0};
        constexpr int num_tasks = 50;
        for (int i = 0; i < num_tasks; ++i) {
            pool.submit([&] { counter.fetch_add(1); });
        }
        pool.wait_all();
        REQUIRE(counter.load() == num_tasks);
    }

    SECTION("wait_all returns immediately when no tasks submitted") {
        pool.wait_all();
        SUCCEED("wait_all returned without blocking");
    }
}

TEST_CASE("ThreadPool concurrent correctness", "[thread_pool]") {
    ThreadPool pool(4);

    SECTION("tasks run concurrently on multiple threads") {
        std::mutex tid_mutex;
        std::vector<std::thread::id> thread_ids;

        constexpr int num_tasks = 8;
        for (int i = 0; i < num_tasks; ++i) {
            pool.submit([&] {
                // Brief sleep so multiple tasks overlap on different threads
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
                std::lock_guard lock(tid_mutex);
                thread_ids.push_back(std::this_thread::get_id());
            });
        }
        pool.wait_all();

        REQUIRE(thread_ids.size() == num_tasks);

        // At least 2 distinct thread IDs should be present (proving concurrency)
        std::sort(thread_ids.begin(), thread_ids.end());
        auto unique_end = std::unique(thread_ids.begin(), thread_ids.end());
        auto unique_count = std::distance(thread_ids.begin(), unique_end);
        REQUIRE(unique_count >= 2);
    }

    SECTION("tasks see consistent shared state with proper synchronization") {
        std::atomic<int> sum{0};
        constexpr int num_tasks = 100;
        for (int i = 0; i < num_tasks; ++i) {
            pool.submit([&, val = i] { sum.fetch_add(val); });
        }
        pool.wait_all();
        // Sum of 0..99 = 4950
        REQUIRE(sum.load() == 4950);
    }
}

TEST_CASE("ThreadPool RAII shutdown", "[thread_pool]") {
    SECTION("destructor joins all threads even with pending work") {
        std::atomic<int> counter{0};
        {
            ThreadPool pool(2);
            for (int i = 0; i < 10; ++i) {
                pool.submit([&] {
                    std::this_thread::sleep_for(std::chrono::milliseconds(5));
                    counter.fetch_add(1);
                });
            }
            // pool destructor runs here -- should drain queue and join
        }
        REQUIRE(counter.load() == 10);
    }

    SECTION("destructor handles pool with no tasks submitted") {
        { ThreadPool pool(2); }
        SUCCEED("empty pool destroyed cleanly");
    }
}
