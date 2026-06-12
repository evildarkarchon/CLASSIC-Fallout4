if(NOT DEFINED CLASSIC_LINKER_CHECK_MODULE OR NOT EXISTS "${CLASSIC_LINKER_CHECK_MODULE}")
    message(FATAL_ERROR
        "CLASSIC_LINKER_CHECK_MODULE must point to cmake/ClassicLinkerCheck.cmake.")
endif()

if(NOT DEFINED CLASSIC_EXPECTED_LINKER OR NOT EXISTS "${CLASSIC_EXPECTED_LINKER}")
    message(FATAL_ERROR
        "CLASSIC_EXPECTED_LINKER must point to a valid MSVC link.exe.")
endif()

if(NOT DEFINED CLASSIC_SELECTED_LINKER)
    set(CLASSIC_SELECTED_LINKER "${CLASSIC_EXPECTED_LINKER}")
endif()

if(NOT EXISTS "${CLASSIC_SELECTED_LINKER}")
    message(FATAL_ERROR
        "CLASSIC_SELECTED_LINKER must point to an existing linker executable.")
endif()

if(NOT DEFINED CLASSIC_SHADOW_LINKER_DIR OR
        NOT EXISTS "${CLASSIC_SHADOW_LINKER_DIR}/link.exe")
    message(FATAL_ERROR
        "CLASSIC_SHADOW_LINKER_DIR must contain a shadowing link.exe.")
endif()

if(NOT DEFINED CLASSIC_COMPILER_ID)
    set(CLASSIC_COMPILER_ID "MSVC")
endif()

set(WIN32 TRUE)
set(CMAKE_CXX_COMPILER_ID "${CLASSIC_COMPILER_ID}")
if(DEFINED CLASSIC_COMPILER_SIMULATE_ID)
    set(CMAKE_CXX_SIMULATE_ID "${CLASSIC_COMPILER_SIMULATE_ID}")
endif()
set(CMAKE_LINKER "${CLASSIC_SELECTED_LINKER}")

set(_classic_saved_path "$ENV{PATH}")
set(ENV{PATH} "${CLASSIC_SHADOW_LINKER_DIR};${_classic_saved_path}")

include("${CLASSIC_LINKER_CHECK_MODULE}")
classic_assert_msvc_linker()

set(ENV{PATH} "${_classic_saved_path}")
