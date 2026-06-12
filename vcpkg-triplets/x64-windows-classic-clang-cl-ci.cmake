include("${CMAKE_CURRENT_LIST_DIR}/x64-windows-classic-clang-cl.cmake")

# GUI CI Release jobs do not need vcpkg's default debug dependency tree.
set(VCPKG_BUILD_TYPE release)
