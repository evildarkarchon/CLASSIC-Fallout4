cmake_minimum_required(VERSION 3.25)
# PROJECT_VERSION here MUST match `CLASSIC_Info.version` in
# `CLASSIC Data/databases/CLASSIC Main.yaml`. The drift guard below
# enforces that invariant so a `set_version.ps1` run that touches one
# without the other fails the build instead of shipping a binary whose
# CPack package version disagrees with the broadcast app version.
project(ClassicGui VERSION 9.1.0 LANGUAGES CXX)

# ── Linker identity guard ────────────────────────────────────────────
# Fail fast if CMake resolves a non-MSVC linker, including PATH-shadowed
# Git for Windows toolchains. See cmake/ClassicLinkerCheck.cmake.
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../cmake")
include(ClassicLinkerCheck)
classic_assert_msvc_linker()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTORCC ON)

# ── App version single-source-of-truth ──────────────────────────────
# `CLASSIC Data/databases/CLASSIC Main.yaml` is the documented source of
# truth for the application version. The CLI extracts it the same way at
# its own configure step (see `classic-cli/CMakeLists.txt`); the TUI does
# the same in `ui-applications/classic-tui/build.rs`. Sourcing the
# installed-binary version from this install-immutable bundled file —
# instead of the runtime cache-preferring `load_main_yaml_version`
# loader — guarantees a per-user YAML data update cannot move the
# broadcast version ahead of the actual installed executable, which would
# otherwise suppress real binary upgrade prompts via
# QApplication::applicationVersion(). This is the codex adversarial-review
# fix for the binary-identity bug; the runtime loader stays available for
# data/schema decisions but MUST NOT be the source of truth for the GUI's
# self-reported version.
set(_CLASSIC_MAIN_YAML "${CMAKE_SOURCE_DIR}/../CLASSIC Data/databases/CLASSIC Main.yaml")
include(ClassicAppVersion)
classic_extract_main_yaml_version("${_CLASSIC_MAIN_YAML}" CLASSIC_APP_VERSION)

# Guard: the CMake `project(VERSION ...)` (used by CPack and as the
# binary's own marker) MUST match the YAML-sourced app version. If they
# diverge silently we ship a binary whose self-reported version disagrees
# with the YAML source of truth, which is exactly the drift class the
# YAML extraction prevents.
if(NOT PROJECT_VERSION STREQUAL CLASSIC_APP_VERSION)
    message(FATAL_ERROR
        "ClassicGui CMake project(VERSION ${PROJECT_VERSION}) disagrees "
        "with CLASSIC Main.yaml CLASSIC_Info.version "
        "(${CLASSIC_APP_VERSION}). Update the `project(... VERSION ...)` "
        "line in classic-gui/CMakeLists.txt to match the YAML, or fix "
        "the YAML if the CMake value is correct.")
endif()

# ── Qt 6 ──────────────────────────────────────────────────────────────
include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/ClassicGuiQt.cmake)
classic_gui_find_qt6()

qt_standard_project_setup()

# ── Rust via Corrosion ────────────────────────────────────────────────
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
        path.rs
        web.rs
        update.rs
        message.rs
        perf.rs
        markdown.rs
)

target_include_directories(classic_cxx_bridge PUBLIC
    "${CMAKE_SOURCE_DIR}/../cpp-bindings/classic-cpp-bridge/include"
)

add_subdirectory(src)

# Enable CTest/BUILD_TESTING and register unit tests when enabled.
include(CTest)
if(BUILD_TESTING)
    add_subdirectory(tests)
endif()

# ── CPack ─────────────────────────────────────────────────────────────
# Produces a distributable ZIP archive via: cmake --build build --target package
set(CPACK_GENERATOR "ZIP")
set(CPACK_PACKAGE_NAME "CLASSIC")
set(CPACK_PACKAGE_VENDOR "CLASSIC Development Team")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "CLASSIC Crash Log Auto Scanner")
set(CPACK_PACKAGE_VERSION_MAJOR ${PROJECT_VERSION_MAJOR})
set(CPACK_PACKAGE_VERSION_MINOR ${PROJECT_VERSION_MINOR})
set(CPACK_PACKAGE_VERSION_PATCH ${PROJECT_VERSION_PATCH})
include(CPack)
