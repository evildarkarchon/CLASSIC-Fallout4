cmake_minimum_required(VERSION 3.25)
project(ClassicGui VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTORCC ON)

# ── Qt 6 ──────────────────────────────────────────────────────────────
find_package(Qt6 REQUIRED COMPONENTS Widgets Network)

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
        runtime.rs
        registry.rs
        yaml.rs
        config.rs
        scanner.rs
        database.rs
        files.rs
        scangame.rs
        game.rs
        path.rs
        update.rs
        message.rs
        perf.rs
        markdown.rs
)

target_include_directories(classic_cxx_bridge PUBLIC
    "${CMAKE_SOURCE_DIR}/../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include"
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
