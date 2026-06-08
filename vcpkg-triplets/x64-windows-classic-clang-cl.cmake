# clang-cl builds should use clang-cl and lld-link for vcpkg packages too.
set(VCPKG_TARGET_ARCHITECTURE x64)
set(VCPKG_CRT_LINKAGE dynamic)
set(VCPKG_LIBRARY_LINKAGE dynamic)
# vcpkg isolates Windows package builds; pass through explicit wrapper-validated
# tool paths instead of the whole PATH to avoid picking up unrelated tools.
set(VCPKG_ENV_PASSTHROUGH CLASSIC_CLANG_CL CLASSIC_LLD_LINK CLASSIC_RC)
set(VCPKG_CHAINLOAD_TOOLCHAIN_FILE "${CMAKE_CURRENT_LIST_DIR}/../cmake/toolchains/vcpkg-clang-cl.cmake")
set(VCPKG_HASH_ADDITIONAL_FILES "${VCPKG_CHAINLOAD_TOOLCHAIN_FILE}")
