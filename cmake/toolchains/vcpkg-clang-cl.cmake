# Set clang-cl before vcpkg's Windows toolchain derives compiler-sensitive flags.
if(DEFINED ENV{CLASSIC_CLANG_CL})
    set(CLASSIC_VCPKG_CLANG_CL "$ENV{CLASSIC_CLANG_CL}")
else()
    find_program(CLASSIC_VCPKG_CLANG_CL clang-cl REQUIRED)
endif()

if(DEFINED ENV{CLASSIC_LLD_LINK})
    set(CLASSIC_VCPKG_LLD_LINK "$ENV{CLASSIC_LLD_LINK}")
else()
    find_program(CLASSIC_VCPKG_LLD_LINK lld-link REQUIRED)
endif()

if(DEFINED ENV{CLASSIC_RC})
    set(CLASSIC_VCPKG_RC "$ENV{CLASSIC_RC}")
else()
    find_program(CLASSIC_VCPKG_RC rc REQUIRED)
endif()

if(DEFINED Z_VCPKG_ROOT_DIR)
    set(_classic_vcpkg_root "${Z_VCPKG_ROOT_DIR}")
elseif(DEFINED _VCPKG_ROOT_DIR)
    set(_classic_vcpkg_root "${_VCPKG_ROOT_DIR}")
elseif(DEFINED ENV{VCPKG_ROOT})
    set(_classic_vcpkg_root "$ENV{VCPKG_ROOT}")
else()
    message(FATAL_ERROR "Could not resolve the vcpkg root for the clang-cl chainloaded toolchain.")
endif()

set(CMAKE_C_COMPILER "${CLASSIC_VCPKG_CLANG_CL}" CACHE FILEPATH "")
set(CMAKE_CXX_COMPILER "${CLASSIC_VCPKG_CLANG_CL}" CACHE FILEPATH "")
set(CMAKE_LINKER "${CLASSIC_VCPKG_LLD_LINK}" CACHE FILEPATH "")
# vcpkg configures package builds in an isolated environment, so CMake's
# manifest link step needs an absolute resource compiler path instead of rc.
set(CMAKE_RC_COMPILER "${CLASSIC_VCPKG_RC}" CACHE FILEPATH "")

include("${_classic_vcpkg_root}/scripts/toolchains/windows.cmake")
