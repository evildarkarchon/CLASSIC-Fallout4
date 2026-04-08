cmake_minimum_required(VERSION 3.25)
project(classic-cli VERSION 9.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# ── vcpkg dependencies ──────────────────────────────────────────────
find_package(fmt CONFIG REQUIRED)
find_package(CLI11 CONFIG REQUIRED)

# ── Rust via Corrosion ──────────────────────────────────────────────
include(FetchContent)
FetchContent_Declare(Corrosion
    GIT_REPOSITORY https://github.com/corrosion-rs/corrosion.git
    GIT_TAG v0.6.1
)
FetchContent_MakeAvailable(Corrosion)

set(CLASSIC_RUST_PROFILE release)
if(CMAKE_BUILD_TYPE)
    string(TOLOWER "${CMAKE_BUILD_TYPE}" _classic_build_type)
    if(_classic_build_type STREQUAL "debug")
        set(CLASSIC_RUST_PROFILE dev)
    endif()
endif()

corrosion_import_crate(
    MANIFEST_PATH ${CMAKE_SOURCE_DIR}/../ClassicLib-rs/Cargo.toml
    CRATES classic-cpp-bridge
    PROFILE ${CLASSIC_RUST_PROFILE}
)

# Generate CXX bridge headers + compiled C++ glue code.
# FILES are relative to the crate's src/ directory.
# Produces include paths like: classic_cxx_bridge/runtime.h
corrosion_add_cxxbridge(classic_cxx_bridge
    CRATE classic_cpp_bridge
    FILES
        types.rs
        constants.rs
        runtime.rs
        registry.rs
        yaml.rs
        config.rs
        scanner.rs
        database.rs
        files.rs
        scangame.rs
        game.rs
        update.rs
        message.rs
        perf.rs
)

target_include_directories(classic_cxx_bridge PUBLIC
    "${CMAKE_SOURCE_DIR}/../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include"
)

# ── CLI executable ──────────────────────────────────────────────────
add_executable(classic-cli
    src/main.cpp
    src/cli_args.cpp
    src/scanner.cpp
    src/progress.cpp
    src/thread_pool.cpp
    src/report_writer.cpp
)

target_include_directories(classic-cli PRIVATE src/)

target_link_libraries(classic-cli PRIVATE
    fmt::fmt
    CLI11::CLI11
    classic_cxx_bridge
)

# ── MSVC-specific flags ─────────────────────────────────────────────
if(MSVC)
    target_compile_options(classic-cli PRIVATE /utf-8 /W4)
endif()

# ── Install ─────────────────────────────────────────────────────────
install(TARGETS classic-cli RUNTIME DESTINATION .)

# CLASSIC Data — runtime data files (databases, graphics, help, game versions).
# Only the subdirectories the app actually uses are installed; dev-only files
# (Python/Pascal scripts, zip archive, local config) at the top level are skipped.
set(CLASSIC_DATA_DIR "${CMAKE_SOURCE_DIR}/../CLASSIC Data")

install(DIRECTORY "${CLASSIC_DATA_DIR}/databases/"
    DESTINATION "CLASSIC Data/databases"
    PATTERN "*.db-shm" EXCLUDE
    PATTERN "*.db-wal" EXCLUDE
    PATTERN "*.backup.*" EXCLUDE
    PATTERN "*.sha256" EXCLUDE
)
install(DIRECTORY "${CLASSIC_DATA_DIR}/graphics/"
    DESTINATION "CLASSIC Data/graphics"
)
install(DIRECTORY "${CLASSIC_DATA_DIR}/Help/"
    DESTINATION "CLASSIC Data/Help"
)
if(EXISTS "${CLASSIC_DATA_DIR}/games")
    install(DIRECTORY "${CLASSIC_DATA_DIR}/games/"
        DESTINATION "CLASSIC Data/games"
    )
endif()

# ── CPack ──────────────────────────────────────────────────────────
set(CPACK_GENERATOR "ZIP")
set(CPACK_PACKAGE_NAME "CLASSIC-CLI")
set(CPACK_PACKAGE_VENDOR "CLASSIC Development Team")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "CLASSIC Crash Log Auto Scanner (CLI)")
set(CPACK_PACKAGE_VERSION_MAJOR ${PROJECT_VERSION_MAJOR})
set(CPACK_PACKAGE_VERSION_MINOR ${PROJECT_VERSION_MINOR})
set(CPACK_PACKAGE_VERSION_PATCH ${PROJECT_VERSION_PATCH})
include(CPack)

# ── Unit Tests (Catch2) ──────────────────────────────────────────────
# Only built when Catch2 is available. These tests cover components
# that don't depend on the Rust CXX bridge (ThreadPool, Progress, CliArgs).
find_package(Catch2 3 CONFIG QUIET)
if(Catch2_FOUND)
    enable_testing()

    add_executable(classic-cli-tests
        tests/test_thread_pool.cpp
        tests/test_progress.cpp
        tests/test_cli_args.cpp
        # Source files under test (bridge-free only)
        src/thread_pool.cpp
        src/progress.cpp
        src/cli_args.cpp
    )

    target_include_directories(classic-cli-tests PRIVATE src/)

    target_link_libraries(classic-cli-tests PRIVATE
        Catch2::Catch2WithMain
        fmt::fmt
        CLI11::CLI11
    )

    if(MSVC)
        target_compile_options(classic-cli-tests PRIVATE /utf-8 /W4)
    endif()

    # Auto-discover TEST_CASEs and register them with CTest
    include(CTest)
    include(Catch)
    catch_discover_tests(classic-cli-tests)

    message(STATUS "Catch2 found -- unit tests enabled")
else()
    message(STATUS "Catch2 not found -- unit tests disabled (add 'catch2' to vcpkg.json)")
endif()
