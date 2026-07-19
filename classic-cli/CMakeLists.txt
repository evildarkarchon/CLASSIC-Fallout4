cmake_minimum_required(VERSION 3.25)
project(classic-cli VERSION 9.1.0 LANGUAGES CXX)

# ── Linker identity guard ────────────────────────────────────────────
# Fail fast if CMake resolves a non-MSVC linker, including PATH-shadowed
# Git for Windows toolchains. See cmake/ClassicLinkerCheck.cmake.
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../cmake")
include(ClassicLinkerCheck)
classic_assert_msvc_linker()

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
    MANIFEST_PATH ${CMAKE_SOURCE_DIR}/../Cargo.toml
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
        runtime.rs
        registry.rs
        settings.rs
        shared.rs
        config.rs
        scanner.rs
        database.rs
        files.rs
        scangame.rs
        game.rs
        xse.rs
        version_registry.rs
        web.rs
        update.rs
        message.rs
        perf.rs
)

target_include_directories(classic_cxx_bridge PUBLIC
    "${CMAKE_SOURCE_DIR}/../cpp-bindings/classic-cpp-bridge/include"
)

# ── CLI executable ──────────────────────────────────────────────────
add_executable(classic-cli
    src/main.cpp
    src/cli_args.cpp
    src/scanner.cpp
    src/scan_run_cli.cpp
    src/progress.cpp
    src/yaml_update.cpp
    src/app_update.cpp
    src/user_settings_action.cpp
)

target_include_directories(classic-cli PRIVATE src/)

# ── App version single-source-of-truth ──────────────────────────────
# `CLASSIC Data/databases/CLASSIC Main.yaml` is the documented source of
# truth for the application version (the Qt GUI also reads CLASSIC_Info.
# version from this file at startup and feeds it to the same
# `check_app_notification` bridge entry point — see classic-gui/src/main.
# cpp). Extracting the version here at configure time keeps the CLI from
# broadcasting a stale CMake literal to the notification check.
set(_CLASSIC_MAIN_YAML "${CMAKE_SOURCE_DIR}/../CLASSIC Data/databases/CLASSIC Main.yaml")
include(ClassicAppVersion)
classic_extract_main_yaml_version("${_CLASSIC_MAIN_YAML}" CLASSIC_APP_VERSION)

# Guard: the CMake `project(VERSION ...)` (used by CPack and as the
# binary's own marker) MUST match the YAML-sourced app version. They are
# conceptually different — one stamps the CLI binary, the other is the
# application's broadcast version — but if they diverge silently we ship
# a binary whose self-reported version disagrees with the YAML source of
# truth, which is exactly the drift class the YAML extraction prevents.
if(NOT PROJECT_VERSION STREQUAL CLASSIC_APP_VERSION)
    message(FATAL_ERROR
        "classic-cli CMake project(VERSION ${PROJECT_VERSION}) disagrees "
        "with CLASSIC Main.yaml CLASSIC_Info.version "
        "(${CLASSIC_APP_VERSION}). Update the `project(... VERSION ...)` "
        "line in classic-cli/CMakeLists.txt to match the YAML, or fix "
        "the YAML if the CMake value is correct.")
endif()

# Single source of truth for the CLI's reported app version. Any C++ site
# that wants to print or transmit the installed CLI version MUST use this
# macro rather than a hardcoded literal — `app_update.cpp` consumes it
# when calling the notification bridge.
target_compile_definitions(classic-cli PRIVATE
    CLASSIC_CLI_VERSION="${CLASSIC_APP_VERSION}"
)

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
# Only built when Catch2 is available. Two test executables:
#   - classic-cli-tests: bridge-free unit tests for ThreadPool / Progress /
#     CliArgs. Fast to build, no Rust link dependency.
#   - classic-cli-bridge-tests: tests that exercise the Rust CXX bridge FFI
#     (e.g. the yaml-update-delivery entry points). Links against
#     classic_cxx_bridge.
find_package(Catch2 3 CONFIG QUIET)
if(Catch2_FOUND)
    enable_testing()

    add_executable(classic-cli-tests
        tests/test_thread_pool.cpp
        tests/test_progress.cpp
        tests/test_cli_args.cpp
        tests/test_app_update_wiring.cpp
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

    # Bridge-linked tests: one entry per FFI surface that warrants a native
    # round-trip check, proving generated declarations and DTO behavior at
    # both compile time and runtime.
    add_executable(classic-cli-bridge-tests
        tests/test_yaml_update.cpp
        tests/test_app_update.cpp
        tests/test_scan_run_contract.cpp
        tests/test_scanner.cpp
        tests/test_user_settings_action.cpp
        src/yaml_update.cpp
        src/app_update.cpp
        src/progress.cpp
        src/scan_run_cli.cpp
        src/user_settings_action.cpp
    )

    target_include_directories(classic-cli-bridge-tests PRIVATE src/)

    # CMake parses the shared JSON once so the native runner consumes the same
    # request and expected-result values without adding a runtime JSON library.
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
        "${CMAKE_SOURCE_DIR}/../tests/fixtures/crash_log_scan_run/manifest.json"
    )
    file(READ "${CMAKE_SOURCE_DIR}/../tests/fixtures/crash_log_scan_run/manifest.json"
         CLASSIC_SCAN_RUN_FIXTURE_JSON)
    function(classic_scan_run_fixture_value output)
        string(JSON value GET "${CLASSIC_SCAN_RUN_FIXTURE_JSON}" ${ARGN})
        set(${output} "${value}" PARENT_SCOPE)
    endfunction()
    classic_scan_run_fixture_value(SCAN_STANDARD_SOURCE fixtures standard expected source)
    classic_scan_run_fixture_value(SCAN_STANDARD_LOG_0 fixtures standard logs 0)
    classic_scan_run_fixture_value(SCAN_STANDARD_LOG_1 fixtures standard logs 1)
    classic_scan_run_fixture_value(SCAN_STANDARD_MAX fixtures standard maxConcurrent)
    classic_scan_run_fixture_value(SCAN_STANDARD_EFFECTIVE fixtures standard expected effectiveConcurrency)
    classic_scan_run_fixture_value(SCAN_STANDARD_ORDER_0 fixtures standard expected discoveryOrder 0)
    classic_scan_run_fixture_value(SCAN_STANDARD_ORDER_1 fixtures standard expected discoveryOrder 1)
    classic_scan_run_fixture_value(SCAN_STANDARD_DISPOSITION_0 fixtures standard expected dispositions 0)
    classic_scan_run_fixture_value(SCAN_STANDARD_DISPOSITION_1 fixtures standard expected dispositions 1)
    classic_scan_run_fixture_value(SCAN_STANDARD_ARTIFACT_SUFFIX fixtures standard expected artifactSuffix)
    classic_scan_run_fixture_value(SCAN_TARGETED_SOURCE fixtures targeted expected source)
    classic_scan_run_fixture_value(SCAN_TARGETED_INPUT_0 fixtures targeted inputs 0)
    classic_scan_run_fixture_value(SCAN_TARGETED_INPUT_1 fixtures targeted inputs 1)
    classic_scan_run_fixture_value(SCAN_TARGETED_INPUT_2 fixtures targeted inputs 2)
    classic_scan_run_fixture_value(SCAN_TARGETED_ACCEPTED_0 fixtures targeted expected acceptedLogs 0)
    classic_scan_run_fixture_value(SCAN_TARGETED_ACCEPTED_1 fixtures targeted expected acceptedLogs 1)
    classic_scan_run_fixture_value(SCAN_TARGETED_REJECTED_0 fixtures targeted expected rejectedInputs 0)
    classic_scan_run_fixture_value(SCAN_TARGETED_MAX fixtures targeted maxConcurrent)
    classic_scan_run_fixture_value(SCAN_TARGETED_EFFECTIVE fixtures targeted expected effectiveConcurrency)
    classic_scan_run_fixture_value(SCAN_TARGETED_ORDER_0 fixtures targeted expected discoveryOrder 0)
    classic_scan_run_fixture_value(SCAN_TARGETED_ORDER_1 fixtures targeted expected discoveryOrder 1)
    classic_scan_run_fixture_value(SCAN_TARGETED_DISPOSITION_0 fixtures targeted expected dispositions 0)
    classic_scan_run_fixture_value(SCAN_TARGETED_DISPOSITION_1 fixtures targeted expected dispositions 1)
    classic_scan_run_fixture_value(SCAN_TARGETED_ARTIFACT_SUFFIX fixtures targeted expected artifactSuffix)
    string(JSON SCAN_TARGETED_UNSOLVED_COUNT LENGTH
           "${CLASSIC_SCAN_RUN_FIXTURE_JSON}" fixtures targeted expected unsolvedLogsArtifacts)
    classic_scan_run_fixture_value(SCAN_INSTALLED_YAML_INPUT fixtures installedYamlData input)
    classic_scan_run_fixture_value(SCAN_MALFORMED_LOCAL_IGNORE fixtures installedYamlData malformedLocalIgnore)
    configure_file(
        tests/scan_run_fixture_config.h.in
        "${CMAKE_CURRENT_BINARY_DIR}/generated/scan_run_fixture_config.h"
        @ONLY
    )
    target_include_directories(classic-cli-bridge-tests PRIVATE
        "${CMAKE_CURRENT_BINARY_DIR}/generated"
    )

    target_link_libraries(classic-cli-bridge-tests PRIVATE
        Catch2::Catch2WithMain
        fmt::fmt
        classic_cxx_bridge
    )

    # The sentinel is intentionally invalid: the disabled-policy test proves
    # User Settings short-circuit before installed-version validation or I/O.
    target_compile_definitions(classic-cli-bridge-tests PRIVATE
        CLASSIC_CLI_VERSION="not-a-version"
        CLASSIC_REPO_ROOT="${CMAKE_SOURCE_DIR}/.."
    )

    if(MSVC)
        target_compile_options(classic-cli-bridge-tests PRIVATE /utf-8 /W4)
    endif()

    catch_discover_tests(classic-cli-bridge-tests)

    message(STATUS "Catch2 found -- unit tests enabled")
else()
    message(STATUS "Catch2 not found -- unit tests disabled (add 'catch2' to vcpkg.json)")
endif()
