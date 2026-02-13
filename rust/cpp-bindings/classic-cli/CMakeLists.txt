cmake_minimum_required(VERSION 3.25)
project(classic-cli VERSION 9.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# ── vcpkg dependencies ──────────────────────────────────────────────
find_package(fmt CONFIG REQUIRED)
find_package(CLI11 CONFIG REQUIRED)

# ── Locate Rust build output ────────────────────────────────────────
# The CXX bridge generates headers and a compiled bridge lib in
# target/{profile}/build/classic-cpp-bridge-*/out/
# We glob for it since the hash suffix changes per build.

set(RUST_TARGET_DIR "${CMAKE_SOURCE_DIR}/../../target")

# Auto-detect which Rust profile was built.
# MSVC uses multi-config generators where CMAKE_BUILD_TYPE is ignored at
# configure time, so we probe for whichever profile directory exists.
# Prefer release, fall back to debug.
file(GLOB CXX_BRIDGE_RELEASE "${RUST_TARGET_DIR}/release/build/classic-cpp-bridge-*/out")
file(GLOB CXX_BRIDGE_DEBUG   "${RUST_TARGET_DIR}/debug/build/classic-cpp-bridge-*/out")

list(LENGTH CXX_BRIDGE_RELEASE RELEASE_COUNT)
list(LENGTH CXX_BRIDGE_DEBUG DEBUG_COUNT)

if(RELEASE_COUNT GREATER 0)
    set(RUST_PROFILE "release")
    set(CXX_BRIDGE_OUT_DIRS ${CXX_BRIDGE_RELEASE})
elseif(DEBUG_COUNT GREATER 0)
    set(RUST_PROFILE "debug")
    set(CXX_BRIDGE_OUT_DIRS ${CXX_BRIDGE_DEBUG})
else()
    message(FATAL_ERROR
        "Could not find CXX bridge output directory.\n"
        "Run 'cargo build -p classic-cpp-bridge' first.\n"
        "Searched: ${RUST_TARGET_DIR}/{debug,release}/build/classic-cpp-bridge-*/out")
endif()

# Use the last match (most recent build)
list(GET CXX_BRIDGE_OUT_DIRS -1 CXX_BRIDGE_OUT)
message(STATUS "Rust profile: ${RUST_PROFILE}")
message(STATUS "CXX bridge output: ${CXX_BRIDGE_OUT}")

# CXX headers live under out/cxxbridge/include/:
#   rust/cxx.h                              (CXX runtime header)
#   classic-cpp-bridge/src/scanner.rs.h     (per-module bridge headers)
set(CXX_INCLUDE_DIR "${CXX_BRIDGE_OUT}/cxxbridge/include")

# ── Rust static libraries ──────────────────────────────────────────
# The staticlib produced by classic-cpp-bridge
find_library(RUST_BRIDGE_LIB
    NAMES classic_cpp_bridge
    PATHS "${RUST_TARGET_DIR}/${RUST_PROFILE}"
    NO_DEFAULT_PATH
)
if(NOT RUST_BRIDGE_LIB)
    message(FATAL_ERROR
        "Could not find classic_cpp_bridge.lib\n"
        "Run 'cargo build -p classic-cpp-bridge' first.\n"
        "Searched: ${RUST_TARGET_DIR}/${RUST_PROFILE}")
endif()
message(STATUS "Rust bridge lib: ${RUST_BRIDGE_LIB}")

# The CXX-generated C++ bridge object files are compiled into a static lib
# by cxx-build and placed in the out/ directory
find_library(CXX_COMPILED_LIB
    NAMES classic-cpp-bridge
    PATHS "${CXX_BRIDGE_OUT}"
    NO_DEFAULT_PATH
)
if(NOT CXX_COMPILED_LIB)
    message(STATUS "CXX compiled bridge lib not found as separate lib (may be linked into staticlib)")
    set(CXX_COMPILED_LIB "")
endif()

# ── CLI executable ──────────────────────────────────────────────────
add_executable(classic-cli
    src/main.cpp
    src/cli_args.cpp
    src/scanner.cpp
    src/progress.cpp
    src/thread_pool.cpp
    src/report_writer.cpp
)

target_include_directories(classic-cli PRIVATE
    ${CXX_INCLUDE_DIR}
    src/
)

target_link_libraries(classic-cli PRIVATE
    fmt::fmt
    CLI11::CLI11
    ${RUST_BRIDGE_LIB}
)

# Link CXX compiled bridge lib if found separately
if(CXX_COMPILED_LIB)
    target_link_libraries(classic-cli PRIVATE ${CXX_COMPILED_LIB})
endif()

# ── Windows system libraries required by Rust ───────────────────────
if(WIN32)
    target_link_libraries(classic-cli PRIVATE
        ws2_32
        bcrypt
        userenv
        ntdll
        advapi32
        crypt32
        secur32
        ncrypt
        shell32
        ole32
        synchronization
    )
endif()

# ── MSVC-specific flags ─────────────────────────────────────────────
if(MSVC)
    target_compile_options(classic-cli PRIVATE /utf-8 /W4)

    # NOTE: Always build with --config Release (or via build_cli.ps1).
    # cxx-build compiles C++ glue with /MD (release CRT) regardless of
    # Rust profile, so Debug builds cause LNK2038 CRT mismatches.
endif()

# ── Install ─────────────────────────────────────────────────────────
install(TARGETS classic-cli RUNTIME DESTINATION bin)

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
