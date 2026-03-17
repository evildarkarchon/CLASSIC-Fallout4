option(CLASSIC_GUI_ALLOW_SYSTEM_QT_FALLBACK
    "Allow a non-vcpkg Qt installation if vcpkg Qt is not being used"
    OFF)

function(_classic_gui_normalize_path input_path output_var)
    if("${input_path}" STREQUAL "")
        set(${output_var} "" PARENT_SCOPE)
        return()
    endif()

    if(EXISTS "${input_path}")
        file(REAL_PATH "${input_path}" _classic_gui_resolved_path)
    else()
        set(_classic_gui_resolved_path "${input_path}")
    endif()

    file(TO_CMAKE_PATH "${_classic_gui_resolved_path}" _classic_gui_resolved_path)
    string(TOLOWER "${_classic_gui_resolved_path}" _classic_gui_resolved_path)
    set(${output_var} "${_classic_gui_resolved_path}" PARENT_SCOPE)
endfunction()

macro(classic_gui_find_qt6)
    set(_classic_gui_vcpkg_installed_dirs "")
    if(DEFINED VCPKG_INSTALLED_DIR AND EXISTS "${VCPKG_INSTALLED_DIR}")
        list(APPEND _classic_gui_vcpkg_installed_dirs "${VCPKG_INSTALLED_DIR}")
    endif()
    if(DEFINED ENV{VCPKG_ROOT} AND EXISTS "$ENV{VCPKG_ROOT}/installed")
        list(APPEND _classic_gui_vcpkg_installed_dirs "$ENV{VCPKG_ROOT}/installed")
    endif()
    if(DEFINED CMAKE_TOOLCHAIN_FILE AND EXISTS "${CMAKE_TOOLCHAIN_FILE}")
        get_filename_component(_classic_gui_toolchain_dir "${CMAKE_TOOLCHAIN_FILE}" DIRECTORY)
        get_filename_component(_classic_gui_vcpkg_scripts_dir "${_classic_gui_toolchain_dir}" DIRECTORY)
        get_filename_component(_classic_gui_vcpkg_root "${_classic_gui_vcpkg_scripts_dir}" DIRECTORY)
        if(EXISTS "${_classic_gui_vcpkg_root}/installed")
            list(APPEND _classic_gui_vcpkg_installed_dirs "${_classic_gui_vcpkg_root}/installed")
        endif()
    endif()
    list(REMOVE_DUPLICATES _classic_gui_vcpkg_installed_dirs)

    find_package(Qt6 QUIET COMPONENTS Core Widgets Network)

    if(NOT Qt6_FOUND)
        if(CLASSIC_GUI_ALLOW_SYSTEM_QT_FALLBACK)
            message(FATAL_ERROR
                "Qt6 was not found. Install Qt through vcpkg for the default workflow, or "
                "set CMAKE_PREFIX_PATH/Qt6_DIR to a system Qt when using "
                "CLASSIC_GUI_ALLOW_SYSTEM_QT_FALLBACK=ON.")
        else()
            message(FATAL_ERROR
                "Qt6 was not found from the vcpkg-first configuration. Install Qt with vcpkg "
                "and configure with the default preset, or explicitly enable "
                "CLASSIC_GUI_ALLOW_SYSTEM_QT_FALLBACK=ON to allow a non-vcpkg Qt install.")
        endif()
    endif()

    _classic_gui_normalize_path("${Qt6_DIR}" _classic_gui_qt_dir_normalized)
    set(_classic_gui_qt_from_vcpkg FALSE)
    foreach(_classic_gui_vcpkg_installed_dir IN LISTS _classic_gui_vcpkg_installed_dirs)
        _classic_gui_normalize_path("${_classic_gui_vcpkg_installed_dir}" _classic_gui_vcpkg_installed_dir_normalized)
        if(NOT _classic_gui_vcpkg_installed_dir_normalized STREQUAL "")
            string(FIND
                "${_classic_gui_qt_dir_normalized}"
                "${_classic_gui_vcpkg_installed_dir_normalized}/"
                _classic_gui_vcpkg_prefix_index)
            if(_classic_gui_vcpkg_prefix_index EQUAL 0)
                set(_classic_gui_qt_from_vcpkg TRUE)
                break()
            endif()
        endif()
    endforeach()

    if(_classic_gui_qt_from_vcpkg)
        message(STATUS "Using vcpkg Qt from ${Qt6_DIR}")
    elseif(CLASSIC_GUI_ALLOW_SYSTEM_QT_FALLBACK)
        message(WARNING
            "Using non-vcpkg Qt from ${Qt6_DIR}. This fallback is enabled by "
            "CLASSIC_GUI_ALLOW_SYSTEM_QT_FALLBACK=ON.")
    else()
        message(FATAL_ERROR
            "Resolved Qt6 from a non-vcpkg path: ${Qt6_DIR}. CLASSIC GUI requires vcpkg Qt by "
            "default. Install Qt with vcpkg and use the default preset, or explicitly enable "
            "CLASSIC_GUI_ALLOW_SYSTEM_QT_FALLBACK=ON to allow a system Qt fallback.")
    endif()
endmacro()
