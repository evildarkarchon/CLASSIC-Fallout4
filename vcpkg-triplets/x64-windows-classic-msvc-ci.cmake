# GUI MSVC CI builds Release binaries, so keep vcpkg dependency builds release-only.
# The default x64-windows triplet also builds a debug Qt tree that CI does not use.
set(VCPKG_TARGET_ARCHITECTURE x64)
set(VCPKG_CRT_LINKAGE dynamic)
set(VCPKG_LIBRARY_LINKAGE dynamic)
set(VCPKG_BUILD_TYPE release)
