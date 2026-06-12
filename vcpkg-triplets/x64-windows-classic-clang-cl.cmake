# clang-cl builds should use clang-cl and lld-link for vcpkg packages too.
set(VCPKG_TARGET_ARCHITECTURE x64)
set(VCPKG_CRT_LINKAGE dynamic)
set(VCPKG_LIBRARY_LINKAGE dynamic)
# vcpkg isolates Windows package builds; pass through explicit wrapper-validated
# tool paths instead of the whole PATH to avoid picking up unrelated tools.
# The Windows SDK version changes SDK-provided import-library packages such as
# opengl, so keep it in the ABI while leaving the installation root untracked.
set(VCPKG_ENV_PASSTHROUGH CLASSIC_CLANG_CL CLASSIC_LLD_LINK CLASSIC_RC WindowsSDKVersion)
set(VCPKG_ENV_PASSTHROUGH_UNTRACKED CLASSIC_DUMPBIN WindowsSdkDir)
# vcpkg_copy_pdbs invokes dumpbin by name after the portfile runs; expose only
# the validated Visual Studio tool directory instead of passing the full PATH.
if(DEFINED ENV{CLASSIC_DUMPBIN} AND NOT "$ENV{CLASSIC_DUMPBIN}" STREQUAL "")
    cmake_path(CONVERT "$ENV{CLASSIC_DUMPBIN}" TO_CMAKE_PATH_LIST CLASSIC_VCPKG_DUMPBIN NORMALIZE)
    cmake_path(GET CLASSIC_VCPKG_DUMPBIN PARENT_PATH CLASSIC_VCPKG_DUMPBIN_DIR)
    set(ENV{PATH} "${CLASSIC_VCPKG_DUMPBIN_DIR};$ENV{PATH}")
endif()
set(VCPKG_CHAINLOAD_TOOLCHAIN_FILE "${CMAKE_CURRENT_LIST_DIR}/../cmake/toolchains/vcpkg-clang-cl.cmake")
set(VCPKG_HASH_ADDITIONAL_FILES "${VCPKG_CHAINLOAD_TOOLCHAIN_FILE}")
