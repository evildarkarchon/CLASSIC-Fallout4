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

# CMake's RC dependency scanner preprocesses resources with clang-cl and forwards
# vcpkg's rc.exe-only /c65001 switch as a compiler input path. Vcpkg also isolates
# package environments, so spell out the SDK includes that rc.exe would normally
# inherit through INCLUDE while avoiding that clang-cl 22 incompatibility.
set(_classic_rc_flags "/DWIN32")
if(DEFINED ENV{WindowsSdkDir} AND DEFINED ENV{WindowsSDKVersion})
    cmake_path(CONVERT "$ENV{WindowsSdkDir}" TO_CMAKE_PATH_LIST _classic_windows_sdk NORMALIZE)
    string(REGEX REPLACE "[/\\\\]+$" "" _classic_windows_sdk_version "$ENV{WindowsSDKVersion}")
    foreach(_classic_sdk_include IN ITEMS um shared ucrt)
        string(APPEND _classic_rc_flags
            " /I\"${_classic_windows_sdk}/Include/${_classic_windows_sdk_version}/${_classic_sdk_include}\"")
    endforeach()
endif()
if(DEFINED ENV{VCToolsInstallDir})
    cmake_path(CONVERT "$ENV{VCToolsInstallDir}" TO_CMAKE_PATH_LIST _classic_vc_tools NORMALIZE)
    string(APPEND _classic_rc_flags " /I\"${_classic_vc_tools}/include\"")
endif()
set(CMAKE_RC_FLAGS "${_classic_rc_flags}" CACHE STRING "" FORCE)
